from rostek_utils.utils.pattern import Define_Class

class MANUAL_OUTPUT_MISSION_STEP(Define_Class):
    CREATED = 0
    BIND_PICKUP = 1
    SEND_RCS = 2
    WAIT_AGV = 3
    WAIT_PICKUP = 4
    WAIT_REACH_PWM = 5
    WAIT_PWM = 6
    OFF_CURTAIN = 7
    CONTINUE_PWM = 8
    WAIT_UNLOAD = 9
    CONTINUE_BEHIND = 10
    WAIT_BEHIND = 11
    CONTINUE_MANUAL = 12
    WAIT_MANUAL = 13
    CONTINUE_FRONT = 14
    WAIT_FRONT = 15

WAIT_PWM_TIMEOUT = 3600