"""Command-line intake-to-grading pipeline."""

from __future__ import annotations

import argparse
from pathlib import Path

from .intake import IntakeError, accept_manifest
from .scoring import score


def run(manifest_path: Path) -> str:
    submission = accept_manifest(manifest_path)
    return f"{submission.submission_id}: {score(submission)}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    try:
        print(run(args.manifest))
    except IntakeError as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
