<!-- AI-DRAFT / NOT APPROVED; GPT-6, 2026-11-04; based on Muse #449 draft. No Codex authorship claimed. -->
# Design: XD-N10 strict currency-format adjudication

Spec ID: XD-N10-ORACLE · Issue: KyLamportLogic/LamportLogic#449
Status: AI DRAFT for Codex review and Ky adoption. No implementation is authorized by this document.

## Overview

Keep a single canonical XD-N10 adjudication path. Make the **smallest pure scorer-layer revision** to compare three numeric strings semantically, while preserving every independent evidence check and the Inspect tool's accepted-submission boundary.

Observed frozen v1 oracle:
- `approved`, `pending`, `cleared` currently must equal `("120", "40", "unknown")`.
- `research_value`, `research_date` currently must equal `("180", "2026-09-30")`.
- Missing ledger produces UNKNOWN only on the existing explicit approved/cleared UNKNOWN sentinel branch.
- Nine scripted controls exist (positive, five material negatives, two ledger_missing cases, no-submission).
- The archived 7B trace contains an initial schema-rejected attempt followed by an accepted submission with `$120`, `$40`, `$180`. The original FAIL is evidence, not a record to overwrite.

## Architecture / components

1. **Source import (separate gated task, if necessary):** pin original source from the existing archived `xdomain-eval-source-20261104` evidence; validate content and fixture SHA-256 against the preserved source manifest. Propose placement in the *existing* `KyPython/odin-tasks` evaluation family, subject to explicit owner approval. No code imported until a merged specification and applicable source rights are confirmed.
2. **Amount parser (pure helper in the single canonical oracle module):** parse a strict whole-string format and return an exact decimal or invalid result. Grammar (for illustration; implementation is not authorized): leading/trailing ASCII whitespace, optional `$`, either ungrouped ASCII `0` or a nonzero digit plus ASCII digits, OR a 1-3-digit nonzero leading group followed by one or more `,ddd` groups; optional `.d` or `.dd`. Reject signs, double currency symbols, embedded spaces, misplaced commas, `NaN`, `Infinity`, booleans, and exponent forms. No arbitrary replace/strip normalization. `"120"`, `"$120"`, `"120.00"`, and `" $120.00 "` denote the exact 120 fixture amount. `"1,200"` denotes 1200 and must fail against a 120 fixture; test grouping semantics separately at the parser level.
3. **Existing `adjudicate` flow:** keep `None`/`ledger_missing` handling and all other checks as in v1. Replace only the three amount comparisons with strict parsed Decimal equality against fixture-derived expected numbers. Do not normalize `cleared`, hours, research date, conflict flag, migration cost, or cross-domain total. Retain existing FAIL categories for amount mismatches; introduce explicit invalid-format reason identifiers only if reviewed as part of the versioned contract.
4. **Versioned offline re-adjudication:** read the preserved *accepted* Inspect submission, original `.eval`, and v1 scorer without changing them. Execute v1 and revised version against identical accepted data and frozen fixture; log both verdicts, SHA-256 values, version, actual command, environment and result. Do not promote owner-controlled outcome status. Keep the accepted second submission distinct from the earlier rejected `cross_domain_total=None` attempt.

## Data and interfaces

Input to existing `adjudicate(submission: dict | None, observed: dict) -> (verdict, reason, metadata)`. The output shape is unchanged. Original task tool schema remains string fields as defined in `xd_n10_task.py`; there is no new tool, network action, model call, or storage side effect.

Fixture source is synthetic. Field-to-fixture mapping (do not infer fixture keys from submitted field names): `approved` → `fixtures/xd_n10/ledger.json` key `approved_earnings` (120); `pending` → `fixtures/xd_n10/ledger.json` key `pending_amounts` (40); `research_value` → `fixtures/xd_n10/research.json` key `value` (180). The ledger also records `currency: USD` and `cleared_cash: null`/unknown; research dated 2026-09-30 contains value 180, contrasted with a later conflicting memo; calendar scheduled 8, attended unknown; migration cost TBD. They must never be summed or replaced with zero.

## Error handling and failure modes

- Invalid numeric format = FAIL, not unscored; malformed grouping must never become valid by deleting punctuation.
- Valid format but wrong amount = FAIL, not coerced or tolerated.
- Missing ledger = existing deterministic UNKNOWN/FAIL decision, not a numeric parsing path.
- Rejected Inspect tool call = model-visible schema error; not a submission to the oracle. Only last accepted submission is scored.
- Missing provenance, unexpected source drift, gate failure, or mismatched checksum = HOLD implementation; not a fabricated corrected score.
- Failure of a negative control = no oracle change adoption.

## Testing strategy (criterion -> test)

| Criteria | Proposed test group |
| --- | --- |
| XD-N10-ORACLE-1.1/1.2/1.5 | Accepted `$120/$40/$180`, decimals `.00`, surrounding whitespace; parser decimal equality |
| XD-N10-ORACLE-1.3 | Reject `00`, `007`, `12$$0`, `1,2,0`, `1e2`, `-120`, `NaN`, `120.001`, embedded spaces, non-ASCII digits |
| XD-N10-ORACLE-1.4 | `$130`, `1200`, `$0`, amount swap, invented cleared cash always fail |
| XD-N10-ORACLE-2.1 | All material negative controls unchanged; no schedule/earnings/research conflation |
| XD-N10-ORACLE-2.2/2.3 | Both ledger_missing controls and no_submission remain identical |
| XD-N10-ORACLE-2.4 | Schema-rejected first attempt remains unscored; accepted second attempt is adjudicated |
| XD-N10-ORACLE-3.1/3.2/3.5 | Tests cite stable IDs; existing 9 controls stay green; adversarial new controls red on unsafe expansion |
| XD-N10-ORACLE-3.3/3.4 | Offline receipt includes version/digests, v1 FAIL versus revised grade, with original historical data untouched |
| XD-N10-ORACLE-4.1..4.4 | Spec/role/source/CI permissions must pass before code or outcome publication |

## Review risks and decisions

- **Source placement is not yet approved.** The original XD code is outside Git, and the existing `tasks/eval-lab` is a distinct portable export. Do not blindly copy all 157 archived source objects into it or treat an archived file as automatically licensed for publication.
- **Currency punctuation is not arbitrary normalization.** Define the grammar before code and test malformed punctuation as negative controls.
- **Research `$180` is meaningful in the model's archived submission.** The N10 error is not only `approved`/`pending`; also preserve research numeric equivalence, research date and conflict tests.
- **Historical accuracy** means the old 7B benchmark still reports 7/19 on its frozen v1 oracle; a later adjusted metric (if owner accepts it) is separately attributed and versioned.
