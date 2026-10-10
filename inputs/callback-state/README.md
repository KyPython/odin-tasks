# OAuth callback state-binding repair — starter

This directory is a self-contained, synthetic debugging exercise. It makes no
network requests and contains no provider credentials or private data. Use
Python 3.11 or newer; no third-party packages are required.

## Contract

`handle_callback` receives a query mapping, a mutable session mapping, and an
integer Unix timestamp. A pending authorization request contains a synthetic
state value, its expiration time, and a post-login path.

The completed handler must preserve the successful callback response while
failing closed with these categories:

| Callback condition | Required result |
| --- | --- |
| Matching, unexpired, unused state | `ok` |
| State is absent | `missing_state` |
| State differs from the pending request | `state_mismatch` |
| Pending request's expiration time has passed | `state_expired` |
| The same pending request is used again | `state_replayed` |

An authorization code and state are synthetic sensitive values. They must not
appear in serialized results or logs. Error responses use the existing
`CallbackResult` shape.

## Included starter material

- `callback.py`: an intentionally incomplete callback implementation.
- `fixtures.py`: deterministic sessions and callback inputs for exploration.
- `run_fixtures.py`: a local observation harness with stable JSON output.
- `tests/test_callback.py`: ordinary-path baseline tests only.

The starter intentionally does **not** include the diagnosis, repair,
decisive negative assertions, or an answer-key diff. Provider interaction and
production session-storage guarantees are outside this local exercise and
remain unverified.

## Reproduce the baseline

From this directory, run:

```sh
python -m unittest discover -s tests -v
python run_fixtures.py
python run_fixtures.py > /tmp/oauth-run-1.json
python run_fixtures.py > /tmp/oauth-run-2.json
cmp /tmp/oauth-run-1.json /tmp/oauth-run-2.json
```
