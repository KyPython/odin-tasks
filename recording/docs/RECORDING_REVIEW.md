# Review a recording as practice

Use the existing task, exact script and worked reference for a guided attempt, then ask any suitable model to review the files against an evidence-based Odin rubric. This is advisory feedback for learning. It does not represent an authorized Odin review, external approval, earnings or mastery. A guided reproduction can be useful even when it is short or imperfect; preserve the separate Human Transfer Test for a later attempt with the required unaided conditions.

The original October 3, 2026 Writer Guidelines supports advance planning on pages 27 and 63, an unworked starting task on pages 45 and 120, and manual task creation without AI interaction during capture on pages 87–89. It requires truthful provenance and actual recorded work. The source does not explicitly settle external eligibility of a complete AI-authored walkthrough. Current announcements and the actual approved task still govern. `docs/WORKED_PLAN_PROCESS.md` records this distinction; this protocol does not invent permission or an expert's independent judgment.

## Make one portable bundle after stopping

Stop TaskRecorder normally and wait through Stopping → Archiving → Idle. Keep the original `recording_TIMESTAMP.zip` and earlier attempts unchanged. The package command copies an explicitly selected attempt's files and hashes the raw ZIP bytes; it does not extract, rename in place, repair, recompress, upload, run tests or start capture. The command can run from the real Recorder account with its own files. It refuses another account's attempt files and symlinks, including a route into another account's home. Do not use impersonation or change ownership to bypass this check.

Create an attempt descriptor in your own account with absolute paths to the exact attempt. Missing evidence is allowed, and remains unverified. These paths are examples, not claims that files exist:

```json
{
  "version": 1,
  "attemptId": "practice-20261008-clock-01",
  "guidanceMode": "guided",
  "priorWork": "I used the supplied AI-authored complete walkthrough and narration plan. This is guided internal practice, not an unaided transfer attempt.",
  "recordingArchive": "/Users/recorder/Library/Application Support/TaskRecorder/recordings/ACTUAL_RECORDING_NAME.zip",
  "video": "/Users/recorder/Library/Application Support/TaskRecorder/recordings/ACTUAL_RECORDING_NAME/video.mp4",
  "deliverablesArchive": "/Users/recorder/Documents/ACTUAL_ATTEMPT/Deliverables.zip",
  "finalWorkspace": "/Users/recorder/Desktop/TaskWork/dispatch-board"
}
```

Replace the example values with actual existing paths; do not guess the newest recording or mix attempts. Add `metadata` for the actual separate Odin `Metadata.rtf`, `audio` for separately supplied actual audio, `transcript` for a truthful supplied transcript, `recordingLog` for the actual recorder log, or `commandLog` for a saved JSON array of command evidence. Bootcamp does not require invented Studio approval, Metadata.rtf or paid time tracking. `declaredDurationSeconds` is an optional declaration; the model must measure actual media before judging timing or calculating screenshots per second. The final workspace is read only; dependency/cache folders are omitted, task files and generated outputs are copied. Review sensitive evidence locally before deliberately choosing to give it to an external model. Packaging performs no upload.

The command log format is typed evidence, never executable shell text:

```json
[
  {
    "argv": ["python3", "-m", "unittest", "discover", "-s", "tests", "-v"],
    "cwd": "dispatch-board",
    "exitCode": 0,
    "stdout": "COPY THE ACTUAL OBSERVED OUTPUT",
    "stderr": "COPY THE ACTUAL OBSERVED OUTPUT"
  }
]
```

Do not replace actual logs with the expected reference output. Submitted logs can support file review; only actual footage supports a claim that the person visibly ran a command. The wrapper never executes submitted argv, repository code, tests or archive members.

Run the installed packager with public Python after the administrative owner includes it in the next verified runtime artifact. Until that sync occurs, its source entrypoint is `scripts/package_recording_review.py` in this repository; do not claim a new installed path exists before verification.

```sh
/usr/bin/env python3 /Users/Shared/TaskWorkRuntime/process/scripts/package_recording_review.py package \
  --task dispatch-board \
  --attempt /Users/recorder/Documents/ACTUAL_ATTEMPT/attempt.json \
  --output /Users/recorder/Documents/ACTUAL_ATTEMPT_REVIEW_BUNDLE \
  --skill-map /Users/Shared/TaskWorkRuntime/process/learning/skill-map.json
```

The registry selects any existing task; there is no new miner or hardcoded four/eight-task list. `--runtime`, `--inputs` and `--plans` can point to portable copies instead of their Shared defaults. The starter inventory, exact Goal bytes and selected cloud reference identity/patch hash must match. `--skill-map` is optional and must bind the existing selected task. Choose an output outside all inputs and attempt folders; its parent must exist and belong to the invoking user. Repeating the same request with the same evidence returns `noop`. A different attempt or an edited bundle is preserved, and the command asks for a different output rather than overwriting it.

The output folder is the portable artifact. It includes its manifest and byte hashes; model prompt; rubric and JSON report schema/template; exact starter/Goal; canonical script and phase patches; distinctly labeled preparation proofs; the raw selected archives/media/metadata/logs; and a static diff of the submitted final workspace against the starter. It contains no model service credentials. Original archive basenames and bytes are preserved. ZIP central-directory inventory is bounded and rejects ambiguous, duplicate, unsafe, encrypted or linked member names; it does not unpack members or assert CRC/media readability. Archive/header validation errors HOLD packaging without changing the attempt.

## Give the bundle to a model you choose

Copy `docs/REVIEWER-PROMPT.txt`, or the bundle's `reviewer-prompt.txt`, as the instruction. Supply the bundle files and actual matching video/audio through that model's supported interface. Some interfaces cannot read large or nested archives; attach the separate media and relevant text/files directly, preserving the manifest identity. If the model cannot watch video or listen to audio, request a text-only review and leave timing, screen execution, audio quality, privacy, mouse behavior and unseen work unverified. A timestamped transcript helps discuss explanation as text; it does not establish what appeared on screen or how clearly speech was delivered.

The reviewer maps each canonical step to actual timestamped observations and returns the report schema. It reports `observed_met`, `observed_gap`, `unverified` or `not_applicable` for each bounded criterion. It cannot guess an overall pass. Full-attempt conditions require full relevant media coverage; a sampled review describes its intervals and leaves the rest unverified. Privacy feedback cites categories/timestamps without repeating sensitive values.

Write the completed report outside the immutable bundle and validate it:

```sh
/usr/bin/env python3 /Users/Shared/TaskWorkRuntime/process/scripts/package_recording_review.py validate-report \
  --bundle /Users/recorder/Documents/ACTUAL_ATTEMPT_REVIEW_BUNDLE \
  --report /Users/recorder/Documents/ACTUAL_ATTEMPT_REVIEW.json
```

Validation checks report shape, exact task/attempt/bundle identity, every criterion/step, actual supplied evidence paths, media capability/coverage declarations, timestamp bounds, lane applicability and preserved advisory limits. It rejects a text/log-only claim of observed recording execution, sample-only whole-attempt success, guided-to-unaided promotion and invented skill IDs. It does not inspect video, authenticate a model's honesty, establish archive/video correspondence from names, or approve the recording. An untouched report template remains all unverified and is not a review.

## Use feedback for the next attempt

Keep one actually observed strength. Pick at most two specific practice focuses, such as naming the file and reason before editing or saving before a decisive check. Use the existing task/script and concrete recovery for a manageable next guided attempt; preserve the previous attempt and its report. Once useful, a separate attempt under the unchanged Human Transfer Test can assess unaided transfer. Rehearsal success or flawless script delivery does not award mastery.

The report emits only proposal-style `skillFeedback`: an existing mapped skill ID, guided/unaided observation kind, observed/needs-practice/unassessed finding, timestamped artifact evidence and an existing remediation task. The skills registry starts human evidence unassessed and remains authoritative. An existing transfer ledger may record assisted exposure with mastery ineligible; this packager creates no new cloud ledger and writes no Notion, ReviewerPass, Transfer Synced, QA, submission, approval or human fields. A human or existing workflow owner reviews feedback before any real state change.
