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

    return AcceptedSubmission(submission_id=submission_id, artifact=artifact)
