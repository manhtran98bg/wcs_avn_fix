from rostek_utils.com.rest_api import Body_Model
from rostek_utils.utils.pattern import Define_Class, Declare_Class

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
    current_state: str
    code: int


class WCS_MISSION_REQUEST_STATUS(Define_Class):
    CREATED = "created"
    EXISTS = "exists"
    FAILED = "failed"


class WCS_MISSION_LOOKUP_STATUS(Define_Class):
    FOUND = "found"
    NOT_FOUND = "not_found"
    FAILED = "failed"


class Mission_Request_Result:
    def __init__(self, status: str, mission=None, mission_code: str = "",
            current_state: str = "", error: str = ""):
        self.status = status
        self.mission = mission
        self.mission_code = mission_code
        self.current_state = current_state
        self.error = error
        self.handler_created = False


class Mission_Lookup_Result:
    def __init__(self, status: str, mission=None, error: str = ""):
        self.status = status
        self.mission = mission
        self.error = error

class Bind_RCS_Model(Body_Model):
    list_data: list
    status: str
