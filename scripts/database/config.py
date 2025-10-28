from rostek_utils.utils.pattern import Define_Class

class DATABASE_SERVER_CONFIG(Define_Class):
    HOST = "127.0.0.1"
    PORT = 6379

class DATABASE_NAME(Define_Class):
    MISSION_TRIGGER_LIST = "LIST_MT"
    PWM_STATUS_RECORD = "PWM_STT"
    PWM_INFO_RECORD = "PWM_INFO"
    AUTO_LINE_STATUS = "AUTO_STT"