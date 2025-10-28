from rostek_utils.utils.pattern import Define_Class, Declare_Class

class PWM_PALLET_STATUS(Define_Class):
    NONE = 0
    HAVE = 1

class PWM_WRAP_STATUS(Define_Class):
    BUSY = 0
    DONE = 1

class PWM_MACHINE_STATUS(Define_Class):
    READY = 0
    WRAP = 1
    MANUAL = 2
    BYPASS = 3

class PWM_Status_Model(Declare_Class):
    wrap_state: int
    machine_state: int

class PWM_Information_Model(Declare_Class):
    gateway_id: str
    plc_id: str
    button_id: int
    agv_code: str
    pallet_state: int