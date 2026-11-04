# Consolidation provenance (Nov 4, 2026)

Nine standalone repos were subtree-merged here with full history preserved.
After the consolidation PR merges and this content is verified, Ky deletes
the source repos (user decision, Nov 2026).

| Directory | Source repo | Source commit at merge |
| --- | --- | --- |
| `tasks/monorepo-build-graph` | `KyPython/monorepo-build-graph` | `e9c9157d488e2404a733d6da49c33830b57d7a15` |
| `tasks/ci-evaluation-contract` | `KyPython/ci-evaluation-contract` | `b33a0e7fc22af4f89f823155beef191d025aec92` |
| `tasks/vacuous-test-suite-audit` | `KyPython/vacuous-test-suite-audit` | `0766d8b3cd0d4aa304f7165c53a8d736c5138d63` |
| `tasks/flaky-clock-injection` | `KyPython/flaky-clock-injection` | `2ca167ea86160f5fe6ae65da324fc33c3066f7cf` |
| `tasks/threshold-evaluation` | `KyPython/threshold-evaluation` | `48b0e255fac05492b96f651cfa24d9d84e255821` |
| `tasks/oauth-callback-state` | `KyPython/oauth-callback-state` | `ef5d5b5e4b96a65ec970916aaab133c2513334d9` |
| `tasks/cursor-pagination-aggregator` | `KyPython/cursor-pagination-aggregator` | `d2cbe0381575ddcc6d6f6415fa90b01703e8f6ac` |
| `tasks/python-exception-propagation` | `KyPython/python-exception-propagation` | `4bfa36dfb94acf892b742e1d5af8e8877a5d6e7d` |
| `recording/` | `KyPython/odin-recording-preparation` | `bbc079450b04b8618d8776b554f42df8d532819e` |

## Adjustments made during the move

- Nested `.github/` dirs removed (9 dead caller workflows + CODEOWNERS +
  dependabot files); root `.github/` replaces them. Root `dependabot.yml`
  covers actions + npm (`tasks/monorepo-build-graph`) + pip (the two
  `requirements-dev.txt` tasks).
- `recording/`'s three real workflows hoisted to root
  (`build-preparation`, `odin-agent-trial`, `odin-inspect-replay`) with
  `recording/` path filters and `working-directory: recording` defaults.
- `tasks/ci-evaluation-contract/scripts/verify.sh` gained its missing exec
  bit (it was mode 644 upstream; the README command could never run).
- `recording/README.md` registry links repointed to `../tasks/<name>`.
  Provenance records (`runtime/task-registry.json`, `runtime-manifest.json`,
  `packs/`, import ledgers) intentionally still name the original repos and
  pinned commits; the recording build reads vendored `inputs/` and needs no
  credentials, so deleting the sources does not break it.
- New root `ci.yml` runs every task's documented verification plus a
  recording smoke (`unittest discover` + `check_recording_pack.py`). All 8
  tasks verified locally before the PR: 1+4+4+2 unittest suites OK,
  cieval verify OK, pytest 8+2 passed, node pass 2 fail 0, recording 35 OK.
