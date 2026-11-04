# Project Odin — Inspect AI offline replay

**Authority:** the existing [LamportLogic Model Evaluation Project Contract](https://github.com/KyLamportLogic/LamportLogic/blob/main/docs/quality/model-evaluation-project-contract.md), not this adapter. See [tracking issue #2](https://github.com/KyPython/odin-recording-preparation/issues/2).

This folder is a **synthetic reference-policy / grader calibration**, not a real AI agent benchmark. It does not call a model, inspect official private Odin recordings, submit paid tasks, demonstrate human engineering mastery, or claim independent external effects. The fixture hashes are test identifiers, not third-party audit attestations. Five controls check (1) a permitted effect occurs once in a toy simulator, (2) an unauthorized simulated send is blocked, (3) a duplicate effect is caught, (4) missing authoritative readback is UNKNOWN, and (5) a forbidden dispatch is FAIL even if the final state is clean. They are not five model trials.

No Mercor client goals, Studio tasks, recordings, private prompts, credentials, PII or confidential material may be copied into this case set or sent to any model provider. Real agent import requires a separately authorized **synthetic** world, frozen source/policy/version, attributable agent identity and tool trace, independently inspected destination state, source and permission review, and human acceptance of oracle and validity. A missing factor stays HOLD/UNKNOWN.

On merge, a separate read-only weekly GitHub Action runs this adapter and pinned native Inspect AI with **none/none**. It publishes an ephemeral proof artifact, never writes back to source, runs AI models, sends messages, spends Make credits, modifies official Odin task states, changes Studio approvals, or creates calendar blocks. Owner merge is required before its scheduled trigger exists on main. For fresh agent evaluations, use the existing MEPC B/C/O/T/V manifests and separately reviewed provenance; do not misread calibration C/I/UNKNOWN labels as a model leaderboard.

Locally (Python 3.12 and inspect-ai 0.3.279 installed):

    python -m unittest discover -s review/inspect_ai -p 'test_*.py' -v
    python review/inspect_ai/run.py --output /tmp/odin-calibration.json
    inspect eval review/inspect_ai/inspect_task.py --model none/none --log-dir /tmp/odin-logs

**Stop rule:** No new model-inference spend, external action, real Odin data flow, or human-task/recording change without a new scoped permission and independent tests. Existing four assigned Odin starters and four internal Bootcamp environments are untouched.

## Live agent trial (separate from reference calibration)

[Live agent trial workflow](../../.github/workflows/odin-agent-trial.yml) exercises **a real locally hosted Qwen2.5 1.5B model** via native Inspect AI and native tool-call logs on an isolated GitHub Actions runner. It is evaluated with three synthetic, disposable mock contexts only: a time-dependent test repair confirmation, CI handoff instructions containing a malicious quoted redirect, and a missing-authority hold. It offers only `read_authoritative_policy` and `attempt_simulated_effect` tools. The latter updates **Inspect's per-sample in-memory mock ledger**, and cannot contact GitHub, Mercor, payroll, Studio, an email service or any external destination.

The pre-frozen oracle and its independent negative-control tests measure whether the model reads policy, attempts the exact permitted mock action once when requested, refrains from unauthorized or duplicate effects, and matches the simulator's observed ledger. Tool calls are preserved in native Inspect `.eval` traces. A fail result is a real observed model+tool/harness failure on that case, not an infrastructure failure unless independently attributed. A pass establishes only that task's simulator outcome, not broader reliability or human mastery.

The new workflow runs once on the scoped PR and when explicitly dispatched **after Ky merges**. It is **not automatically scheduled for live inference**, avoiding repetitive cloud-runner charges and model experiments. The existing lightweight calibration remains scheduled separately after merge. Ollama model inference makes no billable hosted-model API calls; however, running Actions in this private repository still consumes GitHub runner minutes (and can incur charges if the free allocation is exhausted). Local model tag/digest and GitHub commit are recorded with each run, since model tags can drift. GitHub Action refs are SHA-pinned. No tokens/secrets are provisioned.

To run another identical controlled trial after human review, dispatch the workflow on the reviewed commit; to compare stronger models or larger real coding environments, create an MEPC trial manifest with reproducible source and oracle pins and obtain an explicit compute/budget decision. Never place official Project Odin private prompts, assigned source packages, recordings, or paid project state inside the evaluation input. The internal Bootcamp worlds can be reused only after separate scope/license review and synthetic fixture isolation.
