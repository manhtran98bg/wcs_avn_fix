from rostek_utils.utils.pattern import Define_Class

class PWM_REGISTER(Define_Class):
    REG_TRIG_RESET = 4114
    REG_TRIG_CURTAIN = 4102
    REG_TRIG_WRAP = 4113

    REG_WRAP_DONE = 4199
    REG_CURTAIN = 4101
    REG_MACHINE = 4197

class PWM_TRIGGER(Define_Class):
    WRAP = 1
    RESET = 1
    CURTAIN_ON = 0
    CURTAIN_OFF = 1

class PWM_STATUS_VALUE(Define_Class):
    CURTAIN_ON = 0
    CURTAIN_OFF = 1
    WRAP_DONE = 1
    WRAP_BUSY = 0
    MACH_MANUAL = 1
    MACH_WRAP = 2
    MACH_READY = 3
    MACH_BYPASS = 4