from rostek_utils.utils.pattern import Declare_Class
from rostek_utils.com.rest_api import Body_Model

class RCS_Task_Gen_Res(Declare_Class):
    code: int
    message: str
    data: str
    reqCode: str

class RCS_Task_Status_Res(Declare_Class):
    taskCode: str
    taskStatus: int
    taskTyp: str

class RCS_Feedback_Req(Body_Model):
    method: str
    robotCode: str
    taskCode: str

class RCS_Location_Model(Declare_Class):
    position: str
    position_type: str

class RCS_Robot_Data_Res(Declare_Class):
    robotCode: str
    path: str