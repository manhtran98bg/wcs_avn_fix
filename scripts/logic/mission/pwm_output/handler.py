from .config import PWM_OUTPUT_MISSION_STEP
from logic.mission.model import Mission_Handler
from database.model.curtain import Curtain_Status_Model, CURTAIN_LOCATION, CURTAIN_STATUS
from database.model.pwm import PWM_PALLET_STATUS, PWM_WRAP_STATUS, PWM_MACHINE_STATUS
from interface.rcs.config import RCS_TASK_TYPE, RCS_LOCATION_TYPE, RCS_LOCATION
from interface.rcs.model import RCS_Location_Model
from interface.wcs.config import WCS_MISSION_STATUS
from common import INTERFACE_CONVERTER

from time import sleep
from typing import List

class PWM_Output_Mission_Handler(Mission_Handler):
    """
    Handle product pallet store mission from PWM

    Flag:
    - load: agv loaded pallet in PWM
    - unload: agv unload done
    """
    def __unbind(self):
        """
        Unbind return location and all locations above (NOT USED)
        """
        current_index = int(self.path[0].position[-2:])
        prefix = self.path[0].position[:-2]
        for i in range(current_index):
            self.rcs.bindLoction(prefix + str(i+1).zfill(2), False)
    
    def __sendTask(self):
        """
        Create task and send to RCS

        Return: True if success
        """
        task_code = self.rcs.genTask(
            RCS_TASK_TYPE.PWM_PRODUCT,
            self.path, True, self.data.agv_code
        )
        if not task_code:
            return False

        self.data.rcs_code = task_code
        return True
    
    def __controlCurtain(self, on: bool):
        """
        Send command control PWM curtain to Gateway
        """
        curtain = Curtain_Status_Model()
        curtain.location = CURTAIN_LOCATION.PWM
        curtain.status = CURTAIN_STATUS.ON if on else CURTAIN_STATUS.OFF
        return self.gw.controlCurtain(curtain)

    def __checkCurtain(self) -> CURTAIN_STATUS:
        """
        Get PWM curtain status from Database
        """
        curtain = self.db.getCurtainStatus(CURTAIN_LOCATION.PWM)
        if curtain[CURTAIN_LOCATION.PWM] is None:
            return CURTAIN_STATUS.ON
        return curtain[CURTAIN_LOCATION.PWM].status
    
    def __checkPWMReset(self):
        """
        Check if PWM reset
        """
        stt = self.db.getPWMStatus()
        return stt.wrap_state == PWM_WRAP_STATUS.BUSY
    
    def __checkPWMBypass(self):
        """
        Check if PWM bypass
        """
        return self.db.getPWMStatus().machine_state == PWM_MACHINE_STATUS.BYPASS
    
    def __updatePWMInfo(self):
        """
        Set to no pallet state in PWM info
        """
        info = self.db.getPWMInfo()
        info.pallet_state = PWM_PALLET_STATUS.NONE
        self.db.updatePWMInfo(info)
    
    # Mission handler format
    def setup(self) -> None:
        self.flag_load = False
        self.flag_unload = False

        path_mapping = {
            INTERFACE_CONVERTER.WCS_RCS_LOCATION(self.data.return_location): RCS_LOCATION_TYPE.ROADWAY
        }
        self.path: List[RCS_Location_Model] = []
        for position, position_type in path_mapping.items():
            location = RCS_Location_Model()
            location.position = position
            location.position_type = position_type
            self.path.append(location)
    
    def loop(self):
        if self.data.step == PWM_OUTPUT_MISSION_STEP.CREATED:
            self.data.step = PWM_OUTPUT_MISSION_STEP.PENDING
        
        if self.data.step == PWM_OUTPUT_MISSION_STEP.PENDING:
            self.wcs.updateMissionStatus(self.data, WCS_MISSION_STATUS.PENDING)
            self.data.step = PWM_OUTPUT_MISSION_STEP.CURTAIN_OFF
        
        if self.data.step == PWM_OUTPUT_MISSION_STEP.CURTAIN_OFF:
            if self.__checkCurtain() == CURTAIN_STATUS.OFF:
                self.rcs.setBlockArea(RCS_LOCATION.AREA_PWM, False)
                self.data.step = PWM_OUTPUT_MISSION_STEP.GEN_TASK
            else:
                self.__controlCurtain(False)
                sleep(0.5)

            if self.__checkPWMBypass():
                self.__controlCurtain(True)
                self.cancel(False)
                return False
        
        if self.data.step == PWM_OUTPUT_MISSION_STEP.GEN_TASK:
            if self.__sendTask():
                self.wcs.updateMissionStatus(self.data, WCS_MISSION_STATUS.PROCESS)
                self.data.step = PWM_OUTPUT_MISSION_STEP.WAIT_PICKUP
            else:
                sleep(0.5)

            if self.__checkPWMBypass():
                self.cancel(False)
                return False

        if self.data.step == PWM_OUTPUT_MISSION_STEP.WAIT_PICKUP:
            if self.flag_load:
                self.rcs.setBlockArea(RCS_LOCATION.AREA_PWM, True)
                self.__updatePWMInfo()
                self.data.step = PWM_OUTPUT_MISSION_STEP.CURTAIN_ON

        if self.data.step == PWM_OUTPUT_MISSION_STEP.CURTAIN_ON:
            if self.__checkCurtain() == CURTAIN_STATUS.ON:
                self.data.step = PWM_OUTPUT_MISSION_STEP.RESET
            else:
                self.__controlCurtain(True)
                sleep(0.5)

        if self.data.step == PWM_OUTPUT_MISSION_STEP.RESET:
            if self.__checkPWMReset():
                self.data.step = PWM_OUTPUT_MISSION_STEP.WAIT_RETURN
            else:
                self.gw.resetPWM()
                sleep(0.5)

        if self.data.step == PWM_OUTPUT_MISSION_STEP.WAIT_RETURN:
            if self.flag_unload:
                self.wcs.fillLocation(self.data.return_location)
                self.finish()
                return False
        
        return True