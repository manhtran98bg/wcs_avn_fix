from rostek_utils.utils.pattern import Define_Class, Declare_Class

class AUTO_LINE_MODEL_STATUS(Define_Class):
    IDLE = 0
    CALL = 1

class Auto_Line_Model(Declare_Class):
    product_line_1: int
    product_line_2: int
    empty_pallet: int