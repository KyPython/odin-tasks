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
