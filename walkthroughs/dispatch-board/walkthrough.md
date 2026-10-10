# Dispatch board — worked reference

Pinned source: `https://github.com/KyPython/flaky-clock-injection` at `e5652bcb044cd24d2a7d1c2f8bb93b885cea2069` (six starter files). Exact Goal SHA-256: `d416388e21c90e58bc75316bf7864589fb34850d3184bbb06e12b0a378d8000d`.

Exact approved Goal:
> As a software engineer, diagnose a synthetic Python test that fails intermittently because the code under test reads the system clock and local timezone, refactor the function to accept an injected clock, rewrite the test to use fixed timestamps including a midnight and DST boundary, and verify the test passes deterministically across repeated runs and different TZ settings.

### Source instructions and truthful preparation

This is an AI-authored worked reference prepared and rehearsed off-screen at the user's explicit request. The repair and tests have already been analyzed and implemented in disposable reference copies. The original pinned starter inputs and actual recording workspace were not repaired, and no Recorder session was run. Do not attest that no prior analysis or implementation exists; describe this separate preparation accurately wherever prior work is requested. The narration below identifies a prepared plan and observable results, without claiming spontaneous discovery or independent authorship.

The source is the original local **Project Odin Writer Guidelines.pdf**, SHA-256 `af751a041a8855eda3872b795b09f8c12a70c50679f38c47ee22750a9b4c0f81`. Page numbers here are PDF page numbers. Page 27 permits eligible AI-prepared inputs before recording, requires the exact Final Notes disclosure **AI-generated before recording**, and prohibits AI interaction/branding during capture. Page 45 requires privacy cleanup, an allowed Goal-only opening document, and an unworked task start. Page 63 requires knowing the steps before starting and correcting ordinary slips; material unresolved errors or prolonged guessing require stopping/restarting. Pages 87–89 require suitable licenses/privacy for prepared content, prohibit AI generation/revision/assistant interaction during capture, and keep preparation disclosure outside the recording.

Those pages do not explicitly establish acceptance of a complete AI-authored repair-and-test walkthrough. **External solution-walkthrough eligibility remains unresolved.** This reference does not grant approval, claim professional expertise, promise payment or set any human recording/submission gate. Review the current assignment and truthful prior-work requirements before relying on it for a submitted attempt. The original Goal, approval ID and input provenance remain unchanged.

Keep this walkthrough, patches, after-files, verification proof, Notion and all preparation/AI windows off the captured display. Use the prepared code as an off-screen reference for the editing method actually permitted for the attempt. Do not apply the reference patches to the recording project before capture. If code is copied rather than independently composed, disclose that actual method outside capture; do not silently describe it as independent authorship. No AI assistant interaction or generation occurs in the numbered route.

### Off-screen setup before the route

Use the existing account/audio/display/privacy and Odin pre-record checklist with the actual approved Studio task; none of those human checks were completed by this reference. In the real Recorder account, prepare only this selected unworked task with the installed helper command below. A successful per-task receipt is setup evidence only. Reuse an already prepared matching workspace; the helper deliberately refuses to overwrite an edited selected task. Preserve earlier attempts and stop before capture if the selected copy is edited, incomplete or its source/Goal pins do not match.

```bash
/bin/zsh /Users/Shared/TaskWorkRuntime/Prepare-TaskWork.command --task dispatch-board
```

Open `~/Desktop/TaskWork/dispatch-board.code-workspace` in the clean recording VS Code instance. Open its sibling `~/Desktop/TaskWork/dispatch-board-goal.txt` in a separate window of that same instance. Confirm the exact Goal text is the only opening document content; hide IDs, scripts and admin material. Disable AI features/extensions at the instance/user level so both windows are clean, leave only permitted task apps ready, and minimize them according to the checklist. This reference has not executed that Recorder setup or verified its microphone/capture. Confirm the selected project's terminal uses the public Python version prepared by the helper before recording.

The deliverables are `src/dispatch_board/labels.py` and `tests/test_labels.py`. The `after/` copies and three patch files below live outside starter inputs and captured work. `tests.patch` is the failure-producing test/fixture phase; `repair.patch` is the bounded implementation phase; `solution.patch` is their exact concatenation. They are rehearsal artifacts, not a shortcut to a repaired recording start.

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

### Recovery for predictable slips

If unittest reports `Ran 0 tests`, compare the terminal location with `~/Desktop/TaskWork/dispatch-board`, run the explicit `cd` above and rerun; do not call that a pass. An import error means check that `src/dispatch_board/labels.py` and the exact test path exist, and compare your saved imports/indentation with the complete text. A missing `clock` keyword is expected only in Step 5; after Step 6 it usually means the production file was unsaved or the wrong project was opened. A date mismatch after repair means compare the timestamp's `+00:00`, the timezone name, and `instant.astimezone(...).date()` against the prepared text; do not change the expected date to make a failure disappear. `ZoneInfoNotFoundError` for a real test zone indicates missing runtime timezone data: stop before continuing and repair setup off-screen; do not replace the zone or weaken the test. Correct a small visible typing slip, save and rerun the exact relevant command. For a material unexplained difference, stop capture and preserve it for review; do not improvise or claim success. Never rerun setup to reset an edited project.

### Actual disposable verification and reproducibility

`verification.json` records 19 actual command/result checks with public Python 3.12.7, the source/Goal and patch hashes, before/after immutable input inventory, independent combined-versus-phased patch equality, and preserved runtime identity. It confirms no source repository/recording workspace modification and no Recorder execution. Complete final files are in `after/`. The original six pinned files remain unmodified.

For a fresh off-screen disposable proof (outside recording work), run `rehearse.py` with the currently installed inputs/runtime. It validates registry/manifest/source modes and exact Goal, copies only this task into a temporary directory, performs the expected failure and repair phases, and deletes its copies. The command creates a fresh private directory owned by the invoking account; it preserves the installed proof and all captured work. This command does not perform actual Recorder setup or set a human gate.
```bash
proof_dir="$(mktemp -d /private/tmp/taskwork-dispatch-board-reference.XXXXXX)"
/usr/local/bin/python3 /Users/Shared/TaskWorkPlans/dispatch-board/rehearse.py --inputs /Users/Shared/TaskWorkInputs --runtime /Users/Shared/TaskWorkRuntime --output "$proof_dir/proof.json"
```
The script derives its cloud seed from `cloud-proof.json` and has no fixed preparation run ID. Its source commit and Goal are intentionally fixed to this reviewed task revision; a source change requires a new reviewed reference.
