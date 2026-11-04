#!/usr/bin/env python3
"""Verify this worked reference in a disposable pinned starter copy."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
NEUTRAL = 'evaluation-handoff'
SOURCE_REPO = 'https://github.com/KyPython/ci-evaluation-contract'
SOURCE_COMMIT = 'ca532d92ec3db02224061b3ceef105b2bc113b27'
GOAL_SHA256 = 'eae155012790178f9ef10a5f5decd7e9a73c2135d0309ae3491ce542ef80543c'
HERE = Path(__file__).resolve().parent


def sha(data):
    return hashlib.sha256(data).hexdigest()


def inventory(root):
    if not root.is_dir() or root.is_symlink():
        raise ValueError("Missing or unsafe source root: " + str(root))
    result = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink() or not (path.is_dir() or path.is_file()):
            raise ValueError("Unsafe source member: " + str(path))
        if path.is_file():
            result[path.relative_to(root).as_posix()] = {
                "sha256": sha(path.read_bytes()),
                "mode": stat.S_IMODE(path.stat().st_mode),
                "size": path.stat().st_size,
            }
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("inputs", "runtime", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    for path in (args.inputs, args.runtime, args.output):
        if any(parent.is_symlink() for parent in (path, *path.parents)):
            raise ValueError("Symlink paths are not accepted.")
    inputs, runtime, output = args.inputs.resolve(), args.runtime.resolve(), args.output.resolve()
    if any(output.is_relative_to(root) for root in (inputs, runtime, Path("/Users/recorder"))):
        raise ValueError("Proof output must be outside inputs/runtime/Recorder.")
    if "TaskWork" in output.parts or output.name.endswith(".code-workspace"):
        raise ValueError("Proof output cannot be a recording workspace.")
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
    if (task["sourceRepo"], task["commit"], task["goalSha256"]) != (SOURCE_REPO, SOURCE_COMMIT, GOAL_SHA256):
        raise ValueError("This reference requires its exact source and approved Goal pins.")
    goal = registry_api.verify_goal(task, runtime / task["goalFile"])
    source = inputs / NEUTRAL
    source_before = inventory(source)
    if set(source_before) != set(project["files"]):
        raise ValueError("Starter file inventory differs from the pinned manifest.")
    for name, expected in project["files"].items():
        if any(source_before[name][key] != expected[key] for key in ("sha256", "mode")):
            raise ValueError("Pinned source differs: " + name)
    all_inputs_before = inventory(inputs)
    metadata_paths = ["TaskWorkRegistry.py", "task-registry.json", "runtime-manifest.json", task["goalFile"], "cloud-proof.json"]
    metadata_before = {name: sha((runtime / name).read_bytes()) for name in metadata_paths}
    cloud = registry_api.load_json(runtime / "cloud-proof.json")
    patches = {name: (HERE / name).read_bytes() for name in ("tests.patch", "repair.patch", "solution.patch")}
    if patches["solution.patch"] != patches["tests.patch"] + patches["repair.patch"]:
        raise ValueError("The combined patch differs from its reviewed phases.")
    checks = []

    def run(label, argv, cwd, expected=0, contains=(), env=None, stdout=None):
        started = datetime.now(timezone.utc).isoformat()
        result = subprocess.run(argv, cwd=cwd, env=env, capture_output=True, text=True, timeout=60)
        checks.append({"label": label, "command": argv, "cwd": str(cwd),
                       "startedAt": started, "environmentOverrides": {"TZ": env["TZ"]} if env and "TZ" in env else {},
                       "exitCode": result.returncode, "stdout": result.stdout, "stderr": result.stderr})
        allowed = expected if isinstance(expected, tuple) else (expected,)
        if result.returncode not in allowed:
            raise AssertionError((label, result.returncode, result.stdout, result.stderr))
        for fragment in contains:
            if fragment not in result.stdout + result.stderr:
                raise AssertionError((label, fragment, result.stdout, result.stderr))
        if stdout is not None and result.stdout != stdout:
            raise AssertionError((label, "stdout differs", result.stdout))
        print(label + " PASS exit=" + str(result.returncode), flush=True)
        return result

    with tempfile.TemporaryDirectory(prefix="taskwork-" + NEUTRAL + "-reference-") as temporary:
        temp = Path(temporary)
        copy = temp / NEUTRAL
        shutil.copytree(source, copy)
        toolchain = temp / "toolchain"
        toolchain.mkdir()
        (toolchain / "python3").symlink_to(sys.executable)
        env = os.environ.copy()
        for name in ("PYTHONHOME", "PYTHONPATH", "VIRTUAL_ENV", "CONDA_PREFIX", "CONDA_DEFAULT_ENV", "TZ"):
            env.pop(name, None)
        env.update({"PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1", "PATH": str(toolchain) + os.pathsep + env.get("PATH", "")})
        version = run("public-python-version", [sys.executable, "--version"], copy,
                      contains=(cloud["toolVersions"]["python"],), env=env)
        tests = [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"]
        git = shutil.which("git")
        if not git:
            raise ValueError("Public Git is required to apply reviewed unified patches.")
        if NEUTRAL == "dispatch-board":
            utc = dict(env, TZ="UTC")
            run("starter-test-utc", tests, copy, contains=("Ran 1 test", "OK"), env=utc)
            run("starter-two-timezone-observation", [sys.executable, "scripts/show_timezone_variation.py"], copy,
                contains=("Timezone outcomes:",), env=env)
        else:
            run("starter-ordinary-verification", ["sh", "scripts/verify.sh"], copy,
                contains=("Ran 3 tests", "OK"), stdout="sample_001: 3\n", env=env)
            run("starter-valid-cli", [sys.executable, "-m", "grader.pipeline", "fixtures/valid/manifest.json"], copy,
                stdout="sample_001: 3\n", env=env)
        run("combined-patch-check", [git, "apply", "--check", str(HERE / "solution.patch")], copy, env=env)
        run("tests-patch-check", [git, "apply", "--check", str(HERE / "tests.patch")], copy, env=env)
        run("apply-tests-patch", [git, "apply", str(HERE / "tests.patch")], copy, env=env)
        if NEUTRAL == "dispatch-board":
            run("strengthened-tests-fail-before-repair", tests, copy, expected=1,
                contains=("Ran 9 tests", "FAIL: test_default_clock_uses_location_date", "unexpected keyword argument 'clock'", "FAILED"), env=utc)
        else:
            run("strengthened-tests-fail-before-repair", tests, copy, expected=1,
                contains=("Ran 5 tests", "IntakeError not raised", "FAILED"), env=env)
            run("negative-fixture-incorrectly-accepted-before-repair",
                [sys.executable, "-m", "grader.pipeline", "fixtures/negative/manifest.json"], copy,
                stdout="sample_negative_001: 3\n", env=env)
        run("repair-patch-check", [git, "apply", "--check", str(HERE / "repair.patch")], copy, env=env)
        run("apply-repair-patch", [git, "apply", str(HERE / "repair.patch")], copy, env=env)
        if NEUTRAL == "dispatch-board":
            run("repaired-test-utc", tests, copy, contains=("Ran 9 tests", "OK"), env=utc)
            for zone in ("Pacific/Kiritimati", "Etc/GMT+12"):
                for attempt in (1, 2, 3):
                    run("repaired-repeat-" + zone.replace("/", "-") + "-" + str(attempt), tests, copy,
                        contains=("Ran 9 tests", "OK"), env=dict(env, TZ=zone))
            helper = run("repaired-two-timezone-helper", [sys.executable, "scripts/show_timezone_variation.py"], copy,
                         contains=("Pacific/Kiritimati: pass", "Etc/GMT+12: pass"), env=env)
            if helper.stderr.count("Ran 9 tests") != 2:
                raise AssertionError("Timezone helper must execute both complete strengthened suites.")
            demonstration = "import sys; sys.path.insert(0, 'src'); from datetime import datetime; from dispatch_board import dispatch_label; cases=[('2026-01-01T04:59:59+00:00','America/New_York'),('2026-01-01T05:00:00+00:00','America/New_York'),('2026-03-08T06:59:59+00:00','America/New_York'),('2026-03-08T07:00:00+00:00','America/New_York')]; [print(text+' => '+dispatch_label('ROUTE-17',zone,clock=lambda: datetime.fromisoformat(text))) for text,zone in cases]"
            expected = "2026-01-01T04:59:59+00:00 => ROUTE-17 | 2025-12-31\n2026-01-01T05:00:00+00:00 => ROUTE-17 | 2026-01-01\n2026-03-08T06:59:59+00:00 => ROUTE-17 | 2026-03-08\n2026-03-08T07:00:00+00:00 => ROUTE-17 | 2026-03-08\n"
            run("fixed-boundary-outputs", [sys.executable, "-c", demonstration], copy, stdout=expected, env=env)
        else:
            run("repaired-ordinary-verification", ["sh", "scripts/verify.sh"], copy,
                contains=("Ran 5 tests", "OK"), stdout="sample_001: 3\n", env=env)
            for attempt in (1, 2):
                run("repaired-valid-cli-" + str(attempt),
                    [sys.executable, "-m", "grader.pipeline", "fixtures/valid/manifest.json"], copy,
                    stdout="sample_001: 3\n", env=env)
                run("repaired-negative-cli-" + str(attempt),
                    [sys.executable, "-m", "grader.pipeline", "fixtures/negative/manifest.json"], copy, expected=2,
                    contains=("clearance must be approved",), stdout="", env=env)
            pending = json.loads((copy / "fixtures/negative/manifest.json").read_text())
            valid = json.loads((copy / "fixtures/valid/manifest.json").read_text())
            if pending["sha256"] != valid["sha256"] or (copy / "fixtures/negative/artifact.txt").read_bytes() != (copy / "fixtures/valid/artifact.txt").read_bytes():
                raise AssertionError("The negative fixture must preserve artifact bytes and digest.")
        final_source = inventory(copy)
        changed = {name: item for name, item in final_source.items() if item != source_before.get(name)}
        after = inventory(HERE / "after")
        if set(changed) != set(after) or any(final_source[name] != entry for name, entry in after.items()):
            raise AssertionError("Phased edits differ from the documented complete files.")
        combined = temp / "combined"
        shutil.copytree(source, combined)
        run("apply-combined-patch-independently", [git, "apply", str(HERE / "solution.patch")], combined, env=env)
        if inventory(combined) != final_source:
            raise AssertionError("Combined and phased patches produce different source trees.")
    source_after = inventory(source)
    if source_after != source_before or inventory(inputs) != all_inputs_before:
        raise AssertionError("Pinned inputs changed during rehearsal.")
    if {name: sha((runtime / name).read_bytes()) for name in metadata_paths} != metadata_before:
        raise AssertionError("Runtime identity or Goal changed during rehearsal.")
    if registry_api.verify_goal(task, runtime / task["goalFile"]) != goal:
        raise AssertionError("Approved Goal changed during rehearsal.")
    receipt = {
        "version": 1, "status": "PASS", "verifiedAt": datetime.now(timezone.utc).isoformat(),
        "neutral": NEUTRAL, "taskId": task["id"], "notionPageId": task["notionPageId"],
        "sourceRepo": SOURCE_REPO, "sourceCommit": SOURCE_COMMIT, "goalSha256": GOAL_SHA256,
        "approvedGoal": task["approvedGoal"], "sourceInventoryBefore": source_before,
        "sourceInventoryAfter": source_after, "referenceSourceInventory": final_source,
        "patchSha256": {name: sha(data) for name, data in patches.items()},
        "solutionPatchSha256": sha(patches["solution.patch"]), "plannedChangedFiles": changed,
        "runtimeMetadataSha256": metadata_before,
        "toolVersions": {"python": version.stdout.strip(), "git": subprocess.check_output([git, "--version"], text=True).strip()},
        "cloudSeed": {"sourceCommit": cloud["sourceCommit"], "runId": cloud["runId"]},
        "checks": checks, "sourceInputsUnchanged": True, "runtimeMetadataUnchanged": True,
        "sourceRepositoriesWritten": False, "recordingWorkspaceModified": False,
        "recorderExecuted": False, "setupVerified": False, "recordingReady": False,
        "disposableReferencePatchApplied": True, "aiAuthoredBeforeRecording": True,
        "externalSolutionWalkthroughAcceptanceVerified": False,
        "limitations": ["These are disposable off-screen worked-reference results, not an actual Recorder attempt.",
                        "The manual does not explicitly establish eligibility of a fully AI-authored solution walkthrough.",
                        "Clock DST tests assert the calendar-date output; they do not validate an API for displaying hours or offsets."] if NEUTRAL == "dispatch-board" else
                       ["These are disposable off-screen worked-reference results, not an actual Recorder attempt.",
                        "The manual does not explicitly establish eligibility of a fully AI-authored solution walkthrough."],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", dir=output.parent, prefix=".reference-proof-", delete=False) as file:
        json.dump(receipt, file, indent=2)
        file.write("\n")
        staged = Path(file.name)
    staged.replace(output)
    print(json.dumps({"evidence": str(output), "checks": len(checks), "changedFiles": list(changed), "sourceInputsUnchanged": True, "recorderExecuted": False}))


if __name__ == "__main__":
    main()
