# Deployed task preparation processes

The five existing Make scenarios are the cloud owners. Their deployed module
configuration, prompts, routes and source bindings are captured in
[make-processes.json](make-processes.json). The
[receipt](make-processes-receipt.json) records the read time, source hashes,
execution IDs and the precise limits of that evidence. Connection credentials
and connection identities are excluded from the export.

## One task row and one cloud handoff

The existing Notion Task Factory data source
`74aac26d-fcbb-45df-b996-561f76b9cec6` remains the task queue.
Keep an existing row when resuming work. Do not generate another idea, issue or
starter for a row that already has a canonical handoff or published source.

| Existing scenario | Current owner and admission |
| --- | --- |
| 6550627 — Idea Miner | Daily candidate generation from the actual certification authority, market skill gaps and existing Task Factory. Normalized fingerprint, variation axis and title suppress repeat ideas. New rows retain blank approvals, PENDING packs and unchecked human gates. |
| 6550857 — Bootcamp builder | Candidate/PASS, Bootcamp or Dual-candidate, World queued, PENDING, empty paid approvals and Build Issue. A canonical main Spec PR actually merged by KyPython, three exact merged documents, and authenticated private Kiro PASS receipt plus captured CLI evidence are required before coding. |
| 6547847 — Existing Kiro spec handoff | One unfiltered queue read selects either approved Odin with exact Approved Goal/Approval ID, or Candidate/PASS, Bootcamp/Dual-candidate, World queued, PENDING and empty paid approvals. Internal candidates require a source contract and valid spec path. Existing Kiro Issue, Spec PR, Build Issue or published source prevents another handoff; Bootcamp Stage stays Candidate. |
| 6550231 — Manifest reviewer | Admitted rows with a canonical Build Issue and no Build PR. Requires complete bounded manifest evidence before review. |
| 6548371 — PR reviewer | Admitted rows with a Build PR. Requires a merged PR, full source commit, complete bounded file patches before review. |

The daily miner is active at 03:15 configured local time (next verified execution 2026-10-08T07:15:00Z). Builder/reviewers poll every 15 minutes and the existing Kiro handoff hourly. Existing mapped companions also poll every 15 minutes. The miner reads the native certification data source
`d0ea98d6-79eb-4f67-b39b-8ce57d282a2e`. Its prompt accepts the actual row-property
response and preserves supported mapping granularity. New schema fields record
certification evidence level, objective/domain coverage, allowed Human Rebuild
capability IDs and the human transfer test. These fields describe the work being
tested; they do not establish mastery, certification readiness or paid admission. Fresh native certification SQL identifies SAA-C03 as the sole Active now credential. Its real measured gaps receive priority when a world genuinely exercises them; AWS labels are never forced. The capability decoder is bound to the actual cloud 4.1.0/38-ID source in capability-authority.json, with the divergent local 4.2 source kept separate. Actual Code output paths use result.version/ids_csv/ids_json.

## Deployed Bootcamp builder route

The current module order is
`1 → 7 → 2 → 14 → 15 → 16 → 17 → 18 → 19 → 20 → 21 → 3 → 8 → 12 → 13 → 9 → 4 → 10 → 11 → 5 → 6`.

1. Module 1 reads the unfiltered Task Factory with page_size=100. Module 7
   checks eligibility and fingerprints. Module 2 feeds one eligible row with
   a canonical Spec PR; missing Spec PR holds coding.
2. Module 14 reads that PR through the existing GitHub connection. Module 15
   admits only an actual KyPython merge into KyPython/ai-governance main and
   reads the spec directory at merge_commit_sha. Modules 16/17/18 read raw
   requirements.md, design.md and tasks.md at that same immutable merge.
3. Module 19 parses unique execution/receipt markers from the PR and derives
   only the trusted private preparation-repo receipt/capture paths at a full
   immutable commit. Modules 20/21 fetch their actual encoded bytes. Module 3
   verifies encoding, UTF-8, byte sizes, Git blob hashes, receipt/capture
   SHA-256, exact row/Goal/path/PR, actual session target and all three merged
   document hashes. The Goal digest covers UTF-8 verbatim Goal plus one LF.
   Receipt specCommit binds PR head.sha; merge_commit_sha independently pins
   the human-merged documents. Only then does module 3 serialize the complete
   starter contract and supported certification/capability/transfer metadata.
4. Modules 8/12/13 read issue pages 1/2/3 with state=all and per_page=100.
   Module 9 resolves the exact ODIN_BOOTCAMP_ROW_ID:<row-id> marker.
   Canonical recovery pins retain Cursor #58 and Threshold #86.
5. Module 4 uses the resolver's method, URL and serialized payload. Existing
   issues use GET; only a new eligible world uses POST. The exact issue marker
   is verified before any next step.
6. Module 10 reads comments. Module 11 skips an existing Codex handoff/result
   and closed issues. Module 5 uses GET on retry, POST only for a first comment.
7. Module 6 writes only Build Issue, Bootcamp Status=World building and Last
   Updated. Approval, paid-task Stage, Lane, Fit Gate, recording gates, hours
   and human review decisions are preserved.

Keep one serialized builder owner. Issue creation has no native idempotency key.
The complete inventory recovers a created issue after a failed Notion write;
comment history suppresses another handoff after a successful comment.

## Actual Kiro evidence and separate internal admission

The existing Kiro owner reads the complete bounded queue before selecting its
two lanes. Requests carry exact Goal, Source Evidence, Variation Axis, Human
Transfer Test and Professional Judgment; they cannot invent human decisions.
They recover by exact lane-specific row marker. Created/recovered Bootcamp
requests preserve paid-task Stage through dynamic writeback.

The existing authenticated preparation publisher must capture the real completed
Kiro CLI session before publishing PASS. The private version-1 receipt records
engine=kiro, actual executionId, inventorySha256, reviewed specCommit, per-row
bindings and per-document PASS/hashes. executionEvidence requires
source=captured-kiro-cli, executionTarget=local or cloud, the exact paired
capturePath and its SHA-256. Full UUID and sess_UUID identifiers are retained;
a cancelled cloud session cannot substitute for the actual local session.
The PR has unique KIRO_SPEC_EXECUTION_ID, KIRO_RECEIPT_COMMIT and
KIRO_RECEIPT_SHA256 lines. The receipt and capture live at
cloud/kiro-receipts/<full-id>.json and .capture.txt in the private preparation
repository. No credentials or private starter bytes enter the public queue.

The verifier checks authenticated publication integrity and exact bindings.
Normalized metadata or a session identifier alone does not independently prove
engine execution; truthful captured evidence is the publisher's trust boundary.
Missing receipt, blank capture, non-PASS review, changed documents, Goal mismatch
or missing human merge remains HOLD. Synthetic checker receipts are tests only.

Existing eight worlds remain registered and unchanged. Ten recovered source
worlds await actual Kiro spec PASS and human merge before new registration or
promotion. User-authorized internal Bootcamp admission uses separate technical
metadata: original Odin Stage, Fit Gate, Approval ID and Approved Goal remain
untouched, including rejected/awaiting-approval tasks. This does not place them
in the native polling owner's Candidate/PASS lane or grant paid approval.
Reviewed registration, an exact worked route and successful artifact promotion
remain required. There is no second scenario, publisher or source builder.

## Operator pack ownership and gates

The manifest and PR selectors are mutually exclusive through Build PR presence.
Both use the same `operator-pack.js` source. They preserve a single managed pack
identified by `TASKWORK_OPERATOR_PACK:<row-id>`, revision and content digest.
Unchanged content uses GET. Changed verified owned content uses PATCH. Duplicate
managed blocks, manual edits, children on a managed block, incomplete page reads
or an existing finalized native recording route hold for reconciliation.

Content must be durably saved with the expected block and revision before
properties are updated. Only pack metadata, Environment Review Gate and
No-Solution-Leak Gate are written. Local Starter, Pre-Record, Recording QA,
Submission, workflow, hours and human review fields are preserved.

Source review and an operator pack do not establish actual Recorder access,
Studio state, recording QA or submission. Those checks require live evidence
from the recording account. The full Task Factory automation in governance Issue #12 is not claimed complete by these owners. Future worlds still need actual Kiro review and human merge, published source, review, registration, an exact reviewed route and a successful artifact promotion before they enter the runnable kit. Active polling does not establish those stages. Morning refresh reuses existing successful artifacts and preserves work; it is not another world builder.

## Explicit bounds and observed runs

These workflows currently use bounded reads, not unlimited pagination.
Task Factory queries and managed-page block reads use 100 results and hold on
`has_more`. Issue recovery reads at most three 100-item pages and holds when
the third is full. Comment history holds at 100 items. Manifest review holds
on unsafe/duplicate paths, invalid or binary encoding and evidence over 50,000
characters. PR review holds on unmerged or invalid source, missing patches,
incomplete/full 100-file inventory and evidence over 42,000 characters.
A larger source requires complete-tree inspection or a deliberate pagination
extension before automated review.

Private Kiro receipt/capture reads each hold above 1,000,000 bytes; raw spec
documents each hold above 50,000 characters. The merged directory must contain
one entry per required document and cannot exceed 100 entries. Source bindings
include the exact Kiro verifier embedded in builder module 3 and as module 19's
prefix. Raw-file, deployed-code and source-prefix hashes are all checked.

The receipt retains historical canonical recovery execution
`0fb3e185b2144a46afbfca974a55cf1d`: issue #86 and its prior handoff were fetched
with GET, so no new issue or comment was posted. Later successful selector-only
runs are listed separately from that recovery and from any actual source review.
The miner has configuration and offline-contract evidence only; no new miner
run was forced. After the final adapter repair, builder execution
`273dff3d682a4f7e8c63d83211774e62` succeeded and handed off two newly queued worlds
at issues #196/#197, with historical World building writebacks. Both worlds have since been recovered to real private sources, registered, source-reviewed and included in the current eight-task kit with exact scripts. Those dated writebacks are history, not current pending-source claims. The initial worker completions contained cloud task summaries and PR metadata but no actual GitHub PR URL or complete manifest. One stable recovery instruction was posted on each existing issue on 2026-10-08, requiring existing source reuse, complete machine-readable source identity/files and honest real PR evidence. It authorizes no new world or starter repair. See outputRecovery in the current receipt. Both recovery workers responded with an actual access blocker: their GitHub session is unauthenticated and cannot read the already private source repositories. They preserved the source and reported no manifest, baseline or real PR; sandbox administrative records are not published artifacts. Authenticated administrative readback separately confirmed both private repos and exact pins. Worker evidence remains pending, even though the existing eight published worlds are consumable. No credentials were copied to the worker. Authenticated repository metadata also confirms the canonical ai-governance queue is PUBLIC. Private starter bytes were not exported there. A complete-byte connector FINAL RESPONSE is allowed only for a verified private destination; public handoffs return pins/hash inventory and an actual private artifact pointer or an honest blocker. Missing authenticated source publication/review stays pending.
The builder publication contract now requires one private KyPython source, full commit SHA and complete ODIN_STARTER_MANIFEST files, with actual ordinary-path baseline outcomes and a real PR URL when available. Unavailable publication is a blocker, not READY. The operator pack independently requires a published starter repository/full pin and saved verified content; a worker summary alone cannot promote a pack. The latest builder/reviewer run IDs and invoked modules live in
the receipt so a no-op success cannot be mistaken for an end-to-end pack build.

The historical unauthenticated worker blocker is preserved. The existing
manifest owner 6550231 now retrieves private pointers through its healthy
GitHub connection, verifies commit/tree/blobs/modes and guards fresh native
Goal/lane/pins before writes. Its prior actual audit verified 14 files; its
normal retry selected zero rows and made zero review or Notion writes. That
receipt is unchanged and grants no new-task promotion.

Fresh inspected Kiro execution 8e732951abd14190aee8f49c4697ea7c and builder
execution 48053f32d8c94bbfb48a8db802994023 succeeded with only their query,
selector and feeder invoked. Neither reached issue, comment, review or Notion
writes. Final builder verifier source was re-read after its 06:07:16Z edit;
those no-op runs did not execute it. Offline fixtures check that adapter
separately. These observations establish no new Kiro PASS, merge or built world.

After the final Build Issue duplicate guard, Kiro execution
dc81e3abca684e68915395eb24977093 succeeded at 06:22:59Z with only modules 1/2/3
invoked once each and zero errors. No issue, comment or Notion write module ran.
The previous run and source revision remain recorded as history; no absent
packet-cycle field is inferred.

## Duplicate reconciliation and checks

The duplicate cleanup is executed and verified, not proposed.
[duplicate-cleanup-receipts.json](duplicate-cleanup-receipts.json) verifies
114 closed duplicate issues at 2026-10-07T23:47:07.793598Z. Original bodies and
222 pre-closure duplicate comments remain preserved. Canonical #58/#86 and
original Odin #43/#44/#46/#47 remained open. No reconciliation comments were
posted. The [archive](duplicate-cleanup-archive.json) retains the original
outputs; the [index](duplicate-reconciliation-index.md) links every closed
issue and its canonical task or non-admitted Notion row.

Run the offline cloud checks with:

```sh
node scripts/check_cloud_processes.js
node scripts/check_kiro_handoff.js
node scripts/check_kiro_proof.js
node scripts/check_operator_pack.js
node scripts/check_idea_miner.js
node scripts/check_review_evidence.js
node scripts/check_make_exports.js
```

The export checker executes the captured deployed adapters with synthetic
fixtures and checks raw/deployed source hashes, missing/later references,
main/Ky merge ownership, encoded private evidence and exact hashes, HOLD on
missing engine proof, lane-specific recovery, evidence bounds, mutual exclusion,
content-before-properties ordering and human gates. It makes no cloud calls
and cannot create real Kiro evidence.
