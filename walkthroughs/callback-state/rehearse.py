#!/usr/bin/env python3
"""Verify the pinned callback reference only in disposable local-fixture copies."""
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
NEUTRAL = "callback-state"
SOURCE_REPO = "https://github.com/KyPython/oauth-callback-state"
SOURCE_COMMIT = "c65f9343be723ea36289db541b8f373883cbfe8a"
GOAL_SHA256 = "53aa8de22a4d56b96b893bd778b17f0d629b57b4a43de0d34883ada57016ff24"
HERE = Path(__file__).resolve().parent
SENSITIVE_FIXTURE_VALUES = (
    "fixture-authorization-code", "fixture-state-alpha", "fixture-state-beta",
)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def inventory(root):
    if root.is_symlink() or not root.is_dir():
        raise ValueError("Expected a real input directory")
    result = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink() or not (path.is_file() or path.is_dir()):
            raise ValueError("Unsafe input member")
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
            raise ValueError("Use real paths without symlink ancestors")
    inputs, runtime, output = args.inputs.resolve(), args.runtime.resolve(), args.output.resolve()
    protected = (inputs, runtime, HERE, Path("/Users/recorder"), Path("/Users/Shared/TaskWorkPlans"))
    if any(output.is_relative_to(root) for root in protected):
        raise ValueError("Proof output must be outside inputs/runtime/references/Recorder")
    if "TaskWork" in output.parts or output.name.endswith(".code-workspace"):
        raise ValueError("Proof output cannot be a recording workspace")
    if output.exists() or any((parent / ".git").exists() for parent in output.parents):
        raise ValueError("Preserve existing proof files and repository content")
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
        raise ValueError("This reference requires its exact source and candidate Goal")
    if task.get("workflowLane") != "bootcamp" or task.get("goalKind") != "candidate" or task.get("studioTaskUrl"):
        raise ValueError("This is an internal candidate practice reference")
    goal = registry_api.verify_goal(task, runtime / task["goalFile"])
    source = inputs / NEUTRAL
    source_before = inventory(source)
    if set(source_before) != set(project["files"]):
        raise ValueError("Pinned source inventory differs")
    for name, expected in project["files"].items():
        if any(source_before[name][key] != expected[key] for key in ("sha256", "mode")):
            raise ValueError("Pinned source bytes or mode differ")
    inputs_before = inventory(inputs)
    metadata_names = ("TaskWorkRegistry.py", "task-registry.json", "runtime-manifest.json", task["goalFile"], "cloud-proof.json")
    metadata_before = {name: sha((runtime / name).read_bytes()) for name in metadata_names}
    cloud = registry_api.load_json(runtime / "cloud-proof.json")
    if cloud["starterCommits"].get(NEUTRAL) != SOURCE_COMMIT:
        raise ValueError("Actual source-kit cloud proof has a different source pin")
    patches = {name: (HERE / name).read_bytes() for name in ("tests.patch", "repair.patch", "solution.patch")}
    if patches["solution.patch"] != patches["tests.patch"] + patches["repair.patch"]:
        raise ValueError("Combined patch differs from reviewed phases")
    checks = []

    def run(label, argv, cwd, expected=0, contains=(), stdout=None):
        started = datetime.now(timezone.utc).isoformat()
        result = subprocess.run(argv, cwd=cwd, env=env, capture_output=True, text=True, timeout=60)
        if any(value in result.stdout + result.stderr for value in SENSITIVE_FIXTURE_VALUES):
            raise AssertionError("Sensitive callback fixture value appeared in command output")
        checks.append({"label": label, "command": argv, "cwd": str(cwd), "startedAt": started,
                       "exitCode": result.returncode, "expectedExitCode": expected,
                       "stdout": result.stdout, "stderr": result.stderr,
                       "sensitiveCallbackValuesAbsent": True})
        if result.returncode != expected:
            raise AssertionError((label, "unexpected command exit", result.returncode))
        for fragment in contains:
            if fragment not in result.stdout + result.stderr:
                raise AssertionError((label, "expected observation absent", fragment))
        if stdout is not None and result.stdout != stdout:
            raise AssertionError((label, "stdout differs from reviewed observation"))
        print(label + " PASS exit=" + str(result.returncode), flush=True)
        return result

    env = os.environ.copy()
    for name in ("PYTHONHOME", "PYTHONPATH", "VIRTUAL_ENV", "CONDA_PREFIX", "CONDA_DEFAULT_ENV", "TZ",
                 "GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"):
        env.pop(name, None)
    env.update({"PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1",
                "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null"})
    git = shutil.which("git")
    if not git:
        raise ValueError("Public Git is required for disposable patch application")
    tests = [sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests", "-v"]
    harness = [sys.executable, "-B", "run_fixtures.py"]
    with tempfile.TemporaryDirectory(prefix="taskwork-callback-state-reference-") as temporary:
        temp = Path(temporary)
        copy = temp / NEUTRAL
        shutil.copytree(source, copy)
        version = run("public-python-version", [sys.executable, "--version"], copy,
                      contains=(cloud["toolVersions"]["python"],))
        run("starter-ordinary-tests", tests, copy, contains=("Ran 2 tests", "OK"))
        starter = run("starter-fixture-observations", harness, copy)
        ordinary = {"status": "ok", "category": None, "redirect_to": "/dashboard"}
        starter_expected = {name: [ordinary] for name in ("valid", "missing", "mismatched", "expired")}
        starter_expected["replayed"] = [ordinary, {"status": "ok", "category": None, "redirect_to": "/"}]
        if json.loads(starter.stdout) != starter_expected:
            raise AssertionError("Starter observation differs from the pinned defective path")
        run("combined-patch-check", [git, "apply", "--check", str(HERE / "solution.patch")], copy)
        run("tests-patch-check", [git, "apply", "--check", str(HERE / "tests.patch")], copy)
        run("apply-tests-patch", [git, "apply", str(HERE / "tests.patch")], copy)
        run("strengthened-tests-fail-before-repair", tests, copy, expected=1,
            contains=("Ran 12 tests", "FAILED", "test_replay_is_rejected_after_one_success",
                      "test_expired_state_is_rejected_without_consuming_request", "test_mismatch_and_unbound_state_are_rejected"))
        run("repair-patch-check", [git, "apply", "--check", str(HERE / "repair.patch")], copy)
        run("apply-repair-patch", [git, "apply", str(HERE / "repair.patch")], copy)
        run("repaired-complete-tests", tests, copy, contains=("Ran 12 tests", "OK"))
        run("repaired-repeat-complete-tests", tests, copy, contains=("Ran 12 tests", "OK"))
        reference_source = inventory(copy)
        changed = {name: value for name, value in reference_source.items() if value != source_before.get(name)}
        after = inventory(HERE / "after")
        if changed != after:
            raise AssertionError("Actual phased source differs from the complete planned files")
        combined = temp / "combined"
        shutil.copytree(source, combined)
        run("apply-combined-patch-independently", [git, "apply", str(HERE / "solution.patch")], combined)
        if inventory(combined) != reference_source:
            raise AssertionError("Combined and phased patches produce different files")
        run("independent-combined-complete-tests", tests, combined, contains=("Ran 12 tests", "OK"))
        outputs = copy / "practice-checks"
        outputs.mkdir()
        first = run("repaired-fixture-run-1", harness, copy)
        second = run("repaired-fixture-run-2", harness, copy)
        (outputs / "callback-run-1.json").write_text(first.stdout)
        (outputs / "callback-run-2.json").write_text(second.stdout)
        if first.stdout != second.stdout:
            raise AssertionError("Repeated harness outputs differ")
        run("saved-fixture-byte-comparison", ["/usr/bin/cmp", "practice-checks/callback-run-1.json", "practice-checks/callback-run-2.json"], copy, stdout="")
        verify = '''import json
from pathlib import Path
from fixtures import SCENARIOS
path = Path("practice-checks/callback-run-1.json")
text = path.read_text()
observed = json.loads(text)
ok = {"status": "ok", "category": None, "redirect_to": "/dashboard"}
def error(category):
    return {"status": "error", "category": category, "redirect_to": None}
expected = {"valid": [ok], "missing": [error("missing_state")], "mismatched": [error("state_mismatch")], "expired": [error("state_expired")], "replayed": [ok, error("state_replayed")]}
assert observed == expected, "fixture results differ from the local contract"
for case in SCENARIOS.values():
    for field in ("code", "state"):
        value = case["query"].get(field)
        assert not value or value not in text, "serialized output contains a sensitive fixture value"
assert path.read_bytes() == Path("practice-checks/callback-run-2.json").read_bytes()
print("Exact fixture results and sensitive-value checks passed.")
'''
        run("saved-fixture-semantics-and-sensitive-values", [sys.executable, "-B", "-c", verify], copy,
            stdout="Exact fixture results and sensitive-value checks passed.\n")
        generated_outputs = inventory(outputs)
    if inventory(source) != source_before or inventory(inputs) != inputs_before:
        raise AssertionError("Original source inputs changed")
    if {name: sha((runtime / name).read_bytes()) for name in metadata_names} != metadata_before:
        raise AssertionError("Runtime identity or candidate Goal changed")
    if registry_api.verify_goal(task, runtime / task["goalFile"]) != goal:
        raise AssertionError("Candidate Goal changed")
    proof = {
        "version": 1, "status": "PASS", "verifiedAt": datetime.now(timezone.utc).isoformat(),
        "neutral": NEUTRAL, "taskId": task["id"], "notionPageId": task["notionPageId"],
        "workflowLane": "bootcamp", "goalKind": "candidate", "candidateGoal": registry_api.goal_text(task),
        "sourceRepo": SOURCE_REPO, "sourceCommit": SOURCE_COMMIT, "goalSha256": GOAL_SHA256,
        "sourceInventoryBefore": source_before, "sourceInventoryAfter": inventory(source),
        "referenceSourceInventory": reference_source, "plannedChangedFiles": changed,
        "generatedDisposableOutputs": generated_outputs,
        "patchSha256": {name: sha(data) for name, data in patches.items()},
        "solutionPatchSha256": sha(patches["solution.patch"]),
        "runtimeMetadataSha256": metadata_before,
        "toolVersions": {"python": version.stdout.strip(), "git": subprocess.check_output([git, "--version"], text=True).strip()},
        "cloudSeed": {"sourceCommit": cloud["sourceCommit"], "runId": cloud["runId"]},
        "checks": checks, "sourceInputsUnchanged": True, "runtimeMetadataUnchanged": True,
        "serializedSensitiveValuesAbsent": True, "sourceRepositoriesWritten": False,
        "recordingWorkspaceModified": False, "recorderExecuted": False, "setupVerified": False,
        "recordingReady": False, "practiceReady": False, "externalApprovalClaimed": False,
        "disposableReferencePatchApplied": True, "aiAuthoredBeforeRecording": True,
        "unaidedTransferVerified": False, "paidWalkthroughPermissionVerified": False,
        "limitations": ["Only deterministic synthetic local fixtures were executed.",
                        "No provider interaction or production session-storage/concurrency guarantee was verified.",
                        "Replay evidence covers reuse of the consumed request in the same mutable session.",
                        "Guided practice and disposable results do not establish actual human recording or unaided transfer."],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    serialized_proof = json.dumps(proof, indent=2) + "\n"
    with tempfile.NamedTemporaryFile("w", dir=output.parent, prefix=".callback-proof-", delete=False) as file:
        file.write(serialized_proof)
        staged = Path(file.name)
    if output.exists():
        staged.unlink()
        raise ValueError("Preserve a concurrently created proof")
    staged.chmod(0o644)
    staged.replace(output)
    print(json.dumps({"evidence": str(output), "checks": len(checks), "completeTests": 12,
                      "sourceInputsUnchanged": True, "serializedSensitiveValuesAbsent": True,
                      "recorderExecuted": False}))


if __name__ == "__main__":
    main()
