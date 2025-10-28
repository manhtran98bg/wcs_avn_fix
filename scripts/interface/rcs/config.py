from signal_emit.config import SIGNAL_CHANNEL

from rostek_utils.utils.pattern import Define_Class, Mapping_Class

class RCS_TASK_TYPE(Define_Class):
    AUTO_LINE_PRODUCT = "AUF"
    AUTO_LINE_PALLET = "AUE1"
    MANUAL_LINE_PRODUCT = "TP1"
    MANUAL_LINE_PALLET = "TC1"
    MANUAL_LINE_CARTON = "TC11"
    PWM_PRODUCT = "TP21"

class RCS_TASK_PRIORITY(Define_Class):
    HIGH = 127
    LOW = 1

class RCS_LOCATION(Define_Class):
    AUTO_PALLET = "auto_e"
    AUTO_PALLET_BEFORE = "auto_e_1"
    AUTO_LINE_1 = "auto_line_1"
    AUTO_LINE_1_BEFORE = "auto_line_1_1"
    AUTO_LINE_2 = "auto_line_2"
    AUTO_LINE_2_BEFORE = "auto_line_2_1"
    PWM_BEFORE = "W1_1"
    PWM = "W1"
    PWM_AFTER = "W1_2"
    WRAP_MANUAL = "WE"
    WRAP_MANUAL_FRONT = "WE_1"
    MANUAL_PALLET_1 = "line1_e"
    MANUAL_PALLET_1_CHECK = "line1_e_1"
    MANUAL_CARTON_1 = "line1_c"
    MANUAL_CARTON_1_CHECK = "line1_c_1"
    MANUAL_PRODUCT_1 = "line1_f"
    MANUAL_PALLET_2 = "line2_e"
    MANUAL_PALLET_2_CHECK = "line2_e_1"
    MANUAL_CARTON_2 = "line2_c"
    MANUAL_CARTON_2_CHECK = "line2_c_1"
    MANUAL_PRODUCT_2 = "line2_f"
    MANUAL_PALLET_3 = "line3_e"
    MANUAL_PALLET_3_CHECK = "line3_e_1"
    MANUAL_CARTON_3 = "line3_c"
    MANUAL_CARTON_3_CHECK = "line3_c_1"
    MANUAL_PRODUCT_3 = "line3_f"
    MANUAL_PALLET_4 = "line4_e"
    MANUAL_PALLET_4_CHECK = "line4_e_1"
    MANUAL_CARTON_4 = "line4_c"
    MANUAL_CARTON_4_CHECK = "line4_c_1"
    MANUAL_PRODUCT_4 = "line4_f"
    MANUAL_PALLET_5 = "line5_e"
    MANUAL_PALLET_5_CHECK = "line5_e_1"
    MANUAL_CARTON_5 = "line5_c"
    MANUAL_CARTON_5_CHECK = "line5_c_1"
    MANUAL_PRODUCT_5 = "line5_f"

    AREA_PWM = "WRAPING"

class RCS_LOCATION_TYPE(Define_Class):
    POINT = "00"
    ROADWAY = "06"

class RCS_TASK_STATUS(Define_Class):
    SEND_ERROR = 0
    CREATED = 1
    EXECUTING = 2
    CANCELLED = 5
    COMPLETED = 9
    # LESS COMMON
    SENDING = 3
    CANCELING = 4
    RESENDING = 6
    INTERRUPTED = 10

class RCS_URL_PATH(Define_Class):
    # DAL server
    FB_FIX_PATH = "/rcs_fb/v2"
    FB_PICK_AGV = "/agv"
    FB_MANUAL_INPUT = "/manual_input"
    FB_AUTO_INPUT = "/auto_input"
    FB_MANUAL_OUTPUT = "/manual_output"
    FB_AUTO_OUTPUT = "/auto_output"
    FB_PWM_OUTPUT = "/pwm"
    FB_CANCEL = "/cancel"

    # RCS server
    CMD_GEN_TASK = "/genAgvSchedulingTask"
    CMD_BLOCK_AREA = "/blockArea"
    CMD_CONTINUE = "/continueTask"
    CMD_PAUSE = "/stopRobot"
    CMD_RESUME = "/resumeRobot"
    CMD_CANCEL = "/cancelTask"
    CMD_QUERY_TASK = "/queryTaskStatus"
    CMD_BIND = "/bindCtnrAndBin"
    CMD_TASK_LIST = "/mockupList"
    CMD_FREE_ROBOT = "/freeRobot"
    # NOT USED
    CMD_QUERY_RACK = "/queryPodBerthAndMat"
    
    URL_QUERY_AGV = "http://172.21.99.21:8182/rcms-dps/rest/queryAgvStatus"

class RCS_CHANNEL_API_MAPPING(Mapping_Class):
    CHANNEL = [
        SIGNAL_CHANNEL.RCS_UPDATE_AGV,
        SIGNAL_CHANNEL.MANUAL_INPUT_FEEDBACK,
        SIGNAL_CHANNEL.AUTO_INPUT_FEEDBACK,
        SIGNAL_CHANNEL.MANUAL_OUTPUT_FEEDBACK,
        SIGNAL_CHANNEL.AUTO_OUTPUT_FEEDBACK,
        SIGNAL_CHANNEL.PWM_OUTPUT_FEEDBACK,
        SIGNAL_CHANNEL.RCS_CANCEL_MISSION
    ]
    PATH = [
        RCS_URL_PATH.FB_PICK_AGV,
        RCS_URL_PATH.FB_MANUAL_INPUT,
        RCS_URL_PATH.FB_AUTO_INPUT,
        RCS_URL_PATH.FB_MANUAL_OUTPUT,
        RCS_URL_PATH.FB_AUTO_OUTPUT,
        RCS_URL_PATH.FB_PWM_OUTPUT,
        RCS_URL_PATH.FB_CANCEL
    ]

RCS_SUCCESS_CODE = "0"