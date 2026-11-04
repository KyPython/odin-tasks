# Requirements: Odin mono-repo consolidation

Spec ID: ODIN-MONO · Issue: #1 · Status: proposed; Ky approves by merging this spec-only PR

## Introduction

Eight standalone task-starter repos move into this mono-repo with history preserved and one root CI verifying every task. The recording registry stays standalone (its checksummed vendored inputs fight the mono-repo gate) and links to `tasks/` here instead. The offline eval/a11y lab joins as `tasks/eval-lab/`.

## Requirements

### Requirement 1: Content move (ODIN-MONO-1)

**User Story:** As Ky, I want every starter in one repo, so that Odin work stops scattering across a dozen repos.

#### Acceptance Criteria

1. ODIN-MONO-1.1 WHEN the consolidation merges THEN `tasks/<name>/` SHALL contain each of the 8 source repos' `main` tip with history.
2. ODIN-MONO-1.2 WHEN the consolidation merges THEN a `MIGRATION.md` SHALL record each source repo + commit SHA.
3. ODIN-MONO-1.3 WHEN the consolidation merges THEN no nested `.github/` dir SHALL remain (root `.github/` is the only CI configuration).

### Requirement 2: Verification preserved (ODIN-MONO-2)

**User Story:** As Ky, I want every task still verifiable, so that the move proves nothing broke.

#### Acceptance Criteria

1. ODIN-MONO-2.1 WHEN root CI runs THEN each task's documented verify command SHALL pass (matrix job per task).
2. ODIN-MONO-2.2 WHEN the consolidation merges THEN pre-existing gate debt surfaced by the move SHALL be fixed and re-verified, not carried over red.

### Requirement 3: Eval lab move (ODIN-MONO-3)

**User Story:** As Ky, I want the offline eval/a11y lab in the same repo, so that all evaluations live in one place.

#### Acceptance Criteria

1. ODIN-MONO-3.1 WHEN the merge lands THEN `tasks/eval-lab/` SHALL contain oss-integration-checks' `main` tip with history and no nested `.github/` dir.
2. ODIN-MONO-3.2 WHEN the merge lands THEN the lab's fixtures workflow SHALL run hoisted from root CI against `tasks/eval-lab/`.
3. ODIN-MONO-3.3 WHEN the merge lands THEN `MIGRATION.md` SHALL record the source repo + commit SHA.
