from rostek_utils.utils.pattern import Define_Class

class MANUAL_INPUT_MISSION_STEP(Define_Class):
    CREATED = 0
    BIND_RETURN = 1
    SEND_RCS = 2
    WAIT_AGV = 3
    WAIT_PICKUP = 4
    WAIT_CHECK = 5
    CONTINUE_RETURN = 6
    WAIT_UNLOAD = 7
    CONTINUE_PICKUP = 8
    WAIT_RETURN = 9