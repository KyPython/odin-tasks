"""Ordinary-path baseline coverage for the learner starter."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from callback import CallbackResult, handle_callback  # noqa: E402
from fixtures import FIXED_NOW, SYNTHETIC_CODE, scenario  # noqa: E402


class CallbackBaselineTests(unittest.TestCase):
    def test_valid_callback_preserves_return_path(self) -> None:
        case = scenario("valid")

        result = handle_callback(case["query"], case["session"], FIXED_NOW)

        self.assertEqual(
            result,
            CallbackResult(status="ok", redirect_to="/dashboard"),
        )
        self.assertNotIn("oauth_request", case["session"])

    def test_serialized_success_omits_authorization_code(self) -> None:
        case = scenario("valid")

        result = handle_callback(case["query"], case["session"], FIXED_NOW)

        self.assertNotIn(SYNTHETIC_CODE, str(result.as_dict()))


if __name__ == "__main__":
    unittest.main()
