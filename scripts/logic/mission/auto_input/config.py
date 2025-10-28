from rostek_utils.utils.pattern import Define_Class

class AUTO_INPUT_MISSION_STEP(Define_Class):
    CREATED = 0
    BIND_RETURN = 1
    SEND_RCS = 2
    WAIT_AGV = 3
    WAIT_PICKUP = 4
    WAIT_CHECK = 5
    OFF_CURTAIN = 6
    CONTINUE_RETURN = 7
    WAIT_UNLOAD = 8
    CONTINUE_FINISH = 9
    WAIT_FINISH = 10
    ON_CURTAIN = 11
    CONTINUE_PICKUP = 12
    WAIT_RETURN = 13
    CONTINUE_CANCEL = 14
    WAIT_CANCEL = 15