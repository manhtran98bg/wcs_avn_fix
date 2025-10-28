from .config import PDA_URL_PATH
from .model import PDA_Trigger_Req, PDA_Trigger_Res
from common import MODULE_NAME
from database.com import Database_Interface
from database.model.mission_trigger import Mission_Trigger_Model, MISSION_TRIGGER_CREATOR, MISSION_TRIGGER_CREATOR_NAME
from utils.helper import Helper

from rostek_utils.com.rest_api import RestApi
from rostek_utils.utils.logger import Logger

class PDA_Interface:
    """
    Communicate with PDA

    Kwargs:
        host: (str) api server ip = 127.0.0.1
        port: (int) api server port = 5001

    Interface:
    - onTrigger: Receive call/cancel trigger and save to database
    """
    def __init__(self, **kwargs) -> None:
        self.__connect(**Helper.extractDict(kwargs, ["host", "port"]))

    def __connect(self, host: str = "127.0.0.1", port: int = 5001):
        """
        Auto handle request from RCS in another thread
        """
        RestApi.serve(host, port)
    
    @RestApi.server.post(PDA_URL_PATH.TRIGGER)
    def __onTrigger(body: PDA_Trigger_Req):
        """
        Trigger signal from pda
        """
        trigger = Mission_Trigger_Model()
        trigger.creator = MISSION_TRIGGER_CREATOR.PDA
        trigger.creator_name = MISSION_TRIGGER_CREATOR_NAME.pda(body.user)
        trigger.location = body.location
        trigger.sector = body.sectors
        trigger.action = body.status
        Logger(MODULE_NAME.PDA).info(f"Trigger: {trigger.items()}")
        Database_Interface().pushTrigger(trigger)
        return PDA_Trigger_Res.defItems()