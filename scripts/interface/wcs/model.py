from rostek_utils.com.rest_api import Body_Model
from rostek_utils.utils.pattern import Declare_Class

class Device_Information_Res(Declare_Class):
    _id: str
    call_boxes_code: str
    deviceId: int
    rcs_code: str
    sectors: str
    location: str
    gateway_id: str
    plc_id: str
    status_connect: int

class Device_Update_Req(Declare_Class):
    gateway_id: str
    plc_id: str
    deviceId: str

class Mission_Info_Res(Declare_Class):
    _id: str
    mission_code: str
    robot_code: str
    pickup_location: str
    return_location: str
    sector: str
    object_call: str
    mission_rcs: str
    call_boxes_id: str
    current_state: str

class Mission_Trigger_Res(Declare_Class):
    msg: str
    sectors: str
    mission_rcs: int
    mission_code: str
    pickup_location: str
    return_location: str
    location_id: str
    code: int

class Bind_RCS_Model(Body_Model):
    list_data: list
    status: str