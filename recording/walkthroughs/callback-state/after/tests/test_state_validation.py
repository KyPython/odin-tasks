"""Decisive local callback-state checks for the prepared practice plan."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from callback import CallbackResult, handle_callback  # noqa: E402
from fixtures import FIXED_NOW, SYNTHETIC_CODE, EXPECTED_STATE, scenario  # noqa: E402
from run_fixtures import run  # noqa: E402


class CallbackStateTests(unittest.TestCase):
    def assert_error(self, result: CallbackResult, category: str) -> None:
        self.assertEqual(result, CallbackResult(status="error", category=category))

    def test_missing_empty_and_non_string_state_are_rejected(self) -> None:
        for label, state in (("absent", None), ("empty", ""), ("non-string", 7)):
            with self.subTest(case=label):
                case = scenario("valid")
                if label == "absent":
                    case["query"].pop("state")
                else:
                    case["query"]["state"] = state
                result = handle_callback(case["query"], case["session"], FIXED_NOW)
                self.assert_error(result, "missing_state")
                self.assertIn("oauth_request", case["session"])

    def test_mismatch_and_unbound_state_are_rejected(self) -> None:
        for label in ("mismatch", "unbound", "unicode-mismatch"):
            with self.subTest(case=label):
                case = scenario("mismatched")
                if label == "unbound":
                    case["session"] = {}
                elif label == "unicode-mismatch":
                    case["query"]["state"] = "different-opaque-state-\u00e9"
                result = handle_callback(case["query"], case["session"], FIXED_NOW)
                self.assert_error(result, "state_mismatch")
                if label != "unbound":
                    self.assertIn("oauth_request", case["session"])
                    valid_query = scenario("valid")["query"]
                    retry = handle_callback(valid_query, case["session"], FIXED_NOW)
                    self.assertEqual(retry, CallbackResult(status="ok", redirect_to="/dashboard"))

    def test_expired_state_is_rejected_without_consuming_request(self) -> None:
        case = scenario("expired")
        result = handle_callback(case["query"], case["session"], FIXED_NOW)
        self.assert_error(result, "state_expired")
        self.assertIn("oauth_request", case["session"])

    def test_expiration_deadline_and_one_second_before(self) -> None:
        for label, remaining in (("at-deadline", 0), ("one-second-before", 1)):
            with self.subTest(case=label):
                case = scenario("valid")
                case["session"]["oauth_request"]["expires_at"] = FIXED_NOW + remaining
                result = handle_callback(case["query"], case["session"], FIXED_NOW)
                if remaining == 0:
                    self.assert_error(result, "state_expired")
                    self.assertIn("oauth_request", case["session"])
                else:
                    self.assertEqual(result, CallbackResult(status="ok", redirect_to="/dashboard"))
                    self.assertNotIn("oauth_request", case["session"])

    def test_replay_is_rejected_after_one_success(self) -> None:
        case = scenario("replayed")
        first = handle_callback(case["query"], case["session"], FIXED_NOW)
        self.assertEqual(first, CallbackResult(status="ok", redirect_to="/dashboard"))
        self.assertNotIn("oauth_request", case["session"])
        second = handle_callback(case["query"], case["session"], FIXED_NOW)
        third = handle_callback(case["query"], case["session"], FIXED_NOW)
        self.assert_error(second, "state_replayed")
        self.assert_error(third, "state_replayed")

    def test_missing_code_behavior_is_preserved(self) -> None:
        case = scenario("valid")
        case["query"].pop("code")
        result = handle_callback(case["query"], case["session"], FIXED_NOW)
        self.assert_error(result, "missing_code")
        self.assertIn("oauth_request", case["session"])

    def test_malformed_pending_records_fail_closed(self) -> None:
        pending_cases = (
            ("none", None),
            ("empty-record", {}),
            ("non-record", ["invalid"]),
            ("non-string-state", {"state": 7}),
            ("empty-state", {"state": ""}),
        )
        for label, pending in pending_cases:
            with self.subTest(case=label):
                case = scenario("valid")
                case["session"]["oauth_request"] = pending
                result = handle_callback(case["query"], case["session"], FIXED_NOW)
                self.assert_error(result, "state_mismatch")

    def test_invalid_expiration_values_fail_closed(self) -> None:
        for label, expires_at in (("missing", None), ("string", "future"), ("boolean", True)):
            with self.subTest(case=label):
                case = scenario("valid")
                case["session"]["oauth_request"]["expires_at"] = expires_at
                result = handle_callback(case["query"], case["session"], FIXED_NOW)
                self.assert_error(result, "state_expired")
                self.assertIn("oauth_request", case["session"])

    def test_default_success_return_path_is_preserved(self) -> None:
        case = scenario("valid")
        case["session"]["oauth_request"].pop("return_to")
        result = handle_callback(case["query"], case["session"], FIXED_NOW)
        self.assertEqual(result, CallbackResult(status="ok", redirect_to="/"))
        self.assertNotIn("oauth_request", case["session"])

    def test_exact_serialized_scenarios_are_stable_and_credential_free(self) -> None:
        ok = {"status": "ok", "category": None, "redirect_to": "/dashboard"}
        def error(category: str) -> dict[str, str | None]:
            return {"status": "error", "category": category, "redirect_to": None}
        expected = {
            "valid": [ok],
            "missing": [error("missing_state")],
            "mismatched": [error("state_mismatch")],
            "expired": [error("state_expired")],
            "replayed": [ok, error("state_replayed")],
        }
        first = run()
        second = run()
        self.assertEqual(first, expected)
        first_json = json.dumps(first, indent=2, sort_keys=True)
        self.assertEqual(first_json, json.dumps(second, indent=2, sort_keys=True))
        sensitive_values = (
            SYNTHETIC_CODE,
            EXPECTED_STATE,
            scenario("mismatched")["query"]["state"],
        )
        for index, value in enumerate(sensitive_values):
            with self.subTest(sensitive_value_index=index):
                self.assertTrue(value not in first_json, "serialized output contains a sensitive fixture value")


if __name__ == "__main__":
    unittest.main()
