from rostek_utils.utils.pattern import Define_Class, Declare_Class

class CURTAIN_STATUS(Define_Class):
    ON = 0
    OFF = 1

class CURTAIN_LOCATION(Define_Class):
    AUTO_1 = "auto_line_1"
    AUTO_2 = "auto_line_2"
    AUTO_PALLET = "auto_empty_pallet"
    PWM = "pwm"

class Curtain_Status_Model(Declare_Class):
    location: str
    status: int