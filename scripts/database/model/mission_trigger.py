from rostek_utils.utils.pattern import Define_Class, Declare_Class

class MISSION_TRIGGER_CREATOR(Define_Class):
    PDA = 0
    CALLBOX = 1
    AUTO_LINE_1 = 2
    AUTO_LINE_2 = 3
    AUTO_LINE_PALLET = 4
    PWM = 5

class MISSION_TRIGGER_CREATOR_NAME:
    PWM = "PWM"

    @staticmethod
    def pda(user: str):
        """
        Generate PDA name

        Return: "PDA-[user]"
        """
        return f"PDA-{user}"
    
    @staticmethod
    def callbox(button: int):
        """
        Generate callbox name

        Return: "CALLBOX-[button]"
        """
        return f"CALLBOX-{button}"
    
    @staticmethod
    def autoLine(line_creator: int):
        """
        Generate auto line name. Raise exception if wrong creator.

        line_creator: (MISSION_TRIGGER_CREATOR)

        Return: "AUTO-[button]"
        """
        mapping = {
            MISSION_TRIGGER_CREATOR.AUTO_LINE_1: "1",
            MISSION_TRIGGER_CREATOR.AUTO_LINE_2: "2",
            MISSION_TRIGGER_CREATOR.AUTO_LINE_PALLET: "PALLET"
        }
        if line_creator not in mapping:
            raise Exception(f"Wrong line creator: {line_creator}")
        return f"AUTO-{mapping[line_creator]}"

class MISSION_TRIGGER_ACTION(Define_Class):
    CANCEL = 0
    CALL = 1

class Mission_Trigger_Model(Declare_Class):
    """
    - creator: 0-pda | 1-callbox | 2-auto line (MISSION_TRIGGER_CREATOR)
    - creator_name: pda with user | callbox | auto line (MISSION_TRIGGER_CREATOR_NAME)
    - location: production line name (pda)
    - sector: goods category (pda)
    - gateway_id: gateway id (plc)
    - plc_id: plc id (plc)
    - button_id: button index (plc)
    - action: call-1 | cancel-0 (MISSION_TRIGGER_ACTION)
    """
    creator: int
    creator_name: str
    location: str
    sector: str
    gateway_id: str
    plc_id: str
    button_id: int
    action: int