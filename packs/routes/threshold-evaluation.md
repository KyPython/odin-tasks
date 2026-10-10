### Recording sequence — follow this order
**Step 1.** After **Before practice — Recorder checks** in the existing Bootcamp runbook passes for this actual attempt, keep the unchanged project open behind the separate exact candidate Goal window. Click **Start Recording**, immediately minimize TaskRecorder and say: “I will be beginning my task soon. Here is the workflow I have in mind.” Minimize the Goal window with its yellow button and choose **threshold-evaluation** through VS Code's **Window** menu. This is guided internal practice, with no Odin approval or Studio assignment.
**Step 2.** With the project forward, say: “This guided plan uses prepared tests and calculations to check the threshold report.” Open `README.md`, then `fixtures/observations.json` and `fixtures/policy.json` from Explorer. Point to the inclusive score boundary (a score equal to the threshold is predicted positive), FN cost 9, FP cost 2 and minimum-cost/lowest-threshold selection. Choose **Terminal → New Terminal**, then run:
```bash
cd "$HOME/Desktop/TaskWork/threshold-evaluation"
python3 --version
PYTHONPATH=src python3 -m unittest discover -s tests -v > baseline-tests.txt 2>&1
baseline_result=$?
cat baseline-tests.txt
printf 'Baseline exit: %s\n' "$baseline_result"
```
Observed reference result: **Python 3.12.7**, **Ran 4 tests**, **OK**, exit **0**. Say only the actual displayed result. If the version, directory, test count or starting suite differs, stop this sequence and preserve the attempt for setup/source review; do not reset prior human work or invent the expected baseline.
**Step 3.** Open `src/threshold_lab/evaluation.py`, `src/threshold_lab/io.py`, `src/threshold_lab/cli.py`, `tests/test_evaluation.py` and `tests/test_io.py` from Explorer. Point to the two mislabeled error counts and the accuracy selector. Generate the original report:
```bash
PYTHONPATH=src python3 -m threshold_lab.cli --observations fixtures/observations.json --policy fixtures/policy.json > report-before.json
generation_result=$?
cat report-before.json
printf 'Original report generation exit: %s\n' "$generation_result"
```
The observed original report selects **0.85** and lists costs **47, 29, 22, 4** at thresholds **0.3, 0.5, 0.7, 0.85**. Narration: “The prepared calculation at 0.5 has two true positives, two true negatives, three false positives and one false negative, so its cost is nine plus six, or fifteen. The code swaps the two error categories and chooses accuracy. The reference table gives costs nineteen, fifteen, twenty-two and eighteen; the minimum is 0.5.” Keep production unchanged until the red test demonstration. If generation exits nonzero, do not treat a partial JSON file as evidence; correct only an observed command-copy slip and rerun this step, otherwise preserve the unexpected result.
**Step 4.** Open `tests/test_evaluation.py` in Explorer, choose **Edit → Select All** in that editor and replace the file with this complete prepared test text:
```python
from __future__ import annotations

import unittest
from pathlib import Path

from threshold_lab.evaluation import Evaluation, Observation, Policy, build_report, evaluate_threshold
from threshold_lab.io import load_observations, load_policy


EXPECTED_REPORT = {
    "costs": {"false_negative": 9, "false_positive": 2},
    "candidates": [
        {"threshold": 0.3, "true_positive": 2, "true_negative": 0, "false_positive": 5,
         "false_negative": 1, "accuracy": 0.25, "total_cost": 19},
        {"threshold": 0.5, "true_positive": 2, "true_negative": 2, "false_positive": 3,
         "false_negative": 1, "accuracy": 0.5, "total_cost": 15},
        {"threshold": 0.7, "true_positive": 1, "true_negative": 3, "false_positive": 2,
         "false_negative": 2, "accuracy": 0.5, "total_cost": 22},
        {"threshold": 0.85, "true_positive": 1, "true_negative": 5, "false_positive": 0,
         "false_negative": 2, "accuracy": 0.75, "total_cost": 18},
    ],
    "selected_threshold": 0.5,
}


class EvaluationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = Policy((0.25, 0.75), false_negative_cost=4, false_positive_cost=1)
        self.observations = (
            Observation("north", 0.9, True),
            Observation("south", 0.1, False),
        )

    def test_clear_predictions_are_counted_as_correct(self) -> None:
        result = evaluate_threshold(self.observations, 0.5, self.policy)

        self.assertEqual(result.true_positive, 1)
        self.assertEqual(result.true_negative, 1)
        self.assertEqual(result.accuracy, 1.0)

    def test_report_sorts_candidates_and_retains_cost_configuration(self) -> None:
        report = build_report(self.observations, Policy((0.75, 0.25), 4, 1))

        self.assertEqual(
            [candidate["threshold"] for candidate in report["candidates"]],
            [0.25, 0.75],
        )
        self.assertEqual(report["costs"], {"false_negative": 4, "false_positive": 1})

    def test_empty_observations_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "at least one observation"):
            build_report((), self.policy)


    def fixture_inputs(self):
        root = Path(__file__).resolve().parents[1]
        return (load_observations(root / "fixtures/observations.json"),
                load_policy(root / "fixtures/policy.json"))

    def test_all_four_cells_and_inclusive_score_boundary(self) -> None:
        rows = (
            Observation("tp", 0.5, True),
            Observation("tn", 0.49, False),
            Observation("fp-boundary", 0.5, False),
            Observation("fp-high", 0.9, False),
            Observation("fn", 0.49, True),
        )
        result = evaluate_threshold(rows, 0.5, Policy((0.5,), 9, 2))
        self.assertEqual(result, Evaluation(0.5, 1, 1, 2, 1, 0.4, 13))

    def test_fixture_candidate_counts_and_costs(self) -> None:
        rows, policy = self.fixture_inputs()
        self.assertEqual(build_report(rows, policy)["candidates"], EXPECTED_REPORT["candidates"])

    def test_fixture_selects_cost_over_accuracy(self) -> None:
        rows, policy = self.fixture_inputs()
        report = build_report(rows, policy)
        self.assertEqual(report["selected_threshold"], 0.5)
        self.assertEqual(report["candidates"][-1]["accuracy"], 0.75)
        self.assertEqual(report["candidates"][1]["accuracy"], 0.5)

    def test_equal_cost_prefers_lowest_threshold_not_accuracy(self) -> None:
        rows = (Observation("positive", 0.9, True), Observation("negative", 0.6, False))
        report = build_report(rows, Policy((0.7, 0.5), 0, 0))
        self.assertEqual([candidate["threshold"] for candidate in report["candidates"]], [0.5, 0.7])
        self.assertEqual([candidate["total_cost"] for candidate in report["candidates"]], [0, 0])
        self.assertEqual(report["selected_threshold"], 0.5)

    def test_policy_weights_change_selection(self) -> None:
        rows, _ = self.fixture_inputs()
        for false_negative_cost, false_positive_cost, selected in ((9, 2, 0.5), (1, 9, 0.85)):
            with self.subTest(costs=(false_negative_cost, false_positive_cost)):
                report = build_report(rows, Policy((0.85, 0.7, 0.5, 0.3), false_negative_cost, false_positive_cost))
                self.assertEqual(report["selected_threshold"], selected)

    def test_empty_candidate_thresholds_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "at least one candidate threshold"):
            build_report(self.observations, Policy((), 9, 2))

    def test_generator_input_matches_complete_expected_report(self) -> None:
        rows, policy = self.fixture_inputs()
        self.assertEqual(build_report((row for row in rows), policy), EXPECTED_REPORT)


if __name__ == "__main__":
    unittest.main()
```
Choose **File → Save All**. Narration: “The original four tests cover ordinary paths. These prepared additions check exact labels and amounts, the inclusive score boundary, changed cost weights, cost ties, empty candidates and generator input. They retain the useful starter tests and the separate IO check.” Do not claim independent authorship of this prepared test file.
**Step 5.** With production still unchanged, run the stronger suite and save its test digest:
```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v > stronger-before-repair.txt 2>&1
test_result=$?
cat stronger-before-repair.txt
printf 'Before-repair test exit: %s\n' "$test_result"
shasum -a 256 tests/test_evaluation.py > tests-before.sha256
cat tests-before.sha256
```
Observed reference result: **Ran 11 tests**, **FAILED (failures=6)**, exit **1**. Failures are `test_all_four_cells_and_inclusive_score_boundary`, `test_fixture_candidate_counts_and_costs`, `test_fixture_selects_cost_over_accuracy`, `test_equal_cost_prefers_lowest_threshold_not_accuracy`, `test_policy_weights_change_selection` and `test_generator_input_matches_complete_expected_report`. Narration: “These six failures concern the documented counts or selected threshold. They are the planned negative control, rather than syntax or import errors.” If a visible typing/copying slip caused another error, compare the exact Step 4 file, correct that discrepancy, choose **File → Save All** and repeat Step 5. If the six semantic failures are absent or a new failure is unexplained, stop rather than weakening expectations.
**Step 6.** Open `src/threshold_lab/evaluation.py`. Use **Command-F** to locate `false_positive = sum(row.actual and row.score < threshold for row in rows)`, then Escape to return to the editor. Select only that assignment text, leaving the existing four-space indentation, and replace it with:
```python
false_positive = sum(not row.actual and row.score >= threshold for row in rows)
```
Likewise locate `false_negative = sum(not row.actual and row.score >= threshold for row in rows)` and replace only its assignment text, retaining the four-space indentation, with:
```python
false_negative = sum(row.actual and row.score < threshold for row in rows)
```
Leave the selector and all other production lines unchanged. Choose **File → Save All**. Narration: “A false positive is an actual negative predicted positive; a false negative is an actual positive predicted negative. This first phase corrects those labels and their weighted costs without changing the selection rule.”
**Step 7.** Show that count repair alone leaves the selector defect:
```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v > counts-only-tests.txt 2>&1
counts_result=$?
cat counts-only-tests.txt
printf 'Counts-only test exit: %s\n' "$counts_result"
PYTHONPATH=src python3 -m threshold_lab.cli --observations fixtures/observations.json --policy fixtures/policy.json > counts-only-report.json
counts_report_result=$?
cat counts-only-report.json
printf 'Counts-only report generation exit: %s\n' "$counts_report_result"
```
Observed reference result: **Ran 11 tests**, **FAILED (failures=4)**, test exit **1**; report generation exit **0**, correct candidate costs **19, 15, 22, 18**, but selected threshold still **0.85**. The remaining failures are the fixture-selection, equal-cost tie, policy-weight and generator-report methods. Narration: “The count assertions now pass. Selection still chooses the higher accuracy, even though 0.5 costs fifteen and 0.85 costs eighteen. That isolates the second defect.” For a small unsaved/typed count-line discrepancy, correct only the exact Step 6 text, **File → Save All**, and rerun Step 7. Preserve unexplained results rather than improvising a different repair.
**Step 8.** In `src/threshold_lab/evaluation.py`, use **Command-F** to locate the exact assignment `selected = max(evaluations, key=lambda item: (item.accuracy, -item.threshold))`, Escape to return to the editor, and replace only its assignment text while retaining the four-space indentation:
```python
selected = min(evaluations, key=lambda item: (item.total_cost, item.threshold))
```
Leave all remaining source/configuration/fixtures unchanged. Choose **File → Save All**, then run:
```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v > stronger-after-repair.txt 2>&1
repaired_result=$?
cat stronger-after-repair.txt
printf 'After-repair test exit: %s\n' "$repaired_result"
shasum -a 256 tests/test_evaluation.py > tests-after.sha256
cmp tests-before.sha256 tests-after.sha256
digest_result=$?
printf 'Test digest comparison exit: %s\n' "$digest_result"
PYTHONPATH=src python3 -m threshold_lab.cli --observations fixtures/observations.json --policy fixtures/policy.json > report.json
report_result=$?
cat report.json
printf 'Corrected report generation exit: %s\n' "$report_result"
```
Observed reference result: **Ran 11 tests**, **OK**, test exit **0**; digest comparison **0**; report generation **0**, selected threshold **0.5**, with costs **19, 15, 22, 18** in ascending threshold order. Narration: “The same stronger tests now pass. Minimum total cost is the first selection key, and the lower numerical threshold resolves equal costs. Accuracy is still reported but does not override the stated error costs.” If the digest differs, restore the exact Step 4 test file and restore only the three original assignments shown in Steps 6/8; **File → Save All**, repeat Step 5, then Steps 6–8. For an observed unsaved/typed selection-line slip, correct the exact line, **File → Save All** and rerun Step 8. Do not claim success for an unexplained failure or nonzero report generation.
**Step 9.** Choose **File → Save All** before the independent report check and repeated generation. Run this prepared check, which reads fixture JSON and classifies observations without importing the production evaluator:
```bash
python3 - <<'PY'
import json
from pathlib import Path
rows = json.loads(Path("fixtures/observations.json").read_text())
policy = json.loads(Path("fixtures/policy.json").read_text())
report = json.loads(Path("report.json").read_text())
calculated = []
for threshold in sorted(policy["candidate_thresholds"]):
    counts = dict(true_positive=0, true_negative=0, false_positive=0, false_negative=0)
    for row in rows:
        if row["actual"]:
            category = "true_positive" if row["score"] >= threshold else "false_negative"
        else:
            category = "false_positive" if row["score"] >= threshold else "true_negative"
        counts[category] += 1
    cost = counts["false_negative"] * policy["false_negative_cost"] + counts["false_positive"] * policy["false_positive_cost"]
    calculated.append(dict(threshold=threshold, **counts, accuracy=(counts["true_positive"] + counts["true_negative"])/len(rows), total_cost=cost))
assert report["candidates"] == calculated
assert [row["total_cost"] for row in calculated] == [19, 15, 22, 18]
assert report["selected_threshold"] == 0.5
assert min(calculated, key=lambda row: (row["total_cost"], row["threshold"]))["threshold"] == 0.5
print(json.dumps({"independentCountsAndCosts": True, "selectedThreshold": 0.5, "selectedCost": 15}, sort_keys=True))
PY
oracle_result=$?
printf 'Independent arithmetic exit: %s\n' "$oracle_result"
PYTHONPATH=src python3 -m threshold_lab.cli --observations fixtures/observations.json --policy fixtures/policy.json > report-repeat.json
repeat_result=$?
printf 'Repeated report generation exit: %s\n' "$repeat_result"
if [ "$report_result" -eq 0 ] && [ "$repeat_result" -eq 0 ]; then
  cmp report.json report-repeat.json
  comparison_result=$?
  printf 'Report comparison exit: %s\n' "$comparison_result"
else
  printf '%s\n' 'HOLD: a report generation failed; comparison is not evidence.'
fi
PYTHONPATH=src python3 -m unittest discover -s tests -v > repeated-tests.txt 2>&1
repeated_tests_result=$?
cat repeated-tests.txt
printf 'Repeated test exit: %s\n' "$repeated_tests_result"
```
Observed reference result: independent check prints `{"independentCountsAndCosts": true, "selectedCost": 15, "selectedThreshold": 0.5}`, exits **0**; repeated generation and report comparison exit **0**; repeated suite **Ran 11 tests**, **OK**, exit **0**. Narration: “The separate classification check confirms every candidate's counts and cost against the fixture. Equal complete JSON bytes establish repeatability; the assertions and independent arithmetic establish correctness for these cases.” If a displayed command-copy slip caused failure, correct that exact slip and rerun this full step; after any file edit choose **File → Save All** and rerun Steps 8–9. An unexpected arithmetic or byte difference is a HOLD, not a reason to alter expected costs.
**Step 10.** Only after those results actually occur, choose Explorer's **New File**, name it `verification-note.md`, and type this note, adjusting any observed result that differs rather than claiming the prepared proof was your recording:
```markdown
# Guided threshold evaluation verification
This internal practice attempt followed an AI-written prepared plan.
The source starter was unworked before capture; the edits and checks below were performed during this attempt.
The three production changes corrected FP/FN labels and selected minimum total cost with lowest-threshold tie-break.
At 0.3/0.5/0.7/0.85 the correct TP,TN,FP,FN counts are:
0.3: 2,0,5,1; cost19; accuracy0.25.
0.5: 2,2,3,1; cost15; accuracy0.5.
0.7: 1,3,2,2; cost22; accuracy0.5.
0.85: 1,5,0,2; cost18; accuracy0.75.
Selected threshold:0.5, cost15 under FN9/FP2.
Observed tests: starter4 pass; stronger11 with6 failures before repair; counts-only11 with4 failures; same11 pass after full repair and on repetition.
Test-file digest comparison and complete report-byte comparison returned0; independent classification/weighted-cost check passed.
Actual report.json is the deliverable; report-repeat.json is comparison evidence.
This guided plan does not claim unaided transfer, mastery, Odin approval or paid submission.
```
Choose **File → Save All**. Open the saved note, `report.json`, `report-repeat.json`, before/after test logs and corrected source/tests in Explorer. These files must be the actual attempt's output; preparation proofs and after-files remain off-screen.
**Step 11.** Choose **File → Save All** once more. Bring TaskRecorder forward, click **Stop Recording**, and wait for **Stopping → Archiving → Idle**. Follow the existing internal Bootcamp runbook to inspect the actual archive/video and collect review evidence. Preserve the exact candidate Goal, truthful prepared-plan provenance and all unearned assessment gates. This is internal guided practice; no Odin submission, external approval or unaided-transfer credit is claimed.
