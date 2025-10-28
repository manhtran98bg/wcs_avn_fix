from rostek_utils.com.rest_api import Body_Model
from rostek_utils.utils.pattern import Declare_Class

class PDA_Trigger_Req(Body_Model):
    location: str
    sectors: str
    status: int
    user: str

class PDA_Trigger_Res(Declare_Class):
    code: int
    message: str
    response: dict