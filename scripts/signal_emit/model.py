from rostek_utils.utils.pattern import Declare_Class

class AIS_States_Signal(Declare_Class):
    pause: list
    normal: list

class Bind_RCS_Signal(Declare_Class):
    points: list
    binded: bool

class RCS_Notify_Signal(Declare_Class):
    mission_code: str
    agv_code: str
    flag: str