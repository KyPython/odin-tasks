# odin-tasks

Project Odin tasks and evaluations in one mono-repo: synthetic task
starters plus the recording registry. Consolidated Nov 2026; see
`MIGRATION.md` for provenance (source repo + commit per directory).

| Directory | Content | Verify |
| --- | --- | --- |
| `tasks/monorepo-build-graph` | Synthetic pnpm/Turborepo workspace (build reliability) | `pnpm test` |
| `tasks/ci-evaluation-contract` | Submission intake + grading pipeline | `./scripts/verify.sh` |
| `tasks/vacuous-test-suite-audit` | Quote calculator test audit | `pytest -q` |
| `tasks/flaky-clock-injection` | Dispatch-board time test | `python -m unittest discover -s tests` |
| `tasks/threshold-evaluation` | Alert-threshold evaluation | `PYTHONPATH=src python -m unittest discover -s tests` |
| `tasks/oauth-callback-state` | OAuth state-binding repair exercise | `python -m unittest discover -s tests && python run_fixtures.py` |
| `tasks/cursor-pagination-aggregator` | Cursor-paginated client exercise | `PYTHONPATH=src python -m unittest discover -s tests` |
| `tasks/python-exception-propagation` | Exception-propagation repair exercise | `PYTHONPATH=src pytest` |

The recording registry stays a standalone repo
(`KyPython/odin-recording-preparation`): its checksummed vendored inputs
fight the mono-repo gate, so it links here instead of moving here.

Root CI (`ci.yml`) runs every task's verification plus the gate.
