# Requirements: governance gate pass

Spec ID: GATEPASS · Issue: #2 · Status: proposed; Ky approves by merging this spec-only PR

## Introduction

The governance opt-in PR is red because the root `package.json` has no `test`
script, and the turbo `build` task races: `dispatch-service` reads
`route-core/dist` before `route-core` finishes. This spec adds the root script
that runs the workspace tests plus the root tests, and orders the build.

## Requirements

### Requirement 1: Root test script (GATEPASS-1)

**User Story:** As Ky, I want the root `test` script to run the workspace
tests, so that the gate executes real tests on every PR.

#### Acceptance Criteria

1. GATEPASS-1.1 WHEN the gate runs `test` THEN the root `package.json` SHALL
   provide a `test` script that runs `turbo run test` and the root
   `node --test` suite.
2. GATEPASS-1.2 WHEN the root `test` script runs THEN the
   `@harbor/status-check` tests SHALL execute and pass.

### Requirement 2: Ordered turbo build (GATEPASS-2)

**User Story:** As Ky, I want dependency builds ordered before dependents, so
that the gate build never reads outputs that do not exist yet.

#### Acceptance Criteria

1. GATEPASS-2.1 WHEN turbo schedules `build` THEN the `build` task SHALL
   declare `dependsOn` with `^build`.
2. GATEPASS-2.2 WHEN a forced (uncached) build runs THEN it SHALL succeed and
   SHALL produce `apps/dispatch-service/dist/manifest.json` naming the
   `dispatch` service with its routes.
