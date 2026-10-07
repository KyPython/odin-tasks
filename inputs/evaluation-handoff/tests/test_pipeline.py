from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from grader.intake import IntakeError, accept_manifest
from grader.pipeline import run


ROOT = Path(__file__).resolve().parents[1]
VALID_MANIFEST = ROOT / "fixtures" / "valid" / "manifest.json"


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


if __name__ == "__main__":
    unittest.main()
