from rostek_utils.utils.pattern import Define_Class, Declare_Class

class MODULE_NAME(Define_Class):
    AIS = "AIS"
    WCS = "WCS"
    RCS = "RCS"
    GATEWAY = "Gateway"
    PDA = "PDA"
    SIGNAL = "Signal"
    DATABASE = "Database"
    REDIS = "Redis"
    MISSION = "Mission"
    LOGIC = "Logic"
    PWM = "PWM"

class GOODS_SECTOR(Define_Class):
    EMPTY = "Chồng pallet rỗng"
    CARTON = "Pallet carton"
    PDA_PRODUCT = "Pallet bán thành phẩm"
    PRODUCT = "Pallet thành phẩm"
    PWM = "Máy quấn màn"

class LOCATION_STATUS(Define_Class):
    """
    - DISABLE: Vo hieu hoa
    - UNAVAILABLE: Chua chi dinh hang
    - AVAILABLE: Da chi dinh hang, chua co hang
    - FILL: Co hang o day
    """
    DISABLE = "disable"
    UNAVAILABLE = "unavailable"
    AVAILABLE = "available"
    FILL = "fill"

class Device_Information(Declare_Class):
    id: str
    button_id: int
    gateway_id: str
    plc_id: str

class CALLBOX_BUTTON(Define_Class):
    EMPTY = [1, 4, 7, 10, 13]
    CARTON = [2, 5, 8, 11, 14]
    SEMI = [3, 6, 9, 12, 15]

class AUTO_LINE_BUTTON(Define_Class):
    PRODUCT_1 = 16
    EMPTY = 17
    PRODUCT_2 = 18

class INTERFACE_CONVERTER:
    @staticmethod
    def WCS_RCS_LOCATION(location: str):
        """
        Return rcs location
        """
        return location.replace("#", "")