# Python exception-propagation repair

This directory is a synthetic, deterministic debugging exercise. It contains no
production data or private source code.

## Candidate task

The `batch_command` package processes a fixed sequence of item specifications and
records an ordered event log. Repair the implementation so that its behavior
matches the contract below, and strengthen the tests to demonstrate the repair.

### Behavior contract

- A normal item is reported as processed.
- A `HandledItemError` is handled at the item boundary and the batch continues.
- Any other child-operation exception fails that item and is represented once in
  the batch failure report. A failed item is never also reported as processed.
- `SiblingItemError` and other unmatched child exceptions follow the same
  batch-failure rule; exception matching must not depend on input order.
- Every opened item is cleaned up exactly once, on both successful and failing
  paths.
- Statements after a call that propagates an exception do not run.
- Event order and the returned report are identical across repeated runs.

Do not change the deterministic fixture data merely to make a test pass.

## Reproducible commands

From this directory, using Python 3.11 or newer:

```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
PYTHONPATH=src .venv/bin/python -m pytest
```

The supplied tests cover only ordinary baseline paths. The candidate is expected
to add failure-path coverage derived from the contract before repairing the
implementation.
