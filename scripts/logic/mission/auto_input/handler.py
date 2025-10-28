from .config import AUTO_INPUT_MISSION_STEP
from logic.mission.model import Mission_Handler
from database.model.curtain import Curtain_Status_Model, CURTAIN_LOCATION, CURTAIN_STATUS
from database.model.auto_line import AUTO_LINE_MODEL_STATUS
from interface.rcs.config import RCS_LOCATION, RCS_TASK_TYPE, RCS_LOCATION_TYPE
from interface.rcs.model import RCS_Location_Model
from interface.wcs.config import WCS_MISSION_STATUS
from common import INTERFACE_CONVERTER

from time import sleep
from typing import List

class Auto_Input_Mission_Handler(Mission_Handler):
    """
    Handle empty pallet provided mission to auto line

    Flag:
    - pickup: agv reach pickup point
    - check: agv reach checkpoint
    - unload: agv unload done (return | pickup point)
    - last: agv reach last point (auto front | pickup front)
    """
    # Overrite
    def triggerCancel(self, force: bool = False):
        """
        Receive trigger cancel from user
        """
        if self.data.step in [
            AUTO_INPUT_MISSION_STEP.CREATED,
            AUTO_INPUT_MISSION_STEP.BIND_RETURN,
            AUTO_INPUT_MISSION_STEP.SEND_RCS,
            AUTO_INPUT_MISSION_STEP.WAIT_AGV,
            AUTO_INPUT_MISSION_STEP.WAIT_PICKUP,
            AUTO_INPUT_MISSION_STEP.WAIT_CHECK,
            AUTO_INPUT_MISSION_STEP.OFF_CURTAIN
        ]:
            return super().triggerCancel()

    # Method
    def __sendTask(self):
        """
        Create task and send to RCS

        Return: True if success
        """
        task_code = self.rcs.genTask(
            RCS_TASK_TYPE.AUTO_LINE_PALLET,
            self.path[:2], False
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
        curtain.location = CURTAIN_LOCATION.AUTO_PALLET
        curtain.status = CURTAIN_STATUS.ON if on else CURTAIN_STATUS.OFF
        return self.gw.controlCurtain(curtain)

    def __checkCurtain(self) -> CURTAIN_STATUS:
        """
        Get curtain status from Database
        """
        curtain = self.db.getCurtainStatus(CURTAIN_LOCATION.AUTO_PALLET)
        if curtain[CURTAIN_LOCATION.AUTO_PALLET] is None:
            return CURTAIN_STATUS.ON
        return curtain[CURTAIN_LOCATION.AUTO_PALLET].status
    
    def __checkAutoLine(self) -> bool:
        """
        Check if auto line still call
        """
        info = self.db.getAutoStatus()
        return info.empty_pallet == AUTO_LINE_MODEL_STATUS.CALL
    
    # Mission handler format
    def setup(self) -> None:
        self.flag_pickup = False
        self.flag_check = False
        self.flag_unload = False
        self.flag_last = False

        pickup_location = INTERFACE_CONVERTER.WCS_RCS_LOCATION(self.data.pickup_location)
        path_mapping = {
            pickup_location: RCS_LOCATION_TYPE.POINT,
            RCS_LOCATION.AUTO_PALLET_BEFORE: RCS_LOCATION_TYPE.POINT,
            RCS_LOCATION.AUTO_PALLET: RCS_LOCATION_TYPE.POINT,
            pickup_location + "_1": RCS_LOCATION_TYPE.POINT
        }
        self.path: List[RCS_Location_Model] = []
        for position, position_type in path_mapping.items():
            location = RCS_Location_Model()
            location.position = position
            location.position_type = position_type
            self.path.append(location)
    
    def loop(self):
        if self.data.step == AUTO_INPUT_MISSION_STEP.CREATED:
            self.data.step = AUTO_INPUT_MISSION_STEP.BIND_RETURN

        if self.data.step == AUTO_INPUT_MISSION_STEP.BIND_RETURN:
            self.wcs.updateMissionStatus(self.data, WCS_MISSION_STATUS.PENDING)
            self.rcs.bindLoction(self.path[2].position, False)
            self.data.step = AUTO_INPUT_MISSION_STEP.SEND_RCS

        if self.data.step == AUTO_INPUT_MISSION_STEP.SEND_RCS:
            if self.data.cancel_flag:
                self.cancel(False)
                return False
            if self.__sendTask():
                self.wcs.updateMissionStatus(self.data, WCS_MISSION_STATUS.PROCESS)
                self.data.step = AUTO_INPUT_MISSION_STEP.WAIT_AGV
            else:
                sleep(0.5)

        if self.data.step == AUTO_INPUT_MISSION_STEP.WAIT_AGV:
            if self.data.cancel_flag:
                self.cancel()
                return False
            if self.data.agv_code:
                self.data.step = AUTO_INPUT_MISSION_STEP.WAIT_PICKUP

        if self.data.step == AUTO_INPUT_MISSION_STEP.WAIT_PICKUP:
            if self.data.cancel_flag:
                self.cancel()
                return False
            if self.flag_pickup:
                self.wcs.emptyLocation(self.data.pickup_location)
                self.data.step = AUTO_INPUT_MISSION_STEP.WAIT_CHECK

        if self.data.step == AUTO_INPUT_MISSION_STEP.WAIT_CHECK:
            if self.flag_check:
                self.data.step = AUTO_INPUT_MISSION_STEP.OFF_CURTAIN

        if self.data.step == AUTO_INPUT_MISSION_STEP.OFF_CURTAIN:
            if self.data.cancel_flag or not self.__checkAutoLine():
                self.__controlCurtain(True)
                self.data.step = AUTO_INPUT_MISSION_STEP.CONTINUE_PICKUP
            elif self.__checkCurtain() == CURTAIN_STATUS.OFF:
                self.data.step = AUTO_INPUT_MISSION_STEP.CONTINUE_RETURN
            else:
                self.__controlCurtain(False)
                sleep(0.5)

        if self.data.step == AUTO_INPUT_MISSION_STEP.CONTINUE_RETURN:
            if self.__continueTask(self.path[2]):
                self.data.step = AUTO_INPUT_MISSION_STEP.WAIT_UNLOAD
            else:
                sleep(0.5)

        if self.data.step == AUTO_INPUT_MISSION_STEP.WAIT_UNLOAD:
            if self.flag_unload:
                self.data.step = AUTO_INPUT_MISSION_STEP.CONTINUE_FINISH

        if self.data.step == AUTO_INPUT_MISSION_STEP.CONTINUE_FINISH:
            if self.__continueTask(self.path[1]):
                self.data.step = AUTO_INPUT_MISSION_STEP.WAIT_FINISH
            else:
                sleep(0.5)

        if self.data.step == AUTO_INPUT_MISSION_STEP.WAIT_FINISH:
            if self.flag_last:
                self.__controlCurtain(True)
                self.data.step = AUTO_INPUT_MISSION_STEP.ON_CURTAIN

        if self.data.step == AUTO_INPUT_MISSION_STEP.ON_CURTAIN:
            if self.__checkCurtain() == CURTAIN_STATUS.ON:
                self.finish()
                return False
            else:
                self.__controlCurtain(True)
                sleep(0.5)

        if self.data.step == AUTO_INPUT_MISSION_STEP.CONTINUE_PICKUP:
            if self.__continueTask(self.path[0]):
                self.data.step = AUTO_INPUT_MISSION_STEP.WAIT_RETURN
            else:
                sleep(0.5)

        if self.data.step == AUTO_INPUT_MISSION_STEP.WAIT_RETURN:
            if self.flag_unload:
                self.wcs.fillLocation(self.data.pickup_location)
                self.data.step = AUTO_INPUT_MISSION_STEP.CONTINUE_CANCEL

        if self.data.step == AUTO_INPUT_MISSION_STEP.CONTINUE_CANCEL:
            if self.__continueTask(self.path[3]):
                self.data.step = AUTO_INPUT_MISSION_STEP.WAIT_CANCEL
            else:
                sleep(0.5)

        if self.data.step == AUTO_INPUT_MISSION_STEP.WAIT_CANCEL:
            if self.flag_last:
                self.cancel(False)
                return False

        return True