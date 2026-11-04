# Requirements: governance gate pass

Spec ID: GATEPASS · Issue: #2 · Status: proposed; Ky approves by merging this spec-only PR

## Introduction

The governance opt-in PR is red because the root `package.json` has no `test`
script. Only `@harbor/status-check` defines `test`, and `turbo.json` already
defines a `test` task. This spec adds the root script that runs the workspace
tests through turbo.

## Requirements

### Requirement 1: Root test script (GATEPASS-1)

**User Story:** As Ky, I want the root `test` script to run the workspace
tests, so that the gate executes real tests on every PR.

#### Acceptance Criteria

1. GATEPASS-1.1 WHEN the gate runs `test` THEN the root `package.json` SHALL
   provide a `test` script that runs `turbo run test`.
2. GATEPASS-1.2 WHEN the root `test` script runs THEN the
   `@harbor/status-check` tests SHALL execute and pass.
