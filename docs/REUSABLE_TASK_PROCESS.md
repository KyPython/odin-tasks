# Reusable task preparation

One task keeps the same Notion row from idea through preparation and recording. Its real starter remains a separate repository. This administrative repository owns the reusable toolchain, source registry, cloud bundle and recording-pack checks. Existing Make scenarios own the cloud queue; adding a task does not create another queue, builder, repository copy or recording attempt.

## Sources and owners

| Fact or action | Owner | Stable identity |
| --- | --- | --- |
| Task idea, exact approved Goal, admission evidence and attempt gates | [Notion Task Factory](https://app.notion.com/p/5f67c747696c43cabc45a6b1f8dbb410) | Existing page UUID in data source `74aac26d-fcbb-45df-b996-561f76b9cec6` |
| Daily task ideas | Existing Make scenario `6550627` | Existing certification/gap evidence, Task Factory inventory, normalized fingerprint/variation/title |
| Missing certification/capability mapping metadata | Existing Make scenario `6551447` | Same task row, preserved existing fields and durable `Skill Mapping Revision` |
| Canonical Kiro spec handoff | Existing Make scenario `6547847` | Separate Odin approval and queued internal Bootcamp admission; stable lane-specific row marker on the reused Kiro issue |
| Starter-manifest operator-pack delivery | Existing Make scenario `6550231` | Existing task page and verified manifest starter, selected when Build PR is empty |
| Merged-Build-PR operator-pack delivery | Existing Make scenario `6548371` | Same task page, selected when Build PR exists |
| Queued world/build delivery | Existing Make scenario `6550857`, **Project Odin Bootcamp — Queued World → Canonical Cloud Build** | Reused canonical GitHub build issue and task row |
| Specification and build review | [ai-governance](https://github.com/KyPython/ai-governance) | Existing issue/PR; reuse it on retries |
| Starter files | Each task's private GitHub repository | Full immutable commit SHA, file hashes and original modes |
| Registration, dependency preparation and offline setup | [Recording preparation](https://github.com/KyPython/odin-recording-preparation) | `runtime/task-registry.json` and `runtime/runtime-manifest.json` |
| Cloud verification | This repository's existing GitHub Actions workflow | Preparation commit, run ID, artifact digest and `cloud-proof.json` |
| Shared local kit | `TaskWorkCloudSync.py` | Verified artifact inventory plus cloud-sync receipt |
| Current task script and its off-screen copy | Existing Notion task page and `recording_pack.py` | Task ID + page UUID + source commit + exact Goal hash + route hash |
| Reviewed-attempt transfer | Existing active Make scenario `6551517`, with its real existing learning destination | Actual recorded/reviewed source identity, bundle and observed gates; destination write/readback before source receipt; assisted exposure, with mastery ineligible |
| Morning cloud/local refresh | One `com.taskwork.morning-refresh` LaunchAgent and `TaskWorkMorning.py` | Current-head successful existing preparation artifact; integrity receipts; no duplicate world build or Recorder attempt mutation |
| Portable recording review | `process/scripts/package_recording_review.py` and `process/REVIEWER-PROMPT.txt` | The actual attempt files and exact registered source/Goal/route; timestamped advisory findings, never invented human credit |
| Actual attempt and professional judgment | Human under the Recorder account | Observed setup/UI/Studio state and actual recording evidence |

Scenario activation or historical run notes do not prove a successful current execution. The connector owner must inspect live configuration and the relevant execution before reporting cloud automation as working. Repository PR review status likewise remains distinct from a cloud build result.

The queued-world builder serializes delivery, inventories existing GitHub items before creating another and skips a repeated Codex trigger comment. Its inventory is bounded to three pages of 100 GitHub items. If page three is full, it stops rather than claiming the inventory is complete or creating a potential duplicate. Existing canonical world issues remain the owners; a queue retry does not produce another build issue. The manifest and PR pack selectors are mutually exclusive, already delivered rows are skipped, managed content is delivered before its new READY status, and each task retains its stable block/revision reference.

The daily idea miner reads the existing certification/skill-gap sources and full task identity inventory. Supported capability IDs and sourced objective coverage constrain its mapping labels: **Objective-level**, **Credential/domain-level** or **No supported mapping**. Unsupported objective labels are downgraded; empty asserted objective coverage cannot admit a candidate. These labels describe the available source/mapping evidence. They do not establish learner mastery, an exam result, certification eligibility or an official exam blueprint. Candidate Goal and professional judgment fields are proposals until the human uses their judgment; Odin approval fields stay empty. The existing Kiro handoff preserves the exact externally approved Odin contract and separately accepts queued Candidate/PASS Bootcamp or Dual-candidate rows with empty paid approval fields and no previous source/build/spec handoff. Both lanes receive their real source contract and existing human transfer/judgment context without invented decisions.

Actual Kiro spec preparation precedes coding. The existing Bootcamp builder requires KyPython's real merge into ai-governance main, exact Goal/row bindings, unchanged reviewed requirements/design/tasks bytes, and an authenticated immutable private receipt with the actual captured Kiro CLI output. The receipt records the actual local or cloud execution target; a cancelled cloud session cannot substitute for a local Spec run. Missing evidence stays HOLD. This is trusted publisher capture provenance, not independent Kiro web API authentication. Recovered cloud code remains pending until it matches the passed specification; recovery does not create another coding job.

For the user's explicitly authorized internal preparation of current held ideas, including rejected IaC, use [INTERNAL_BOOTCAMP_ADMISSION.md](INTERNAL_BOOTCAMP_ADMISSION.md). The independent preparation record binds the actual user instruction, native row, exact Goal, pinned source and Kiro evidence while preserving the original Odin Lane, Stage, Fit Gate and approval fields. It grants no recording readiness, paid eligibility or human assessment.

The companion mapper fills missing mapping metadata on the existing row. A fresh native-page read precedes its write plan; existing mappings, human transfer wording and `Transfer Synced` are preserved. Its `Skill Mapping Revision` records a reviewed mapping result even when no credential or capability mapping is supported, preventing an intentionally empty result from generating repeated classification work. Mapping a task does not establish a completed human transfer.

The fresh October 8 inspection found the existing reviewed-attempt owner active, with a real create/recover/readback delivery chain into data source `a6d74f65-0b06-4d1a-ab64-b4fb5f1a5a52`. The earlier inactive snapshot is historical. Its October 8 in-place repair removes the unsafe assumption that Reviewer Pass means an unaided attempt or mastered skill. Current Task Factory fields cannot establish validated unaided provenance, so this owner records schema-supported assisted exposure and `Mastery Eligible = false`. Known registered worked-reference pins are explicitly guided; unknown preparation does not become unaided evidence. Source/review/mapping/capture gates bind the transfer revision, and real destination identity/readback must precede the source `Transfer Synced` receipt. Preserve actual pending human state; no new ledger or parallel transfer controller is created.

The installed `process/cloud/` directory carries dated, redacted configurations and receipts for the five preparation owners and these two companions. The corresponding administrative sources are `cloud/make-processes.json` and `cloud/companion-processes.json`. They make the handoff inspectable across Mac accounts; fetch the current live configuration before a cloud change or dispatch, and reconcile a newer owner revision instead of overwriting it from a snapshot.

[Full factory issue #12](https://github.com/KyPython/ai-governance/issues/12) remains the broader factory owner. A completed Codex cloud chat alone is not an importable built world: its canonical issue must contain a real published pinned starter/PR and machine-readable starter manifest accepted by the existing pack owner. Recover a missing publication result on that issue, reusing the real source and prior work. Actual review/merge, unsupported adapters, human learning and admission decisions retain their respective owners. Never announce every stage or queued idea ready from scenario activation alone.

The existing manifest owner `6550231` now retrieves published private sources through its own authorized GitHub connection. It resolves the existing native source pin or a trusted public pointer, verifies private repository identity, the exact commit, complete Git trees and every bounded UTF-8 blob/hash/mode, then supplies those real bytes only to its private review path. Public issue comments carry pointers and hashes; private byte manifests are rejected there. An audit-only live run verified the existing Batch and Callback sources without invoking model review or any Notion write. Source retrieval does not create a starter, register a task or approve its Goal.

The saved task-idea Codex process assembles the remaining complete reviewed payload: fresh native source snapshot, exact lane/Goal, pinned source inventory, supported setup recipe, one canonical recording route, complete phased worked reference and source-bound learning-map addition. The existing registration CLI preserves prior tasks; one preparation commit triggers the existing build, and Morning installs only its successful current-head paired artifacts. Missing source publication or reviewed payload stays queued. There is no second builder, promotion workflow or learning ledger.

## Add another idea once

1. Reuse an existing Notion task row when its identity/fingerprint already exists. Compare the task's professional objective, variation axis and duplicate fingerprint before creating another row. Retain the existing specification issue/PR, build issue/PR and starter manifest references on retries.
2. Retain the task's workflow lane. Odin requires real external admission and the verbatim approved Goal. Bootcamp practice uses its own world/practice evidence; it cannot invent an Odin approval or become an unrehearsed Odin task after substantive practice.
3. Route the row through the existing cloud owner for its actual source type. When Build PR exists, the PR owner verifies that actual merged PR; when it is empty, the manifest owner verifies the real starter manifest. These are mutually exclusive paths for one task, even if both kinds of reference are stored. Do not dispatch both owners for the same row.
4. Resolve a real starter repository and full commit. Verify the spec/build/manifest against that tree. Keep the recording starter unworked. A complete worked reference must analyze and validate exact diagnosis, repair and decisive tests in a separate disposable copy; its planned steps and actual execution have separate evidence. Follow [the worked-plan process](WORKED_PLAN_PROCESS.md), preserving original requirements and truthful preparation disclosure.
5. Use `scripts/register_task.py plan` then `register` with a fresh native Notion fetch, real GitHub repository URL, immutable commit, neutral name, supported dependency profile and reviewed setup recipe. It fetches the real Git tree, verifies a clean source copy and exports unchanged files/Goals while preserving old registrations. It appends the task to `runtime/task-registry.json` and hashes/modes to `runtime/runtime-manifest.json`; it does not fabricate a recording route. Include stable identity, source/build references, dependency versions/roots and disposable baseline commands in the reviewed recipe. Current supported profiles are `python-stdlib`, `python-pytest`, `node-stdlib` and `pnpm-workspace`; other profiles need a reviewed adapter. Dependency-free Node uses the public pinned Node 22.22.0 and no package installation. Declared local Python JSON outputs require a safe source-bound producer before a later baseline consumes them.
6. Put the reviewed task route in `packs/routes/<neutral>.md` and a native, complete Notion fetch in `packs/pages/<neutral>.json`. A route has exactly one `### Recording sequence — follow this order` heading, contiguous numbered steps, concrete source paths and commands, conditional outcomes, and capture start/stop instructions. Existing files are dated cloud snapshots; a connector must fetch again before publishing a live edit.
7. Run the existing preparation workflow. Reuse a successful artifact for the same preparation revision instead of rebuilding it for every account switch or recording attempt. Validate the archive, inventory, source files, Goal files and cloud proof before syncing the shared kit.
8. Under the actual Recorder account, prepare only the selected task using the installed helper's supported selection. Existing tasks with human edits remain intact. Open that task's exact workspace, Goal document and current Notion page; complete actual admission and UI checks before capture.

Registration fails closed for missing or contradictory source/Goal evidence, unsupported dependency profiles or unsupported workflow authorization. A queued idea without a real source and reviewed pack remains queued. Adding a name or proposed spec path does not establish a built environment.

`workflowLane` is separate from the professional `lane`. Odin records retain their exact `ODIN-...` approval ID and `approvedGoal`. Bootcamp records use `BOOTCAMP-<existing-page-UUID-hex>` and `candidateGoal` with `goalKind: candidate`; the Notion row's legacy **Odin Goal** field stores that candidate text, while **Approval ID** and **Approved Goal** must remain empty. The candidate must have a real canonical build issue, PASS fit, Candidate stage and World building state for registration. Its source and script can be reviewed without claiming a Studio assignment, Odin admission or a merged spec.

For a new task, a reviewed recipe JSON supplies `lane`, `workflowLane`, `dependencyVersions`, `dependencyRoots` and `baseline` command objects (`argv`, optional `env`, `allowedExitCodes`, `contains`); pytest also needs `requirementsFile`. Run the registration tool off-screen, for example:

```bash
python3 scripts/register_task.py plan \
  --page-json /path/to/fresh-native-notion-fetch.json \
  --source-repo https://github.com/KyPython/real-starter-repository \
  --commit FULL_VERIFIED_40_CHARACTER_SHA \
  --neutral selected-neutral-name \
  --profile python-stdlib \
  --setup-json /path/to/reviewed-setup-recipe.json
```

The example values are placeholders to resolve from actual cloud/source evidence. After reviewing that concrete plan, use `register` with the same verified inputs; a retry reuses the same task, repository and canonical issue. Registration never requests another completed cloud build simply to import its existing starter.

## Readiness means a specific verified fact

| State | Evidence required | Next action |
| --- | --- | --- |
| Idea queued | Existing task row and its recorded lane/objective | Existing cloud owner resolves the spec and starter |
| Starter verified | Real repository/commit, exact source inventory, review and no-solution-leak checks | Register that starter and its exact Goal |
| Cloud prepared | Successful preparation run and verified bundle for the selected registry revision | Sync that bundle to the shared local runtime |
| Shared kit synced | Archive/member/source checks plus sync receipt | Actual Recorder account runs selected setup |
| Recorder setup verified | Real Recorder-owned workspace, dependencies and controlled profile checked | Complete current Studio, permissions, metadata and pre-record checks |
| Ready to record | Actual attempt has its current admission and pre-record checklist evidence | Human records the task |
| Recorded/reviewed/submitted | Actual recording, review and submission observations | Update only the corresponding observed gates |

The publisher's receipts always keep `recordingReady: false`, `practiceReady: false`, `setupVerified: false` and `recorderExecuted: false`. They describe off-screen source/script publication. Bootcamp exports explicitly identify a candidate Goal and make no external approval claim. A supplied, independently verified cloud proof can establish `cloudPrepared`; a page's prose or an old checked gate cannot substitute for that proof. No exporter or cloud builder checks live admission gates on the human's behalf.

## Update a script without duplicating it

`recording_pack.py` uses the existing page UUID. It replaces the exact managed route with a targeted Notion update, preserving unrelated wording and native child pages, databases, folders and mentions. It never updates tracker properties. First insertion requires `--initialize` and a page with no route; repeating that insertion produces a no-op. Duplicate routes, unsupported blocks, incomplete fetches and ambiguous source/Goal identity produce `HOLD`.

For Make's existing `TASKWORK_OPERATOR_PACK:<page-UUID>` paragraph, the publisher verifies the recorded full body SHA-256 before reading its route. It accepts supported escaped-markdown/line-break representations only when decoding reproduces that exact ownership digest. A matching reviewed route publishes with a no-op; a changed route returns to the existing Make block owner rather than creating or rewriting a competing native pack. Manual edits, a mismatched ledger revision, duplicate markers or a second native route stop publication and preserve the content.

The connector runs this sequence off-screen:

1. Fetch the registered Notion page through the existing authenticated Notion connection and save the complete JSON response to a temporary file outside recorded work.
2. Generate a plan from that fresh fetch and the reviewed route. For example, from this administrative repository:

   ```bash
   python3 scripts/recording_pack.py plan \
     --task dispatch-board \
     --page-json /Users/Shared/TaskWorkStart/sync-staging/dispatch-board-fetch.json \
     --route-file packs/routes/dispatch-board.md \
     > /Users/Shared/TaskWorkStart/sync-staging/dispatch-board-plan.json
   ```

3. If the operation is `noop`, keep the page. Otherwise fetch again immediately before applying the plan and run `assert-current` against that latest fetch. A changed page revision or body requires reconciliation and a new plan. Pass only the plan's `notionUpdate` object to `notion.update_page`; do not wrap it in a whole-page rewrite or append another pack.

   ```bash
   python3 scripts/recording_pack.py assert-current \
     --task dispatch-board \
     --page-json /Users/Shared/TaskWorkStart/sync-staging/dispatch-board-latest.json \
     --plan-json /Users/Shared/TaskWorkStart/sync-staging/dispatch-board-plan.json
   ```

4. Fetch the updated page again. The exporter verifies its task, exact Goal, source pin, route hash and unchanged content outside the route before publishing. A no-op still uses the fresh fetched page as its readback.

   ```bash
   python3 scripts/recording_pack.py publish \
     --task dispatch-board \
     --page-json /Users/Shared/TaskWorkStart/sync-staging/dispatch-board-readback.json \
     --plan-json /Users/Shared/TaskWorkStart/sync-staging/dispatch-board-plan.json \
     --cloud-proof /Users/Shared/TaskWorkRuntime/cloud-proof.json \
     --output /Users/Shared/TaskWorkStart/generated
   ```

After installation, use `/Users/Shared/TaskWorkRuntime/recording_pack.py` with the same arguments; it locates the installed registry, source inventory and reviewed pack files. Task IDs or neutral workspace names work as `--task`; examples are not a four-task limit. The selected registry record supplies the real page, repository and Goal.

The examples above publish the shared guide under its administrative owner. Under Recorder, keep fetch/plan/readback files in `$HOME/Documents/TaskWorkPreparation/sync-staging/` and use `--output "$HOME/Documents/TaskWorkPreparation/generated"`. Recorder must not write into ky-owned shared directories or change their permissions; its current copies and status report belong to Recorder.

Publication writes `generated/tasks/<neutral>/cue-card.{html,txt}`, the complete native fetch/body, exact Goal and a hashed receipt. Identical input produces a no-op with no new history. Changed verified input preserves the previous publication under `generated/history/<neutral>/` before replacing that task's cue directory. Ownership hashes cover every generated file and receipt; edits, unexpected files, symlinks, an unmanaged destination or another publisher's active lock stop replacement. Existing Recorder projects, recording archives and human notes are never publisher destinations.

Make's block owner should likewise retain one stable managed block per task, recover its marker after a partial delivery, compare its revision before generation and set operator-pack delivery status only after successful content delivery. It must preserve unrelated native page content and keep actual attempt gates unchanged. A failed content write must not leave a new `READY` claim.

## Retry the missing stage

| Existing verified result | Retry behavior |
| --- | --- |
| Same task row/fingerprint | Reuse the row and its source references |
| Existing spec or build issue/PR | Inspect and advance that item; do not create a twin |
| Same delivered operator-pack revision | Skip generation and content write |
| Existing supported or explicitly unsupported mapping revision | Preserve its fields and skip repeated classification |
| Reviewed-attempt transfer lacks verified destination writes | Preserve pending transfer; retry the existing destination identity and delivery stage, with assisted exposure and no mastery credit |
| Same preparation commit has a successful artifact | Verify and reuse it |
| Local shared kit matches the verified artifact | Verify existing receipt; avoid another download/extract/install cycle |
| Cue publication bytes match | No-op; retain modification times and history |
| Another task already has recorded human edits | Preserve it while preparing the selected task |
| The selected task contains human edits | Hold before overwriting; inspect its existing attempt |
| Actual Recorder/UI/Studio checks are missing | Complete those checks under the real account; keep attempt readiness pending |

Baseline rehearsal runs in disposable cloud or off-screen copies. Recording workspaces contain unchanged starters and local dependency setup until the human begins the task. Cloud sync publishes verified shared inputs/runtime, and the Recorder helper owns Recorder-local setup; neither path resets a human attempt.

Complete worked references for every runnable registered task use the same task identity, immutable source and exact Goal. The existing preparation workflow verifies them in disposable copies and publishes a separate `taskwork-worked-plans-macos-arm64-{commit}` artifact. Its proof describes actual reference repairs/checks and preserves the unworked starter bundle. Synchronize the verified reference into `/Users/Shared/TaskWorkPlans/`; keep its exact walkthrough available off-screen. Reuse that proof/reference on account switches and retries instead of solving or rebuilding the same plan again. Reference verification establishes the technical sequence, not paid acceptance, actual Recorder admission or unaided skill transfer. Original Writer Guidelines p. 63 requires advance knowledge of each step; a categorical ban on all off-camera analysis/rehearsal was our earlier interpretation and is superseded by this process.

## Verification

```bash
python3 scripts/check_recording_pack.py
python3 scripts/recording_pack.py validate --pages-dir packs/pages --routes-dir packs/routes
```

The behavior checks cover retry no-ops, one targeted update, first insertion, stale page rejection, unrelated native-content preservation, duplicate route rejection, exact Goal/approval/source checks, truthful readiness, HTML escaping, old-version retention, preservation of edited output/receipts, safe destinations and publication locking. The normal preparation workflow runs these alongside source, dependency, cloud-sync and selected-setup checks.
