from rostek_utils.utils.pattern import Declare_Class

class Device_Connection_Model(Declare_Class):
    gateway_id: str
    plc_id: str
    button_id: int
    connected: bool
    updated_at: float