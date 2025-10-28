from .config import MANUAL_INPUT_MISSION_STEP
from logic.mission.model import Mission_Handler
from database.model.mission import MISSION_MODEL_TYPE
from interface.rcs.config import RCS_TASK_TYPE, RCS_LOCATION, RCS_LOCATION_TYPE
from interface.rcs.model import RCS_Location_Model
from interface.wcs.config import WCS_MISSION_STATUS
from common import INTERFACE_CONVERTER

from time import sleep
from typing import List

class Manual_Input_Mission_Handler(Mission_Handler):
    """
    Handle empty pallet and carton pallet provided mission to manual line
    
    Flag:
    - pickup: agv reach pickup point
    - check: agv reach checkpoint
    - unload: agv unload done
    """
    # Overrite
    def triggerCancel(self, force: bool = False):
        """
        Receive trigger cancel from user
        """
        if self.data.step in [
            MANUAL_INPUT_MISSION_STEP.CREATED,
            MANUAL_INPUT_MISSION_STEP.BIND_RETURN,
            MANUAL_INPUT_MISSION_STEP.SEND_RCS,
            MANUAL_INPUT_MISSION_STEP.WAIT_AGV,
            MANUAL_INPUT_MISSION_STEP.WAIT_PICKUP,
            MANUAL_INPUT_MISSION_STEP.WAIT_CHECK
        ]:
            return super().triggerCancel()

    # Method
    def __sendTask(self):
        """
        Create task and send to RCS

        Return: True if success
        """
        task_code = self.rcs.genTask(
            RCS_TASK_TYPE.MANUAL_LINE_PALLET\
                if self.path[0].position_type == RCS_LOCATION_TYPE.POINT\
                    else RCS_TASK_TYPE.MANUAL_LINE_CARTON,
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
    
    # Mission handler format
    def setup(self) -> None:
        self.flag_pickup = False
        self.flag_check = False
        self.flag_unload = False
        
        empty_mapping = {
            MISSION_MODEL_TYPE.MANUAL_PALLET_1: [
                RCS_LOCATION.MANUAL_PALLET_1_CHECK,
                RCS_LOCATION.MANUAL_PALLET_1
            ],
            MISSION_MODEL_TYPE.MANUAL_PALLET_2: [
                RCS_LOCATION.MANUAL_PALLET_2_CHECK,
                RCS_LOCATION.MANUAL_PALLET_2
            ],
            MISSION_MODEL_TYPE.MANUAL_PALLET_3: [
                RCS_LOCATION.MANUAL_PALLET_3_CHECK,
                RCS_LOCATION.MANUAL_PALLET_3
            ],
            MISSION_MODEL_TYPE.MANUAL_PALLET_4: [
                RCS_LOCATION.MANUAL_PALLET_4_CHECK,
                RCS_LOCATION.MANUAL_PALLET_4
            ],
            MISSION_MODEL_TYPE.MANUAL_PALLET_5: [
                RCS_LOCATION.MANUAL_PALLET_5_CHECK,
                RCS_LOCATION.MANUAL_PALLET_5
            ]
        }
        carton_mapping = {
            MISSION_MODEL_TYPE.MANUAL_CARTON_1: [
                RCS_LOCATION.MANUAL_CARTON_1_CHECK,
                RCS_LOCATION.MANUAL_CARTON_1
            ],
            MISSION_MODEL_TYPE.MANUAL_CARTON_2: [
                RCS_LOCATION.MANUAL_CARTON_2_CHECK,
                RCS_LOCATION.MANUAL_CARTON_2
            ],
            MISSION_MODEL_TYPE.MANUAL_CARTON_3: [
                RCS_LOCATION.MANUAL_CARTON_3_CHECK,
                RCS_LOCATION.MANUAL_CARTON_3
            ],
            MISSION_MODEL_TYPE.MANUAL_CARTON_4: [
                RCS_LOCATION.MANUAL_CARTON_4_CHECK,
                RCS_LOCATION.MANUAL_CARTON_4
            ],
            MISSION_MODEL_TYPE.MANUAL_CARTON_5: [
                RCS_LOCATION.MANUAL_CARTON_5_CHECK,
                RCS_LOCATION.MANUAL_CARTON_5
            ]
        }
        
        pickup_location = INTERFACE_CONVERTER.WCS_RCS_LOCATION(self.data.pickup_location)
        if self.data.type in empty_mapping:
            path_mapping = {
                pickup_location: RCS_LOCATION_TYPE.POINT,
                empty_mapping[self.data.type][0]: RCS_LOCATION_TYPE.POINT,
                empty_mapping[self.data.type][1]: RCS_LOCATION_TYPE.POINT
            }
        elif self.data.type in carton_mapping:
            path_mapping = {
                pickup_location: RCS_LOCATION_TYPE.ROADWAY,
                carton_mapping[self.data.type][0]: RCS_LOCATION_TYPE.POINT,
                carton_mapping[self.data.type][1]: RCS_LOCATION_TYPE.POINT
            }
        else:
            raise Exception(f"Wrong mission type: {self.data.type}")
    
        self.path: List[RCS_Location_Model] = []
        for position, position_type in path_mapping.items():
            location = RCS_Location_Model()
            location.position = position
            location.position_type = position_type
            self.path.append(location)

    def loop(self):
        if self.data.step == MANUAL_INPUT_MISSION_STEP.CREATED:
            self.data.step = MANUAL_INPUT_MISSION_STEP.BIND_RETURN

        if self.data.step == MANUAL_INPUT_MISSION_STEP.BIND_RETURN:
            self.wcs.updateMissionStatus(self.data, WCS_MISSION_STATUS.PENDING)
            self.rcs.bindLoction(self.path[2].position, False)
            self.data.step = MANUAL_INPUT_MISSION_STEP.SEND_RCS

        if self.data.step == MANUAL_INPUT_MISSION_STEP.SEND_RCS:
            if self.data.cancel_flag:
                self.cancel(False)
                return False
            if self.__sendTask():
                self.wcs.updateMissionStatus(self.data, WCS_MISSION_STATUS.PROCESS)
                self.data.step = MANUAL_INPUT_MISSION_STEP.WAIT_AGV
            else:
                sleep(0.5)

        if self.data.step == MANUAL_INPUT_MISSION_STEP.WAIT_AGV:
            if self.data.cancel_flag:
                self.cancel()
                return False
            if self.data.agv_code:
                self.data.step = MANUAL_INPUT_MISSION_STEP.WAIT_PICKUP

        if self.data.step == MANUAL_INPUT_MISSION_STEP.WAIT_PICKUP:
            if self.data.cancel_flag:
                self.cancel()
                return False
            if self.flag_pickup:
                self.wcs.emptyLocation(self.data.pickup_location)
                self.data.step = MANUAL_INPUT_MISSION_STEP.WAIT_CHECK

        if self.data.step == MANUAL_INPUT_MISSION_STEP.WAIT_CHECK:
            if self.flag_check:
                if self.data.cancel_flag:
                    self.data.step = MANUAL_INPUT_MISSION_STEP.CONTINUE_PICKUP
                else:
                    self.data.step = MANUAL_INPUT_MISSION_STEP.CONTINUE_RETURN

        if self.data.step == MANUAL_INPUT_MISSION_STEP.CONTINUE_RETURN:
            if self.__continueTask(self.path[2]):
                self.data.step = MANUAL_INPUT_MISSION_STEP.WAIT_UNLOAD
            else:
                sleep(0.5)

        if self.data.step == MANUAL_INPUT_MISSION_STEP.WAIT_UNLOAD:
            if self.flag_unload:
                self.finish()
                return False

        if self.data.step == MANUAL_INPUT_MISSION_STEP.CONTINUE_PICKUP:
            point = RCS_Location_Model()
            point.position = self.path[0].position
            point.position_type = self.path[2].position_type
            if self.__continueTask(point):
                self.data.step = MANUAL_INPUT_MISSION_STEP.WAIT_RETURN
            else:
                sleep(0.5)

        if self.data.step == MANUAL_INPUT_MISSION_STEP.WAIT_RETURN:
            if self.flag_unload:
                self.wcs.fillLocation(self.data.pickup_location)
                self.cancel(False)
                return False
        
        return True