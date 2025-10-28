from .model import AIS_AGV_STATE_MSG, AIS_Msg_Heartbeat
from .config import AIS_TOPIC
from utils.helper import Helper
from signal_emit.com import Signal_Handle
from signal_emit.config import SIGNAL_CHANNEL
from signal_emit.config import AIS_States_Signal

from rostek_utils.com.mqtt import Mqtt_Client
from rostek_utils.utils.thread import Worker
from time import time, sleep

class AIS_Interface:
    """
    Communicate with AIS

    Kwargs:
        broker: (str) broker ip = 127.0.0.1
        port: (int) broker port = 1883
        user: (str) username if required = None
        password: (str) user password if required = None
        timeout: (float) connection timeout

    Interface:
    - connected: Check if AIS is connected
    - signal: List of agv need to pause/continue (channel: AIS_AGV_STATES)
    """
    def __init__(self, **kwargs) -> None:
        self.__conn: Mqtt_Client = None
        self.__conn_timeout = kwargs["timeout"]
        self.__last_uptime = 0

        keys = ["broker", "port", "user", "password"]
        self.__connect(**Helper.extractDict(kwargs, keys, keys))
    
    def connected(self):
        """
        Check if AIS connection is open
        """
        return time() - self.__last_uptime < self.__conn_timeout

    @Worker.employ
    def __connect(self, broker: str = "127.0.0.1", port: int = 1883, user: str = None, password: str = None):
        """
        Auto handle mqtt message from AIS
        """
        self.__conn = Mqtt_Client("dal")
        self.__conn.subscribe(
            AIS_TOPIC.AGV_STATES,
            AIS_AGV_STATE_MSG,
            qos=2,
            clbk=self.__onAgvState)
        self.__conn.subscribe(
            AIS_TOPIC.HEARTBEAT,
            AIS_Msg_Heartbeat,
            qos=2,
            clbk=self.__onHeartbeat)
        self.__conn.serve(
            host=broker,
            port=port, 
            user=user,
            password=password)
        self.__sendUptime()
    
    def __onAgvState(self, name: str, topic: str, msg: AIS_AGV_STATE_MSG):
        """
        Handle agv state message
        """
        self.__last_uptime = time()
        states = AIS_States_Signal()
        states.pause = msg.pause
        states.normal = msg.normal
        Signal_Handle().emit(SIGNAL_CHANNEL.AIS_AGV_STATES, states)
    
    def __onHeartbeat(self, name: str, topic: str, msg: AIS_Msg_Heartbeat):
        """
        Handle agv state message
        """
        self.__last_uptime = time()
    
    @Worker.employ
    def __sendUptime(self):
        """
        Send uptime message to AIS in a loop
        """
        while 1:
            self.__conn.publish("wcs_status", AIS_AGV_STATE_MSG())
            sleep(2)