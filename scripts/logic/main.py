from .config import MISSION_TYPE_MAPPING, DEVICE_CONNECTION_TIMEOUT
from .mission.manual_input.handler import Manual_Input_Mission_Handler
from .mission.auto_input.handler import Auto_Input_Mission_Handler
from .mission.manual_output.handler import Manual_Output_Mission_Handler
from .mission.auto_output.handler import Auto_Output_Mission_Handler
from .mission.pwm_output.handler import PWM_Output_Mission_Handler
from .mission.model import Mission_Handler
from common import Device_Information, GOODS_SECTOR, AUTO_LINE_BUTTON
from database.com import Database_Interface
from database.model.mission import Mission_Model, MISSION_MODEL_TYPE
from database.model.mission_trigger import (
    MISSION_TRIGGER_CREATOR, Mission_Trigger_Model,
    MISSION_TRIGGER_CREATOR_NAME, MISSION_TRIGGER_ACTION
)
from database.model.pwm import PWM_PALLET_STATUS, PWM_WRAP_STATUS, PWM_MACHINE_STATUS
from database.model.auto_line import AUTO_LINE_MODEL_STATUS
from database.model.curtain import Curtain_Status_Model, CURTAIN_STATUS, CURTAIN_LOCATION
from database.model.pause_list import PAUSE_DEFAULT_METHOD
from signal_emit.com import Signal_Handle
from signal_emit.config import SIGNAL_CHANNEL
from signal_emit.model import AIS_States_Signal, RCS_Notify_Signal
from interface.wcs.com import WCS_Interface
from interface.wcs.config import WCS_MISSION_STATUS, WCS_LOCATION
from interface.rcs.com import RCS_Interface
from interface.rcs.config import RCS_LOCATION
from interface.gateway.com import Gateway_Interface
from interface.gateway.config import GATEWAY_CONFIG, GATEWAY_AUTO_LINE
from interface.ais.com import AIS_Interface
from common import MODULE_NAME

from rostek_utils.utils.thread import Worker
from rostek_utils.utils.logger import Logger
from typing import Dict
from time import sleep, time
from threading import Lock
from collections import deque

AIS_COMMAND_RETRY_INTERVAL = 2
AIS_COMMAND_IDLE_SLEEP = 0.5

class Main_Logic:
    """
    Handle working flow

    Initialize:
    - __clearMission: Clear all missions
    - __handleSignal: Setup callback for signal
    
    Thread:
    - checkMissionTrigger: Check mission trigger
    - checkPWMStatus: Check PWM status
    - checkAutoLineStatus: Check auto line status
    - checkAISConnection: Pause all robot if AIS not connected

    Callback:
    - __onUpdateAgv: Handle agv code feedback from RCS
    - __onMissionFeedback: Handle mission feedback from RCS
    - __onAISTrigger: AIS command
    """
    def __init__(self, wcs: WCS_Interface, rcs: RCS_Interface, gateway: Gateway_Interface, ais: AIS_Interface):
        self.__wcs = wcs
        self.__rcs = rcs
        self.__gw = gateway
        self.__ais = ais
        self.__logger = Logger(MODULE_NAME.LOGIC)

        self.__db = Database_Interface()
        self.__handlers: Dict[str, Mission_Handler] = {}
        self.__auto_line_latch = {
            MISSION_TRIGGER_CREATOR.AUTO_LINE_1: False,
            MISSION_TRIGGER_CREATOR.AUTO_LINE_2: False,
            MISSION_TRIGGER_CREATOR.AUTO_LINE_PALLET: False
        }

        self.__pwm_bypass = False
        self.__spec_robot_list = ["1645", "1646", "1647"]
        self.__spec_robot_id = 0
        self.__ais_command_lock = Lock()
        self.__ais_command_queue = deque()
        self.__ais_command_seq = 0
        self.__ais_latest_commands = {}

        self.__clearMission()
        self.__clearPause()
        self.__processAISCommandQueue()
        self.__handleSignal()
        self.checkAISConnection()
        self.__serviceLoop()

    def __clearMission(self):
        """
        Remove all mission in Database and Backend
        """
        self.__db.removeMissions()

        wcs_missions = self.__wcs.getMissions(status=[
            WCS_MISSION_STATUS.SIGN,
            WCS_MISSION_STATUS.PENDING,
            WCS_MISSION_STATUS.PROCESS
        ])
        for mission in wcs_missions:
            self.__wcs.updateMissionStatus(
                mission, WCS_MISSION_STATUS.CANCEL)
    
    def __clearPause(self):
        """
        Clear pause information, unblock in RCS if necessary
        """
        data = self.__db.getPauseList()
        for robot_code in data:
            if data[robot_code] and data[robot_code].method != PAUSE_DEFAULT_METHOD:
                self.__rcs.setBlockArea(data[robot_code].method, False)
        self.__db.removePause()

    def __handleSignal(self):
        """
        Handle triggers from interfaces
        - RCS feedback
        - AIS pause/resume command
        """
        s = Signal_Handle()
        s.subscribe(SIGNAL_CHANNEL.AIS_AGV_STATES, self.__onAISTrigger)
        s.subscribe(SIGNAL_CHANNEL.RCS_UPDATE_AGV, self.__onUpdateAgv)
        s.subscribe(SIGNAL_CHANNEL.MANUAL_INPUT_FEEDBACK, self.__onMissionFeedback)
        s.subscribe(SIGNAL_CHANNEL.AUTO_INPUT_FEEDBACK, self.__onMissionFeedback)
        s.subscribe(SIGNAL_CHANNEL.MANUAL_OUTPUT_FEEDBACK, self.__onMissionFeedback)
        s.subscribe(SIGNAL_CHANNEL.AUTO_OUTPUT_FEEDBACK, self.__onMissionFeedback)
        s.subscribe(SIGNAL_CHANNEL.PWM_OUTPUT_FEEDBACK, self.__onMissionFeedback)
        s.subscribe(SIGNAL_CHANNEL.RCS_CANCEL_MISSION, self.__onMissionFeedback)
    
    def __onAISTrigger(self, state: AIS_States_Signal):
        """
        Queue AIS pause/resume robot command
        """
        self.__logger.info(f"AIS TRIGGER RECEIVE: pause={state.pause}, normal={state.normal}")

        robot_datas = self.__rcs.queryAgvStatus() if state.pause else {}

        for robot_code in state.pause:
            pause_method = robot_datas.get(robot_code) or PAUSE_DEFAULT_METHOD
            self.__enqueueAISCommand(robot_code, "pause", pause_method)

        for robot_code in state.normal:
            self.__enqueueAISCommand(robot_code, "resume")

    def __enqueueAISCommand(self, robot_code: str, action: str, method: str = None):
        """
        Save the latest AIS desired action for a robot and queue it for sequential processing.
        """
        with self.__ais_command_lock:
            previous = self.__ais_latest_commands.get(robot_code)
            if action == "resume" and method is None and previous:
                previous_method = previous.get("method")
                if previous.get("action") == "pause" and previous_method != PAUSE_DEFAULT_METHOD:
                    method = previous_method

            self.__ais_command_seq += 1
            command = {
                "seq": self.__ais_command_seq,
                "robot_code": robot_code,
                "action": action,
                "method": method,
                "attempt": 0,
                "next_retry_at": time()
            }
            self.__ais_latest_commands[robot_code] = command
            self.__ais_command_queue.append(command)

        self.__logger.info(f"AIS COMMAND ENQUEUE: {command}")

    def __isLatestAISCommand(self, command: Dict):
        with self.__ais_command_lock:
            latest = self.__ais_latest_commands.get(command["robot_code"])
            return latest and latest["seq"] == command["seq"]

    def __clearLatestAISCommand(self, command: Dict):
        with self.__ais_command_lock:
            latest = self.__ais_latest_commands.get(command["robot_code"])
            if latest and latest["seq"] == command["seq"]:
                self.__ais_latest_commands.pop(command["robot_code"])

    def __popAISCommand(self):
        with self.__ais_command_lock:
            if not self.__ais_command_queue:
                return None
            return self.__ais_command_queue.popleft()

    def __requeueAISCommand(self, command: Dict):
        with self.__ais_command_lock:
            self.__ais_command_queue.append(command)

    @Worker.employ
    def __processAISCommandQueue(self):
        """
        Process AIS commands sequentially and retry failed RCS requests.
        """
        while True:
            command = self.__popAISCommand()
            if not command:
                sleep(AIS_COMMAND_IDLE_SLEEP)
                continue

            retry_delay = command["next_retry_at"] - time()
            if retry_delay > 0:
                self.__requeueAISCommand(command)
                sleep(min(retry_delay, AIS_COMMAND_IDLE_SLEEP))
                continue

            if not self.__isLatestAISCommand(command):
                self.__logger.info(f"SKIP OLD AIS COMMAND: {command}")
                continue

            try:
                if command["action"] == "pause":
                    success = self.__handleAISPauseCommand(command)
                elif command["action"] == "resume":
                    success = self.__handleAISResumeCommand(command)
                else:
                    self.__logger.warn(f"WRONG AIS COMMAND ACTION: {command}")
                    success = True
            except Exception as e:
                self.__logger.error(f"AIS COMMAND HANDLE ERROR: {command}, error={e}")
                success = False

            if success:
                self.__clearLatestAISCommand(command)
                self.__logger.info(f"AIS COMMAND DONE: {command}")
                continue

            if not self.__isLatestAISCommand(command):
                self.__logger.info(f"AIS COMMAND REPLACED, STOP RETRY: {command}")
                continue

            command["attempt"] += 1
            command["next_retry_at"] = time() + AIS_COMMAND_RETRY_INTERVAL
            self.__logger.warn(f"AIS COMMAND RETRY: {command}")
            self.__requeueAISCommand(command)

    def __handleAISPauseCommand(self, command: Dict):
        robot_code = command["robot_code"]
        pause_method = command["method"] or PAUSE_DEFAULT_METHOD

        pause_data = self.__db.getPauseList(robot_code).get(robot_code)
        if pause_data:
            self.__logger.info(f"PAUSE ALREADY PAUSED: {robot_code}, {pause_data.method}")
            return True

        if pause_method != PAUSE_DEFAULT_METHOD:
            self.__logger.info(f"PAUSE BY BLOCK: {robot_code}, {pause_method}")
            block_result = self.__rcs.setBlockArea(pause_method, True)
            self.__logger.info(f"PAUSE BLOCK RESULT: {robot_code}, {pause_method}, success={block_result}")
        else:
            self.__logger.info(f"PAUSE BY PAUSE: {robot_code}")

        if not self.__rcs.pauseRobot(robot_code):
            self.__logger.warn(
                f"PAUSE FAILED, KEEP QUEUE RETRY: {robot_code}, method={pause_method}"
            )
            return False

        self.__db.updatePause(robot_code, pause_method)
        return True

    def __handleAISResumeCommand(self, command: Dict):
        robot_code = command["robot_code"]
        pause_data = self.__db.getPauseList(robot_code).get(robot_code)
        pause_method = pause_data.method if pause_data else command.get("method")

        if pause_method == PAUSE_DEFAULT_METHOD:
            self.__logger.info(f"RESUME ON PAUSE: {robot_code}")
        elif pause_method:
            self.__logger.info(f"RESUME ON BLOCK: {robot_code}, {pause_method}")
        else:
            self.__logger.info(f"RESUME NOT PAUSE: {robot_code}")

        if not self.__rcs.resumeRobot(robot_code):
            self.__logger.warn(
                f"RESUME FAILED, KEEP QUEUE RETRY: {robot_code}, method={pause_method}"
            )
            return False

        if pause_method and pause_method != PAUSE_DEFAULT_METHOD:
            unblock_result = self.__rcs.setBlockArea(pause_method, False)
            self.__logger.info(f"RESUME UNBLOCK RESULT: {robot_code}, {pause_method}, success={unblock_result}")

        if pause_data:
            self.__removePauseIfMatch(robot_code, pause_method)

        return True
    
    def __removePauseIfMatch(self, robot_code: str, pause_method: str):
        """
        Remove pause data only if it was not replaced by a newer AIS event.
        """
        current_pause = self.__db.getPauseList(robot_code).get(robot_code)
        if current_pause and current_pause.method == pause_method:
            self.__db.removePause(robot_code)
        else:
            current_method = current_pause.method if current_pause else None
            self.__logger.info(f"SKIP REMOVE PAUSE, DATA CHANGED: {robot_code}, old={pause_method}, current={current_method}")
    
    def __onUpdateAgv(self, signal: RCS_Notify_Signal):
        """
        Handle agv code feedback from RCS
        """
        code = signal.mission_code
        if code in self.__handlers:
            Logger(MODULE_NAME.RCS).info(f"Feedback to mission {code}: agv={signal.agv_code}, flag={signal.flag}")
            self.__handlers[code].setAgv(signal.agv_code)
    
    def __onMissionFeedback(self, signal: RCS_Notify_Signal):
        """
        Handle mission feedback from RCS
        """
        code = signal.mission_code
        if code in self.__handlers:
            Logger(MODULE_NAME.RCS).info(f"Feedback to mission {code}: agv={signal.agv_code}, flag={signal.flag}")
            self.__handlers[code].setAgv(signal.agv_code)
            self.__handlers[code].setFlag(signal.flag)
    
    @Worker.employ
    def checkAISConnection(self):
        """
        Pause all robot if AIS not connected
        """
        ais_connected = True
        while True:
            check_connection = self.__ais.connected()
            if ais_connected == check_connection:
                sleep(0.5)
                continue

            state = AIS_States_Signal()
            if check_connection:
                state.normal = ["1645", "1646", "1647"]
            else:
                state.pause = ["1645", "1646", "1647"]
            Logger(MODULE_NAME.LOGIC).info(
                f"AIS CONNECTION CHANGE: connected={check_connection}"
            )
            self.__onAISTrigger(state)
            ais_connected = check_connection
            sleep(0.5)
    
    @Worker.employ
    def __serviceLoop(self):
        """
        Run all service
        """
        while True:
            try:
                while self.checkMissionTrigger():
                    pass
                self.checkPWMStatus()
                self.checkAutoLineStatus()
            except Exception as e:
                self.__logger.error(f"Service error: {e}")
            sleep(1)
    
    def __createMission(self, trigger: Mission_Trigger_Model, agv_code: str = ""):
        """
        Create mission from trigger
        - Generate mission on Backend
        - Map type of mission, initialize default value of rcs_code
        """
        mission = self.__wcs.getMission(trigger)
        if not mission:
            return False
        
        mission = self.__mapMissionInfo(mission)
        mission.agv_code = agv_code
        self.__logger.info(f"Create mission: {trigger.items()}\n-> {mission.items()}")
        return self.__createMissionHandler(mission)
    
    def __mapMissionInfo(self, mission: Mission_Model):
        """
        Check mission type.
        
        check:
            pickup_location
            return_location
        return:
            type
        """
        if mission.sector == GOODS_SECTOR.EMPTY:
            manual_mapping = {
                WCS_LOCATION.MANUAL_1: MISSION_MODEL_TYPE.MANUAL_PALLET_1,
                WCS_LOCATION.MANUAL_2: MISSION_MODEL_TYPE.MANUAL_PALLET_2,
                WCS_LOCATION.MANUAL_3: MISSION_MODEL_TYPE.MANUAL_PALLET_3,
                WCS_LOCATION.MANUAL_4: MISSION_MODEL_TYPE.MANUAL_PALLET_4,
                WCS_LOCATION.MANUAL_5: MISSION_MODEL_TYPE.MANUAL_PALLET_5
            }
            if mission.return_location in manual_mapping:
                mission.type = manual_mapping[mission.return_location]
                return mission
            
            if mission.return_location == WCS_LOCATION.AUTO_PALLET:
                mission.type = MISSION_MODEL_TYPE.AUTO_PALLET
                return mission
            
        elif mission.sector == GOODS_SECTOR.CARTON:
            manual_mapping = {
                WCS_LOCATION.MANUAL_1: MISSION_MODEL_TYPE.MANUAL_CARTON_1,
                WCS_LOCATION.MANUAL_2: MISSION_MODEL_TYPE.MANUAL_CARTON_2,
                WCS_LOCATION.MANUAL_3: MISSION_MODEL_TYPE.MANUAL_CARTON_3,
                WCS_LOCATION.MANUAL_4: MISSION_MODEL_TYPE.MANUAL_CARTON_4,
                WCS_LOCATION.MANUAL_5: MISSION_MODEL_TYPE.MANUAL_CARTON_5
            }
            if mission.return_location in manual_mapping:
                mission.type = manual_mapping[mission.return_location]
                return mission
            
        elif mission.sector in [GOODS_SECTOR.PWM, GOODS_SECTOR.PDA_PRODUCT]:
            manual_mapping = {
                WCS_LOCATION.MANUAL_1: MISSION_MODEL_TYPE.MANUAL_PRODUCT_1,
                WCS_LOCATION.MANUAL_2: MISSION_MODEL_TYPE.MANUAL_PRODUCT_2,
                WCS_LOCATION.MANUAL_3: MISSION_MODEL_TYPE.MANUAL_PRODUCT_3,
                WCS_LOCATION.MANUAL_4: MISSION_MODEL_TYPE.MANUAL_PRODUCT_4,
                WCS_LOCATION.MANUAL_5: MISSION_MODEL_TYPE.MANUAL_PRODUCT_5
            }
            if mission.pickup_location in manual_mapping:
                mission.type = manual_mapping[mission.pickup_location]
                return mission
            
            auto_mapping = {
                WCS_LOCATION.AUTO_PRODUCT_1: MISSION_MODEL_TYPE.AUTO_PRODUCT_1,
                WCS_LOCATION.AUTO_PRODUCT_2: MISSION_MODEL_TYPE.AUTO_PRODUCT_2
            }
            if mission.pickup_location in auto_mapping:
                mission.type = auto_mapping[mission.pickup_location]
                return mission
            
        elif mission.sector == GOODS_SECTOR.PRODUCT:
            mission.type = MISSION_MODEL_TYPE.PWM_PRODUCT
            return mission
        
        raise Exception(f"Wrong sector to map mission type: {mission.sector}")

    def __createMissionHandler(self, mission: Mission_Model):
        """
        Create handler for mission
        """
        self.__db.updateMission(mission)

        type_list = [
            MISSION_TYPE_MAPPING.MANUAL_INPUT,
            MISSION_TYPE_MAPPING.MANUAL_OUTPUT,
            MISSION_TYPE_MAPPING.AUTO_INPUT,
            MISSION_TYPE_MAPPING.AUTO_OUTPUT,
            MISSION_TYPE_MAPPING.PWM_OUTPUT
        ]
        class_list = [
            Manual_Input_Mission_Handler,
            Manual_Output_Mission_Handler,
            Auto_Input_Mission_Handler,
            Auto_Output_Mission_Handler,
            PWM_Output_Mission_Handler
        ]
        for i in range(type_list.__len__()):
            if mission.type in type_list[i]:
                self.__handlers[mission.code] = class_list[i](
                    mission, self.__wcs, self.__rcs, self.__gw, self.__handlerDestructor)
                return True
        
        self.__logger.error(f"Wrong mission type: {mission.items()}")
        return False

    def __handlerDestructor(self, mission_code: str):
        """
        To give self-destruction to all mission handler
        """
        self.__handlers.pop(mission_code)
    
    def __cancelMission(self, trigger: Mission_Trigger_Model):
        """
        Cancel mission from trigger
        - Cannot cancel mission from PWM
        - Get first handler matched with trigger
        """
        if trigger.creator == MISSION_TRIGGER_CREATOR.PWM:
            return
        
        handler = None
        for code in self.__handlers:
            if self.__handlers[code].checkTrigger(trigger):
                handler = self.__handlers[code]
                break
        if handler is None:
            return
        
        self.__logger.info(f"Cancel mission: {trigger.items()}\n-> {handler.data.items()}")
        handler.triggerCancel(trigger.creator == MISSION_TRIGGER_CREATOR.PDA)
    
    def checkMissionTrigger(self):
        """
        Handle mission triggers from PDA, Callbox
        """
        try:
            trigger = self.__db.popTrigger()
            if not trigger:
                return False
            
            if trigger.creator == MISSION_TRIGGER_CREATOR.PDA:
                trigger = self.__wcs.fillPDATrigger(trigger)
                Logger(MODULE_NAME.PDA).info(f"-> Filled: {trigger.items()}")
                if not trigger:
                    return False
            else:
                Logger(MODULE_NAME.GATEWAY).info(f"Callbox trigger: {trigger.items()}")

            if trigger.action == MISSION_TRIGGER_ACTION.CALL:
                for mission_code in self.__handlers:
                    if self.__handlers[mission_code].checkTrigger(trigger):
                        return False
                self.__createMission(trigger)
            elif trigger.action == MISSION_TRIGGER_ACTION.CANCEL:
                self.__cancelMission(trigger)
            else:
                raise Exception(f"Wrong trigger action: {trigger.items()}")
            
            return True
        except Exception as e:
            self.__logger.error(f"Handle trigger error: {e}")
            return False

    def checkPWMStatus(self):
        """
        - If normal to bypass
            - RCS set block area
            - Release agv waiting for wrapping
            (when not create pwm output mission for that agv yet)
        - Create pwm output mission if no handler
        """
        stt = self.__db.getPWMStatus()
        info = self.__db.getPWMInfo()

        if stt.machine_state == PWM_MACHINE_STATUS.BYPASS:
            if not self.__pwm_bypass:
                self.__rcs.setBlockArea(RCS_LOCATION.AREA_PWM, True)
                self.__pwm_bypass = True
            if info.pallet_state == PWM_PALLET_STATUS.HAVE:
                self.__rcs.freeRobot(info.agv_code)
                info.pallet_state = PWM_PALLET_STATUS.NONE
                self.__db.updatePWMInfo(info)
        else:
            self.__pwm_bypass = False

        if info.pallet_state == PWM_PALLET_STATUS.HAVE\
            and stt.wrap_state == PWM_WRAP_STATUS.DONE\
            and stt.machine_state == PWM_MACHINE_STATUS.WRAP:
            
            has_handler = False
            for mission_code in self.__handlers:
                if self.__handlers[mission_code].data.type in MISSION_TYPE_MAPPING.PWM_OUTPUT\
                        and self.__handlers[mission_code].data.agv_code == info.agv_code:
                    has_handler = True
                    break
            if has_handler:
                return
        
            trigger = Mission_Trigger_Model()
            trigger.gateway_id = info.gateway_id
            trigger.plc_id = info.plc_id
            trigger.button_id = info.button_id
            trigger.creator = MISSION_TRIGGER_CREATOR.PWM
            trigger.creator_name = MISSION_TRIGGER_CREATOR_NAME.PWM
            trigger.action = MISSION_TRIGGER_ACTION.CALL
            Logger(MODULE_NAME.GATEWAY).info(f"PWM trigger: {trigger.items()}")
            self.__createMission(trigger, info.agv_code)

    def checkAutoLineStatus(self):
        """
        Create auto line mission once for each IDLE -> CALL edge.
        """
        info = self.__db.getAutoStatus()
        if not info:
            Logger(MODULE_NAME.GATEWAY).info("Auto line status: None")
            return

        auto_lines = [
            (MISSION_TRIGGER_CREATOR.AUTO_LINE_1, info.product_line_1, "line1"),
            (MISSION_TRIGGER_CREATOR.AUTO_LINE_2, info.product_line_2, "line2"),
            (MISSION_TRIGGER_CREATOR.AUTO_LINE_PALLET, info.empty_pallet, "pallet")
        ]
        # Logger(MODULE_NAME.GATEWAY).info(
        #     f"Auto line status: line1={info.product_line_1}, "
        #     f"line2={info.product_line_2}, pallet={info.empty_pallet}, "
        #     f"latch={self.__auto_line_latch}"
        # )
        for creator, status, _ in auto_lines:
            if status == AUTO_LINE_MODEL_STATUS.IDLE:
                if self.__auto_line_latch[creator]:
                    Logger(MODULE_NAME.GATEWAY).info(
                        f"Auto line latch reset: creator={creator}"
                    )
                self.__auto_line_latch[creator] = False
                continue

            if status != AUTO_LINE_MODEL_STATUS.CALL:
                continue

            if self.__auto_line_latch[creator]:
                Logger(MODULE_NAME.GATEWAY).info(
                    f"Auto line call ignored by latch: creator={creator}"
                )
                continue

            Logger(MODULE_NAME.GATEWAY).info(
                f"Auto line call accepted: creator={creator}"
            )
            if self.__autoLineCreateMission(creator):
                self.__auto_line_latch[creator] = True
                Logger(MODULE_NAME.GATEWAY).info(
                    f"Auto line latch set: creator={creator}"
                )
            else:
                Logger(MODULE_NAME.GATEWAY).info(
                    "Auto line mission create failed, "
                    f"keep latch open for retry: creator={creator}"
                )
    
    def __autoLineCreateMission(self, creator: MISSION_TRIGGER_CREATOR):
        """
        Create mission to auto line (empty, done 1, done 2)
        """
        creator_mapping = {
            MISSION_TRIGGER_CREATOR.AUTO_LINE_1: {
                "type": MISSION_MODEL_TYPE.AUTO_PRODUCT_1,
                "button": AUTO_LINE_BUTTON.PRODUCT_1
            },
            MISSION_TRIGGER_CREATOR.AUTO_LINE_2: {
                "type": MISSION_MODEL_TYPE.AUTO_PRODUCT_2,
                "button": AUTO_LINE_BUTTON.PRODUCT_2
            },
            MISSION_TRIGGER_CREATOR.AUTO_LINE_PALLET: {
                "type": MISSION_MODEL_TYPE.AUTO_PALLET,
                "button": AUTO_LINE_BUTTON.EMPTY
            }
        }
        for handler in self.__handlers.values():
            if handler.data.type == creator_mapping[creator]["type"]:
                Logger(MODULE_NAME.GATEWAY).info(
                    "Auto line mission ignored because handler exists: "
                    f"creator={creator}, type={creator_mapping[creator]['type']}"
                )
                return True

        trigger = Mission_Trigger_Model()
        trigger.creator = creator
        trigger.creator_name = MISSION_TRIGGER_CREATOR_NAME.autoLine(trigger.creator)
        trigger.gateway_id = GATEWAY_CONFIG.ID
        trigger.plc_id = GATEWAY_AUTO_LINE.ID
        trigger.button_id = creator_mapping[creator]["button"]
        trigger.action = MISSION_TRIGGER_ACTION.CALL
        Logger(MODULE_NAME.GATEWAY).info(f"Auto line trigger: {trigger.items()}")
        return self.__createMission(trigger)
    
    def checkDeviceConnection(self):
        """
        Receive connection feedback from Gateway and update to WCS (NOT USED)
        """
        current_time = time()
        connection = self.__db.getConnections()
        for name in connection:
            if connection[name].updated_at - current_time > DEVICE_CONNECTION_TIMEOUT:
                self.__db.removeConnection(connection)
            else:
                device = Device_Information()
                device.gateway_id = connection[name].gateway_id
                device.plc_id = connection[name].plc_id
                device.button_id = connection[name].button_id
                self.__wcs.updateDeviceConnection(device)
    
    def __checkSpecialTrigger(self, trigger: Mission_Trigger_Model):
        """
        Handle unused trigger in process

        Line TD1: call carton -> start PWM
        Line TD1: cancel carton -> change robot id to resume
        Line TD2: call/cancel empty -> trigger/cancel PWM output mission
        Line TD2: call/cancel pallet -> resume/pause robot by robot id
        """
        logger = Logger(MODULE_NAME.PDA)
        if trigger.location == WCS_LOCATION.AUTO_PRODUCT_2:
            if trigger.sector == GOODS_SECTOR.EMPTY:
                info = self.__db.getPWMInfo()
                trigger.gateway_id = info.gateway_id
                trigger.plc_id = info.plc_id
                trigger.button_id = info.button_id
                if trigger.action == MISSION_TRIGGER_ACTION.CALL:
                    logger.info(f"Create PWM mission: {trigger.items()}")
                    self.__createMission(trigger)
                elif trigger.action == MISSION_TRIGGER_ACTION.CANCEL:
                    logger.info(f"Cancel PWM mission: {trigger.items()}")
                    self.__cancelMission(trigger)
                return True
            elif trigger.sector == GOODS_SECTOR.CARTON:
                agv_code = self.__spec_robot_list[self.__spec_robot_id]
                if trigger.action == MISSION_TRIGGER_ACTION.CALL:
                    logger.info(f"Resume robot: {agv_code}")
                    self.__rcs.resumeRobot(agv_code)
                elif trigger.action == MISSION_TRIGGER_ACTION.CANCEL:
                    logger.info(f"Pause robot: {agv_code}")
                    self.__rcs.pauseRobot(agv_code)
                return True
        elif trigger.location == WCS_LOCATION.AUTO_PRODUCT_1:
            if trigger.sector == GOODS_SECTOR.CARTON:
                if trigger.action == MISSION_TRIGGER_ACTION.CALL:
                    logger.info(f"Trigger start PWM")
                    state = Curtain_Status_Model()
                    state.location = CURTAIN_LOCATION.PWM
                    state.status = CURTAIN_STATUS.ON
                    self.__gw.controlCurtain(state)
                    self.__gw.resetPWM()
                    self.__gw.triggerPWM()
                elif trigger.action == MISSION_TRIGGER_ACTION.CANCEL:
                    self.__spec_robot_id += 1
                    if self.__spec_robot_id >= self.__spec_robot_list.__len__():
                        self.__spec_robot_id = 0
                    logger.info(f"Roll agv: {self.__spec_robot_list[self.__spec_robot_id]}")
                return True
            
        return False
