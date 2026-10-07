"""JSON input loading for the threshold report command."""

from __future__ import annotations

import json
from pathlib import Path

from .evaluation import Observation, Policy


def load_observations(path: Path) -> tuple[Observation, ...]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return tuple(Observation(**row) for row in payload)


def load_policy(path: Path) -> Policy:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return Policy(
        candidate_thresholds=tuple(payload["candidate_thresholds"]),
        false_negative_cost=payload["false_negative_cost"],
        false_positive_cost=payload["false_positive_cost"],
    )
