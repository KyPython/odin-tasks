### Recording sequence — follow this order
**Step 1.** After the actual checklist passes, click **Start Recording** and immediately minimize TaskRecorder. With the exact Goal-only document visible in its separate VS Code window, say: **“I will be beginning my task soon. Here is the workflow I have in mind. I’ll map the contract to intake, add a negative fixture, enforce clearance, and check accepted and rejected cases.”** Keep the introduction under 20 seconds; do not read the full Goal aloud. Click the Goal window's yellow minimize button, then use VS Code's **Window** menu to bring the already-open `evaluation-handoff` project window forward.
**Step 2.** In Explorer expand `docs` and open `evaluation-contract.md`. Read the four exact pre-grading requirements. Open `scripts/verify.sh`, choose **Terminal → New Terminal**, and run the baseline commands separately.
```bash
cd ~/Desktop/TaskWork/evaluation-handoff
sh scripts/verify.sh
python3 -m grader.pipeline fixtures/valid/manifest.json
```
The verified starter result is three passing tests and `sample_001: 3`; the direct valid command also prints that score and exits 0. Use `sh` because the starter verification file is not executable. If your actual results match, say **“The existing three checks and valid score pass, but they do not yet cover every written pre-grading requirement.”** Follow recovery notes for a mismatch.
**Step 3.** Open `grader/pipeline.py`, `grader/intake.py`, then `grader/scoring.py`. Observe that `run` calls intake before `score`, and intake checks ID, contained path, nonempty artifact and digest. Read exact contract requirement 4 aloud: “`clearance` is the string `approved`.” Say **“My prepared comparison found that this intake path does not enforce that requirement. I’ll add one exact clearance guard before intake returns an accepted submission and test that rejection occurs before scoring.”** This synthetic clearance field is separate from any platform task approval.
**Step 4.** In Explorer right-click `fixtures`, choose **New Folder**, and name it `negative`. Create `fixtures/negative/artifact.txt` inside it with these exact contents, including the blank second line and a final newline after `gamma`. The bytes intentionally match the valid fixture so the clearance field is the bounded negative condition.
```plain text
alpha

beta
gamma
```
Create `fixtures/negative/manifest.json` with this exact content. The artifact digest is the real SHA-256 of those unchanged fixture bytes; do not use a placeholder.
```json
{
  "submission_id": "sample_negative_001",
  "artifact": "artifact.txt",
  "sha256": "87a3c52b88cf5eeec4bff79b5f65de20adbdb2d79a7f78d93f996a319c42ff5f",
  "clearance": "pending"
}
```
**Step 5.** Open `tests/test_pipeline.py` and replace its complete contents with this prepared suite. It preserves the three original cases, adds the real negative fixture and malformed-clearance cases, and checks that `grader.pipeline.score` is not called when intake rejects. Choose **File → Save All**.
```python
from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from grader.intake import IntakeError, accept_manifest
from grader.pipeline import run


ROOT = Path(__file__).resolve().parents[1]
VALID_MANIFEST = ROOT / "fixtures" / "valid" / "manifest.json"
NEGATIVE_MANIFEST = ROOT / "fixtures" / "negative" / "manifest.json"


class PipelineTests(unittest.TestCase):
    def test_valid_submission_is_scored_deterministically(self) -> None:
        self.assertEqual(run(VALID_MANIFEST), "sample_001: 3")

    def test_digest_mismatch_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifact = root / "artifact.txt"
            artifact.write_text("content\n", encoding="utf-8")
            manifest = root / "manifest.json"
            manifest.write_text(
                json.dumps(
                    {
                        "submission_id": "sample_002",
                        "artifact": artifact.name,
                        "sha256": "0" * 64,
                        "clearance": "approved",
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(IntakeError, "digest mismatch"):
                accept_manifest(manifest)

    def test_artifact_cannot_escape_manifest_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            outside = root / "outside.txt"
            outside.write_text("content\n", encoding="utf-8")
            fixture = root / "fixture"
            fixture.mkdir()
            manifest = fixture / "manifest.json"
            manifest.write_text(
                json.dumps(
                    {
                        "submission_id": "sample_003",
                        "artifact": "../outside.txt",
                        "sha256": hashlib.sha256(outside.read_bytes()).hexdigest(),
                        "clearance": "approved",
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(IntakeError, "escapes"):
                accept_manifest(manifest)


    def test_unapproved_clearance_is_rejected_before_grading(self) -> None:
        with patch("grader.pipeline.score", return_value=3) as grading:
            with self.assertRaisesRegex(IntakeError, "clearance must be approved"):
                run(NEGATIVE_MANIFEST)
            grading.assert_not_called()

    def test_clearance_requires_the_exact_approved_string(self) -> None:
        cases = (
            ("missing", {}),
            ("empty", {"clearance": ""}),
            ("capitalized", {"clearance": "Approved"}),
            ("boolean", {"clearance": True}),
            ("number", {"clearance": 1}),
            ("list", {"clearance": ["approved"]}),
        )
        for name, clearance_fields in cases:
            with self.subTest(case=name), tempfile.TemporaryDirectory() as directory:
                folder = Path(directory)
                artifact = folder / "artifact.txt"
                artifact.write_text("content\n", encoding="utf-8")
                manifest = folder / "manifest.json"
                payload = {
                    "submission_id": "sample_004",
                    "artifact": artifact.name,
                    "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
                    **clearance_fields,
                }
                manifest.write_text(json.dumps(payload), encoding="utf-8")
                with self.assertRaisesRegex(IntakeError, "clearance must be approved"):
                    accept_manifest(manifest)


if __name__ == "__main__":
    unittest.main()
```
**Step 6.** Before production changes, run the stronger suite and immediately print its status; then show the negative fixture's actual CLI behavior.
```bash
python3 -m unittest discover -s tests -v
printf 'Strengthened-suite exit code: %s\n' "$?"
python3 -m grader.pipeline fixtures/negative/manifest.json
printf 'Negative-case exit code before repair: %s\n' "$?"
```
The observed result for these exact saved files on the pinned starter is `Ran 5 tests`, `FAILED (failures=7)`, exit 1, with `IntakeError not raised`. The negative CLI incorrectly prints `sample_negative_001: 3` and exits 0. The count of seven failures includes subtests inside one method. If those results appear, say **“The negative clearance cases are currently accepted. This pending fixture reaches scoring, so the new checks expose the missing pre-grading guard.”** If the result is a parse error, missing file or digest mismatch, follow recovery rather than calling it the intended rejection.
**Step 7.** Open `grader/intake.py` and replace its complete contents with the following bounded repair. The only production addition is the clearance check immediately before the accepted result; the existing ID/path/artifact/digest checks remain. Choose **File → Save All**. Say **“The new guard requires the exact approved string and raises the existing intake error otherwise. Since the pipeline calls intake before scoring, rejection stops the scoring path.”**
```python
"""Manifest loading and pre-grading intake checks."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path


_SUBMISSION_ID = re.compile(r"[A-Za-z0-9_-]+\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


class IntakeError(ValueError):
    """Raised when a submission cannot be transferred to grading."""


@dataclass(frozen=True)
class AcceptedSubmission:
    submission_id: str
    artifact: Path


def accept_manifest(manifest_path: Path) -> AcceptedSubmission:
    manifest_path = manifest_path.resolve()
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise IntakeError("manifest is unreadable") from exc

    submission_id = payload.get("submission_id")
    if not isinstance(submission_id, str) or not _SUBMISSION_ID.fullmatch(submission_id):
        raise IntakeError("invalid submission_id")

    artifact_name = payload.get("artifact")
    if not isinstance(artifact_name, str) or not artifact_name:
        raise IntakeError("invalid artifact path")

    root = manifest_path.parent
    artifact = (root / artifact_name).resolve()
    if artifact == root or root not in artifact.parents:
        raise IntakeError("artifact escapes manifest directory")
    if not artifact.is_file() or artifact.stat().st_size == 0:
        raise IntakeError("artifact must be a non-empty regular file")

    expected_digest = payload.get("sha256")
    if not isinstance(expected_digest, str) or not _SHA256.fullmatch(expected_digest):
        raise IntakeError("invalid sha256")
    actual_digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    if actual_digest != expected_digest:
        raise IntakeError("artifact digest mismatch")

    clearance = payload.get("clearance")
    if not isinstance(clearance, str) or clearance != "approved":
        raise IntakeError("clearance must be approved")

    return AcceptedSubmission(submission_id=submission_id, artifact=artifact)
```
**Step 8.** Run ordinary verification and the valid CLI against the saved files.
```bash
sh scripts/verify.sh
python3 -m grader.pipeline fixtures/valid/manifest.json
```
The checked result is `Ran 5 tests`, `OK` and `sample_001: 3`; the direct CLI still prints `sample_001: 3`. If observed, say **“All five test methods pass, including the assertion that scoring is not called after rejection. The existing accepted fixture retains the same score.”**
**Step 9.** Run this exact negative-case block, which preserves and displays the pipeline's actual exit status.
```bash
if python3 -m grader.pipeline fixtures/negative/manifest.json; then
  negative_status=0
else
  negative_status=$?
fi
printf 'Negative-case exit code: %s\n' "$negative_status"
```
The verified output is `pipeline.py: error: clearance must be approved` and `Negative-case exit code: 2`, with no score printed. Exit 0 means incorrect acceptance; a nonzero code with another reason is not this intended validation proof. Only if the message and code match, say **“The pending-clearance fixture is rejected by the intended intake guard with exit 2 and no score output.”**
**Step 10.** Choose **File → Save All**, then run the valid CLI and the exact negative block from Steps 8 and 9 once more. The checked repeated result is unchanged valid `sample_001: 3` / exit 0, followed by the clearance error / exit 2 for the pending fixture. Say **“The repeated checks preserve the accepted case and reject the bounded negative case. The separate test proves scoring was not invoked for that rejection.”** Use the actual displayed outputs; do not infer pre-grading rejection from a CLI exit alone.
**Step 11.** Return to the clearance guard, the negative manifest and its grading-not-called test so the final deliverables are visible. Say **“The saved change enforces this one missing written requirement before accepted intake returns. The negative fixture keeps the artifact and digest valid, while the original valid case remains accepted.”** Claim that only after the verification above passes. Choose **File → Save All**, bring TaskRecorder forward, click **Stop Recording**, and wait for **Stopping → Archiving → Idle**. Review the actual capture and prepare the required upload/Final Notes through the existing checklist. Keep prior-work and `AI-generated before recording` disclosure truthful outside capture.
