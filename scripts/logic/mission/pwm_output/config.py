from rostek_utils.utils.pattern import Define_Class

class PWM_OUTPUT_MISSION_STEP(Define_Class):
    CREATED = 0
    PENDING = 1
    CURTAIN_OFF = 2
    GEN_TASK = 3
    WAIT_PICKUP = 4
    CURTAIN_ON = 5
    RESET = 6
    WAIT_RETURN = 7