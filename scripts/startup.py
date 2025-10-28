from database.com import Database, Database_Interface
from database.model.mission_trigger import Mission_Trigger_Model, MISSION_TRIGGER_ACTION
from database.model.device_connection import Device_Connection_Model
from database.model.mission import Mission_Model
from database.model.pwm import PWM_Information_Model
from database.model.curtain import Curtain_Status_Model

d = Database()
d.delete(PWM_Information_Model)
d.delete(Curtain_Status_Model)
d.delete(Mission_Model)