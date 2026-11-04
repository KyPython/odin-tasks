#!/usr/bin/env python3
"""Rehearse the pinned Harbor reference in disposable copies; never set recording gates."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import shlex
import stat
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True

NEUTRAL = "harbor-workspace"
SOURCE_COMMIT = "2ddf3c8f2a0e054ea2e40ab077c5a48132c34a38"
SOURCE_REPO = "https://github.com/KyPython/monorepo-build-graph"
GOAL_SHA256 = "54d506c1f74e626aa6126b9df52d0adbfd337a211606a85a1d320010f43e7160"
HERE = Path(__file__).resolve().parent


def sha(data):
    return hashlib.sha256(data).hexdigest()


def inventory(root):
    result = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError("Unexpected source/cache symlink: " + str(path))
        if path.is_file():
            result[path.relative_to(root).as_posix()] = {
                "sha256": sha(path.read_bytes()),
                "mode": stat.S_IMODE(path.stat().st_mode),
                "size": path.stat().st_size,
            }
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    for path in (args.inputs, args.runtime, args.output):
        if any(parent.is_symlink() for parent in (path, *path.parents)):
            raise ValueError("Symlink paths are not accepted.")
    inputs, runtime, output = args.inputs.resolve(), args.runtime.resolve(), args.output.resolve()
    if any(output.is_relative_to(root) for root in (inputs, runtime, Path("/Users/recorder"))):
        raise ValueError("Proof output must be separate from immutable inputs/runtime/Recorder.")
    if "TaskWork" in output.parts or output.name.endswith(".code-workspace"):
        raise ValueError("Proof output must not be a recorded task workspace.")
    if output.exists() and not output.is_file():
        raise ValueError("Proof output must be a regular file.")
    spec = importlib.util.spec_from_file_location("TaskWorkRegistry", runtime / "TaskWorkRegistry.py")
    registry_api = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(registry_api)
    registry = registry_api.load_json(runtime / "task-registry.json")
    manifest = registry_api.load_json(runtime / "runtime-manifest.json")
    tasks = registry_api.validate_registry(registry)
    projects = registry_api.validate_manifest(manifest, registry)
    task = tasks[NEUTRAL]
    project = next(item for item in projects if item["neutral"] == NEUTRAL)
    if task["sourceRepo"] != SOURCE_REPO or task["commit"] != SOURCE_COMMIT or task["goalSha256"] != GOAL_SHA256:
        raise ValueError("The worked reference applies only to the reviewed source and exact Goal.")
    goal = registry_api.verify_goal(task, runtime / task["goalFile"])
    source = inputs / NEUTRAL
    source_before = inventory(source)
    if set(source_before) != set(project["files"]):
        raise ValueError("Starter file inventory differs from its pinned manifest.")
    for name, expected in project["files"].items():
        if any(source_before[name][key] != expected[key] for key in ("sha256", "mode")):
            raise ValueError("Pinned starter content/mode changed: " + name)
    all_inputs_before = inventory(inputs)
    cache_before = {name: inventory(runtime / name) for name in ("corepack", "pnpm-store")}
    metadata_paths = ("TaskWorkRegistry.py", "task-registry.json", "runtime-manifest.json",
                      task["goalFile"], "cloud-proof.json")
    metadata_before = {name: sha((runtime / name).read_bytes()) for name in metadata_paths}
    cloud = json.loads((runtime / "cloud-proof.json").read_text())
    checks = []

    def run(label, argv, cwd, expected=0, contains=(), env=None):
        started = datetime.now(timezone.utc).isoformat()
        result = subprocess.run(argv, cwd=cwd, env=env, capture_output=True, text=True, timeout=60)
        checks.append({
            "label": label, "command": argv, "cwd": str(cwd),
            "startedAt": started, "exitCode": result.returncode, "expectedExitCode": expected,
            "stdout": result.stdout, "stderr": result.stderr,
        })
        if result.returncode != expected:
            raise AssertionError((label, result.returncode, result.stdout, result.stderr))
        for fragment in contains:
            if fragment not in result.stdout + result.stderr:
                raise AssertionError((label, fragment, result.stdout, result.stderr))
        print(label + " PASS exit=" + str(result.returncode), flush=True)
        return result

    def cold_service(label, project_copy, cp, env):
        result = run(label, cp + ["build:service"], project_copy,
                     contains=("built route-core", "built dispatch-service with 2 routes",
                               "2 successful, 2 total", "0 cached, 2 total"), env=env)
        if result.stdout.index("built route-core") > result.stdout.index("built dispatch-service"):
            raise AssertionError("Dependency build must precede service build.")
        return result

    patches = {name: (HERE / name).read_bytes()
               for name in ("solution.patch", "graph.patch", "container.patch")}
    if patches["solution.patch"] != patches["graph.patch"] + patches["container.patch"]:
        raise ValueError("Combined patch and reviewed independent phases differ.")
    with tempfile.TemporaryDirectory(prefix="taskwork-harbor-reference-") as temporary:
        temp = Path(temporary)
        project_copy = temp / NEUTRAL
        shutil.copytree(source, project_copy)
        cache = temp / "offline"
        for name in cache_before:
            shutil.copytree(runtime / name, cache / name)
        node_executable = os.environ.get("NODE_EXECUTABLE", manifest["node"])
        corepack_executable = os.environ.get("COREPACK_EXECUTABLE", "/opt/homebrew/bin/corepack")
        # Workspace scripts call pnpm themselves. Resolve every nested call to
        # this same pinned Corepack rather than relying on a global installation.
        tool_bin = temp / "tool-bin"
        tool_bin.mkdir()
        pnpm_shim = tool_bin / "pnpm"
        pnpm_shim.write_text("#!/bin/sh\nexec " + shlex.quote(corepack_executable) + ' pnpm "$@"\n')
        pnpm_shim.chmod(0o755)
        env = os.environ.copy()
        for name in ("PYTHONHOME", "PYTHONPATH", "VIRTUAL_ENV", "CONDA_PREFIX",
                     "CONDA_DEFAULT_ENV", "NODE_PATH", "NODE_OPTIONS", "PNPM_HOME"):
            env.pop(name, None)
        env.update({
            "PATH": str(tool_bin) + os.pathsep + str(Path(node_executable).parent) + os.pathsep + env.get("PATH", ""),
            "COREPACK_HOME": str(cache / "corepack"),
            "COREPACK_ENABLE_NETWORK": "0", "COREPACK_ENABLE_AUTO_PIN": "0",
            "COREPACK_ENABLE_DOWNLOAD_PROMPT": "0",
            "npm_config_store_dir": str(cache / "pnpm-store"),
            "TURBO_TELEMETRY_DISABLED": "1", "DO_NOT_TRACK": "1", "CI": "1", "NO_COLOR": "1",
        })
        if shutil.which("pnpm", path=env["PATH"]) != str(pnpm_shim):
            raise ValueError("Nested workspace commands must use the disposable pinned pnpm shim.")
        node, cp = [node_executable], [corepack_executable, "pnpm"]
        run("public-node-version", node + ["--version"], project_copy,
            contains=(cloud["toolVersions"]["node"],), env=env)
        run("public-corepack-version", [corepack_executable, "--version"], project_copy,
            contains=(cloud["toolVersions"]["corepack"],), env=env)
        run("offline-pnpm-version", cp + ["--version"], project_copy,
            contains=(task["dependencyVersions"]["pnpm"],), env=env)
        run("offline-frozen-install",
            cp + ["install", "--offline", "--frozen-lockfile", "--store-dir", str(cache / "pnpm-store")],
            project_copy, contains=("downloaded 0",), env=env)
        run("turbo-version", cp + ["exec", "turbo", "--version"], project_copy,
            contains=(task["dependencyVersions"]["turbo"],), env=env)
        run("starter-unrelated-pass", cp + ["check:unrelated"], project_copy,
            contains=("status check passed",), env=env)
        run("starter-cold-service-fail", cp + ["build:service"], project_copy, expected=1,
            contains=("ENOENT", "packages/route-core/dist/routes.json", "0 cached, 1 total"), env=env)
        run("starter-container-target-fail", cp + ["check:container"], project_copy, expected=1,
            contains=("container target @harbor/dispatch-api is not a workspace package",), env=env)
        run("combined-patch-apply-check", ["git", "apply", "--check", str(HERE / "solution.patch")],
            project_copy, env=env)
        run("graph-patch-apply-check", ["git", "apply", "--check", str(HERE / "graph.patch")],
            project_copy, env=env)
        run("apply-graph-patch", ["git", "apply", str(HERE / "graph.patch")], project_copy, env=env)
        cold_service("graph-only-cold-service-pass", project_copy, cp, env)
        run("graph-only-container-remains-fail", cp + ["check:container"], project_copy, expected=1,
            contains=("container target @harbor/dispatch-api is not a workspace package",), env=env)
        run("container-patch-apply-check", ["git", "apply", "--check", str(HERE / "container.patch")],
            project_copy, env=env)
        run("apply-container-patch", ["git", "apply", str(HERE / "container.patch")],
            project_copy, env=env)
        copied_source = {
            name: {"sha256": sha((project_copy / name).read_bytes()),
                   "mode": stat.S_IMODE((project_copy / name).stat().st_mode),
                   "size": (project_copy / name).stat().st_size}
            for name in source_before
        }
        changed = {name: entry for name, entry in copied_source.items()
                   if entry != source_before[name]}
        if set(changed) != {"turbo.json", "container/Dockerfile"}:
            raise AssertionError("The planned repair must change only its two reviewed configuration files.")
        graph_result = run("patched-build-graph",
                           cp + ["exec", "turbo", "run", "build", "--filter=@harbor/dispatch-service", "--dry=json"],
                           project_copy, env=env)
        graph = json.loads(graph_result.stdout)
        service = next(item for item in graph["tasks"]
                       if item["taskId"] == "@harbor/dispatch-service#build")
        if service["dependencies"] != ["@harbor/route-core#build"]:
            raise AssertionError(service)
        cold_service("patched-cold-service-pass-1", project_copy, cp, env)
        artifact_check = (
            "import assert from 'node:assert/strict'; import {readFile} from 'node:fs/promises'; "
            "const source=JSON.parse(await readFile('packages/route-core/src/routes.json','utf8')); "
            "const built=JSON.parse(await readFile('packages/route-core/dist/routes.json','utf8')); "
            "const manifest=JSON.parse(await readFile('apps/dispatch-service/dist/manifest.json','utf8')); "
            "assert.deepEqual(built,source); assert.deepEqual(manifest,{service:'dispatch',routes:source}); "
            "console.log('generated route data and dispatch manifest match source');"
        )
        run("patched-artifact-content-pass", node + ["--input-type=module", "-e", artifact_check],
            project_copy, contains=("generated route data and dispatch manifest match source",), env=env)
        run("patched-container-target-pass", cp + ["check:container"], project_copy,
            contains=("container target is valid",), env=env)
        run("patched-unrelated-pass", cp + ["check:unrelated"], project_copy,
            contains=("status check passed",), env=env)
        cold_service("patched-cold-service-pass-2", project_copy, cp, env)
        for number in (1, 2):
            run("whole-workspace-cold-clean-" + str(number), node + ["scripts/clean.mjs"],
                project_copy, env=env)
            run("whole-workspace-cold-build-pass-" + str(number), cp + ["build"], project_copy,
                contains=("built route-core", "built dispatch-service with 2 routes",
                          "2 successful, 2 total", "0 cached, 2 total"), env=env)
        run("whole-workspace-existing-test-pass", cp + ["exec", "turbo", "run", "test"],
            project_copy, contains=("status check passed", "1 successful, 1 total"), env=env)
        artifacts = {
            "routeData": json.loads((project_copy / "packages/route-core/dist/routes.json").read_text()),
            "manifest": json.loads((project_copy / "apps/dispatch-service/dist/manifest.json").read_text()),
        }
        expected_routes = json.loads((source / "packages/route-core/src/routes.json").read_text())
        if artifacts != {"routeData": expected_routes,
                         "manifest": {"service": "dispatch", "routes": expected_routes}}:
            raise AssertionError("Generated artifacts differ from the unchanged route contract.")
    if inventory(inputs) != all_inputs_before:
        raise AssertionError("Immutable source inputs changed during rehearsal.")
    if {name: inventory(runtime / name) for name in cache_before} != cache_before:
        raise AssertionError("Immutable offline cache inputs changed during rehearsal.")
    if {name: sha((runtime / name).read_bytes()) for name in metadata_paths} != metadata_before:
        raise AssertionError("Runtime source identity or exact Goal metadata changed during rehearsal.")
    if registry_api.verify_goal(task, runtime / task["goalFile"]) != goal:
        raise AssertionError("Exact Goal changed during rehearsal.")
    receipt = {
        "version": 1, "status": "PASS", "verifiedAt": datetime.now(timezone.utc).isoformat(),
        "taskId": task["id"], "neutral": NEUTRAL,
        "sourceRepo": SOURCE_REPO, "sourceCommit": SOURCE_COMMIT,
        "notionPageId": task["notionPageId"], "approvedGoal": task["approvedGoal"],
        "goalSha256": task["goalSha256"], "sourceInventory": source_before,
        "patchSha256": {name: sha(data) for name, data in patches.items()},
        "solutionPatchSha256": sha(patches["solution.patch"]), "plannedChangedFiles": changed,
        "toolVersions": cloud["toolVersions"],
        "cloudSeed": {"runId": cloud["runId"], "sourceCommit": cloud["sourceCommit"]},
        "checks": checks, "resultArtifacts": artifacts,
        "dependencyGraphEvidence": {"dispatchServiceBuildDependencies": service["dependencies"]},
        "sourceInputsUnchanged": True, "sharedSourceAndCacheInputsUnchanged": True,
        "runtimeMetadataUnchanged": True, "runtimeMetadataSha256": metadata_before,
        "sourceRepositoriesWritten": False, "disposableReferencePatchApplied": True,
        "humanAttemptsTouched": False, "recordingWorkspaceModified": False, "recorderExecuted": False,
        "setupVerified": False, "recordingReady": False,
        "externalSolutionWalkthroughAcceptanceVerified": False, "dockerImageBuilt": False,
        "aiAuthoredBeforeRecording": True,
        "limitations": [
            "Container target validation checks the Dockerfile package selector against the workspace; no Docker image build or Linux runtime was executed.",
            "Existing deterministic synthetic checks ran in disposable reference copies; no actual Recorder attempt or external acceptance was simulated.",
        ],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", dir=output.parent, prefix=".reference-proof-", delete=False) as staged:
        json.dump(receipt, staged, indent=2)
        staged.write("\n")
        staged_path = Path(staged.name)
    staged_path.replace(output)
    print(json.dumps({"evidence": str(output), "checks": len(checks),
                      "changedFiles": list(changed), "immutableSourcesAndCachesPreserved": True}))


if __name__ == "__main__":
    main()
