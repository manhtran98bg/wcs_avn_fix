from .config import MISSION_INTERVAL
from database.model.mission import Mission_Model, MISSION_MODEL_TYPE
from database.model.mission_trigger import Mission_Trigger_Model
from database.com import Database_Interface
from interface.rcs.com import RCS_Interface
from interface.wcs.com import WCS_Interface
from interface.gateway.com import Gateway_Interface
from interface.wcs.config import WCS_MISSION_STATUS
from common import MODULE_NAME

from rostek_utils.utils.thread import Worker
from rostek_utils.utils.logger import Logger
from time import sleep
from typing import Callable

class Mission_Handler:
    """
    Handle any mission

    Args:
        self_destruct: function call on cleaning -> func(mission_code)

    Trigger:
    - checkTrigger: check if trigger for this mission
    - setAgv: when RCS notify agv code
    - triggerCancel: when pda trigger cancel
    - setFlag: set flag on RCS notification

    Method:
    - WCSLocationToRCS: convert location name from WCS to RCS
    - clean: clean mission
    - finish: finish misison
    - cancel: cancel mission

    Need implement:
    - setup: init value
    - loop: run while loop
    """
    def __init__(self, mission: Mission_Model, wcs: WCS_Interface,
            rcs: RCS_Interface, gateway: Gateway_Interface, self_destruct: Callable) -> None:
        self.data = mission
        self.db = Database_Interface()
        self.rcs = rcs
        self.wcs = wcs
        self.gw = gateway
        self.logger = Logger(MODULE_NAME.MISSION)

        self.alive = True
        self.__self_destruct = self_destruct
        self.flag_cancel = False

        self.setup()
        self.logger.info(f"Mission {self.data.rcs_code}: created")
        self.logger.info(f"Mission {self.data.rcs_code}: {self.data.items()}")
        self.__mainLoop()
    
    # To implement
    def setup(self) -> None:
        """
        To init some flag. Call after init object.

        Flag variant format: self.flag_[flag name]
        """
        raise Exception("Not implemented")
    
    def loop(self) -> bool:
        """
        Call after each interval of 1s

        Return: False if want to break
        """
        raise Exception("Not implemented")
    
    @Worker.employ
    def __mainLoop(self):
        """
        Handle loop
        """
        step = self.data.step
        while self.alive:
            if step != self.data.step:
                step = self.data.step
                self.logger.info(f"Mission {self.data.rcs_code}: step {step}")
            if self.flag_cancel:
                self.cancel(False)
                break
            if not self.loop():
                break

            self.db.updateMission(self.data)
            sleep(MISSION_INTERVAL.MAIN_LOOP)
        self.logger.info(f"Mission {self.data.rcs_code}: finish")
    
    # Trigger
    def checkTrigger(self, trigger: Mission_Trigger_Model):
        """
        Check if trigger for this mission
        (Only trigger from callbox, PDA)
        """
        return self.data.gateway_id == trigger.gateway_id and\
            self.data.plc_id == trigger.plc_id and\
            self.data.button_id == trigger.button_id

    def setAgv(self, agv_code: str):
        """
        Receive agv code from RCS
        """
        self.data.agv_code = agv_code
        self.wcs.updateMissionAgv(self.data)
    
    def triggerCancel(self, force: bool = True):
        """
        Receive trigger cancel from user

        force: force to cancel
        (some missions need to check, implemented in future)
        """
        self.data.cancel_flag = True

    def setFlag(self, flag: str):
        """
        Raise flag by flag name
        """
        self.__setattr__(f"flag_{flag}", True)

    # Method
    def clean(self):
        """
        Remove redundant data
        """
        if self.data.type in [
            MISSION_MODEL_TYPE.MANUAL_PALLET_1, MISSION_MODEL_TYPE.MANUAL_CARTON_1, MISSION_MODEL_TYPE.MANUAL_PRODUCT_1,
            MISSION_MODEL_TYPE.MANUAL_PALLET_2, MISSION_MODEL_TYPE.MANUAL_CARTON_2, MISSION_MODEL_TYPE.MANUAL_PRODUCT_2,
            MISSION_MODEL_TYPE.MANUAL_PALLET_3, MISSION_MODEL_TYPE.MANUAL_CARTON_3, MISSION_MODEL_TYPE.MANUAL_PRODUCT_3,
            MISSION_MODEL_TYPE.MANUAL_PALLET_4, MISSION_MODEL_TYPE.MANUAL_CARTON_4, MISSION_MODEL_TYPE.MANUAL_PRODUCT_4,
            MISSION_MODEL_TYPE.MANUAL_PALLET_5, MISSION_MODEL_TYPE.MANUAL_CARTON_5, MISSION_MODEL_TYPE.MANUAL_PRODUCT_5
        ]:
            self.gw.setCallboxLed(self.data.button_id)
        self.db.removeMissions(self.data.code)
        self.alive = False
        self.__self_destruct(self.data.code)
    
    def finish(self):
        """
        Finish mission
        """
        self.wcs.updateMissionStatus(self.data, WCS_MISSION_STATUS.DONE)
        self.clean()
    
    def cancel(self, with_rcs: bool = True):
        """
        Cancel mission
        """
        if with_rcs:
            self.rcs.cancelTask(self.data.rcs_code)
        self.wcs.updateMissionStatus(self.data, WCS_MISSION_STATUS.CANCEL)
        self.clean()