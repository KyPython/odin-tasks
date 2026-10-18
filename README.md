# Synthetic integration checks

Portable, source-only checks for promptfoo, DeepEval and Pa11y/axe. This export
contains invented document facts and scripted dispatch controls. It includes no
private application source, credentials, real evaluation logs or private dispatch
dataset. It deploys no product and makes no paid-model calls.

The GitHub workflow runs two jobs:

- **Evaluation:** install hash/integrity-locked tools into a digest-pinned OCI
  image, then run pytest, real DeepEval metrics and the real promptfoo CLI in a
  Docker container with `--network none`. A separate synthetic listener is
  reachable before and after the test; the test container must fail to reach
  that same numeric IP/port. Loopback fixtures remain available.
- **Accessibility:** install the locked Pa11y dependencies and use the runner's
  preinstalled system Chrome with its sandbox retained. Real browser controls
  distinguish accessible HTML, unnamed controls, missing alternate text,
  unreachable pages, HTTP errors and redirects. Only self-contained synthetic
  loopback HTML is served. The runner/browser version is recorded; the hosted
  runner image can advance.

## Run the evaluation tools

Docker must already be available. Dependency downloads happen during the build;
the subsequent fixture run has no network access or provider credentials.

```sh
docker build --tag evaluation-lab-ci:local .
python3 scripts/run_offline.py --output-dir artifacts/evaluation
```

Use a new output directory for each run. Reports contain actual pytest output,
JUnit, four promptfoo fixture outcomes, three repeat-equal DeepEval QA replays,
seven synthetic dispatch controls, installed versions, source hashes and the
network controls. Failure to establish either network control fails the run.
Only uniquely named disposable containers created by the runner are removed.

## Run the browser controls

Use Node 22.23.2 and an already installed sandbox-capable system Chrome:

```sh
PUPPETEER_SKIP_DOWNLOAD=true npm ci --prefix accessibility --ignore-scripts --no-audit --no-fund
PUPPETEER_EXECUTABLE_PATH=/usr/bin/google-chrome python3 scripts/browser_ci.py
```

On other platforms, explicitly select the installed browser executable. No
browser is downloaded or started on installation, and no application route is
audited by the test command. Reports are written under `artifacts/browser/`.

## What the results establish

The QA oracle checks exact synthetic facts, citation/fact alignment and explicit
abstention for an unsupported question. Equivalent paraphrases outside its
narrow grammar can fail. Actual DeepEval custom metrics use that same oracle;
they do not introduce a general semantic judge.

Dispatch controls preserve separate meanings for delivery authorization,
required-delivery coverage and required-tool name presence. Rejected calls do
not count as execution; a failed tool can satisfy name presence while failing
delivery. Negative controls demonstrate those limits. These scripted controls
are not real model benchmark results, and the original private replay dataset
is deliberately absent.

`qa/provider.py` retains a separately opted-in HTTP adapter, tested with mocked
transport. Default CI exports only its saved-fixture configuration. Live use
would require a separately prepared matching corpus/namespace, explicit endpoint
and authentication choice, and a separate decision about product side effects
and model costs. HTTP success does not verify authentication or tenant identity.
No live application, retrieval system or model quality is verified here.

This is a portable export of a local experiment, not a second canonical copy of
the original lab. Source-copy/adaptation provenance and preparation reviews are
retained separately by the owner, outside this source-only repository.
