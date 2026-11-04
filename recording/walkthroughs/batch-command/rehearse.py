#!/usr/bin/env python3
"""Verify the prepared Batch reference in disposable copies, never Recorder."""
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
NEUTRAL = "batch-command"
SOURCE_COMMIT = "ac4aaa7d95fd07d3bdc58aa88128d24e533ec4c2"
GOAL_SHA256 = "a519473d08c3e12ec135b069285a123814414356e2bef0bc27c4a37d8792d717"
def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def inventory(folder):
    require(folder.is_dir() and not folder.is_symlink(), "Expected a plain input directory")
    files = {}
    for path in sorted(folder.rglob("*")):
        require(not path.is_symlink(), "Input symlinks require review")
        if path.is_dir():
            continue
        require(path.is_file(), "Input special files require review")
        files[path.relative_to(folder).as_posix()] = {
            "sha256": sha(path.read_bytes()), "mode": stat.S_IMODE(path.stat().st_mode)}
    return files


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def run_check(proof, name, argv, cwd=None, env=None):
    record = {"name": name, "command": [str(item) for item in argv],
              "cwd": str(cwd) if cwd else None, "startedAt": utc_now()}
    result = subprocess.run(record["command"], cwd=cwd, env=env, text=True,
                            capture_output=True, timeout=180)
    record.update(exitCode=result.returncode, stdout=result.stdout, stderr=result.stderr,
                  finishedAt=utc_now())
    proof["checks"].append(record)
    return record


def apply_patch(proof, work, name, env):
    patch = HERE / name
    require(patch.is_file() and not patch.is_symlink(), "Prepared patch is missing or unsafe")
    checked = run_check(proof, name + " check", ["git", "apply", "--check", str(patch)], work, env)
    require(checked["exitCode"] == 0, name + " does not match the pinned disposable source")
    applied = run_check(proof, name + " apply", ["git", "apply", str(patch)], work, env)
    require(applied["exitCode"] == 0, name + " could not be applied in its disposable copy")


def execute(args, proof):
    require(sys.version_info[:3] == (3, 12, 7), "Reviewed Python 3.12.7 is required")
    require(not args.inputs.is_symlink() and not args.runtime.is_symlink(), "Input roots must be plain directories")
    inputs, runtime = args.inputs.resolve(), args.runtime.resolve()
    spec = importlib.util.spec_from_file_location("TaskWorkRegistry", runtime / "TaskWorkRegistry.py")
    api = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(api)
    registry = api.load_json(runtime / "task-registry.json")
    tasks = api.validate_registry(registry)
    projects = api.validate_manifest(api.load_json(runtime / "runtime-manifest.json"), registry)
    task = tasks[NEUTRAL]
    project = next(item for item in projects if item["neutral"] == NEUTRAL)
    require(task["commit"] == SOURCE_COMMIT and task["goalSha256"] == GOAL_SHA256,
            "Reference does not cover this source/Goal revision")
    require(task["sourceRepo"] == "https://github.com/KyPython/python-exception-propagation"
            and task["id"] == "BOOTCAMP-3F38621E0A7A81498DD1C3E0EF4BFF3D"
            and task["workflowLane"] == "bootcamp" and task["goalKind"] == "candidate",
            "Reference belongs to another task or approval lane")
    require(task["dependencyProfile"] == "python-pytest"
            and task["dependencyVersions"] == {"pytest": "8.3.5"}, "Reviewed dependency recipe changed")
    goal_path = runtime / task["goalFile"]
    goal = api.verify_goal(task, goal_path)
    source = inputs / NEUTRAL
    before = inventory(source)
    require(before == project["files"], "Starter bytes/modes differ from manifest")
    wheels = runtime / "wheels"
    wheels_before = inventory(wheels)
    require(wheels_before, "Prepared offline wheel cache is empty")
    proof.update(taskId=task["id"], sourceRepo=task["sourceRepo"], sourceCommit=task["commit"],
                 goalSha256=sha(goal), exactCandidateGoal=task["candidateGoal"],
                 sourceFiles=len(before), sourceFileInventory=before,
                 pythonVersion=sys.version.split()[0], pythonExecutable=sys.executable,
                 patchSha256={name: sha((HERE / name).read_bytes())
                              for name in ("tests.patch", "repair.patch", "solution.patch")})
    require((HERE / "solution.patch").read_bytes()
            == (HERE / "tests.patch").read_bytes() + (HERE / "repair.patch").read_bytes(),
            "Combined patch disagrees with staged reference")
    temporary_root = Path(tempfile.gettempdir()).resolve()
    require(not any(temporary_root == p or p in temporary_root.parents for p in (inputs, runtime)),
            "Disposable workspace cannot be under protected roots")
    env = os.environ.copy()
    for key in ("PYTHONHOME", "PYTHONPATH", "VIRTUAL_ENV", "CONDA_PREFIX", "CONDA_DEFAULT_ENV",
                "PYTEST_ADDOPTS", "PYTEST_PLUGINS"):
        env.pop(key, None)
    env.update(PYTHONDONTWRITEBYTECODE="1", PIP_NO_INDEX="1", PIP_NO_CACHE_DIR="1",
               PIP_DISABLE_PIP_VERSION_CHECK="1", PYTEST_DISABLE_PLUGIN_AUTOLOAD="1")
    with tempfile.TemporaryDirectory(prefix="batch-reference-", dir=temporary_root) as directory:
        temporary = Path(directory)
        work = temporary / NEUTRAL
        shutil.copytree(source, work)
        created = run_check(proof, "Create disposable venv", [sys.executable, "-I", "-m", "venv", work / ".venv"], env=env)
        require(created["exitCode"] == 0, "Disposable venv failed")
        python = work / ".venv/bin/python"
        installed = run_check(proof, "Install pinned pytest offline", [python, "-I", "-m", "pip", "install", "--no-index",
                             "--no-cache-dir", "--find-links", wheels, "-r", task["requirementsFile"]], work, env)
        require(installed["exitCode"] == 0, "Offline install failed")
        version = run_check(proof, "Verify pytest pin", [python, "-I", "-c", "import pytest; print(pytest.__version__)"], work, env)
        require(version["exitCode"] == 0 and version["stdout"].strip() == "8.3.5", "Wrong pytest version")
        env["PYTHONPATH"] = "src"
        baseline = run_check(proof, "Unchanged ordinary suite", [python, "-m", "pytest"], work, env)
        require(baseline["exitCode"] == 0 and re.search(r"\b2 passed\b", baseline["stdout"]), "Expected two-test baseline")
        production = work / "src/batch_command/command.py"
        production_before = production.read_bytes()
        apply_patch(proof, work, "tests.patch", env)
        strengthened = (work / "tests/test_contract.py").read_bytes()
        require(production.read_bytes() == production_before, "Tests-only stage changed production")
        red = run_check(proof, "Strengthened suite before repair", [python, "-m", "pytest"], work, env)
        failures = set(re.findall(r"^FAILED (\S+)(?:\s|$)", red["stdout"], re.M))
        expected_failures = {
            "tests/test_contract.py::test_failed_item_is_reported_once_and_never_processed[unmatched]",
            "tests/test_contract.py::test_failed_item_is_reported_once_and_never_processed[sibling]",
            "tests/test_contract.py::test_original_deterministic_fixture",
            "tests/test_contract.py::test_other_child_exception_fails_item_and_batch_continues",
            "tests/test_contract.py::test_wrapped_exception_keeps_cause_cleans_up_and_skips_after_call[RuntimeError]",
            "tests/test_contract.py::test_repeated_mixed_reports_are_identical",
        }
        expected_failures.update("tests/test_contract.py::test_failure_semantics_do_not_depend_on_input_order[order" + str(i) + "]" for i in range(6))
        require(red["exitCode"] == 1 and failures == expected_failures
                and re.search(r"\b12 failed, 7 passed\b", red["stdout"]),
                "Expected only the twelve seeded contract failures")
        apply_patch(proof, work, "repair.patch", env)
        require((work / "tests/test_contract.py").read_bytes() == strengthened, "Repair changed tests")
        expected_production = production_before.replace(b"except ChildOperationError as error:", b"except Exception as error:", 1).replace(
            b"        finally:\n            processed.append", b"        else:\n            processed.append", 1)
        require(production.read_bytes() == expected_production, "Repair exceeds the planned two handling changes")
        for repeat in (1, 2, 3):
            green = run_check(proof, "Same strengthened suite after repair run " + str(repeat), [python, "-m", "pytest"], work, env)
            require(green["exitCode"] == 0 and re.search(r"\b19 passed\b", green["stdout"]), "Full contract suite did not pass")
        sample = "from batch_command import ItemSpec, run_batch; print(run_batch((ItemSpec('alpha', 'ok'), ItemSpec('bravo', 'unmatched'), ItemSpec('charlie', 'sibling'))))"
        first = run_check(proof, "Deterministic mixed report", [python, "-c", sample], work, env)
        second = run_check(proof, "Repeat deterministic mixed report", [python, "-c", sample], work, env)
        require(first["exitCode"] == second["exitCode"] == 0 and first["stdout"] == second["stdout"], "Report bytes differ")
        expected_report = "BatchReport(processed=('alpha',), failures=('bravo', 'charlie'), events=('open:alpha', 'execute:alpha', 'cleanup:alpha', 'processed:alpha', 'open:bravo', 'execute:bravo', 'cleanup:bravo', 'failed:bravo', 'open:charlie', 'execute:charlie', 'cleanup:charlie', 'failed:charlie'))\n"
        require(first["stdout"] == expected_report, "Report violates independently specified expected events")
        combined = temporary / "combined-patch-check"
        shutil.copytree(source, combined)
        apply_patch(proof, combined, "solution.patch", env)
        require(all((combined / name).read_bytes() == (work / name).read_bytes() for name in list(before) + ["tests/test_contract.py"]),
                "Combined patch differs from staged repair")
        proof.update(weakSuiteGreen=True, strengthenedSuiteRed=True, strengthenedFailureIds=sorted(failures),
                     sameStrengthenedTestsAfterRepair=True, strengthenedSuiteGreen=True,
                     strengthenedTestsSha256=sha(strengthened), repairedProductionSha256=sha(production.read_bytes()),
                     repeatedSuiteRuns=3, repeatedReportBytesIdentical=True,
                     combinedPatchMatchesStagedRepair=True, disposableCopiesRemoved=True,
                     afterCallPropagationVerified=True, cleanupExactlyOnceVerified=True,
                     ordinaryAndHandledPathsPreserved=True, processControlSignalsPreserved=True)
    require(inventory(source) == before and goal_path.read_bytes() == goal
            and inventory(wheels) == wheels_before, "Protected source/Goal/offline cache changed")
    proof.update(status="PASS", sourceInputsUnchanged=True, offlineWheelCacheUnchanged=True,
                 solutionPatchSha256=sha((HERE / "solution.patch").read_bytes()),
                 recorderExecuted=False, recordingWorkspaceModified=False, finishedAt=utc_now())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    protected = (args.inputs.resolve(), args.runtime.resolve(), Path("/Users/recorder").resolve())
    require(not args.output.is_symlink() and not any(output == p or p in output.parents for p in protected),
            "Proof output must be outside source/runtime/Recorder inputs")
    proof = {"version": 1, "task": NEUTRAL, "referenceKind": "AI-prepared guided Bootcamp repair and test walkthrough",
             "startedAt": utc_now(), "checks": [], "sourceCommit": SOURCE_COMMIT, "goalSha256": GOAL_SHA256,
             "sourceInputsUnchanged": False, "recorderExecuted": False, "recordingWorkspaceModified": False,
             "practiceClassification": "guided rehearsal; no unaided mastery, Odin approval or paid eligibility claimed"}
    exit_code = 0
    try:
        execute(args, proof)
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        proof.update(status="HOLD", error=str(error), finishedAt=utc_now())
        exit_code = 1
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(proof, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"status": proof["status"], "task": NEUTRAL,
                      "checks": len(proof["checks"]), "proof": str(output), "error": proof.get("error")}))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
