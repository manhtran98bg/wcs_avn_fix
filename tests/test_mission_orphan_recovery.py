import sys
import unittest
from collections import deque
from pathlib import Path
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import rostek_utils.com.rest_api as rest_api

if not hasattr(rest_api, "Body_Model"):
    rest_api.Body_Model = rest_api.Request_Model

from common import GOODS_SECTOR
from database.model.mission import Mission_Model, MISSION_MODEL_TYPE
from database.model.mission_pending import (
    Mission_Pending_Model,
    MISSION_PENDING_STATE,
)
from database.model.mission_trigger import (
    MISSION_TRIGGER_ACTION,
    MISSION_TRIGGER_CREATOR,
    Mission_Trigger_Model,
)
from interface.wcs.config import WCS_MISSION_STATUS
from interface.wcs.model import (
    Mission_Lookup_Result,
    Mission_Request_Result,
    WCS_MISSION_LOOKUP_STATUS,
    WCS_MISSION_REQUEST_STATUS,
)
from logic import main as main_module


class FakeDatabase:
    def __init__(self, triggers=None):
        self.triggers = deque(triggers or [])
        self.pendings = {}
        self.removed_missions = False

    def popTrigger(self):
        return self.triggers.popleft() if self.triggers else None

    def getMissionPendings(self, *keys):
        if keys:
            return {key: self.pendings.get(key) for key in keys}
        return dict(self.pendings)

    def updateMissionPending(self, pending):
        self.pendings[pending.key] = pending

    def removeMissionPendings(self, *keys):
        for key in keys:
            self.pendings.pop(key, None)

    def removeMissions(self, *codes):
        self.removed_missions = True


def make_trigger(action=MISSION_TRIGGER_ACTION.CALL, button_id=12):
    trigger = Mission_Trigger_Model()
    trigger.creator = MISSION_TRIGGER_CREATOR.CALLBOX
    trigger.creator_name = f"CALLBOX-{button_id}"
    trigger.location = ""
    trigger.sector = ""
    trigger.gateway_id = "gateway-1"
    trigger.plc_id = "plc-1"
    trigger.button_id = button_id
    trigger.action = action
    return trigger


def make_backend_mission(rcs_code=0, agv_code="",
        current_state=WCS_MISSION_STATUS.SIGN):
    mission = Mission_Model()
    mission.code = "MISSION-existing"
    mission.sector = GOODS_SECTOR.PDA_PRODUCT
    mission.location_id = "location-1"
    mission.pickup_location = "Line_04"
    mission.return_location = "Máy quấn màng"
    mission.rcs_code = rcs_code
    mission.agv_code = agv_code
    mission.call_boxes_id = "plc-1"
    mission.current_state = current_state
    return mission


class MissionOrphanRecoveryTest(unittest.TestCase):
    def setUp(self):
        self.clock = 100.0
        self.time_patch = patch.object(
            main_module, "time", side_effect=lambda: self.clock
        )
        self.logger_patch = patch.object(main_module, "Logger")
        self.time_patch.start()
        self.logger_patch.start()

    def tearDown(self):
        self.logger_patch.stop()
        self.time_patch.stop()

    def make_logic(self, triggers=None):
        logic = object.__new__(main_module.Main_Logic)
        logic._Main_Logic__db = FakeDatabase(triggers)
        logic._Main_Logic__handlers = {}
        logic._Main_Logic__logger = Mock()
        logic._Main_Logic__wcs = Mock()
        logic._Main_Logic__rcs = Mock()
        logic._Main_Logic__gw = Mock()
        logic._Main_Logic__createMissionHandler = Mock(return_value=True)
        return logic

    def pending(self, logic):
        values = list(logic._Main_Logic__db.pendings.values())
        return values[0] if values else None

    def test_successful_call_creates_handler_without_retry_delay(self):
        logic = self.make_logic([make_trigger()])
        mission = make_backend_mission()
        logic._Main_Logic__wcs.getMission.return_value = Mission_Request_Result(
            WCS_MISSION_REQUEST_STATUS.CREATED,
            mission=mission
        )

        self.assertTrue(logic.checkMissionTrigger())

        self.assertIsNone(self.pending(logic))
        logic._Main_Logic__createMissionHandler.assert_called_once_with(mission)
        self.assertEqual(MISSION_MODEL_TYPE.MANUAL_PRODUCT_4, mission.type)

    def test_cancel_without_handler_or_pending_does_not_call_backend(self):
        logic = self.make_logic([
            make_trigger(action=MISSION_TRIGGER_ACTION.CANCEL)
        ])

        self.assertTrue(logic.checkMissionTrigger())

        self.assertIsNone(self.pending(logic))
        logic._Main_Logic__wcs.cancelMission.assert_not_called()

    def test_existing_handler_skips_backend_and_pending_creation(self):
        logic = self.make_logic([make_trigger()])
        handler = Mock()
        handler.checkTrigger.return_value = True
        logic._Main_Logic__handlers["MISSION-running"] = handler

        self.assertTrue(logic.checkMissionTrigger())

        self.assertIsNone(self.pending(logic))
        logic._Main_Logic__wcs.getMission.assert_not_called()

    def test_timeout_then_exists_is_recovered_after_two_stable_reads(self):
        logic = self.make_logic([make_trigger()])
        logic._Main_Logic__wcs.getMission.side_effect = [
            Mission_Request_Result(
                WCS_MISSION_REQUEST_STATUS.FAILED, error="timeout"
            ),
            Mission_Request_Result(
                WCS_MISSION_REQUEST_STATUS.EXISTS,
                mission_code="MISSION-existing"
            ),
        ]
        mission = make_backend_mission()
        logic._Main_Logic__wcs.getMissionByCode.side_effect = [
            Mission_Lookup_Result(
                WCS_MISSION_LOOKUP_STATUS.FOUND, mission=mission
            ),
            Mission_Lookup_Result(
                WCS_MISSION_LOOKUP_STATUS.FOUND,
                mission=make_backend_mission()
            ),
        ]

        self.assertTrue(logic.checkMissionTrigger())
        self.assertEqual(MISSION_PENDING_STATE.CALL_PENDING, self.pending(logic).state)
        self.assertEqual(105.0, self.pending(logic).next_retry_at)

        self.clock = 105.0
        self.assertFalse(logic.checkMissionTrigger())
        self.assertEqual(MISSION_PENDING_STATE.VERIFYING, self.pending(logic).state)

        self.assertFalse(logic.checkMissionTrigger())
        self.assertEqual(1, self.pending(logic).verify_count)
        self.assertEqual(110.0, self.pending(logic).next_retry_at)

        self.clock = 110.0
        self.assertFalse(logic.checkMissionTrigger())
        self.assertIsNone(self.pending(logic))
        recovered = logic._Main_Logic__createMissionHandler.call_args.args[0]
        self.assertEqual("MISSION-existing", recovered.code)
        self.assertEqual(MISSION_MODEL_TYPE.MANUAL_PRODUCT_4, recovered.type)
        self.assertEqual(12, recovered.button_id)

    def test_changed_snapshot_requires_two_new_stable_reads(self):
        logic = self.make_logic([make_trigger()])
        logic._Main_Logic__wcs.getMission.return_value = Mission_Request_Result(
            WCS_MISSION_REQUEST_STATUS.EXISTS,
            mission_code="MISSION-existing"
        )
        first = make_backend_mission()
        changed = make_backend_mission()
        changed.return_location = "May quan mang 2"
        stable = make_backend_mission()
        stable.return_location = "May quan mang 2"
        logic._Main_Logic__wcs.getMissionByCode.side_effect = [
            Mission_Lookup_Result(WCS_MISSION_LOOKUP_STATUS.FOUND, mission=first),
            Mission_Lookup_Result(WCS_MISSION_LOOKUP_STATUS.FOUND, mission=changed),
            Mission_Lookup_Result(WCS_MISSION_LOOKUP_STATUS.FOUND, mission=stable),
        ]

        logic.checkMissionTrigger()
        logic.checkMissionTrigger()
        self.clock = 105.0
        logic.checkMissionTrigger()
        logic._Main_Logic__createMissionHandler.assert_not_called()

        self.clock = 110.0
        logic.checkMissionTrigger()
        logic._Main_Logic__createMissionHandler.assert_called_once()
        self.assertIsNone(self.pending(logic))

    def test_failed_requests_use_capped_backoff_without_dropping_pending(self):
        logic = self.make_logic([make_trigger()])
        logic._Main_Logic__wcs.getMission.return_value = Mission_Request_Result(
            WCS_MISSION_REQUEST_STATUS.FAILED, error="network down"
        )

        expected_delays = [5, 10, 30, 60, 60]
        logic.checkMissionTrigger()
        self.assertEqual(105.0, self.pending(logic).next_retry_at)

        for expected_delay in expected_delays[1:]:
            self.clock = self.pending(logic).next_retry_at
            previous = self.clock
            logic.checkMissionTrigger()
            self.assertEqual(
                previous + expected_delay,
                self.pending(logic).next_retry_at
            )

        self.assertEqual(5, logic._Main_Logic__wcs.getMission.call_count)
        self.assertIsNotNone(self.pending(logic))

    def test_pending_model_survives_redis_json_round_trip(self):
        logic = self.make_logic()
        pending = logic._Main_Logic__newMissionPending(make_trigger())
        restored = Mission_Pending_Model.decode(pending.encode())

        self.assertEqual(pending.key, restored.key)
        self.assertEqual(pending.button_id, restored.button_id)
        self.assertEqual(MISSION_PENDING_STATE.CALL_PENDING, restored.state)
        self.assertEqual({}, restored.first_snapshot)

    def test_cancel_during_pending_calls_backend_and_removes_pending(self):
        call = make_trigger()
        cancel = make_trigger(action=MISSION_TRIGGER_ACTION.CANCEL)
        logic = self.make_logic([call, cancel])
        logic._Main_Logic__wcs.getMission.return_value = Mission_Request_Result(
            WCS_MISSION_REQUEST_STATUS.FAILED, error="timeout"
        )
        logic._Main_Logic__wcs.cancelMission.return_value = True

        self.assertTrue(logic.checkMissionTrigger())
        self.assertIsNotNone(self.pending(logic))
        self.assertTrue(logic.checkMissionTrigger())

        self.assertIsNone(self.pending(logic))
        logic._Main_Logic__wcs.cancelMission.assert_called_once()
        self.assertEqual(1, logic._Main_Logic__wcs.getMission.call_count)

    def test_cancel_timeout_blocks_new_call_and_retries_cancel(self):
        call = make_trigger()
        cancel = make_trigger(action=MISSION_TRIGGER_ACTION.CANCEL)
        duplicate_call = make_trigger()
        logic = self.make_logic([call, cancel, duplicate_call])
        logic._Main_Logic__wcs.getMission.return_value = Mission_Request_Result(
            WCS_MISSION_REQUEST_STATUS.FAILED, error="timeout"
        )
        logic._Main_Logic__wcs.cancelMission.return_value = False

        logic.checkMissionTrigger()
        logic.checkMissionTrigger()
        self.assertEqual(MISSION_PENDING_STATE.CANCEL_PENDING, self.pending(logic).state)

        logic.checkMissionTrigger()
        self.assertEqual(1, logic._Main_Logic__wcs.getMission.call_count)

        self.clock = self.pending(logic).next_retry_at
        logic.checkMissionTrigger()
        self.assertEqual(2, logic._Main_Logic__wcs.cancelMission.call_count)

    def test_existing_rcs_task_is_never_recovered(self):
        logic = self.make_logic([make_trigger()])
        logic._Main_Logic__wcs.getMission.return_value = Mission_Request_Result(
            WCS_MISSION_REQUEST_STATUS.EXISTS,
            mission_code="MISSION-existing"
        )
        logic._Main_Logic__wcs.getMissionByCode.return_value = Mission_Lookup_Result(
            WCS_MISSION_LOOKUP_STATUS.FOUND,
            mission=make_backend_mission(rcs_code="TP11-existing")
        )

        logic.checkMissionTrigger()
        logic.checkMissionTrigger()

        self.assertEqual(
            MISSION_PENDING_STATE.ORPHAN_PROCESSING,
            self.pending(logic).state
        )
        logic._Main_Logic__createMissionHandler.assert_not_called()

    def test_terminal_backend_mission_releases_pending(self):
        logic = self.make_logic([make_trigger()])
        logic._Main_Logic__wcs.getMission.return_value = Mission_Request_Result(
            WCS_MISSION_REQUEST_STATUS.EXISTS,
            mission_code="MISSION-existing"
        )
        logic._Main_Logic__wcs.getMissionByCode.return_value = Mission_Lookup_Result(
            WCS_MISSION_LOOKUP_STATUS.FOUND,
            mission=make_backend_mission(current_state=WCS_MISSION_STATUS.CANCEL)
        )

        logic.checkMissionTrigger()
        logic.checkMissionTrigger()

        self.assertIsNone(self.pending(logic))
        logic._Main_Logic__createMissionHandler.assert_not_called()

    def test_cancel_timeout_is_resolved_when_history_is_terminal(self):
        logic = self.make_logic([make_trigger()])
        logic._Main_Logic__wcs.getMission.return_value = Mission_Request_Result(
            WCS_MISSION_REQUEST_STATUS.EXISTS,
            mission_code="MISSION-existing"
        )
        logic.checkMissionTrigger()

        cancel = make_trigger(action=MISSION_TRIGGER_ACTION.CANCEL)
        logic._Main_Logic__wcs.cancelMission.return_value = False
        logic._Main_Logic__wcs.getMissionByCode.return_value = Mission_Lookup_Result(
            WCS_MISSION_LOOKUP_STATUS.FOUND,
            mission=make_backend_mission(current_state=WCS_MISSION_STATUS.CANCEL)
        )

        logic._Main_Logic__cancelMission(cancel)

        self.assertIsNone(self.pending(logic))
        logic._Main_Logic__wcs.cancelMission.assert_called_once()

    def test_duplicate_call_does_not_repeat_backend_request(self):
        logic = self.make_logic([make_trigger(), make_trigger()])
        logic._Main_Logic__wcs.getMission.return_value = Mission_Request_Result(
            WCS_MISSION_REQUEST_STATUS.FAILED, error="timeout"
        )

        logic.checkMissionTrigger()
        logic.checkMissionTrigger()

        self.assertEqual(1, logic._Main_Logic__wcs.getMission.call_count)
        self.assertEqual(1, len(logic._Main_Logic__db.pendings))

    def test_startup_preserves_pending_mission_and_cancels_unrelated(self):
        logic = self.make_logic()
        pending = logic._Main_Logic__newMissionPending(make_trigger())
        pending.mission_code = "MISSION-existing"
        logic._Main_Logic__db.updateMissionPending(pending)

        protected = make_backend_mission()
        unrelated = make_backend_mission()
        unrelated.code = "MISSION-unrelated"
        unrelated.call_boxes_id = "plc-2"
        logic._Main_Logic__wcs.getMissions.return_value = [protected, unrelated]

        logic._Main_Logic__clearMission()

        logic._Main_Logic__wcs.updateMissionStatus.assert_called_once_with(
            unrelated, WCS_MISSION_STATUS.CANCEL
        )


if __name__ == "__main__":
    unittest.main()
