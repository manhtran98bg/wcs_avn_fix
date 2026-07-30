from .config import (
    GATEWAY_CONFIG, GATEWAY_AUTO_LINE, GATEWAY_CALLBOX,
    GATEWAY_SUCCESS_MSG, GATEWAY_CALLBOX_BUTTON_MAPPING
)
from utils.helper import Helper
from .model import Gateway_Callbox_Trigger, Gateway_Button_State, Gateway_Uptime_Payload
from interface.pwm.com import PWM_Interface
from database.model.device_connection import Device_Connection_Model
from database.model.mission_trigger import Mission_Trigger_Model, MISSION_TRIGGER_CREATOR, MISSION_TRIGGER_CREATOR_NAME, MISSION_TRIGGER_ACTION
from database.model.curtain import Curtain_Status_Model, CURTAIN_LOCATION, CURTAIN_STATUS
from database.model.auto_line import AUTO_LINE_MODEL_STATUS
from database.com import Database_Interface
from common import MODULE_NAME, CALLBOX_BUTTON

from rostek_utils.com.rest_api import RestApi, HTTP_RESPONSE_CODE
from rostek_utils.utils.logger import Logger
from rostek_utils.utils.thread import Worker
import base64, time
from typing import List

class Gateway_Interface:
    """
    Communicate with Gateway

    Kwargs:
        url: gateway url
        host: api server ip = 127.0.0.1
        port: api server port = 5001
        pwm_ip: pwm plc ip
        pwm_port: pwm plc ModbusTCP port = 502

    Private method:
    - __getToken: Generate token to communicate with gateway
    - __getButtonStates: Read device all buttons state
    - __controlDevice: Write to device button

    Thread:
    - __loop: get PWM, auto line status

    Callback:
    - __onUptime: Subscribe uptime to check plc connection
    - __onTrigger: Receive trigger call/cancel from callbox

    Interface:
    - controlCurtain: Control auto line/pwm light curtain
    - Auto line:
        - getAutoLineStatus: Check auto line trigger/curtain status
    - Pallet wrapping machine:
        - resetPWM(self): Reset PWM after wrap done
        - triggerPWM: Trigger start/reset pwm
    """
    def __init__(self, **kwargs) -> None:
        self.__url = kwargs["url"]
        self.__token: dict
        self.__logger = Logger(MODULE_NAME.GATEWAY)
        self.__getToken()

        self.__connect(**Helper.extractDict(kwargs, ["host", "port"]))
        print(f"Connect to {self.__url}")
        pwm_info = kwargs["pwm"]
        self.__pwm = PWM_Interface(ip=pwm_info["ip"], port=pwm_info["port"])
        self.__loop()

    def __getToken(self):
        """
        Generate token to call gateway
        """
        byte_data = f"{GATEWAY_CONFIG.ACC_USER}:{GATEWAY_CONFIG.ACC_PASS}".encode("utf-8")
        encoded_data = base64.b64encode(byte_data)
        self.__token = {
            "Authorization": f"Basic {encoded_data.decode()}"
        }

    def __connect(self, host: str = "127.0.0.1", port: int = 5001):
        """
        Auto handle request from RCS in another thread
        """
        RestApi.serve(host, port)
    
    def __onUptime(self, name: str, topic: str, msg: Gateway_Uptime_Payload):
        """
        Save connection status to database
        (UNUSABLE: WRONG CODE IN GATEWAY)
        """
        mapping = {
            1: msg.button1,
            2: msg.button2,
            3: msg.button3,
            4: msg.button4
        }
        connection = Device_Connection_Model()
        connection.gateway_id = msg.gateway_id
        connection.plc_id = msg.deviceId
        for button in mapping:
            connection.button_id = button
            connection.connected = mapping[button]
            connection.updated_at = time.time()
            Database_Interface().updateConnection(connection)
    
    @Worker.employ
    def __loop(self):
        """
        Get PWM, auto line status
        """
        while True:
            try:
                self.getAutoLineStatus()
            except Exception as e:
                self.__logger.error(f"Fail read auto line status: {e}")
            time.sleep(5)
    
    def __getButtonStates(self, device_id: str) -> List[Gateway_Button_State]:
        """
        Read device button status by device id

        response:
        ```
        {
            "button":
            [{
                "button_id": (int)
                "action": 0 | 1
            }]
        }
        ```
        """
        try:
            res = RestApi.client.get(
                f"{self.__url}{GATEWAY_CONFIG.URL_DEVICE_INFO}{device_id}",
                headers=self.__token,
                timeout=3)
            if res.status_code in HTTP_RESPONSE_CODE.OK:
                response = res.json()
                if response:
                    states = []
                    for button_data in response["button"]:
                        state = Gateway_Button_State()
                        state.button_id = button_data["button_id"]
                        state.action = button_data["action"]
                        states.append(state)
                    return states
            
            self.__logger.warn(f"Get device status fail: {res.content}")
        except Exception as e:
            self.__logger.error(f"Get device status error: {e}")

        return []

    def __controlDevice(self, device_id: str, *states: Gateway_Button_State):
        """
        Set register through gateway
        """
        req = {}
        for state in states:
            req[f"fb{state.button_id}"] = state.action
        
        try:
            res = RestApi.client.post(
                f"{self.__url}{GATEWAY_CONFIG.URL_DEVICE_CONTROL}{device_id}",
                headers=self.__token ,
                json=req,
                timeout=4,
            )
            if res.status_code in HTTP_RESPONSE_CODE.OK:
                response = res.json()
                self.__logger.info(f"Control device res: {res.content}")
                if response["msg"] == GATEWAY_SUCCESS_MSG.CONTROL:
                    return True
                
            self.__logger.warn(f"Control device fail: {res.content}")
        except Exception as e:
            self.__logger.error(f"Control device error: {e}")
        return False

    def __controlPWMCurtain(self, status: Curtain_Status_Model):
        """
        Control pwm light curtain
        """
        self.__pwm.controlLC(status)

    def __controlAutoLineCurtain(self, button_id: int, status: Curtain_Status_Model):
        """
        Control auto line light curtain
        """
        if status.location == CURTAIN_LOCATION.AUTO_PALLET:
            curtain_trigger = {
                CURTAIN_STATUS.ON: GATEWAY_AUTO_LINE.TRIG_EMPTY_CURTAIN_ON,
                CURTAIN_STATUS.OFF: GATEWAY_AUTO_LINE.TRIG_EMPTY_CURTAIN_OFF
            }
        else:
            curtain_trigger = {
                CURTAIN_STATUS.ON: GATEWAY_AUTO_LINE.TRIG_CURTAIN_ON,
                CURTAIN_STATUS.OFF: GATEWAY_AUTO_LINE.TRIG_CURTAIN_OFF
            }
        
        state = Gateway_Button_State()
        state.button_id = button_id
        state.action = curtain_trigger[status.status]
        self.__logger.info(f"Control auto req: {state.items()}")
        return self.__controlDevice(GATEWAY_AUTO_LINE.ID, state)

    def controlCurtain(self, status: Curtain_Status_Model):
        """
        Control auto line/pwm light curtain
        """
        curtain_auto_button = {
            CURTAIN_LOCATION.AUTO_1: GATEWAY_AUTO_LINE.REG_CURTAIN_CMD_1,
            CURTAIN_LOCATION.AUTO_2: GATEWAY_AUTO_LINE.REG_CURTAIN_CMD_2,
            CURTAIN_LOCATION.AUTO_PALLET: GATEWAY_AUTO_LINE.REG_CURTAIN_CMD_EMPTY
        }
        if status.location in curtain_auto_button:
            return self.__controlAutoLineCurtain(curtain_auto_button[status.location], status)
        elif status.location == CURTAIN_LOCATION.PWM:
            return self.__controlPWMCurtain(status)

        raise Exception(f"Wrong curtain location: {status.location}")

    def getAutoLineStatus(self):
        """
        Get auto line trigger:
        - need empty pallet
        - done line 1
        - done line 2
        Get auto line curtain status. All save to database
        """
        line_mapping = {
            GATEWAY_AUTO_LINE.STT_CALL: AUTO_LINE_MODEL_STATUS.CALL,
            GATEWAY_AUTO_LINE.STT_IDLE: AUTO_LINE_MODEL_STATUS.IDLE
        }
        curtain_location = {
            GATEWAY_AUTO_LINE.REG_CURTAIN_FB_1: CURTAIN_LOCATION.AUTO_1,
            GATEWAY_AUTO_LINE.REG_CURTAIN_FB_2: CURTAIN_LOCATION.AUTO_2,
            GATEWAY_AUTO_LINE.REG_CURTAIN_FB_EMPTY: CURTAIN_LOCATION.AUTO_PALLET
        }
        curtain_status = {
            GATEWAY_AUTO_LINE.TRIG_CURTAIN_ON: CURTAIN_STATUS.ON,
            GATEWAY_AUTO_LINE.TRIG_CURTAIN_OFF: CURTAIN_STATUS.OFF
        }

        db = Database_Interface()
        states = self.__getButtonStates(GATEWAY_AUTO_LINE.ID)
        auto_line_status = db.getAutoStatus()
        for state in states:
            if state.action is None:
                continue

            if state.button_id == GATEWAY_AUTO_LINE.REG_DONE_1:
                auto_line_status.product_line_1 = line_mapping[state.action]
            elif state.button_id == GATEWAY_AUTO_LINE.REG_DONE_2:
                auto_line_status.product_line_2 = line_mapping[state.action]
            elif state.button_id == GATEWAY_AUTO_LINE.REG_EMPTY:
                auto_line_status.empty_pallet = line_mapping[state.action]

            if state.button_id in curtain_location:
                location = curtain_location[state.button_id]
                status = db.getCurtainStatus(location)[location]
                status.status = curtain_status[state.action]
                db.updateCurtainStatus(status)
        db.updateAutoStatus(auto_line_status)
    
    def setCallboxLed(self, button: CALLBOX_BUTTON):
        """
        Turn off callbox led
        """
        state = Gateway_Button_State()
        state.button_id = GATEWAY_CALLBOX_BUTTON_MAPPING.mapping(
            GATEWAY_CALLBOX_BUTTON_MAPPING.BUTTON,
            GATEWAY_CALLBOX_BUTTON_MAPPING.REGISTER,
            button
        )[0]
        state.action = GATEWAY_CALLBOX.TRIG_LED_OFF
        self.__logger.info(f"Control callbox: {state.items()}")
        return self.__controlDevice(GATEWAY_CALLBOX.ID, state)

    def triggerPWM(self):
        """
        Trigger PWM to start wrapping 
        """
        return self.__pwm.trigger()

    def resetPWM(self):
        """
        Reset PWM after wrap done
        """
        return self.__pwm.reset()

    @RestApi.server.post(GATEWAY_CALLBOX.URL_TRIGGER)
    def __onTrigger(req: Gateway_Callbox_Trigger):
        """
        Receive trigger call/cancel from callbox
        """
        db = Database_Interface()
        trigger_mapping = {
            GATEWAY_CALLBOX.STT_CALL: MISSION_TRIGGER_ACTION.CALL,
            GATEWAY_CALLBOX.STT_CANCEL: MISSION_TRIGGER_ACTION.CANCEL
        }
        for task in req.tasks:
            state = Gateway_Button_State.fromDict(task)
            trigger = Mission_Trigger_Model()
            trigger.creator = MISSION_TRIGGER_CREATOR.CALLBOX
            trigger.gateway_id = req.gateway_id
            trigger.plc_id = req.device_id
            trigger.button_id = state.button_id
            trigger.action = trigger_mapping[state.action]
            trigger.creator_name = MISSION_TRIGGER_CREATOR_NAME.callbox(state.button_id)
            db.pushTrigger(trigger)
