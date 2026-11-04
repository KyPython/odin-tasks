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
NEUTRAL = 'cursor-pagination-aggregator'
SOURCE_REPO = 'https://github.com/KyPython/cursor-pagination-aggregator'
SOURCE_COMMIT = '9c829c6ec7f85cf382f97e286bf8acce20a96fe7'
GOAL_SHA256 = 'c08197cea0e65611a4f9d8979822968de9156e24a829c24fea2063e031fd6e86'
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
        raise ValueError("This reference requires its exact source and candidate Goal pins.")
    if task.get("workflowLane") != "bootcamp" or task.get("goalKind") != "candidate" or task.get("approvedGoal") or task.get("studioTaskUrl"):
        raise ValueError("Internal candidate reference must not invent Odin approval or a Studio assignment.")
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
                       "startedAt": started, "environmentOverrides": {"PYTHONPATH": "src"},
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

    expected_records = {
        "ordinary": [{"id": "rec-101", "label": "amber"}, {"id": "rec-102", "label": "blue"}, {"id": "rec-103", "label": "coral"}],
        "repeated-cursor": [{"id": "rec-201", "label": "dune"}, {"id": "rec-202", "label": "ember"}],
        "empty-page": [{"id": "rec-301", "label": "fern"}, {"id": "rec-302", "label": "gold"}],
        "duplicate-records": [{"id": "rec-401", "label": "harbor"}, {"id": "rec-402", "label": "indigo"}, {"id": "rec-403", "label": "juniper"}],
    }
    with tempfile.TemporaryDirectory(prefix="taskwork-cursor-reference-") as temporary:
        temp = Path(temporary)
        copy = temp / NEUTRAL
        shutil.copytree(source, copy)
        env = os.environ.copy()
        for name in ("PYTHONHOME", "PYTHONPATH", "VIRTUAL_ENV", "CONDA_PREFIX", "CONDA_DEFAULT_ENV", "TZ"):
            env.pop(name, None)
        env.update({"PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1", "PYTHONPATH": "src"})
        version = run("public-python-version", [sys.executable, "--version"], copy,
                      contains=(cloud["toolVersions"]["python"],), env=env)
        tests = [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"]
        git = shutil.which("git")
        if not git:
            raise ValueError("Public Git is required to apply reviewed unified patches.")
        run("unchanged-starter-tests", tests, copy, contains=("Ran 4 tests", "OK"), env=env)
        cli = lambda fixture: [sys.executable, "-m", "cursor_client.cli", "fixtures/" + fixture + ".json"]
        ordinary_stdout = json.dumps(expected_records["ordinary"], indent=2) + "\n"
        run("unchanged-ordinary-cli", cli("ordinary"), copy, stdout=ordinary_stdout, env=env)
        run("unchanged-repeat-overrequests-transcript", cli("repeated-cursor"), copy, expected=1,
            contains=("pagination failed: no fixture response for cursor 'repeat'",), stdout="", env=env)
        run("unchanged-empty-page-stops-too-early", cli("empty-page"), copy,
            stdout=json.dumps(expected_records["empty-page"][:1], indent=2) + "\n", env=env)
        defective_duplicates = [expected_records["duplicate-records"][0], expected_records["duplicate-records"][1],
                                expected_records["duplicate-records"][1], expected_records["duplicate-records"][2]]
        run("unchanged-duplicate-cli-keeps-repeat", cli("duplicate-records"), copy,
            stdout=json.dumps(defective_duplicates, indent=2) + "\n", env=env)
        run("combined-patch-check", [git, "apply", "--check", str(HERE / "solution.patch")], copy, env=env)
        run("tests-patch-check", [git, "apply", "--check", str(HERE / "tests.patch")], copy, env=env)
        run("apply-tests-patch", [git, "apply", str(HERE / "tests.patch")], copy, env=env)
        test_before_repair = sha((copy / "tests/test_aggregator.py").read_bytes())
        run("strengthened-tests-detect-exact-boundary-defects", tests, copy, expected=1,
            contains=("Ran 13 tests", "FAILED (failures=5, errors=2)",
                      "ERROR: test_supplied_repeated_cursor_stops_without_an_extra_request",
                      "ERROR: test_nonadjacent_cursor_cycle_stops_after_unique_requests",
                      "FAIL: test_supplied_empty_page_continues_to_its_next_cursor",
                      "FAIL: test_supplied_duplicates_retain_first_server_order",
                      "FAIL: test_empty_first_page_continues_to_records",
                      "FAIL: test_duplicate_in_one_page_keeps_first_payload",
                      "FAIL: test_duplicate_across_pages_keeps_first_payload"), env=env)
        run("repair-patch-check", [git, "apply", "--check", str(HERE / "repair.patch")], copy, env=env)
        run("apply-repair-patch", [git, "apply", str(HERE / "repair.patch")], copy, env=env)
        for number in (1, 2, 3):
            run("same-strengthened-tests-pass-" + str(number), tests, copy,
                contains=("Ran 13 tests", "OK"), env=env)
        test_after_repair = sha((copy / "tests/test_aggregator.py").read_bytes())
        if test_before_repair != test_after_repair:
            raise AssertionError("Acceptance tests changed between the expected failure and success.")
        outputs = {}
        for fixture, records in expected_records.items():
            expected = json.dumps(records, indent=2) + "\n"
            first = run("repaired-" + fixture + "-cli-1", cli(fixture), copy, stdout=expected, env=env)
            second = run("repaired-" + fixture + "-cli-2", cli(fixture), copy, stdout=expected, env=env)
            if first.stdout != second.stdout:
                raise AssertionError("Fixture output is not reproducible: " + fixture)
            outputs[fixture] = {"records": records, "stdoutSha256": sha(first.stdout.encode()), "repeatBytesEqual": True}
        final_source = inventory(copy)
        changed = {name: item for name, item in final_source.items() if item != source_before.get(name)}
        after = inventory(HERE / "after")
        if set(changed) != {"src/cursor_client/aggregator.py", "tests/test_aggregator.py"} or set(changed) != set(after):
            raise AssertionError("Only the reviewed aggregator and its tests may change.")
        if any(final_source[name] != entry for name, entry in after.items()):
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
        raise AssertionError("Candidate Goal changed during rehearsal.")
    receipt = {
        "version": 1, "status": "PASS", "verifiedAt": datetime.now(timezone.utc).isoformat(),
        "neutral": NEUTRAL, "taskId": task["id"], "notionPageId": task["notionPageId"],
        "workflowLane": "bootcamp", "goalKind": "candidate", "candidateGoal": task["candidateGoal"],
        "sourceRepo": SOURCE_REPO, "sourceCommit": SOURCE_COMMIT, "goalSha256": GOAL_SHA256,
        "sourceInventoryBefore": source_before, "sourceInventoryAfter": source_after,
        "referenceSourceInventory": final_source,
        "patchSha256": {name: sha(data) for name, data in patches.items()},
        "solutionPatchSha256": sha(patches["solution.patch"]), "plannedChangedFiles": changed,
        "acceptanceTestSha256BeforeRepair": test_before_repair,
        "acceptanceTestSha256AfterRepair": test_after_repair,
        "fixtureOutputs": outputs, "runtimeMetadataSha256": metadata_before,
        "toolVersions": {"python": version.stdout.strip(), "git": subprocess.check_output([git, "--version"], text=True).strip()},
        "cloudSeed": {"sourceCommit": cloud["sourceCommit"], "runId": cloud["runId"]},
        "checks": checks, "sourceInputsUnchanged": True, "runtimeMetadataUnchanged": True,
        "sourceRepositoriesWritten": False, "recordingWorkspaceModified": False,
        "recorderExecuted": False, "setupVerified": False, "recordingReady": False, "practiceReady": False,
        "disposableReferencePatchApplied": True, "aiAuthoredBeforeRecording": True,
        "paidWalkthroughPermissionVerified": False, "externalSolutionWalkthroughAcceptanceVerified": False,
        "unaidedTransferProficiencyVerified": False,
        "limitations": ["This is guided internal practice evidence from disposable copies, not an actual Recorder attempt or unaided transfer test.",
                        "The client uses only local synthetic fixtures; no HTTP service, network behavior or production endpoint was exercised.",
                        "Termination is bounded by unique cursors for the supplied repeated-cursor fixtures; an endpoint generating infinitely many distinct cursors is outside this exercise.",
                        "No Odin approval, Studio assignment, paid-task eligibility or human gate is created by a reference PASS."],
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
