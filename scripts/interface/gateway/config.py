from common import CALLBOX_BUTTON

from rostek_utils.utils.pattern import Define_Class, Mapping_Class

# Conntection
class GATEWAY_MQTT:
    BROKER = "172.21.99.23"
    PORT = 1883
    USER = "rostek"
    PASSWORD = "rostek2019"
    UPTIME_TOPIC = "/v2.0.0/rostek/uptime"

class GATEWAY_CONFIG(Define_Class):
    ID = "10000000088422e6"

    # Account login
    ACC_USER = "admin"
    ACC_PASS = "admin"

    # URL
    URL_DEVICE_INFO = "/api/v2.0.0/device/"
    URL_DEVICE_CONTROL = "/api/v2.0.0/device/control/"
    URL_CONTROL_LINE = "/api/v2.0.0/control/line/"
    # NOT USED
    URL_CONTROL_DOOR = "/api/v2.0.0/control/door/"

class GATEWAY_SUCCESS_MSG(Define_Class):
    CONTROL = "Write to Control box success"

# AUTO LINE
class GATEWAY_AUTO_LINE(Define_Class):
    ID = "device5489411b-8562-4ac2-826f-e2fccbb142b3"
    
    # Register
    REG_DONE_1 = 1
    REG_EMPTY = 2
    REG_DONE_2 = 3
    REG_CURTAIN_FB_1 = 4
    REG_CURTAIN_FB_2 = 5
    REG_CURTAIN_FB_EMPTY = 6
    REG_CURTAIN_CMD_1 = 1
    REG_CURTAIN_CMD_EMPTY = 2
    REG_CURTAIN_CMD_2 = 3

    # Trigger
    TRIG_CURTAIN_ON = 0
    TRIG_CURTAIN_OFF = 1
    TRIG_EMPTY_CURTAIN_ON = 2
    TRIG_EMPTY_CURTAIN_OFF = 1

    # Status
    STT_CURTAIN_ON = 0
    STT_CURTAIN_OFF = 1
    STT_CALL = 1
    STT_IDLE = 0

# CALLBOX
class GATEWAY_CALLBOX(Define_Class):
    ID = "deviceb5e4f7ae-60a2-48f1-96c8-068b1cffeb37"
    
    # Register
    REG_EMPTY = [1, 4, 7, 10, 13]
    REG_CARTON = [2, 5, 8, 11, 14]
    REG_SEMI = [3, 6, 9, 12, 15]

    # Status
    STT_CANCEL = 0
    STT_CALL = 1

    # Trigger
    TRIG_LED_OFF = 1

    # URL
    URL_TRIGGER = "/trigger"

class GATEWAY_CALLBOX_BUTTON_MAPPING(Mapping_Class):
    BUTTON = [
        CALLBOX_BUTTON.EMPTY[0], CALLBOX_BUTTON.CARTON[0], CALLBOX_BUTTON.SEMI[0],
        CALLBOX_BUTTON.EMPTY[1], CALLBOX_BUTTON.CARTON[1], CALLBOX_BUTTON.SEMI[1],
        CALLBOX_BUTTON.EMPTY[2], CALLBOX_BUTTON.CARTON[2], CALLBOX_BUTTON.SEMI[2],
        CALLBOX_BUTTON.EMPTY[3], CALLBOX_BUTTON.CARTON[3], CALLBOX_BUTTON.SEMI[3],
        CALLBOX_BUTTON.EMPTY[4], CALLBOX_BUTTON.CARTON[4], CALLBOX_BUTTON.SEMI[4]
    ]
    REGISTER = [
        GATEWAY_CALLBOX.REG_EMPTY[0], GATEWAY_CALLBOX.REG_CARTON[0], GATEWAY_CALLBOX.REG_SEMI[0],
        GATEWAY_CALLBOX.REG_EMPTY[1], GATEWAY_CALLBOX.REG_CARTON[1], GATEWAY_CALLBOX.REG_SEMI[1],
        GATEWAY_CALLBOX.REG_EMPTY[2], GATEWAY_CALLBOX.REG_CARTON[2], GATEWAY_CALLBOX.REG_SEMI[2],
        GATEWAY_CALLBOX.REG_EMPTY[3], GATEWAY_CALLBOX.REG_CARTON[3], GATEWAY_CALLBOX.REG_SEMI[3],
        GATEWAY_CALLBOX.REG_EMPTY[4], GATEWAY_CALLBOX.REG_CARTON[4], GATEWAY_CALLBOX.REG_SEMI[4]
    ]