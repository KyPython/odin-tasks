# Consolidation provenance (Nov 4, 2026)

Eight standalone task repos were subtree-merged here with full history
preserved. After the consolidation PR merges and this content is verified,
Ky deletes the 8 source repos (user decision, Nov 2026).

`KyPython/odin-recording-preparation` intentionally stays standalone: its
checksummed vendored `inputs/` must stay byte-identical, which fights the
mono-repo gate (container + dependency checks flag the frozen copies as
new). It links to `tasks/` here instead; only its registry links move.

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

## Adjustments made during the move

- Nested `.github/` dirs removed (8 dead caller workflows + CODEOWNERS +
  dependabot files); root `.github/` replaces them. Root `dependabot.yml`
  covers actions + npm (`tasks/monorepo-build-graph`) + pip (the two
  `requirements-dev.txt` tasks).
- `tasks/ci-evaluation-contract/scripts/verify.sh` gained its missing exec
  bit (it was mode 644 upstream; the README command could never run).
- Pre-existing debt fixed so the gate passes on the moved tree: non-root
  `USER` in the harbor Dockerfile; pytest 8.3.5 → 9.0.3 (GHSA-6w46,
  PYSEC-2026-1845); turbo 2.3.3 → 2.9.14 (GHSA-3qcw, GHSA-hcf7).
  Re-verified locally after each bump.
- New root `ci.yml` runs every task's documented verification. All 8
  tasks verified locally before the PR: 1+4+4+2 unittest suites OK,
  cieval verify OK, pytest 8+2 passed, node pass 2 fail 0.
