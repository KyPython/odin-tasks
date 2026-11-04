"""Threshold evaluation for the Harbor Signal fixture."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable


@dataclass(frozen=True)
class Observation:
    id: str
    score: float
    actual: bool


@dataclass(frozen=True)
class Policy:
    candidate_thresholds: tuple[float, ...]
    false_negative_cost: int
    false_positive_cost: int


@dataclass(frozen=True)
class Evaluation:
    threshold: float
    true_positive: int
    true_negative: int
    false_positive: int
    false_negative: int
    accuracy: float
    total_cost: int


def evaluate_threshold(
    observations: Iterable[Observation], threshold: float, policy: Policy
) -> Evaluation:
    rows = tuple(observations)
    true_positive = sum(row.actual and row.score >= threshold for row in rows)
    true_negative = sum(not row.actual and row.score < threshold for row in rows)
    false_positive = sum(not row.actual and row.score >= threshold for row in rows)
    false_negative = sum(row.actual and row.score < threshold for row in rows)
    correct = true_positive + true_negative

    return Evaluation(
        threshold=threshold,
        true_positive=true_positive,
        true_negative=true_negative,
        false_positive=false_positive,
        false_negative=false_negative,
        accuracy=correct / len(rows),
        total_cost=(false_negative * policy.false_negative_cost)
        + (false_positive * policy.false_positive_cost),
    )


def build_report(observations: Iterable[Observation], policy: Policy) -> dict[str, object]:
    rows = tuple(observations)
    if not rows:
        raise ValueError("at least one observation is required")
    if not policy.candidate_thresholds:
        raise ValueError("at least one candidate threshold is required")

    evaluations = [
        evaluate_threshold(rows, threshold, policy)
        for threshold in sorted(policy.candidate_thresholds)
    ]
    selected = min(evaluations, key=lambda item: (item.total_cost, item.threshold))

    return {
        "costs": {
            "false_negative": policy.false_negative_cost,
            "false_positive": policy.false_positive_cost,
        },
        "candidates": [asdict(item) for item in evaluations],
        "selected_threshold": selected.threshold,
    }
