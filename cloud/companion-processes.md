# Existing metadata and transfer companions

The [fresh snapshot](companion-processes.json) and [receipt](companion-processes-receipt.json) capture the two existing owners, their exact deployed code, current schedules and observed post-fix executions. Connection identities and credentials are excluded. Earlier held-router observations are preserved as dated history in the receipt.

| Existing owner | Current state | Owned writes |
| --- | --- | --- |
| 6551447 — World → Certification + Skill Mapper | Active, every 15 minutes; fixed 2026-10-08T03:07:10.774Z | Missing taxonomy fields, Skill Mapping Revision and Last Updated |
| 6551517 — Reviewed Attempt → Transfer Router | Active, every 15 minutes; fixed 2026-10-08T03:02:03.138Z | Real assisted-exposure destination, then Transfer Synced and Last Updated after readback |

## Metadata preservation and real authority

The mapper reads the actual certification queue, current capability router and Task Factory. It creates no task or build and changes no approval, pay, review, recording or transfer flag. Its route is `1 → 11 → 12 → 2 → 3 → 4 → 5 → 8 → 6 → 7`.

The capability source is the verified GitHub cloud matrix pinned in [capability-authority.json](capability-authority.json): version 4.1.0, 38 IDs, commit c9e0db70705c548c6b9ef30a98154aa180c741ad, blob 74dfde6bdcab1d9b2475b7f8e9371b32204ef5f1. The separate local 4.2.0/35-ID checkout is divergent and is not silently promoted. The decoder requires the native Current row's exact source, version, blob and ID set. Code output mappings use the observed `result.version`, `result.ids_csv` and `result.ids_json` wrapper; wrong or missing authority holds before metadata writes.

The selector accepts complete reads, skips rejected/archived pages and preserves existing complete mappings. Empty capability lists and an explicit No supported mapping are valid outcomes. After classification, module 8 fetches the native page again. The writer verifies selected source identity and fills only missing certification, capability, transfer-test and skill fields. It preserves authored text, links and judgment. Another owner's completed mapping becomes GET. New writes have a semantic source/mapping revision, so repeats skip and later manual changes hold.

Post-fix execution 844958a2c712466b8c8b2702c0ecbb6a succeeded through the live authority decoder, selector and feeder with `{rows:[],count:0,held:[]}`. It performed no metadata or attempt write. Offline contracts check the reachable deployed writer with synthetic fixtures. These classifications establish no learning credit.

## Actual destination, conservative exposure

The existing [Study Log](https://app.notion.com/p/3e98621e0a7a818f880afb817185a6d1) now embeds Software + AI Mastery — Transfer Evidence, data source `a6d74f65-0b06-4d1a-ab64-b4fb5f1a5a52`. The same existing router queries the real Dedup Key, creates or recovers the destination, reads its actual content, fetches the source row afresh, and only then marks its owned sync flag. No second ledger or controller was introduced.

Eligible rows require actual Bootcamp Reviewed lifecycle, explicit internal Pass/Needs work/Fail and a finite 0–100 review score with notes, completed recording QA/workflow, an actual Google Drive review bundle, exact starter repository/full commit, and valid mapping/next action. A score or Reviewer Pass alone never proves an unaided attempt. The known eight AI-prepared source pins are classified as guided; other assistance is explicitly unknown. Both conservatively record Assisted exposure and Mastery Eligible=false. The router cannot automatically claim unaided transfer, mastery, exam readiness, paid approval or learner-score credit.

The V2 dedup digest binds source, guidance, review, capture gates, artifact, mappings and next action. Incomplete inventories, duplicate destination rows, stale fresh-source values, wrong destination or edited readback hold without claiming sync. Only Transfer Synced and Last Updated may change on the source row. Existing human fields are preserved.

Post-fix execution 1822039b599c44db9c95b863564dc759 succeeded with modules 1/2/3 only, selected zero qualified attempts and wrote no destination or source. That is a live selector proof, not an end-to-end human transfer receipt. Offline destination/create/retry/readback fixtures cover the actual deployed adapters.

## Portable advisory review remains proposal-only

The recording-review packager validates real immutable local bundle/media bytes, source/Goal/route/attempt identity and timestamped observations. Its report deliberately has no synthetic overall PASS or 0–100 grade. It fixes advisoryOnly=true, mastery=not_established and unaidedTransferEstablished=false; no Odin/payment assessment is implied. A JSON assertion in Reviewer Notes does not prove those media bindings, and a valid local bundle does not itself establish a cloud-accessible artifact.

That advisory feedback does not satisfy the native scored-attempt route above. No actual recording/report has been supplied. Preserve its notes and next verification as proposals; do not invent scalar grades, mark human capture/QA gates, or present it as validated human transfer. The native route remains available for genuinely supplied internal reviewed-attempt evidence. Human Rebuild grading and any unaided mastery proof remain separate human evidence.

Run `node scripts/check_companion_processes.js` for the captured source, exact authority/output mappings, preservation/retry guards and real-destination assisted-only checks. The checker makes no cloud calls.
