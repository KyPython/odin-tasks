# Requirements: Odin mono-repo consolidation

Spec ID: ODIN-MONO · Issue: #1 · Status: proposed; Ky approves by merging this spec-only PR

## Introduction

Nine standalone repos (8 task starters + the recording registry) move
into this mono-repo with history preserved, one root CI verifying every
task, and the recording build kept working from vendored inputs.

## Requirements

### Requirement 1: Content move (ODIN-MONO-1)

**User Story:** As Ky, I want every starter in one repo, so that Odin
work stops scattering across a dozen repos.

#### Acceptance Criteria

1. ODIN-MONO-1.1 WHEN the consolidation merges THEN `tasks/<name>/`
   SHALL contain each source repo's `main` tip with history, and
   `recording/` SHALL contain the registry with history.
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
2. ODIN-MONO-2.2 WHEN root CI runs THEN the recording smoke (unittest
   discover + `check_recording_pack.py`) SHALL pass.
3. ODIN-MONO-2.3 WHEN the consolidation merges THEN the recording
   registry SHALL reference the local `tasks/` dirs while keeping
   original pinned commits as provenance, and the preparation build
   SHALL still read only vendored `inputs/`.
