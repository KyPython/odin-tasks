#!/usr/bin/env python3
"""Verify the guided Threshold plan only in disposable off-screen copies."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
NEUTRAL = "threshold-evaluation"
COMMIT = "aca7a6ac52a9a2dee2d7bc3a0a77dca09f2a6fe5"
GOAL_SHA = "7df67f3a13654442be4f04c14cabb7a15eb9fab1c5ff52058c06775e867c47cb"
RED_METHODS = {
    "test_all_four_cells_and_inclusive_score_boundary",
    "test_fixture_candidate_counts_and_costs",
    "test_fixture_selects_cost_over_accuracy",
    "test_equal_cost_prefers_lowest_threshold_not_accuracy",
    "test_policy_weights_change_selection",
    "test_generator_input_matches_complete_expected_report",
}
COUNTS_ONLY_METHODS = RED_METHODS - {
    "test_all_four_cells_and_inclusive_score_boundary", "test_fixture_candidate_counts_and_costs"}
REPORT_ARGV = ["-m", "threshold_lab.cli", "--observations", "fixtures/observations.json",
               "--policy", "fixtures/policy.json"]
SUITE_ARGV = ["-m", "unittest", "discover", "-s", "tests", "-v"]
MANUAL_CANDIDATES = [
    {"threshold": 0.3, "true_positive": 2, "true_negative": 0, "false_positive": 5,
     "false_negative": 1, "accuracy": 0.25, "total_cost": 19},
    {"threshold": 0.5, "true_positive": 2, "true_negative": 2, "false_positive": 3,
     "false_negative": 1, "accuracy": 0.5, "total_cost": 15},
    {"threshold": 0.7, "true_positive": 1, "true_negative": 3, "false_positive": 2,
     "false_negative": 2, "accuracy": 0.5, "total_cost": 22},
    {"threshold": 0.85, "true_positive": 1, "true_negative": 5, "false_positive": 0,
     "false_negative": 2, "accuracy": 0.75, "total_cost": 18},
]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def inventory(root):
    require(root.is_dir() and not root.is_symlink(), "Expected a plain input directory")
    result = {}
    for path in sorted(root.rglob("*")):
        require(not path.is_symlink() and (path.is_dir() or path.is_file()), "Unsafe input object")
        if path.is_file():
            result[path.relative_to(root).as_posix()] = {
                "sha256": sha(path.read_bytes()), "mode": stat.S_IMODE(path.stat().st_mode)}
    return result


def now():
    return datetime.now(timezone.utc).isoformat()


def check(proof, name, argv, cwd, env):
    item = {"name": name, "command": [str(value) for value in argv], "cwd": str(cwd), "startedAt": now()}
    result = subprocess.run(item["command"], cwd=cwd, env=env, capture_output=True, text=True, timeout=120)
    item.update(exitCode=result.returncode, stdout=result.stdout, stderr=result.stderr, finishedAt=now())
    proof["checks"].append(item)
    return item


def apply(proof, work, filename, env):
    patch = HERE / filename
    for arguments, suffix in ((["--check"], "check"), ([], "apply")):
        result = check(proof, filename + " " + suffix, ["git", "apply", *arguments, patch], work, env)
        require(result["exitCode"] == 0, filename + " failed " + suffix)


def fails_as(result, methods, count):
    actual = set(re.findall(r"^FAIL: (\w+)(?:\s|$)", result["stderr"], re.M))
    return (result["exitCode"] == 1 and actual == methods
            and "Ran 11 tests" in result["stderr"] and f"FAILED (failures={count})" in result["stderr"])


def counts_repair(original):
    return original.replace(
        b"false_positive = sum(row.actual and row.score < threshold for row in rows)",
        b"false_positive = sum(not row.actual and row.score >= threshold for row in rows)", 1).replace(
        b"false_negative = sum(not row.actual and row.score >= threshold for row in rows)",
        b"false_negative = sum(row.actual and row.score < threshold for row in rows)", 1)


def execute(args, proof):
    require(sys.version_info[:3] == (3, 12, 7), "Use the pinned public Python 3.12.7")
    require(not args.inputs.is_symlink() and not args.runtime.is_symlink(), "Unsafe input roots")
    inputs, runtime = args.inputs.resolve(), args.runtime.resolve()
    validator = runtime / "TaskWorkRegistry.py"
    require(validator.is_file() and not validator.is_symlink(), "Missing reviewed registry validator")
    spec = importlib.util.spec_from_file_location("threshold_registry", validator)
    api = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(api)
    registry = api.load_json(runtime / "task-registry.json")
    manifest = api.load_json(runtime / "runtime-manifest.json")
    tasks = api.validate_registry(registry)
    projects = api.validate_manifest(manifest, registry)
    task = tasks[NEUTRAL]
    project = next(item for item in projects if item["neutral"] == NEUTRAL)
    require(task["commit"] == COMMIT and task["goalSha256"] == GOAL_SHA
            and task["sourceRepo"] == "https://github.com/KyPython/threshold-evaluation"
            and task["id"] == "BOOTCAMP-3F28621E0A7A81BCABB6C65D74863966"
            and task.get("workflowLane") == "bootcamp" and task.get("goalKind") == "candidate"
            and task["dependencyProfile"] == "python-stdlib", "Reference source/Goal/lane changed")
    source = inputs / NEUTRAL
    original_inventory = inventory(source)
    require(original_inventory == project["files"], "Source bytes/modes differ from the pinned manifest")
    goal_path = runtime / task["goalFile"]
    goal = api.verify_goal(task, goal_path)
    metadata = {path: path.read_bytes() for path in (validator, runtime / "task-registry.json", runtime / "runtime-manifest.json", goal_path)}
    wheels_before = inventory(runtime / "wheels") if (runtime / "wheels").exists() else None
    patches = {name: (HERE / name).read_bytes() for name in ("tests.patch", "repair.patch", "solution.patch")}
    require(patches["solution.patch"] == patches["tests.patch"] + patches["repair.patch"], "Patch phases differ")
    proof.update(taskId=task["id"], workflowLane="bootcamp", goalKind="candidate", sourceRepo=task["sourceRepo"],
                 exactCandidateGoal=task["candidateGoal"], sourceFiles=len(original_inventory),
                 sourceFileInventory=original_inventory, pythonExecutable=sys.executable,
                 pythonVersion=sys.version.split()[0], patchSha256={name: sha(data) for name, data in patches.items()})
    scratch_root = Path("/private/tmp") if Path("/private/tmp").is_dir() else Path(tempfile.gettempdir())
    scratch_root = scratch_root.resolve()
    require(not any(scratch_root == path or path in scratch_root.parents
                    for path in (inputs, runtime, Path("/Users/recorder"))), "Unsafe disposable root")
    env = os.environ.copy()
    for name in ("PYTHONHOME", "PYTHONPATH", "VIRTUAL_ENV", "CONDA_PREFIX", "CONDA_DEFAULT_ENV"):
        env.pop(name, None)
    env.update(PYTHONPATH="src", PYTHONDONTWRITEBYTECODE="1", TMPDIR=str(scratch_root))
    with tempfile.TemporaryDirectory(prefix="threshold-worked-reference-", dir=scratch_root) as directory:
        temporary = Path(directory)
        work = temporary / NEUTRAL
        shutil.copytree(source, work)
        baseline = check(proof, "Original four-test baseline", [sys.executable, *SUITE_ARGV], work, env)
        require(baseline["exitCode"] == 0 and "Ran 4 tests" in baseline["stderr"] and "\nOK\n" in baseline["stderr"], "Original baseline differs")
        old_report = check(proof, "Original defective report", [sys.executable, *REPORT_ARGV], work, env)
        require(old_report["exitCode"] == 0, "Original report failed to generate")
        old = json.loads(old_report["stdout"])
        require(old["selected_threshold"] == 0.85
                and [row["total_cost"] for row in old["candidates"]] == [47, 29, 22, 4], "Defective report differs")
        production = work / "src/threshold_lab/evaluation.py"
        original_production = production.read_bytes()
        apply(proof, work, "tests.patch", env)
        test_bytes = (work / "tests/test_evaluation.py").read_bytes()
        require(production.read_bytes() == original_production, "Tests phase changed production")
        red = check(proof, "Strengthened tests before repair", [sys.executable, *SUITE_ARGV], work, env)
        require(fails_as(red, RED_METHODS, 6), "Expected six semantic failures, not syntax/import failures")
        partial = temporary / "counts-only"
        shutil.copytree(work, partial)
        (partial / "src/threshold_lab/evaluation.py").write_bytes(counts_repair(original_production))
        partial_red = check(proof, "Counts-only repair leaves selection tests failing", [sys.executable, *SUITE_ARGV], partial, env)
        require(fails_as(partial_red, COUNTS_ONLY_METHODS, 4), "Counts-only stage must retain four selection failures")
        partial_report = check(proof, "Counts-only report still selects highest accuracy", [sys.executable, *REPORT_ARGV], partial, env)
        require(partial_report["exitCode"] == 0 and json.loads(partial_report["stdout"])["candidates"] == MANUAL_CANDIDATES
                and json.loads(partial_report["stdout"])["selected_threshold"] == 0.85, "Selection defect was not isolated")
        apply(proof, work, "repair.patch", env)
        expected_production = counts_repair(original_production).replace(
            b"selected = max(evaluations, key=lambda item: (item.accuracy, -item.threshold))",
            b"selected = min(evaluations, key=lambda item: (item.total_cost, item.threshold))", 1)
        require(production.read_bytes() == expected_production
                and (work / "tests/test_evaluation.py").read_bytes() == test_bytes, "Repair exceeded the three-line boundary or changed tests")
        green = check(proof, "Same eleven tests after repair", [sys.executable, *SUITE_ARGV], work, env)
        require(green["exitCode"] == 0 and "Ran 11 tests" in green["stderr"] and "\nOK\n" in green["stderr"], "Strengthened suite did not pass")
        report = check(proof, "Corrected report", [sys.executable, *REPORT_ARGV], work, env)
        repeat = check(proof, "Repeat corrected report", [sys.executable, *REPORT_ARGV], work, env)
        expected = {"costs": {"false_negative": 9, "false_positive": 2}, "candidates": MANUAL_CANDIDATES, "selected_threshold": 0.5}
        require(report["exitCode"] == repeat["exitCode"] == 0 and json.loads(report["stdout"]) == expected
                and report["stdout"] == repeat["stdout"] == json.dumps(expected, indent=2, sort_keys=True) + "\n", "Report calculation or complete repeated bytes differ")
        (work / "report.json").write_text(report["stdout"])
        oracle_code = '''import json
from pathlib import Path
rows = json.loads(Path("fixtures/observations.json").read_text())
policy = json.loads(Path("fixtures/policy.json").read_text())
report = json.loads(Path("report.json").read_text())
calculated = []
for threshold in sorted(policy["candidate_thresholds"]):
    counts = dict(true_positive=0, true_negative=0, false_positive=0, false_negative=0)
    for row in rows:
        if row["actual"]:
            category = "true_positive" if row["score"] >= threshold else "false_negative"
        else:
            category = "false_positive" if row["score"] >= threshold else "true_negative"
        counts[category] += 1
    cost = counts["false_negative"] * policy["false_negative_cost"] + counts["false_positive"] * policy["false_positive_cost"]
    calculated.append(dict(threshold=threshold, **counts, accuracy=(counts["true_positive"] + counts["true_negative"])/len(rows), total_cost=cost))
assert report["candidates"] == calculated
assert [row["total_cost"] for row in calculated] == [19, 15, 22, 18]
assert report["selected_threshold"] == 0.5
assert min(calculated, key=lambda row: (row["total_cost"], row["threshold"]))["threshold"] == 0.5
print(json.dumps({"independentCountsAndCosts": True, "selectedThreshold": 0.5, "selectedCost": 15}, sort_keys=True))
'''
        oracle = check(proof, "Independent fixture arithmetic check", [sys.executable, "-c", oracle_code], work, env)
        require(oracle["exitCode"] == 0 and json.loads(oracle["stdout"])["independentCountsAndCosts"], "Independent report arithmetic failed")
        combined = temporary / "combined"
        shutil.copytree(source, combined)
        apply(proof, combined, "solution.patch", env)
        require(all((combined / name).read_bytes() == (work / name).read_bytes() for name in original_inventory), "Combined and phased final source differ")
        repeat_suite = check(proof, "Repeat complete strengthened suite", [sys.executable, *SUITE_ARGV], work, env)
        require(repeat_suite["exitCode"] == 0 and "Ran 11 tests" in repeat_suite["stderr"], "Repeated strengthened suite failed")
        proof.update(originalSuiteGreen=True, strengthenedSuiteRed=True, expectedFailureMethods=sorted(RED_METHODS),
                     countsOnlySelectionDefectIsolated=True, sameStrengthenedTestsAfterRepair=True,
                     strengthenedSuiteGreen=True, strengthenedTestsSha256=sha(test_bytes),
                     repairedProductionSha256=sha(production.read_bytes()), independentlyVerifiedReport=expected,
                     reportSha256=sha(report["stdout"].encode()), repeatedReportBytesIdentical=True,
                     combinedPatchMatchesPhasedRepair=True)
    require(inventory(source) == original_inventory and all(path.read_bytes() == data for path, data in metadata.items()), "Source/Goal/runtime metadata changed")
    require(wheels_before is None or inventory(runtime / "wheels") == wheels_before, "Offline wheel cache changed")
    proof.update(status="PASS", sourceInputsUnchanged=True, runtimeMetadataAndGoalUnchanged=True,
                 offlineWheelCacheUnchanged=True, disposableCopiesRemoved=True,
                 solutionPatchSha256=sha(patches["solution.patch"]), finishedAt=now())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    protected = (args.inputs.resolve(), args.runtime.resolve(), Path("/Users/recorder").resolve())
    require(not args.output.is_symlink() and not any(output == path or path in output.parents for path in protected), "Output must stay outside source/runtime/Recorder inputs")
    proof = {"version": 1, "task": NEUTRAL, "referenceKind": "AI-prepared guided internal Bootcamp walkthrough",
             "startedAt": now(), "sourceCommit": COMMIT, "goalSha256": GOAL_SHA, "checks": [],
             "sourceInputsUnchanged": False, "recorderExecuted": False, "recordingWorkspaceModified": False,
             "externalApprovalClaimed": False, "unaidedTransferCreditClaimed": False,
             "paidWalkthroughPermissionVerified": False}
    status = 0
    try:
        execute(args, proof)
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        proof.update(status="HOLD", error=str(error), finishedAt=now())
        status = 1
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(proof, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"task": NEUTRAL, "status": proof["status"], "checks": len(proof["checks"]), "proof": str(output), "error": proof.get("error")}))
    return status


if __name__ == "__main__":
    raise SystemExit(main())
