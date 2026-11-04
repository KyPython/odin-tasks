# Batch command — complete guided reference

This is an AI-prepared internal Bootcamp practice plan, bound to source commit `ac4aaa7d95fd07d3bdc58aa88128d24e533ec4c2` and exact candidate Goal SHA-256 `a519473d08c3e12ec135b069285a123814414356e2bef0bc27c4a37d8792d717`. It does not create Odin approval, paid eligibility or an unaided Human Transfer Test result. The protected starter, fixture data, original tests and captured workspace stay unworked during preparation. The separate reference supplies every implementation, assertion, command, expected result and narration; actual recorded edits occur manually.

Disposable local verification: 16 checks PASS; original 2 tests pass; strengthened suite produces exactly 12 failed/7 passed before repair; the identical 19 tests pass on three repaired runs. Repeated mixed report bytes match an independently specified full report. The planned two-line repair preserves handled items and cleanup, catches other Exception failures at the child boundary, retains causes and leaves BaseException control signals unhandled.

To repeat reference verification off-camera with the installed matching source/runtime/reference receipts, use a fresh private output directory:

```bash
proof_dir="$(mktemp -d /private/tmp/taskwork-batch-command-reference.XXXXXX)"
/usr/local/bin/python3 -B /Users/Shared/TaskWorkPlans/batch-command/rehearse.py --inputs /Users/Shared/TaskWorkInputs --runtime /Users/Shared/TaskWorkRuntime --output "$proof_dir/proof.json"
```

Keep this plan on a second device or printout; keep the AI/Codex setup window off the captured display. Guided completion supplies practice evidence only; the separate unaided Human Transfer Test criteria remain unchanged and uncompleted.

### Recording sequence — follow this order
**Step 1.** After **Before practice — Recorder checks** passes for this actual attempt and the installed source kit and separate worked-plan receipt cover `batch-command`, stage the clean project and exact candidate Goal windows. Click **Start Recording**, minimize TaskRecorder, and say: **“This is a guided internal practice task. I will check the batch contract, demonstrate the failure paths with prepared tests, apply two handling changes, and verify repeatable results.”** Minimize the Goal window and select the prepared `batch-command` project through VS Code’s **Window** menu. This candidate has no Odin approval or Studio assignment.
**Step 2.** Open `README.md`, then `src/batch_command/command.py`, `src/batch_command/errors.py`, `tests/conftest.py` and `tests/test_baseline.py`. Say: **“The contract distinguishes cleanup from success. Handled item errors allow continuation; other child-operation exceptions fail an item once. The outer finally currently marks every item processed, including failures. The inner catch also misses ordinary exceptions outside its custom hierarchy.”** Use **Terminal → New Terminal** and run:
```bash
PYTHONPATH=src .venv/bin/python -m pytest
```
Expected: **2 passed**. Say only after that appears: **“The two baseline tests pass, but they cover ordinary and handled items. They do not detect incorrect failure reporting.”** Pytest already has its quiet option in `pyproject.toml`.
**Step 3.** In Explorer, select `tests`, choose **New File**, name it `test_contract.py`, and enter the complete prepared file below. Keep `tests/conftest.py`, both original baseline tests and all fixture data unchanged. These assertions independently specify exact processed/failure/event results, every permutation of the existing fixture, unexpected child exceptions, exception causes, skipped statements, process-control signals, empty input and repetition.
```python
from itertools import permutations

import pytest

import batch_command.command as command
from batch_command import BatchReport, ItemSpec, run_batch
from batch_command.errors import ItemProcessingError, SiblingItemError, UnmatchedChildError


@pytest.mark.parametrize("mode", ["unmatched", "sibling"])
def test_failed_item_is_reported_once_and_never_processed(mode):
    assert run_batch((ItemSpec("failed", mode),)) == BatchReport(
        (), ("failed",),
        ("open:failed", "execute:failed", "cleanup:failed", "failed:failed"),
    )


def test_original_deterministic_fixture(deterministic_failure_set):
    assert run_batch(deterministic_failure_set) == BatchReport(
        ("alpha",), ("bravo", "charlie"),
        (
            "open:alpha", "execute:alpha", "cleanup:alpha", "processed:alpha",
            "open:bravo", "execute:bravo", "cleanup:bravo", "failed:bravo",
            "open:charlie", "execute:charlie", "cleanup:charlie", "failed:charlie",
        ),
    )


@pytest.mark.parametrize("order", list(permutations(("alpha", "bravo", "charlie"))))
def test_failure_semantics_do_not_depend_on_input_order(order):
    items = {
        "alpha": ItemSpec("alpha", "ok"),
        "bravo": ItemSpec("bravo", "unmatched"),
        "charlie": ItemSpec("charlie", "sibling"),
    }
    expected_events = {
        "alpha": ("open:alpha", "execute:alpha", "cleanup:alpha", "processed:alpha"),
        "bravo": ("open:bravo", "execute:bravo", "cleanup:bravo", "failed:bravo"),
        "charlie": ("open:charlie", "execute:charlie", "cleanup:charlie", "failed:charlie"),
    }
    assert run_batch(tuple(items[name] for name in order)) == BatchReport(
        ("alpha",), tuple(name for name in order if name != "alpha"),
        tuple(event for name in order for event in expected_events[name]),
    )


def test_other_child_exception_fails_item_and_batch_continues(monkeypatch):
    original = command._child_operation

    def child(item, events):
        if item.name == "unexpected":
            events.append("execute:unexpected")
            raise RuntimeError("synthetic child failure")
        original(item, events)

    monkeypatch.setattr(command, "_child_operation", child)
    assert run_batch((ItemSpec("unexpected", "ok"), ItemSpec("next", "handled"))) == BatchReport(
        ("next",), ("unexpected",),
        (
            "open:unexpected", "execute:unexpected", "cleanup:unexpected", "failed:unexpected",
            "open:next", "execute:next", "handled:next", "cleanup:next", "processed:next",
        ),
    )


@pytest.mark.parametrize("error_type", [UnmatchedChildError, SiblingItemError, RuntimeError])
def test_wrapped_exception_keeps_cause_cleans_up_and_skips_after_call(monkeypatch, error_type):
    failure = error_type("synthetic child failure")
    events = []

    def child(item, observed):
        observed.append("execute:item")
        raise failure

    monkeypatch.setattr(command, "_child_operation", child)
    with pytest.raises(ItemProcessingError) as raised:
        command._process_item(ItemSpec("item", "ok"), events)
        events.append("after-call")
    assert raised.value.__cause__ is failure
    assert events == ["open:item", "execute:item", "cleanup:item"]


@pytest.mark.parametrize("error_type", [KeyboardInterrupt, SystemExit])
def test_process_control_signal_is_not_swallowed(monkeypatch, error_type):
    failure = error_type("synthetic stop")
    events = []

    def child(item, observed):
        observed.append("execute:item")
        raise failure

    monkeypatch.setattr(command, "_child_operation", child)
    with pytest.raises(error_type) as raised:
        command._process_item(ItemSpec("item", "ok"), events)
        events.append("after-call")
    assert raised.value is failure
    assert events == ["open:item", "execute:item", "cleanup:item"]


def test_empty_batch():
    assert run_batch(()) == BatchReport((), (), ())


def test_repeated_mixed_reports_are_identical():
    items = (ItemSpec("a", "unmatched"), ItemSpec("b", "handled"), ItemSpec("c", "sibling"))
    expected = BatchReport(
        ("b",), ("a", "c"),
        (
            "open:a", "execute:a", "cleanup:a", "failed:a",
            "open:b", "execute:b", "handled:b", "cleanup:b", "processed:b",
            "open:c", "execute:c", "cleanup:c", "failed:c",
        ),
    )
    assert [run_batch(items) for _ in range(3)] == [expected, expected, expected]
```
Use **File → Save All**. Say: **“These tests require a failed item to have cleanup and one failure event, with no processed event. They also require successful siblings to continue, preserve exception causes, and ensure statements after a propagating call do not run.”**
**Step 4.** Before changing production code, run:
```bash
PYTHONPATH=src .venv/bin/python -m pytest
```
Expected: **12 failed, 7 passed**, exit 1. The failures are the two failed-item modes, the original three-item fixture, its six order permutations, unexpected RuntimeError continuation, RuntimeError wrapping and the repeated mixed report. Say only after that appears: **“The strengthened tests expose both defects in the untouched implementation. The ordinary paths, cleanup and process-control checks already pass. I will keep the same tests for the repair.”**
**Step 5.** Open `src/batch_command/command.py` and replace its contents with this complete prepared file. Only two handling lines change: `except ChildOperationError as error:` becomes `except Exception as error:`, and the outer `finally:` becomes `else:`. The inner cleanup `finally:` stays unchanged. Do not alter the strengthened tests.
```python
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
        except Exception as error:
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
        else:
            processed.append(item.name)
            events.append(f"processed:{item.name}")

    return BatchReport(tuple(processed), tuple(failures), tuple(events))
```
Use **File → Save All**. Say: **“HandledItemError is still caught first. Other ordinary exceptions are wrapped as ItemProcessingError with their original cause, while BaseException control signals still propagate. Cleanup runs once in the inner finally. The outer else records success only when processing returns normally.”**
**Step 6.** Run the same full tests three times:
```bash
(
  set -e
  for run in 1 2 3; do
    printf 'Verification run %s\n' "$run"
    PYTHONPATH=src .venv/bin/python -m pytest
  done
)
```
Expected: **19 passed** on each of the three runs. Say only after all three pass: **“The unchanged baseline and the same strengthened tests now pass on three runs. Failure reporting is independent of input order; ordinary and handled items still succeed; cleanup happens once; causes and process-control propagation are preserved.”**
**Step 7.** Run this exact itemized report command twice:
```bash
PYTHONPATH=src .venv/bin/python -c "from batch_command import ItemSpec, run_batch; print(run_batch((ItemSpec('alpha', 'ok'), ItemSpec('bravo', 'unmatched'), ItemSpec('charlie', 'sibling'))))"
PYTHONPATH=src .venv/bin/python -c "from batch_command import ItemSpec, run_batch; print(run_batch((ItemSpec('alpha', 'ok'), ItemSpec('bravo', 'unmatched'), ItemSpec('charlie', 'sibling'))))"
```
Both lines must be identical:
```plain text
BatchReport(processed=('alpha',), failures=('bravo', 'charlie'), events=('open:alpha', 'execute:alpha', 'cleanup:alpha', 'processed:alpha', 'open:bravo', 'execute:bravo', 'cleanup:bravo', 'failed:bravo', 'open:charlie', 'execute:charlie', 'cleanup:charlie', 'failed:charlie'))
```
Say only after that appears: **“Only alpha is processed. Bravo and charlie each fail once after cleanup, and the report preserves their input order. The repeated output is identical. This is the bounded local batch contract verified by these tests.”**
**Step 8.** Use **File → Save All**. Say: **“The two handling changes and contract tests are saved. This was guided practice using a prepared plan; it does not establish an unaided transfer test.”** Bring TaskRecorder forward, click **Stop Recording**, and wait for **Stopping → Archiving → Idle**. Review the actual artifacts through the internal Bootcamp runbook; do not claim approval, submission, practice review or unaided mastery in advance. **Recovery for any earlier mismatch:** say **“The displayed result differs from the prepared evidence; I am stopping this practice take for an off-camera check.”** Stop recording and wait for Idle. In the uncaptured Codex setup window, use the saved handoff with `Task: batch-command` and `Unexpected result:` followed by the exact displayed output; require a verified diagnosis and refreshed script before another take. Preserve the edited workspace and recording. Do not improvise changes, reset the workspace or interact with AI while recording.
