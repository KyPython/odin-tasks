"""Deterministic batch command with a seeded exception-handling defect."""

from dataclasses import dataclass
from typing import Literal

from .errors import (
    ChildOperationError,
    HandledItemError,
    ItemProcessingError,
    SiblingItemError,
    UnmatchedChildError,
)

Mode = Literal["ok", "handled", "unmatched", "sibling"]


@dataclass(frozen=True)
class ItemSpec:
    name: str
    mode: Mode


@dataclass(frozen=True)
class BatchReport:
    processed: tuple[str, ...]
    failures: tuple[str, ...]
    events: tuple[str, ...]


def _child_operation(item: ItemSpec, events: list[str]) -> None:
    events.append(f"execute:{item.name}")
    if item.mode == "handled":
        raise HandledItemError(item.name)
    if item.mode == "unmatched":
        raise UnmatchedChildError(item.name)
    if item.mode == "sibling":
        raise SiblingItemError(item.name)


def _process_item(item: ItemSpec, events: list[str]) -> None:
    events.append(f"open:{item.name}")
    try:
        try:
            _child_operation(item, events)
        except HandledItemError:
            events.append(f"handled:{item.name}")
        except ChildOperationError as error:
            raise ItemProcessingError(item.name) from error
    finally:
        events.append(f"cleanup:{item.name}")


def run_batch(items: tuple[ItemSpec, ...]) -> BatchReport:
    """Process items and return an immutable report of the observed run."""

    events: list[str] = []
    processed: list[str] = []
    failures: list[str] = []

    for item in items:
        try:
            _process_item(item, events)
        except ItemProcessingError:
            failures.append(item.name)
            events.append(f"failed:{item.name}")
        finally:
            processed.append(item.name)
            events.append(f"processed:{item.name}")

    return BatchReport(tuple(processed), tuple(failures), tuple(events))
