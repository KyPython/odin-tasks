### Recording sequence — follow this order
**Step 1.** After the actual checklist passes, click **Start Recording** and immediately minimize TaskRecorder. With the exact Goal-only document visible in its separate VS Code window, say: **“I will be beginning my task soon. Here is the workflow I have in mind. I’ll check the current behavior, add fixed-time checks, inject one clock reading, and verify the results across timezones.”** Keep the introduction under 20 seconds; do not read the full Goal aloud. Click the Goal window's yellow minimize button, then use VS Code's **Window** menu to bring the already-open `dispatch-board` project window forward.
**Step 2.** In Explorer expand `docs` and open `behavior.md`. Read the actual dispatch-location date contract. Choose **Terminal → New Terminal**. Run the commands separately in this order; the first command puts this terminal in the prepared project.
```bash
cd ~/Desktop/TaskWork/dispatch-board
TZ=UTC python3 -m unittest discover -s tests -v
python3 scripts/show_timezone_variation.py
```
The UTC baseline should show `Ran 1 test` and `OK`. The helper prints its two actual child outcomes and itself exits 0 even when a child fails. Its original outcomes depend on the recording time: the disposable rehearsal saw Kiritimati pass and GMT+12 fail, but do not promise that result today. If the outcomes differ, say **“The same original test produced different results under the displayed host timezones.”** If they match, say **“The original outcomes match at this instant; this run alone does not establish deterministic behavior.”** No live timezone flip is needed to continue with the deterministic regression check below.
**Step 3.** Open `src/dispatch_board/labels.py`, then `tests/test_labels.py`. Point to the two `datetime.now` calls, both branches assigning `local_day`, and the original test deriving its expectation from the current UTC date. Say **“My prepared plan addresses two observable dependencies: this function reads time twice and returns the host-local date in both branches. I’ll use one aware instant, convert it to the dispatch timezone, and test fixed boundary instants.”** The implementation below retains the existing two-argument call by making the injected clock optional.
**Step 4.** Open `tests/test_labels.py`. Replace its complete contents with the prepared regression tests below. Choose **File → Save All**. The default-clock regression holds the original two-argument API to a known location-date result; the injected-clock cases cover fixed normal time, local midnight, positive offset, both DST transitions, one read and invalid inputs.
```python
"""Deterministic dispatch-location date and clock-boundary coverage."""

import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfoNotFoundError
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from dispatch_board import dispatch_label


class DispatchLabelTests(unittest.TestCase):
    def assert_label_at(self, instant_text, location_timezone, expected_day):
        instant = datetime.fromisoformat(instant_text)
        self.assertEqual(
            dispatch_label("ROUTE-17", location_timezone, clock=lambda: instant),
            f"ROUTE-17 | {expected_day}",
        )

    def test_default_clock_uses_location_date(self):
        instant = datetime.fromisoformat("2026-01-01T04:59:59+00:00")
        with patch("dispatch_board.labels.datetime") as system_clock:
            system_clock.now.return_value = instant
            self.assertEqual(
                dispatch_label("ROUTE-17", "America/New_York"),
                "ROUTE-17 | 2025-12-31",
            )
            system_clock.now.assert_called_once_with(timezone.utc)

    def test_normal_fixed_instant(self):
        self.assert_label_at("2026-10-05T12:30:00+00:00", "UTC", "2026-10-05")

    def test_location_midnight_before_and_after(self):
        cases = (
            ("2026-01-01T04:59:59+00:00", "2025-12-31"),
            ("2026-01-01T05:00:00+00:00", "2026-01-01"),
        )
        for instant, expected in cases:
            with self.subTest(instant=instant):
                self.assert_label_at(instant, "America/New_York", expected)

    def test_positive_offset_changes_calendar_date(self):
        self.assert_label_at(
            "2025-12-31T10:00:00+00:00", "Pacific/Kiritimati", "2026-01-01"
        )

    def test_spring_dst_transition(self):
        for instant in ("2026-03-08T06:59:59+00:00", "2026-03-08T07:00:00+00:00"):
            with self.subTest(instant=instant):
                self.assert_label_at(instant, "America/New_York", "2026-03-08")

    def test_fall_dst_transition(self):
        for instant in ("2026-11-01T05:59:59+00:00", "2026-11-01T06:00:00+00:00"):
            with self.subTest(instant=instant):
                self.assert_label_at(instant, "America/New_York", "2026-11-01")

    def test_clock_is_read_once(self):
        readings = []

        def fixed_clock():
            readings.append("read")
            return datetime.fromisoformat("2026-10-05T12:30:00+00:00")

        self.assertEqual(
            dispatch_label("ROUTE-17", "UTC", clock=fixed_clock),
            "ROUTE-17 | 2026-10-05",
        )
        self.assertEqual(readings, ["read"])

    def test_naive_clock_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "timezone-aware"):
            dispatch_label("ROUTE-17", "UTC", clock=lambda: datetime(2026, 1, 1))

    def test_unknown_location_timezone_is_rejected(self):
        instant = datetime.fromisoformat("2026-10-05T12:30:00+00:00")
        with self.assertRaises(ZoneInfoNotFoundError):
            dispatch_label("ROUTE-17", "TaskWork/Not_A_Zone", clock=lambda: instant)


if __name__ == "__main__":
    unittest.main()
```
**Step 5.** Run this before editing production code. The second command immediately prints the unittest command's actual exit status.
```bash
TZ=UTC python3 -m unittest discover -s tests -v
printf 'Strengthened-suite exit code: %s\n' "$?"
```
For the exact saved tests on the pinned starter, the observed deterministic result is `Ran 9 tests`, `FAILED (failures=1, errors=11)`, exit 1. The default-clock failure displays actual `ROUTE-17 | 2026-01-01` versus expected `ROUTE-17 | 2025-12-31`; the other errors report the missing `clock` keyword API. Say **“The fixed default-clock check exposes the incorrect date, and the other cases cannot yet supply the planned clock. These are the expected before-repair failures.”** If your saved file produces another result, follow the recovery notes; do not narrate an unobserved failure.
**Step 6.** Open `src/dispatch_board/labels.py`. Replace its complete contents with this bounded implementation and choose **File → Save All**. Say **“This prepared change reads one timezone-aware instant, rejects a naive injected value, and converts that instant to the location date. The original two-argument call uses one aware UTC reading by default.”**
```python
"""Create labels displayed on a dispatch board."""

from collections.abc import Callable
from datetime import datetime, timezone
from zoneinfo import ZoneInfo


Clock = Callable[[], datetime]


def dispatch_label(
    dispatch_id: str,
    location_timezone: str,
    *,
    clock: Clock | None = None,
) -> str:
    """Use one timezone-aware clock reading and the dispatch location's date."""
    instant = datetime.now(timezone.utc) if clock is None else clock()
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise ValueError("clock must return a timezone-aware datetime")

    location_day = instant.astimezone(ZoneInfo(location_timezone)).date()
    return f"{dispatch_id} | {location_day.isoformat()}"
```
**Step 7.** Run the exact regression suite again and inspect its actual summary.
```bash
TZ=UTC python3 -m unittest discover -s tests -v
printf 'Repaired-suite exit code: %s\n' "$?"
```
The verified result is `Ran 9 tests`, `OK`, exit 0. If you observe that result, say **“All nine test methods pass, including the known midnight date, DST boundary instants and the one-read check.”** `Ran 9 tests` counts methods; some methods contain multiple boundary subtests. The DST assertions cover this API's calendar-date result on both sides of each transition; they do not claim to display or validate a clock hour/offset API.
**Step 8.** Choose **File → Save All** and run this subshell. It executes the nine methods three times per host timezone and stops at the first unsuccessful command.
```bash
(
  set -e
  for verification_run in 1 2 3; do
    printf 'Verification run %s\n' "$verification_run"
    TZ=Pacific/Kiritimati python3 -m unittest discover -s tests -v
    TZ=Etc/GMT+12 python3 -m unittest discover -s tests -v
  done
)
```
The reference observed six `Ran 9 tests` / `OK` summaries. Only after all six appear, say **“The fixed suite passed three times in each of these two different host timezones. Its expected dates come from fixed instants and location timezones.”** If any run fails, use the recovery notes and rerun this complete block after saving.
**Step 9.** Run the existing helper against the saved repaired implementation.
```bash
python3 scripts/show_timezone_variation.py
```
The checked result is `Pacific/Kiritimati: pass` and `Etc/GMT+12: pass`, with a nine-method passing suite for each child. Its “outcomes matched” sentence is accurate for the repaired tests. Say **“Both helper child suites pass. The explicit repeated test results establish the outcome; the helper's own zero exit alone would not.”**
**Step 10.** Return to the saved production function and fixed boundary tests so the final deliverables are visible. Say **“The label now uses the dispatch location's date from one instant. The saved tests cover the normal case, midnight, both DST transitions, host timezone independence, one read and invalid clock/timezone inputs. The commands shown verify these synthetic cases.”** Claim this only if the preceding summaries passed. Choose **File → Save All**, bring TaskRecorder forward, click **Stop Recording**, and wait for **Stopping → Archiving → Idle**. Review the actual capture and prepare the required upload/Final Notes through the existing checklist. Keep prior-work and `AI-generated before recording` disclosure truthful outside capture.
