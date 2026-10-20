# Scoped quality requirements

This source-only export contains two synthetic verification systems: an offline
QA/dispatch/promptfoo evaluation suite and native sandboxed accessibility browser
controls. Their assessments remain separate because their runtimes and evidence
boundaries differ. Neither system tests a live application or private dataset.

1. **Correctness:** evaluation must run the complete pytest suite, actual DeepEval
   custom metrics and promptfoo saved-fixture cases, including negative controls
   and repeat-equal QA replays. Browser controls must run actual Chrome/axe on
   accessible and deliberately invalid synthetic pages and reject request errors,
   HTTP errors and redirects. Preserve existing expectations.
2. **Security:** evaluation runtime must retain actual same-address positive/
   negative/positive network controls and Docker network-none execution without
   provider credentials. Browser controls must retain the native Chrome sandbox
   and self-contained loopback fixtures. No application tenant or authorization
   boundary is established by these fixtures.
3. **Reliability:** bound every declared command and CI job; retain error,
   unavailable-target and deterministic replay controls. Failure or timeout must
   produce a failed policy/test result. Production crashes, concurrency and live
   provider reliability remain unmeasured.
4. **Data integrity:** keep synthetic corpora/oracles and scripted dispatch
   semantics independent of reported success. Record scoped input hashes and
   reject stale or changed evidence. Do not export private dispatch records or
   claim to restore application data.
5. **Observability:** retain actual tool/JUnit/network/browser reports plus
   maintained command receipts and complete eight-dimension assessments. Missing
   evidence or validation failure must fail the job; failure artifacts must stay
   available without a fabricated success summary.
6. **Delivery:** retain digest-pinned evaluation images, hashed Python packages,
   npm integrity locks, SHA-pinned actions, least privilege and finite timeouts.
   Record exact revision/context. Native runner and browser versions are observed
   rather than falsely described as immutable. No product deployment occurs.
7. **Operations:** document local reproduction and failure inspection. Actual
   product ownership, alerting, durable backup/restore and incident recovery are
   unverified. Disposable fixture cleanup is not a backup restoration.
8. **Outcome evidence:** distinguish exact synthetic answer/citation/abstention,
   dispatch and accessibility controls from live semantic quality, retrieval,
   model performance, application accessibility or customer outcomes.

Each exported subsystem supplies all eight dimensions to the same maintained
runner/validator. It records real finite-timeout command receipts and hashed
requirements/inputs; no caller-supplied success flag is authoritative. A passing
scoped CI policy leaves partial and unverified dimensions visible and never
certifies full readiness or independently verifies manual/external evidence.
