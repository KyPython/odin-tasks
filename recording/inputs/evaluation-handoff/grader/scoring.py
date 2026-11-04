"""Deterministic scoring for accepted submissions."""

from .intake import AcceptedSubmission


def score(submission: AcceptedSubmission) -> int:
    lines = submission.artifact.read_text(encoding="utf-8").splitlines()
    return sum(bool(line.strip()) for line in lines)
