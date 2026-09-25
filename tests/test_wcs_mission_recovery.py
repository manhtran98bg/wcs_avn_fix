import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import rostek_utils.com.rest_api as rest_api

if not hasattr(rest_api, "Body_Model"):
    rest_api.Body_Model = rest_api.Request_Model

from database.model.mission_trigger import (
    MISSION_TRIGGER_ACTION,
    MISSION_TRIGGER_CREATOR,
    Mission_Trigger_Model,
)
from interface.wcs import com as wcs_module
from interface.wcs.config import WCS_MISSION_STATUS
from interface.wcs.model import (
    WCS_MISSION_LOOKUP_STATUS,
    WCS_MISSION_REQUEST_STATUS,
)


def make_trigger():
    trigger = Mission_Trigger_Model()
    trigger.creator = MISSION_TRIGGER_CREATOR.CALLBOX
    trigger.creator_name = "CALLBOX-12"
    trigger.location = ""
    trigger.sector = ""
    trigger.gateway_id = "gateway-1"
    trigger.plc_id = "plc-1"
    trigger.button_id = 12
    trigger.action = MISSION_TRIGGER_ACTION.CALL
    return trigger


def make_response(payload, status_code=200):
    response = Mock()
    response.status_code = status_code
    response.content = str(payload).encode()
    response.json.return_value = payload
    return response


def make_mission_data(code, state=WCS_MISSION_STATUS.SIGN,
        rcs_code=0, robot_code=""):
    return {
        "_id": f"history-{code}",
        "mission_code": code,
        "robot_code": robot_code,
        "pickup_location": "Line_04",
        "return_location": "May quan mang",
        "sector": "Pallet ban thanh pham",
        "object_call": MISSION_TRIGGER_CREATOR.CALLBOX,
        "mission_rcs": rcs_code,
        "call_boxes_id": "plc-1",
        "current_state": state,
    }


class WCSMissionRecoveryTest(unittest.TestCase):
    def setUp(self):
        self.wcs = object.__new__(wcs_module.WCS_Interface)
        self.wcs._WCS_Interface__url = "http://backend"
        self.wcs._WCS_Interface__token = {"Authorization": "Bearer test"}
        self.wcs._WCS_Interface__logger = Mock()

    def test_code_two_is_classified_as_existing_mission(self):
        payload = {
            "msg": "Exist mission with device",
            "mission_rcs": 0,
            "mission_code": "MISSION-existing",
            "pickup_location": "Line_04",
            "return_location": "May quan mang",
            "current_state": WCS_MISSION_STATUS.SIGN,
            "code": 2,
        }

        with patch.object(
            wcs_module.RestApi.client,
            "patch",
            return_value=make_response(payload),
        ):
            result = self.wcs.getMission(make_trigger())

        self.assertEqual(WCS_MISSION_REQUEST_STATUS.EXISTS, result.status)
        self.assertEqual("MISSION-existing", result.mission_code)
        self.assertEqual(WCS_MISSION_STATUS.SIGN, result.current_state)
        self.assertIsNone(result.mission)

    def test_normal_response_is_classified_as_created(self):
        payload = {
            "msg": "Create mission success",
            "sectors": "Pallet ban thanh pham",
            "mission_rcs": 0,
            "mission_code": "MISSION-new",
            "pickup_location": "Line_04",
            "return_location": "May quan mang",
            "location_id": "location-1",
            "current_state": WCS_MISSION_STATUS.SIGN,
            "code": 0,
        }

        with patch.object(
            wcs_module.RestApi.client,
            "patch",
            return_value=make_response(payload),
        ):
            result = self.wcs.getMission(make_trigger())

        self.assertEqual(WCS_MISSION_REQUEST_STATUS.CREATED, result.status)
        self.assertEqual("MISSION-new", result.mission.code)
        self.assertEqual("plc-1", result.mission.plc_id)
        self.assertEqual(12, result.mission.button_id)

    def test_code_two_without_mission_code_is_failed(self):
        payload = {
            "msg": "Exist mission with device",
            "mission_rcs": 0,
            "current_state": WCS_MISSION_STATUS.SIGN,
            "code": 2,
        }

        with patch.object(
            wcs_module.RestApi.client,
            "patch",
            return_value=make_response(payload),
        ):
            result = self.wcs.getMission(make_trigger())

        self.assertEqual(WCS_MISSION_REQUEST_STATUS.FAILED, result.status)
        self.assertIsNone(result.mission)

    def test_read_timeout_is_classified_as_failed(self):
        with patch.object(
            wcs_module.RestApi.client,
            "patch",
            side_effect=TimeoutError("read timeout"),
        ):
            result = self.wcs.getMission(make_trigger())

        self.assertEqual(WCS_MISSION_REQUEST_STATUS.FAILED, result.status)
        self.assertIsNone(result.mission)

    def test_lookup_selects_only_exact_mission_code(self):
        payload = {
            "msg": "Ok",
            "metaData": [
                make_mission_data("MISSION-other"),
                make_mission_data("MISSION-existing"),
            ],
        }

        with patch.object(
            wcs_module.RestApi.client,
            "post",
            return_value=make_response(payload),
        ) as request:
            result = self.wcs.getMissionByCode("MISSION-existing", "plc-1")

        self.assertEqual(WCS_MISSION_LOOKUP_STATUS.FOUND, result.status)
        self.assertEqual("MISSION-existing", result.mission.code)
        self.assertEqual(WCS_MISSION_STATUS.SIGN, result.mission.current_state)
        self.assertEqual("plc-1", result.mission.call_boxes_id)
        body = request.call_args.kwargs["json"]
        self.assertEqual("plc-1", body["filter"]["call_boxes_id"])
        self.assertIn(
            WCS_MISSION_STATUS.SIGN,
            body["filter"]["current_state"],
        )
        self.assertIn(
            WCS_MISSION_STATUS.CANCEL,
            body["filter"]["current_state"],
        )

    def test_lookup_rejects_duplicate_exact_mission_codes(self):
        mission = make_mission_data("MISSION-existing")
        payload = {"msg": "Ok", "metaData": [mission, dict(mission)]}

        with patch.object(
            wcs_module.RestApi.client,
            "post",
            return_value=make_response(payload),
        ):
            result = self.wcs.getMissionByCode("MISSION-existing", "plc-1")

        self.assertEqual(WCS_MISSION_LOOKUP_STATUS.FAILED, result.status)
        self.assertIsNone(result.mission)


if __name__ == "__main__":
    unittest.main()
