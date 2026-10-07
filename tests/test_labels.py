"""Starter coverage for dispatch labels."""

import sys
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from dispatch_board import dispatch_label


class DispatchLabelTests(unittest.TestCase):
    def test_label_uses_dispatch_location_date(self) -> None:
        location_timezone = "UTC"
        expected_day = datetime.now(ZoneInfo(location_timezone)).date().isoformat()

        self.assertEqual(
            dispatch_label("ROUTE-17", location_timezone),
            f"ROUTE-17 | {expected_day}",
        )


if __name__ == "__main__":
    unittest.main()
