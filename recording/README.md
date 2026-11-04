# Recording preparation

This directory (consolidated Nov 2026 from the standalone odin-recording-preparation repo; live starters now live in `../tasks/`) builds registered recording starters and their offline dependency caches in the existing GitHub Actions workflow. The starter bundle contains unchanged source inputs, Recorder setup helper, exact Goal documents, reviewed scripts, checksums and observed cloud verification results. Complete worked references for every registered task separately supply analyzed causes, exact code/tests and verified execution plans. Actual task edits and checks occur in the recording; references are validated beforehand in disposable copies. The first four Odin starters are the initial registry entries:

| Neutral workspace | Original repository | Pinned source commit |
| --- | --- | --- |
| `dispatch-board` | [flaky-clock-injection](../tasks/flaky-clock-injection) | `e5652bcb044cd24d2a7d1c2f8bb93b885cea2069` |
| `evaluation-handoff` | [ci-evaluation-contract](../tasks/ci-evaluation-contract) | `ca532d92ec3db02224061b3ceef105b2bc113b27` |
| `quote-calculator` | [vacuous-test-suite-audit](../tasks/vacuous-test-suite-audit) | `c5986e93719cfd4b08a57104576c04a78d1f16ee` |
| `harbor-workspace` | [monorepo-build-graph](../tasks/monorepo-build-graph) | `2ddf3c8f2a0e054ea2e40ab077c5a48132c34a38` |

The registry also includes four recovered cloud-built Bootcamp candidates. Their external Approval ID and Approved Goal remain empty; their existing candidate Goals and internal page identities are preserved.

| Neutral workspace | Private source repository | Pinned source commit |
| --- | --- | --- |
| `cursor-pagination-aggregator` | [cursor-pagination-aggregator](../tasks/cursor-pagination-aggregator) | `9c829c6ec7f85cf382f97e286bf8acce20a96fe7` |
| `threshold-evaluation` | [threshold-evaluation](../tasks/threshold-evaluation) | `aca7a6ac52a9a2dee2d7bc3a0a77dca09f2a6fe5` |
| `batch-command` | [python-exception-propagation](../tasks/python-exception-propagation) | `ac4aaa7d95fd07d3bdc58aa88128d24e533ec4c2` |
| `callback-state` | [oauth-callback-state](../tasks/oauth-callback-state) | `c65f9343be723ea36289db541b8f373883cbfe8a` |

Their existing cloud diff files were verified against Git blob hashes before import. The first two received only a README `cd` setup-path change; the batch command received only a README `PYTHONPATH=src` setup clarification, and all OAuth file blobs remain unchanged. [The import ledger](cloud/starter-imports.json) records original and imported file hashes and every exact setup-only edit. No starter code, fixtures or tests were repaired during recovery.

[`runtime/task-registry.json`](runtime/task-registry.json) binds each existing task page, task identity, Goal, cloud source references, pinned source commit, dependency profile and baseline contracts. `inputs/` holds the registered source files; [`runtime/runtime-manifest.json`](runtime/runtime-manifest.json) records their SHA-256 hashes and original modes. Task and file counts come from these files. The workflow checks inputs before and after dependency installation and baseline rehearsal. It reads this repository's committed snapshot and needs no credentials for the other private repositories.

See [the reusable task process](docs/REUSABLE_TASK_PROCESS.md) for the existing Notion/Make owners and one-page publishing flow. [`register_task.py`](scripts/register_task.py) plans or imports another real starter from a full GitHub SHA and a fresh complete Notion export. It compares real Git blob bytes and modes, refuses edits to existing registered tasks, and preserves the original inputs and Goals. `plan` writes nothing; `register` appends the reviewed task locally without pushing or publishing. An identical registration retry is a no-op. Odin registration requires actual approval; Bootcamp registration keeps its candidate Goal and internal page identity separate, with external approval fields empty.

## Cloud build

[Build recording preparation](.github/workflows/build-preparation.yml) runs on GitHub's standard `macos-26` ARM64 runner. It installs Python **3.12.7**, Node **22.22.0** and an isolated Corepack **0.34.0**; the starter locks pnpm **9.15.4** and Turbo **2.3.3**. Official actions are pinned to full commit SHAs, and the workflow token has only `contents: read` permission. No cloud credentials are included in the bundle.

The builder downloads the pinned dependencies into fresh caches, verifies a second installation with network access disabled, and rehearses the starters in disposable copies. CI verification passes when observed behavior matches the unchanged registered baseline: three CI tests and the valid fixture pass; eight quote tests pass; the unrelated monorepo check passes while its service build and container-target checks fail; cursor and threshold each pass four unittests using `PYTHONPATH=src`; the batch command passes two pytest tests with the same import override and pinned pytest 8.3.5; OAuth passes two ordinary unittests and runs its existing deterministic observation harness. Clock outcomes are recorded as observations because they depend on the current date and timezone. A successful preparation run does not mean the tasks have been repaired.

Each successful run uploads `taskwork-cloud-macos-arm64-{commit}` with:

- `taskwork-cloud-macos-arm64.tar.gz`, containing `TaskWorkInputs/`, `TaskWorkRuntime/`, `cloud-proof.json` and `bundle-manifest.json`.
- `taskwork-cloud-macos-arm64.tar.gz.sha256`, for verifying the downloaded archive.

The same workflow also validates all eight registered tasks' complete [worked references](walkthroughs/) against its fresh pinned starter/cache snapshot. It uploads a separate `taskwork-worked-plans-macos-arm64-{commit}` artifact containing exact walkthroughs, phase/full patches, reproducible rehearsal scripts, source/Goal identities, real cloud checks and a complete manifest, plus its archive checksum. [The worked-plan process](docs/WORKED_PLAN_PROCESS.md) distinguishes the original manual's advance-planning requirement from its explicit recording restrictions and unresolved acceptance of a complete AI-written repair/test walkthrough. The starter proof describes unchanged inputs/baselines; the reference proof truthfully records repairs verified only in disposable copies. Neither establishes paid acceptance, Recorder admission or unaided learning.

The tar preserves executable modes and cache symlinks. Python virtual environments and project `node_modules` are recreated locally from the caches. Hosted runner images can receive updates even with the `macos-26` label; the cloud proof records the actual runner image, OS, architecture, tools, source revision and command results. Artifacts are retained for 90 days, subject to the repository's retention limit. [GitHub runner documentation](https://docs.github.com/en/actions/reference/runners/github-hosted-runners) and [artifact documentation](https://github.com/actions/upload-artifact) describe those platform limits.

## Local synchronization

The artifact also contains the versioned `TaskWorkCloudSync.py` utility. The cloud workflow verifies a complete backup and identical installed contents in a disposable fixture, then proves changed source work is refused and preserved. Future kits may add registered tasks while keeping every existing task/source/Goal unchanged. A failed installation rolls back new shared inputs and restores the prior runtime. The sync receipt includes hashes of verified runtime metadata and process documents for Recorder-side checks.

Download an artifact from a successful run for the intended preparation commit. Check its archive SHA-256 before extracting it into a new staging directory, then verify every file and symlink against `bundle-manifest.json` and the source map in `runtime-manifest.json`. Only a verified bundle should supply `/Users/Shared/TaskWorkInputs/` and `/Users/Shared/TaskWorkRuntime/`. Preserve any existing Recorder work; never reset its project folders during synchronization.

After that matching starter kit is synced, verify the separate worked-reference artifact with `scripts/sync_worked_plans.py ARCHIVE CHECKSUM --commit FULL_SHA --run-id REAL_RUN_ID`; add `--sync` to install its verified contents in `/Users/Shared/TaskWorkPlans/`. This binds each plan to the same run's starter proof and exact source/Goal, preserves prior owned plans, refuses edits/unmanaged destinations, and reuses an identical installation without changing timestamps. Read the selected `walkthrough.md` off-screen; the helper never copies its patches or final tests into the captured starter.

Under the actual **Recorder** macOS account, run the installed saved prompt in `TaskWorkRuntime/process/RECORDER-CODEX-PROMPT.txt`, or select one task off-screen:

```bash
/Users/Shared/TaskWorkRuntime/Prepare-TaskWork.command --task dispatch-board
```

The registry supplies the selected task; this example is not a fixed task list. The helper creates its neutral workspace, writable Recorder runtime namespace, offline dependencies, workspace settings and exact Goal-only document. Another task's human edits remain intact. Repeating unchanged selected setup is idempotent; a selected workspace, dependency tree, Goal, settings or receipt with edits is held for review. Open the matching `.code-workspace` file for public tool paths and disabled AI features. The per-task receipt at `~/Library/Caches/TaskWork/ready-receipts/<neutral>.json` covers setup checks only. Existing legacy receipts require off-screen migration review rather than an automatic overwrite.

The setup helper deliberately requires the Recorder account and protected Recorder home. Cloud verification cannot complete TaskRecorder permissions or actual microphone/display/privacy checks. Odin tasks additionally require live Studio admission, Metadata.rtf preparation and submission transitions through the [Notion master cue card](https://www.notion.so/3f08621e0a7a81628eedd127c597ef12). Bootcamp candidates use **Before practice — Recorder checks** in the [internal Bootcamp runbook](https://app.notion.com/p/3f28621e0a7a81d2b092d5f3f4c537f4), with no external approval or paid-task claim. This administrative repository, its run logs and its rehearsal proofs stay outside the captured project roots.
