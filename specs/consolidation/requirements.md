# Requirements: Odin mono-repo consolidation

Spec ID: ODIN-MONO · Issue: #1 · Status: proposed; Ky approves by merging this spec-only PR

## Introduction

Eight standalone task-starter repos move into this mono-repo with history
preserved and one root CI verifying every task. The recording registry
stays standalone (its checksummed vendored inputs fight the mono-repo
gate) and links to `tasks/` here instead.

## Requirements

### Requirement 1: Content move (ODIN-MONO-1)

**User Story:** As Ky, I want every starter in one repo, so that Odin
work stops scattering across a dozen repos.

#### Acceptance Criteria

1. ODIN-MONO-1.1 WHEN the consolidation merges THEN `tasks/<name>/`
   SHALL contain each of the 8 source repos' `main` tip with history.
2. ODIN-MONO-1.2 WHEN the consolidation merges THEN a `MIGRATION.md`
   SHALL record each source repo + commit SHA.
3. ODIN-MONO-1.3 WHEN the consolidation merges THEN no nested `.github/`
   dir SHALL remain (root `.github/` is the only CI configuration).

### Requirement 2: Verification preserved (ODIN-MONO-2)

**User Story:** As Ky, I want every task still verifiable, so that the
move proves nothing broke.

#### Acceptance Criteria

1. ODIN-MONO-2.1 WHEN root CI runs THEN each task's documented verify
   command SHALL pass (matrix job per task).
2. ODIN-MONO-2.2 WHEN the consolidation merges THEN pre-existing gate
   debt surfaced by the move (container USER, vulnerable pins) SHALL be
   fixed and re-verified, not carried over red.
