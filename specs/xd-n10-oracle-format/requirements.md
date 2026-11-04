<!--
AI-DRAFT / NOT APPROVED / NOT PUBLISHED TO REPOSITORY
Prepared by GPT-6, 2026-11-04, using Muse's issue #449 draft and source evidence.
NOT authored by Kiro, Codex, or the owner. No owner adoption/merge is asserted.
Canonical issue: https://github.com/KyLamportLogic/LamportLogic/issues/449
Owner authorization: manual owner-override SPECIFICATION PATH ONLY, 2026-11-04.
Repository main observed at 96d167450b2ddd9502da827de945be6cbb784e67.
-->
# Requirements: XD-N10 strict currency-format adjudication

Spec ID: XD-N10-ORACLE · Issue: KyLamportLogic/LamportLogic#449
Status: AI DRAFT — pending Codex review, owner adoption, spec-only PR and Ky merge.
Intended eventual home: `KyPython/odin-tasks/specs/xd-n10-oracle-format/requirements.md`.

## Introduction

The synthetic XD-N10 conflicted-brief evaluation compares submitted facts to frozen fixture values. The frozen v1 oracle matches stripped strings (`approved == "120"`, `pending == "40"`, `research_value == "180"`), so an otherwise correct submission using `$120`, `$40`, and `$180` is mis-scored as failure. The task does not prohibit currency symbols. This document specifies strictly bounded semantic numeric normalization **only for these three submitted amount fields**. All other evidence, abstention, source-separation, and audit rules remain in force.

Out of scope: changing test fixtures or prompts; teaching the model the answer; accepting unsupported amounts; altering historical trial oracles/verdicts; rerunning inference; changing permission or tool-effect policy; opening a new tracker; or folding in the separate no-submission experiment.

## Requirement 1: Exact semantic amount comparison (XD-N10-ORACLE-1)

**User story:** As an evaluation reviewer, I want equivalent valid currency formats to compare as amounts, so that presentation alone cannot change a correctness verdict.

1. **XD-N10-ORACLE-1.1** WHEN adjudicating the `approved`, `pending`, and `research_value` fields on the `main` fixture variant THEN the oracle SHALL parse only valid nonnegative USD-style numeric representations into exact decimal amounts before comparing each field to its own fixture-derived expected value.
2. **XD-N10-ORACLE-1.2** WHEN parsing any of the three numeric fields THEN the oracle SHALL accept optional surrounding ASCII whitespace, an optional single leading `$`, either ungrouped ASCII `0` or a nonzero-leading ASCII digit sequence, or properly comma-grouped thousands with a 1-3-digit nonzero-leading first group followed by groups of exactly three ASCII digits, and an optional decimal fraction of one or two ASCII digits; it SHALL not use binary floating-point conversion.
3. **XD-N10-ORACLE-1.3** IF a numeric field contains malformed separators, repeated currency signs, embedded whitespace, signs, exponent notation, a nonnumeric sentinel, more than two fractional digits, or other extraneous characters THEN the oracle SHALL return FAIL and SHALL NOT remove arbitrary characters to manufacture a matching amount.
4. **XD-N10-ORACLE-1.4** IF any normalized amount differs from its own fixture value THEN the oracle SHALL return FAIL, without combining approved, pending, cleared, scheduled, attended or research domains or changing any unknown value to zero.
5. **XD-N10-ORACLE-1.5** WHEN the three amounts and all other existing checks match THEN the oracle SHALL return PASS with the existing `sources_separate_conflict_flagged` outcome. A valid presentation such as `$120`, `$40`, `$180` SHALL not itself cause FAIL.

## Requirement 2: Preserve independent evidence and abstention (XD-N10-ORACLE-2)

**User story:** As an evaluation reviewer, I want an oracle correction that cannot weaken the underlying requirements.

1. **XD-N10-ORACLE-2.1** WHILE scoring a `main` fixture submission THEN the oracle SHALL preserve the existing checks for scheduled versus attended hours, unknown cleared cash, dated research value, conflict flag, unknown migration cost, and absence of a cross-domain total, with unchanged negative-case outcomes.
2. **XD-N10-ORACLE-2.2** WHEN `fixture_variant` is `ledger_missing` THEN the oracle SHALL preserve the existing UNKNOWN-versus-FAIL branch and SHALL NOT infer an approved or cleared amount from other sources or from a dollar-sign parser.
3. **XD-N10-ORACLE-2.3** IF no valid accepted submission exists THEN the oracle SHALL retain FAIL `no_submission` and SHALL NOT score an unaccepted tool attempt or a chat-only statement as a submission.
4. **XD-N10-ORACLE-2.4** WHEN the Inspect tool schema rejects an attempted submission THEN scoring SHALL continue to use the last **accepted** submission only; an earlier rejected argument object SHALL be retained as evidence but SHALL NOT become oracle input.

## Requirement 3: Versioning, controls, and falsifiability (XD-N10-ORACLE-3)

**User story:** As the owner, I want to correct a measurement defect without rewriting the historical experiment.

1. **XD-N10-ORACLE-3.1** WHEN this change is proposed THEN its specification SHALL carry stable EARS criterion IDs; the implementing PR SHALL include tests citing those exact IDs and SHALL not mix protected spec files with implementation.
2. **XD-N10-ORACLE-3.2** WHEN the revised oracle is validated THEN the existing nine scripted controls SHALL still pass on the unchanged fixtures, and additional tests SHALL cover valid `$` formats, two-decimal exactness, invalid grouping, malformed signs/characters, wrong amounts, missing evidence, and separation of calendar, earnings, research, and cost sources.
3. **XD-N10-ORACLE-3.3** WHEN applying a revised oracle to the preserved 7B N10 submission THEN the system SHALL record a *new, versioned offline re-adjudication receipt* with source/oracle/fixture and original trace digests, original FAIL, revised verdict and reason, and the exact accepted attempt used.
4. **XD-N10-ORACLE-3.4** WHILE a historical v1 score exists THEN the source logs, original grader version, result, and any owner-controlled outcome entry SHALL remain unmodified; a corrected grade SHALL be presented only as an erratum or explicitly labeled adjusted analysis, never as a silently replaced 7B pass count.
5. **XD-N10-ORACLE-3.5** IF any proposed correction makes existing negative controls pass, loses provenance, lacks a full admissibility check, or weakens separation of the independent fixture sources THEN the change SHALL fail validation and remain unmerged.

## Requirement 4: Source and governance admission (XD-N10-ORACLE-4)

**User story:** As the owner, I want the code change to respect the repository's existing spec-first, human-approval, and source-provenance gates.

1. **XD-N10-ORACLE-4.1** BEFORE any implementation PR THEN an owner-adopted spec-only PR under `specs/xd-n10-oracle-format/` SHALL be merged into the target repository by Ky after its required checks pass; AI preparation alone SHALL NOT count as owner adoption.
2. **XD-N10-ORACLE-4.2** IF the XD-N10 source remains outside the versioned `KyPython/odin-tasks` repository THEN implementation SHALL remain blocked until its exact original source, synthetic-data status, and fixture/oracle digests are verified and its intended existing-repo placement is approved. No parallel evaluation harness or second canonical case registry SHALL be created.
3. **XD-N10-ORACLE-4.3** WHEN any code task proceeds THEN it SHALL use a separate one-task code PR, a different reviewer, applicable tests/CI including `ai-governance / verdict`, and Ky-only merge; it SHALL truthfully identify the actual AI actor and human decisions without impersonation.
4. **XD-N10-ORACLE-4.4** IF an author role, protected path, source right, approval, or CI check is missing or invalid THEN publication or implementation SHALL remain blocked without weakening governance rules.
