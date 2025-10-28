from rostek_utils.utils.pattern import Declare_Class
from rostek_utils.com.mqtt import Mqtt_Message
from rostek_utils.com.rest_api import Body_Model

class Gateway_Uptime_Payload(Mqtt_Message):
    gateway_id: str
    deviceId: str
    button1: int
    button2: int
    button3: int
    button4: int

class Gateway_Callbox_Trigger(Body_Model):
    gateway_id: str
    device_id: str
    timestamp: float
    tasks: list

class Gateway_Button_State(Declare_Class):
    button_id: int
    action: int