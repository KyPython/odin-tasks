### Recording sequence — follow this order
**Step 1.** With actual pre-record checks passed, show only the separate exact Goal in the clean VS Code window. Bring TaskRecorder forward and click **Start Recording**. Say only the required opening, in under **20 seconds**: “I will be beginning my task soon. Here is the workflow I have in mind.” Minimize TaskRecorder, then the Goal window, and use VS Code’s **Window** menu to bring the already-open `harbor-workspace.code-workspace` project forward. Save the prepared workflow explanation for Step 2.
**Step 2.** With the project forward, use this planned narration: “My planned workflow is to reproduce the focused service and container-target failures, restore dependency build ordering, update the stale package selector, and verify the focused and workspace checks.” Do not describe this prepared analysis as a spontaneous discovery. Use **Terminal → New Terminal**. Run the following commands individually from the workspace root; after each check, `echo $?` immediately shows that command’s actual exit code.
```bash
cd "$HOME/Desktop/TaskWork/harbor-workspace"
pwd
/opt/homebrew/bin/node --version
/opt/homebrew/bin/corepack pnpm --version
/opt/homebrew/bin/corepack pnpm exec turbo --version
/opt/homebrew/bin/corepack pnpm check:unrelated
echo $?
/opt/homebrew/bin/corepack pnpm build:service
echo $?
/opt/homebrew/bin/corepack pnpm check:container
echo $?
```
The prepared starter reference showed Node `v22.22.0`, pnpm `9.15.4`, Turbo `2.3.3`; unrelated check exit **0** with `status check passed`; cold service exit **1** with `ENOENT` for `packages/route-core/dist/routes.json`; container target exit **1** with `container target @harbor/dispatch-api is not a workspace package`. `build:service` already invokes the existing clean script before Turbo, so it removes generated service/shared outputs and the root task cache each time.
If those are the results actually displayed, say: “The unrelated package check passes. The service build is attempting to read route-core’s generated routes before that output exists. The independent container check rejects a package name that is absent from this workspace.” If any result or version differs, report what actually happened and stop the attempt to reconcile source/setup off-screen; do not invent the prepared failure or reset existing work.
**Step 3.** Use **Go → Go to File…** (**⌘P**) and open each exact path below. Explain the concrete dependency chain while showing its files:
- `apps/dispatch-service/package.json`: name `@harbor/dispatch-service`; declared dependency `@harbor/route-core: workspace:*`.
- `apps/dispatch-service/scripts/build.mjs`: reads `packages/route-core/dist/routes.json` and writes the dispatch manifest.
- `packages/route-core/package.json` and `packages/route-core/scripts/build.mjs`: the shared package now has its own build step which copies the unchanged source routes into `dist/routes.json`.
- `turbo.json`: the build task lists outputs but currently has no prerequisite build tasks.
- `container/Dockerfile`: the last line filters `@harbor/dispatch-api`.
- `scripts/check-container-target.mjs`: compares that filter with the declared workspace names.
Planned narration: “The service’s package dependency is already declared. I will add Turbo’s dependency-build prerequisite so the shared package’s build finishes before the service consumes its output. Separately, I will make the Dockerfile selector match the actual service package name. This keeps the repair in configuration instead of manually building a prerequisite or renaming the workspace.”
**Step 4.** Open `turbo.json` with **⌘P**. Insert this exact line at the start of `tasks.build`, directly before `outputs`:
```json
"dependsOn": ["^build"],
```
The complete saved file must be:
```json
{
  "$schema": "https://turbo.build/schema.json",
  "tasks": {
    "build": {
      "dependsOn": ["^build"],
      "outputs": ["dist/**"]
    },
    "test": {
      "outputs": []
    }
  }
}
```
Use **File → Save All** (**⌥⌘S**) before checking. Return to the existing integrated terminal and run:
```bash
/opt/homebrew/bin/corepack pnpm build:service
echo $?
/opt/homebrew/bin/corepack pnpm check:container
echo $?
```
The reviewed graph-only phase gave service exit **0**, `built route-core` before `built dispatch-service with 2 routes`, **2 successful, 2 total** and **0 cached, 2 total**. The container command still exited **1** with the obsolete `@harbor/dispatch-api` error. If observed, say: “The cold service now builds its dependency first and then creates the two-route manifest. The container check still fails because that separate stale identity has not been changed yet.” This intermediate failure is expected; do not weaken its check.
**Step 5.** Open `container/Dockerfile` with **⌘P**. Replace only its last line:
```docker
RUN pnpm turbo run build --filter=@harbor/dispatch-service
```
Leave the image, work directory, COPY and frozen-install lines unchanged. Use **File → Save All** (**⌥⌘S**) before every verification or retry. In the existing terminal run:
```bash
/opt/homebrew/bin/corepack pnpm check:container
echo $?
/opt/homebrew/bin/corepack pnpm build:service
echo $?
/opt/homebrew/bin/corepack pnpm build:service
echo $?
/opt/homebrew/bin/corepack pnpm check:unrelated
echo $?
```
Both focused builds must actually exit **0** and show dependency-first build output with **2 successful, 2 total** and **0 cached, 2 total**; the existing root script cleans before each run. The container check must actually exit **0** and print `container target is valid`; unrelated must exit **0** and print `status check passed`.
Run this exact additional content assertion; it compares generated route data with its unchanged source and checks the dispatch manifest’s identity and full routes:
```bash
/opt/homebrew/bin/node --input-type=module -e "import assert from 'node:assert/strict'; import {readFile} from 'node:fs/promises'; const source=JSON.parse(await readFile('packages/route-core/src/routes.json','utf8')); const built=JSON.parse(await readFile('packages/route-core/dist/routes.json','utf8')); const manifest=JSON.parse(await readFile('apps/dispatch-service/dist/manifest.json','utf8')); assert.deepEqual(built,source); assert.deepEqual(manifest,{service:'dispatch',routes:source}); console.log('generated route data and dispatch manifest match source');"
echo $?
cat packages/route-core/dist/routes.json
cat apps/dispatch-service/dist/manifest.json
```
The prepared assertion exited **0** and printed `generated route data and dispatch manifest match source`. The data includes `north-pier` active **true**, then `south-basin` active **false**, in that order. The manifest has `service: "dispatch"` and those same two records.
If observed, say: “The corrected selector is a real workspace package. Two clean focused builds succeeded without cache hits, the generated files match the source routes, and the unrelated test still passes. Container target validation checks the Dockerfile package selector against the workspace; no Docker image build or Linux runtime was executed.”
**Step 6.** Broaden to a fresh whole-workspace build and the existing workspace tests:
```bash
/opt/homebrew/bin/node scripts/clean.mjs
/opt/homebrew/bin/corepack pnpm build
echo $?
/opt/homebrew/bin/node scripts/clean.mjs
/opt/homebrew/bin/corepack pnpm build
echo $?
/opt/homebrew/bin/corepack pnpm exec turbo run test
echo $?
```
Require the actual two cold builds to exit **0**, each with **2 successful, 2 total**, **0 cached, 2 total**, and dependency-first output. The test command must exit **0**, print `status check passed`, and report **1 successful, 1 total**. Turbo lists three workspace packages, but only route-core and dispatch-service have a build task, while status-check has the existing test task; do not call this three passing build tasks.
If observed, say: “Both clean workspace builds pass, and the existing workspace test passes. The two configuration edits restore build ordering and consistent package selection while preserving the route data and unrelated package.”
**Step 7.** Use **File → New Text File** (**⌘N**), then **File → Save As…** (**⇧⌘S**) to save `~/Desktop/TaskWork/harbor-workspace/VERIFICATION.md`. Use the template below and replace bracketed result fields with this attempt’s actual terminal results. Do not substitute the separate rehearsal’s results for missing recorded evidence.
```markdown
# Harbor verification

Source: monorepo-build-graph at 2ddf3c8f2a0e054ea2e40ab077c5a48132c34a38.

Changes:
- turbo.json: build.dependsOn = ["^build"].
- container/Dockerfile: service filter = @harbor/dispatch-service.

Observed during this attempt:
- Starter unrelated check: [exit code and output].
- Starter cold service: [exit code and missing routes path].
- Starter container target: [exit code and obsolete-name message].
- Graph-only phase: [service exit/result; container still fails result].
- Final container target: [exit code and output].
- Two final cold focused builds: [both exit codes; task/cache counts].
- Generated artifact assertions: [exit code and output].
- Unrelated check after changes: [exit code and output].
- Two cold whole-workspace builds: [both exit codes; task/cache counts].
- Existing workspace test: [exit code and output].

Generated manifest: service dispatch; north-pier active true then south-basin active false.
Container coverage: static Dockerfile workspace-selector validation only.
No Docker image build or Linux container runtime was performed.
```
Use **File → Save All** (**⌥⌘S**) and review the two edited configuration files and note. Reconcile the note and final narration with actual output; leave a failing or unobserved result truthful. Summarize the planned changes and their demonstrated results without claiming unobserved deployment, personal discovery or approval. Bring TaskRecorder forward from the Dock, click **Stop Recording**, and wait through **Stopping → Archiving → Idle**. Preserve the original archive and workspace, then complete the mandatory recording QA and metadata/provenance/submission checks off-screen. Do not mark gates passed merely because this prepared reference passed.
**Deterministic recovery actions — preserve the attempt**
- Wrong working directory: run `pwd`; return with `cd "$HOME/Desktop/TaskWork/harbor-workspace"` before using the shown commands.
- Unsaved edit or JSON parse error: use **⌘P** → `turbo.json`, compare with the complete file above, correct the comma/line, and use **File → Save All** before repeating the failed verification.
- Graph fix still gives missing routes: confirm the saved `dependsOn: ["^build"]` is inside `tasks.build`, not `tasks.test`, and the original dependency remains in `apps/dispatch-service/package.json`. Save All and repeat `build:service` only after the files match the reviewed plan.
- Container check still names dispatch-api after its edit: use **⌘P** → `container/Dockerfile`, verify the last line is the exact dispatch-service line above, Save All, then repeat `check:container`.
- Missing pnpm/Turbo/dependency or unexpected version: stop capture, preserve the edited workspace and archive, and resolve the current controlled setup off-screen. Do not overwrite or reset the attempt or rerun batch setup.
- A check fails for another reason: state the actual failure, stop TaskRecorder using its normal stop/archive flow, and preserve all work for off-screen reconciliation. Do not broaden the patch, weaken assertions or narrate a pass.
- Every retry after an edit begins with **File → Save All**. A successful later retry does not erase the earlier observed failure.
