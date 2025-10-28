from rostek_utils.utils.pattern import Define_Class

class WCS_URL_PATH(Define_Class):
    # DAL server
    BIND_RCS = "/send_bind"

    # WCS server
    LOGIN = "/auth/login"
    GET_DEVICES = "/call_boxes/list"
    UPDATE_DEVICE = "/call_boxes/update_status_connect/dal"
    GET_MISSIONS = "/mission_history/list"
    UPDATE_MISSION  = "/mission_history"
    TRIGGER_WRAP_MISSION = "/call_boxes/update_status_curtain_wrap/dal"
    TRIGGER_STORE_MISSION = "/call_boxes/update_status_action/dal"
    UPDATE_LOCATION = "/location"

class WCS_SUCCESS_MSG(Define_Class):
    LOGIN = "Login Success"
    GET_LIST = "Ok"
    UPDATE = "Update Success"
    CANCEL_MISSION = "Cancel Ok"
    GET_LOCATION = "OK"

class WCS_MISSION_STATUS(Define_Class):
    """
    - sign: mission just registered, not process
    - process: mission on process
    - pending: mission created but rcs not confirm
    - done: mission finished
    - cancel: mission cancelled
    """
    SIGN = "registered"
    PROCESS = "processing"
    PENDING = "pending"
    CANCEL = "cancel"
    DONE = "accomplished"
    
BIND_RCS_STATUS = "fill"

class WCS_LOCATION(Define_Class):
    MANUAL_1 = "Line_01"
    MANUAL_2 = "Line_02"
    MANUAL_3 = "Line_03"
    MANUAL_4 = "Line_04"
    MANUAL_5 = "Line_05"
    AUTO_PALLET = "LineTD_01"
    AUTO_PRODUCT_1 = "LineTD_01"
    AUTO_PRODUCT_2 = "LineTD_02"