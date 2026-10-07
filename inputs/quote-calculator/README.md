# Quote Calculator

This small Python project calculates itemized customer quotes. Its behavior is
defined in [`docs/behavior.md`](docs/behavior.md).

## Setup and baseline run

From this directory, create an isolated environment and run the test suite:

```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pytest -q
```

On Windows, use `.venv\\Scripts\\python` in place of `.venv/bin/python`.

