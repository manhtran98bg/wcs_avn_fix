from rostek_utils.com.mqtt import Mqtt_Message

class AIS_AGV_STATE_MSG(Mqtt_Message):
    pause: list
    normal: list

class AIS_Msg_Heartbeat(Mqtt_Message):
    heartbeat: bool
    timestamp: float
    sequence: int