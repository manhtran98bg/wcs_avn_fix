from rostek_utils.utils.pattern import Define_Class, Declare_Class

class MISSION_MODEL_TYPE(Define_Class):
    MANUAL_PALLET_1 = 0
    MANUAL_CARTON_1 = 1
    MANUAL_PRODUCT_1 = 2
    MANUAL_PALLET_2 = 3
    MANUAL_CARTON_2 = 4
    MANUAL_PRODUCT_2 = 5
    MANUAL_PALLET_3 = 6
    MANUAL_CARTON_3 = 7
    MANUAL_PRODUCT_3 = 8
    MANUAL_PALLET_4 = 9
    MANUAL_CARTON_4 = 10
    MANUAL_PRODUCT_4 = 11
    MANUAL_PALLET_5 = 12
    MANUAL_CARTON_5 = 13
    MANUAL_PRODUCT_5 = 14
    AUTO_PALLET = 15
    AUTO_PRODUCT_1 = 16
    AUTO_PRODUCT_2 = 17
    PWM_PRODUCT = 18

class Mission_Model(Declare_Class):
    gateway_id: str
    plc_id: str
    button_id: int

    code: str
    sector: str
    location_id: str
    pickup_location: str
    return_location: str
    rcs_code: str

    rcs_status: str
    agv_code: str

    type: int
    step: int
    cancel_flag: bool