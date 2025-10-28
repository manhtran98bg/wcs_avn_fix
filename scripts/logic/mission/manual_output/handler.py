from .config import MANUAL_OUTPUT_MISSION_STEP, WAIT_PWM_TIMEOUT
from database.model.curtain import Curtain_Status_Model, CURTAIN_LOCATION, CURTAIN_STATUS
from database.model.pwm import PWM_MACHINE_STATUS, PWM_PALLET_STATUS, PWM_WRAP_STATUS
from database.model.mission import MISSION_MODEL_TYPE
from interface.rcs.config import RCS_LOCATION, RCS_TASK_TYPE, RCS_LOCATION_TYPE
from interface.rcs.model import RCS_Location_Model
from interface.wcs.config import WCS_MISSION_STATUS
from logic.mission.model import Mission_Handler

from time import sleep
from typing import List

class Manual_Output_Mission_Handler(Mission_Handler):
    """
    Handle product pallet wrapping mission from manual line

    Flag:
    - pickup: agv reach pickup point
    - pwm: agv reach pwm front point
    - unload: agv unload done (pwm | manual wrap)
    - last: agv reach last point (pwm behind | manual front)
    """
    def triggerCancel(self, force: bool = False):
        if self.data.step in [
            MANUAL_OUTPUT_MISSION_STEP.CREATED,
            MANUAL_OUTPUT_MISSION_STEP.BIND_PICKUP,
            MANUAL_OUTPUT_MISSION_STEP.SEND_RCS,
            MANUAL_OUTPUT_MISSION_STEP.WAIT_AGV,
            MANUAL_OUTPUT_MISSION_STEP.WAIT_PICKUP
        ]:
            return super().triggerCancel()
    
    def cancel(self, with_rcs: bool = True):
        """
        Cancel mission first
        Free robot later
        """
        super().cancel(with_rcs)
        self.rcs.freeRobot(self.data.agv_code)
    
    def __sendTask(self):
        """
        Create task and send to RCS

        Return: True if success
        """
        task_code = self.rcs.genTask(
            RCS_TASK_TYPE.MANUAL_LINE_PRODUCT,
            self.path, False
        )
        if not task_code:
            return False

        self.data.rcs_code = task_code
        return True
    
    def __continueTask(self, location: RCS_Location_Model):
        """
        Send continue task to RCS
        
        Return: True if success
        """
        return self.rcs.continueTask(self.data.rcs_code, location)
    
    def __controlCurtain(self, on: bool):
        """
        Send command control curtain to Gateway
        """
        curtain = Curtain_Status_Model()
        curtain.location = CURTAIN_LOCATION.PWM
        curtain.status = CURTAIN_STATUS.ON if on else CURTAIN_STATUS.OFF
        return self.gw.controlCurtain(curtain)

    def __checkCurtain(self) -> CURTAIN_STATUS:
        """
        Get curtain status from Database
        """
        curtain = self.db.getCurtainStatus(CURTAIN_LOCATION.PWM)
        if curtain[CURTAIN_LOCATION.PWM] is None:
            return CURTAIN_STATUS.ON
        return curtain[CURTAIN_LOCATION.PWM].status
    
    def __checkPWM(self):
        """
        Check if PWM ready for new pallet to go inside
        """
        info = self.db.getPWMInfo()
        stt = self.db.getPWMStatus()
        return stt.machine_state == PWM_MACHINE_STATUS.READY\
            and stt.wrap_state == PWM_WRAP_STATUS.BUSY\
            and info.pallet_state == PWM_PALLET_STATUS.NONE\
            and self.__checkCurtain() == CURTAIN_STATUS.ON
    
    def __checkPWMBypass(self):
        """
        Check if PWM bypass
        """
        return self.db.getPWMStatus().machine_state == PWM_MACHINE_STATUS.BYPASS
    
    def __savePWMInfo(self):
        """
        Save product origin and agv info
        """
        info = self.db.getPWMInfo()
        info.gateway_id = self.data.gateway_id
        info.plc_id = self.data.plc_id
        info.button_id = self.data.button_id
        info.agv_code = self.data.agv_code
        info.pallet_state = PWM_PALLET_STATUS.HAVE
        self.db.updatePWMInfo(info)        
    
    # Mission handler format
    def setup(self) -> None:
        self.flag_pickup = False
        self.flag_pwm = False
        self.flag_unload = False
        self.flag_last = False

        self.__wait_timer = 0

        mapping = {
            MISSION_MODEL_TYPE.MANUAL_PRODUCT_1: RCS_LOCATION.MANUAL_PRODUCT_1,
            MISSION_MODEL_TYPE.MANUAL_PRODUCT_2: RCS_LOCATION.MANUAL_PRODUCT_2,
            MISSION_MODEL_TYPE.MANUAL_PRODUCT_3: RCS_LOCATION.MANUAL_PRODUCT_3,
            MISSION_MODEL_TYPE.MANUAL_PRODUCT_4: RCS_LOCATION.MANUAL_PRODUCT_4,
            MISSION_MODEL_TYPE.MANUAL_PRODUCT_5: RCS_LOCATION.MANUAL_PRODUCT_5
        }
        if self.data.type not in mapping:
            raise Exception(f"Wrong mission type: {self.data.type}")
        
        path_mapping = {
            mapping[self.data.type]: RCS_LOCATION_TYPE.POINT,
            RCS_LOCATION.PWM_BEFORE: RCS_LOCATION_TYPE.POINT,
            RCS_LOCATION.PWM: RCS_LOCATION_TYPE.POINT,
            RCS_LOCATION.PWM_AFTER: RCS_LOCATION_TYPE.POINT,
            RCS_LOCATION.WRAP_MANUAL: RCS_LOCATION_TYPE.POINT,
            RCS_LOCATION.WRAP_MANUAL_FRONT: RCS_LOCATION_TYPE.POINT
        }
        self.path: List[RCS_Location_Model] = []
        for position, position_type in path_mapping.items():
            location = RCS_Location_Model()
            location.position = position
            location.position_type = position_type
            self.path.append(location)

    def loop(self):
        if self.data.cancel_flag:
            self.cancel()
            return False

        if self.data.step == MANUAL_OUTPUT_MISSION_STEP.CREATED:
            if not self.__checkPWMBypass():
                self.data.step = MANUAL_OUTPUT_MISSION_STEP.BIND_PICKUP

        if self.data.step == MANUAL_OUTPUT_MISSION_STEP.BIND_PICKUP:
            self.wcs.updateMissionStatus(self.data, WCS_MISSION_STATUS.PENDING)
            self.rcs.bindLoction(self.path[0].position, True)
            self.data.step = MANUAL_OUTPUT_MISSION_STEP.SEND_RCS

        if self.data.step == MANUAL_OUTPUT_MISSION_STEP.SEND_RCS:
            if self.__sendTask():
                self.wcs.updateMissionStatus(self.data, WCS_MISSION_STATUS.PROCESS)
                self.data.step = MANUAL_OUTPUT_MISSION_STEP.WAIT_AGV
            else:
                sleep(0.5)
            
        if self.data.step == MANUAL_OUTPUT_MISSION_STEP.WAIT_AGV:
            if self.data.agv_code:
                self.data.step = MANUAL_OUTPUT_MISSION_STEP.WAIT_PICKUP

        if self.data.step == MANUAL_OUTPUT_MISSION_STEP.WAIT_PICKUP:
            if self.flag_pickup:
                self.data.step = MANUAL_OUTPUT_MISSION_STEP.WAIT_REACH_PWM

        if self.data.step == MANUAL_OUTPUT_MISSION_STEP.WAIT_REACH_PWM:
            if self.flag_pwm:
                self.__wait_timer = 0
                self.data.step = MANUAL_OUTPUT_MISSION_STEP.WAIT_PWM

        if self.data.step == MANUAL_OUTPUT_MISSION_STEP.WAIT_PWM:
            if self.__checkPWM():
                self.data.step = MANUAL_OUTPUT_MISSION_STEP.OFF_CURTAIN
            else:
                self.__wait_timer += 1

            if self.__wait_timer > WAIT_PWM_TIMEOUT or self.__checkPWMBypass():
                self.rcs.bindLoction(self.path[4].position, False)
                self.data.step = MANUAL_OUTPUT_MISSION_STEP.CONTINUE_MANUAL

        if self.data.step == MANUAL_OUTPUT_MISSION_STEP.OFF_CURTAIN:
            if self.__checkCurtain() == CURTAIN_STATUS.OFF:
                self.rcs.setBlockArea(RCS_LOCATION.AREA_PWM, False)
                self.rcs.bindLoction(self.path[2].position, False)
                self.data.step = MANUAL_OUTPUT_MISSION_STEP.CONTINUE_PWM
            else:
                self.__controlCurtain(False)
                self.__wait_timer += 1

            if self.__wait_timer > WAIT_PWM_TIMEOUT or self.__checkPWMBypass():
                self.rcs.bindLoction(self.path[4].position, False)
                self.data.step = MANUAL_OUTPUT_MISSION_STEP.CONTINUE_MANUAL

        if self.data.step == MANUAL_OUTPUT_MISSION_STEP.CONTINUE_PWM:
            if self.__continueTask(self.path[2]):
                self.data.step = MANUAL_OUTPUT_MISSION_STEP.WAIT_UNLOAD
            else:
                sleep(0.5)

        if self.data.step == MANUAL_OUTPUT_MISSION_STEP.WAIT_UNLOAD:
            if self.flag_unload:
                self.__savePWMInfo()
                self.data.step = MANUAL_OUTPUT_MISSION_STEP.CONTINUE_BEHIND

        if self.data.step == MANUAL_OUTPUT_MISSION_STEP.CONTINUE_BEHIND:
            if self.__continueTask(self.path[3]):
                self.data.step = MANUAL_OUTPUT_MISSION_STEP.WAIT_BEHIND
            else:
                sleep(0.5)

        if self.data.step == MANUAL_OUTPUT_MISSION_STEP.WAIT_BEHIND:
            if self.flag_last:
                self.rcs.setBlockArea(RCS_LOCATION.AREA_PWM, True)
                self.__controlCurtain(True)
                self.gw.triggerPWM()
                self.finish()
                return False
            
        if self.data.step == MANUAL_OUTPUT_MISSION_STEP.CONTINUE_MANUAL:
            if self.__continueTask(self.path[4]):
                self.data.step = MANUAL_OUTPUT_MISSION_STEP.WAIT_MANUAL
            else:
                sleep(0.5)

        if self.data.step == MANUAL_OUTPUT_MISSION_STEP.WAIT_MANUAL:
            if self.flag_unload:
                self.data.step = MANUAL_OUTPUT_MISSION_STEP.CONTINUE_FRONT

        if self.data.step == MANUAL_OUTPUT_MISSION_STEP.CONTINUE_FRONT:
            if self.__continueTask(self.path[5]):
                self.data.step = MANUAL_OUTPUT_MISSION_STEP.WAIT_FRONT
            else:
                sleep(0.5)

        if self.data.step == MANUAL_OUTPUT_MISSION_STEP.WAIT_FRONT:
            if self.flag_last:
                self.cancel(False)
                return False

        return True