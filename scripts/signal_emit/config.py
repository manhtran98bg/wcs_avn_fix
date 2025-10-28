from .model import AIS_States_Signal, Bind_RCS_Signal, RCS_Notify_Signal

from rostek_utils.utils.pattern import Define_Class, Mapping_Class

class SIGNAL_SERVER_CONFIG(Define_Class):
    HOST = "127.0.0.1"
    PORT = 6379

class SIGNAL_CHANNEL(Define_Class):
    AIS_AGV_STATES = "ais_agv_states"
    WCS_BIND_RCS = "wcs_rcs_bind"
    RCS_UPDATE_AGV = "rcs_agv_code"
    MANUAL_INPUT_FEEDBACK = "rcs_manual_input"
    AUTO_INPUT_FEEDBACK = "rcs_auto_input"
    MANUAL_OUTPUT_FEEDBACK = "rcs_manual_output"
    AUTO_OUTPUT_FEEDBACK = "rcs_auto_output"
    PWM_OUTPUT_FEEDBACK = "rcs_pwm_output"
    RCS_CANCEL_MISSION = "rcs_cancel"

class SIGNAL_CHANNEL_MODEL_MAPPING(Mapping_Class):
    """
    Uni-directional
    """
    CHANNEL = [
        SIGNAL_CHANNEL.AIS_AGV_STATES,
        SIGNAL_CHANNEL.WCS_BIND_RCS,
        SIGNAL_CHANNEL.RCS_UPDATE_AGV,
        SIGNAL_CHANNEL.MANUAL_INPUT_FEEDBACK,
        SIGNAL_CHANNEL.AUTO_INPUT_FEEDBACK,
        SIGNAL_CHANNEL.MANUAL_OUTPUT_FEEDBACK,
        SIGNAL_CHANNEL.AUTO_OUTPUT_FEEDBACK,
        SIGNAL_CHANNEL.PWM_OUTPUT_FEEDBACK,
        SIGNAL_CHANNEL.RCS_CANCEL_MISSION
    ]
    MODEL = [
        AIS_States_Signal,
        Bind_RCS_Signal,
        RCS_Notify_Signal,
        RCS_Notify_Signal,
        RCS_Notify_Signal,
        RCS_Notify_Signal,
        RCS_Notify_Signal,
        RCS_Notify_Signal,
        RCS_Notify_Signal
    ]