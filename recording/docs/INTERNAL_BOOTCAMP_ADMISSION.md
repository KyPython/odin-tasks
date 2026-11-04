# User-authorized internal Bootcamp preparation

The user explicitly authorized internal practice preparation for the existing
ideas, including the IaC idea whose Odin status remains Rejected. Preparation
does not change Odin eligibility, paid approval, human assessment or capture gates.
Existing registered tasks retain their original identities and admission rules.

An additional task may use `workflowLane: bootcamp`, `goalKind: candidate` and
the verbatim `Odin Goal` through a reviewed `internalBootcampAdmission` record.
Its identity remains `BOOTCAMP-<native-page-UUID-hex-uppercase>`. The CLI still
requires real pinned Git source, an exact Goal hash and a reviewed setup recipe.
Do not register it before the actual Kiro PASS and KyPython's spec merge.

The setup JSON's `internalBootcampAdmission` contains these administrative facts:

- `version: 1`, `authority: explicit-user`, `scope: internal-bootcamp-world-preparation`.
- `authorizationRef` and `authorizationTextSha256`, identifying the actual user
  instruction. These are reviewed evidence, not cryptographic proof of consent.
- `notionPageId`, `goalSha256`, `sourceRepo`, `sourceCommit`, matching the task exactly.
- `originalOdinFields`: the exact `Lane`, `Stage`, `Fit Gate`, `Approval ID` and
  `Approved Goal` from the fresh native row. Approval ID and Approved Goal stay empty.
- `kiroReview`: `receiptSha256`, immutable preparation-repository `receiptCommit`,
  `receiptPath: cloud/kiro-receipts/<executionId>.json`, actual `executionId`, exact full-idea
  `inventorySha256`, produced `specCommit`, and `specFiles` mapping each actual
  requirements.md, design.md and tasks.md path under the spec directory to SHA-256.
- `specMerge`: actual `prUrl`, full merge `commit`, `mergedAt` and `mergedBy: KyPython`.

Supply the bounded plain receipt through `kiroReviewReceiptFile` in the setup JSON.
The normalized receipt is version 1, engine `kiro`, status `PASS`, with matching
executionId, inventorySha256 and specCommit. Its `paths` object maps each reviewed
file path to `{status: PASS, sha256: <actual-file-digest>}`. Preserve the real CLI
execution/output evidence behind that receipt; do not synthesize a future PASS.
The receipt requires actual `executionEvidence` with source `captured-kiro-cli`,
executionTarget `local` or `cloud`, capturePath
`cloud/kiro-receipts/<full-executionId>.capture.txt`, and the exact captureSha256.
Registration reads and hashes the actual nonempty private capture at receiptCommit.
Execution IDs accept exactly a UUID or `sess_` plus UUID and retain the full ID.
These records establish trusted capture provenance, not independent Kiro web API
authentication. A cancelled session or fallback authored elsewhere cannot become
Kiro PASS. The receipt also requires a `bindings` object keyed by
native page UUID, each with matching rowId, goalSha256, specPath and specPr.
Goal hashes use the exact verbatim Goal plus its final newline.

Registration reads the actual receipt bytes and requires byte identity with the
authenticated immutable receipt in KyPython/odin-recording-preparation. It then reads GitHub's merged PR and
all three file blobs at the human merge commit. Open or agent-merged PRs, changed
receipt/spec/source/Goal bytes, and changed original Odin fields stop registration.
The actual PR head must equal the reviewed specCommit; the distinct merge commit
must contain the identical reviewed document bytes.
The native publisher retains those same policy guards and binds the authorization
digest into this task's pack revision. It changes route content only; it cannot
upgrade tracker fields. An unchanged retry remains NOOP.

Complete the reviewed source-bound setup, exact route, disposable worked proof
and learning metadata before the existing combined cloud build. Technical proof
continues to report no Recorder execution, capture readiness or human mastery.

For dependency-free Node source, the reviewed `node-stdlib` profile uses
`dependencyVersions: {node: "22.22.0"}`, no dependency roots, and `{node}` baseline
commands. Its real package.json must declare no package dependencies or package
manager. Setup checks the public pinned Node version without installing packages
or running task tests. Any browser interaction and static-server start/stop belong
in the eventual exact source-bound recording script.

For Python standard-library generators, declare one `generatedFiles` JSON path
under `build/` on the exact `{python} -m <local.module> --output <path>` baseline.
The module must exist in pinned source, the output must not replace source, and
later checks may reference it only after that generator. Undeclared, traversing,
competing or unsupported generators HOLD. Cloud checks run in disposable copies
and record the actual regular JSON output's digest; setup never runs generators.
