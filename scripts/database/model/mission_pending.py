from rostek_utils.utils.pattern import Define_Class, Declare_Class


class MISSION_PENDING_STATE(Define_Class):
    CALL_PENDING = "call_pending"
    VERIFYING = "verifying"
    CANCEL_PENDING = "cancel_pending"
    ORPHAN_PROCESSING = "orphan_processing"


class Mission_Pending_Model(Declare_Class):
    key: str

    creator: int
    creator_name: str
    location: str
    sector: str
    gateway_id: str
    plc_id: str
    button_id: int

    state: str
    mission_code: str
    retry_count: int
    next_retry_at: float
    verify_count: int
    first_snapshot: dict
    last_error: str
    created_at: float
    updated_at: float
