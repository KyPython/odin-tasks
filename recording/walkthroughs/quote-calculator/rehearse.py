#!/usr/bin/env python3
"""Verify the prepared Quote reference in disposable copies, never Recorder."""
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
NEUTRAL = "quote-calculator"
SOURCE_COMMIT = "c5986e93719cfd4b08a57104576c04a78d1f16ee"
GOAL_SHA256 = "ad882a58279d4809c1a4c036554a3400509b50c46bbb58e41f9665d54a30b135"
EXPECTED_FAILURES = {
    "tests/test_calculator.py::test_volume_order_receives_discount[at-threshold]",
    "tests/test_calculator.py::test_tax_is_included_in_total",
    "tests/test_calculator.py::test_tax_rate_endpoints_are_allowed[one-rate]",
}
EXAMPLES = (
    "from decimal import Decimal; from quote_calculator import calculate_quote; "
    "print(calculate_quote(Decimal('8.00'), 10, Decimal('0.05'))); "
    "print(calculate_quote(Decimal('20.00'), 12, Decimal('0.075')))"
)


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
    require(sys.version_info[:3] == (3, 12, 7), "Run this reference with reviewed Python 3.12.7")
    require(not args.inputs.is_symlink() and not args.runtime.is_symlink(), "Input roots must not be symlinks")
    inputs, runtime = args.inputs.resolve(), args.runtime.resolve()
    validator = runtime / "TaskWorkRegistry.py"
    require(validator.is_file() and not validator.is_symlink(), "The reviewed registry validator is required")
    spec = importlib.util.spec_from_file_location("TaskWorkRegistry", validator)
    registry_api = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(registry_api)
    registry = registry_api.load_json(runtime / "task-registry.json")
    manifest = registry_api.load_json(runtime / "runtime-manifest.json")
    tasks = registry_api.validate_registry(registry)
    projects = registry_api.validate_manifest(manifest, registry)
    task = tasks[NEUTRAL]
    project = next(item for item in projects if item["neutral"] == NEUTRAL)
    require(task["commit"] == SOURCE_COMMIT and task["goalSha256"] == GOAL_SHA256,
            "Reference does not cover this source/Goal revision")
    require(task["sourceRepo"] == "https://github.com/KyPython/vacuous-test-suite-audit"
            and task["id"] == "ODIN-5959D60FB16547A0A846BB836D8D0C3F", "Reference belongs to another task")
    require(task["dependencyProfile"] == "python-pytest"
            and task["dependencyVersions"] == {"pytest": "8.3.5"}, "Reviewed pytest recipe changed")
    goal_path = runtime / task["goalFile"]
    goal = registry_api.verify_goal(task, goal_path)
    source = inputs / NEUTRAL
    before = inventory(source)
    require(before == project["files"], "Starter bytes, modes or file inventory differ from the pinned manifest")
    wheels = runtime / "wheels"
    wheels_before = inventory(wheels)
    require(wheels_before, "Prepared offline wheel cache is empty")
    proof.update(taskId=task["id"], sourceRepo=task["sourceRepo"], sourceCommit=task["commit"],
                 goalSha256=sha(goal), exactApprovedGoal=task["approvedGoal"],
                 sourceFiles=len(before), sourceFileInventory=before,
                 pythonVersion=sys.version.split()[0], pythonExecutable=sys.executable,
                 patchSha256={name: sha((HERE / name).read_bytes())
                              for name in ("tests.patch", "repair.patch", "solution.patch")})
    require((HERE / "solution.patch").read_bytes()
            == (HERE / "tests.patch").read_bytes() + (HERE / "repair.patch").read_bytes(),
            "Combined patch disagrees with the staged reference")
    temporary_root = Path(tempfile.gettempdir()).resolve()
    require(not any(temporary_root == p or p in temporary_root.parents for p in (inputs, runtime)),
            "Disposable workspace cannot be under protected input/runtime roots")
    env = os.environ.copy()
    for key in ("PYTHONHOME", "PYTHONPATH", "VIRTUAL_ENV", "CONDA_PREFIX", "CONDA_DEFAULT_ENV",
                "PYTEST_ADDOPTS", "PYTEST_PLUGINS"):
        env.pop(key, None)
    env.update(PYTHONDONTWRITEBYTECODE="1", PIP_NO_INDEX="1", PIP_NO_CACHE_DIR="1",
               PIP_DISABLE_PIP_VERSION_CHECK="1", PYTEST_DISABLE_PLUGIN_AUTOLOAD="1")
    with tempfile.TemporaryDirectory(prefix="quote-reference-", dir=temporary_root) as directory:
        temporary = Path(directory)
        work = temporary / NEUTRAL
        shutil.copytree(source, work)
        venv = run_check(proof, "Create disposable venv", [sys.executable, "-I", "-m", "venv", str(work / ".venv")], env=env)
        require(venv["exitCode"] == 0, "Disposable virtual environment failed")
        python = work / ".venv/bin/python"
        install = run_check(proof, "Install pinned pytest offline", [python, "-I", "-m", "pip", "install", "--no-index",
                            "--no-cache-dir", "--find-links", wheels, "-r", task["requirementsFile"]], work, env)
        require(install["exitCode"] == 0, "Offline pinned pytest installation failed")
        version = run_check(proof, "Verify pytest pin", [python, "-I", "-c", "import pytest; print(pytest.__version__)"], work, env)
        require(version["exitCode"] == 0 and version["stdout"].strip() == "8.3.5", "Wrong pytest version")
        proof["pytestVersion"] = version["stdout"].strip()
        weak = run_check(proof, "Weak unchanged suite", [python, "-m", "pytest", "-q"], work, env)
        require(weak["exitCode"] == 0 and re.search(r"\b8 passed\b", weak["stdout"]), "Expected unchanged eight-test green baseline")
        example_env = {**env, "PYTHONPATH": "src"}
        defective = run_check(proof, "Defective itemized examples", [python, "-c", EXAMPLES], work, example_env)
        require(defective["exitCode"] == 0, "Defective example collection failed")
        production = work / "src/quote_calculator/calculator.py"
        production_before = production.read_bytes()
        apply_patch(proof, work, "tests.patch", env)
        tests_before = (work / "tests/test_calculator.py").read_bytes()
        require(production.read_bytes() == production_before, "Tests-only stage changed production")
        red = run_check(proof, "Strengthened suite before repair", [python, "-m", "pytest", "-q"], work, env)
        failures = set(re.findall(r"^FAILED (\S+)(?:\s|$)", red["stdout"], re.M))
        require(red["exitCode"] == 1 and failures == EXPECTED_FAILURES
                and re.search(r"\b3 failed, 14 passed\b", red["stdout"]),
                "Strengthened suite must fail only on the three wrong discounted-tax behaviors")
        apply_patch(proof, work, "repair.patch", env)
        require((work / "tests/test_calculator.py").read_bytes() == tests_before, "Repair changed the strengthened tests")
        require(production.read_bytes() == production_before.replace(
            b"    tax = subtotal * tax_rate\n", b"    tax = (subtotal - discount) * tax_rate\n", 1),
            "Production repair is not the planned one-line discounted-tax calculation")
        green = run_check(proof, "Same strengthened suite after repair", [python, "-m", "pytest", "-q"], work, env)
        require(green["exitCode"] == 0 and re.search(r"\b17 passed\b", green["stdout"]), "Strengthened suite did not pass after repair")
        boundary = run_check(proof, "Contract boundary regressions", [python, "-m", "pytest", "-q", "-k",
                             "volume_order or amounts_have_cent_precision or invalid_inputs or tax_rate_endpoints or zero_price"], work, env)
        require(boundary["exitCode"] == 0 and re.search(r"\b15 passed, 2 deselected\b", boundary["stdout"]), "Boundary regression checks failed")
        repaired = run_check(proof, "Repaired itemized examples", [python, "-c", EXAMPLES], work, example_env)
        repeated = run_check(proof, "Repeat repaired itemized examples", [python, "-c", EXAMPLES], work, example_env)
        require(repaired["exitCode"] == repeated["exitCode"] == 0
                and repaired["stdout"] == repeated["stdout"], "Repaired examples are not repeatable")
        combined = temporary / "combined-patch-check"
        shutil.copytree(source, combined)
        apply_patch(proof, combined, "solution.patch", env)
        require(all((combined / name).read_bytes() == (work / name).read_bytes() for name in before),
                "Combined patch differs from the staged red/green repair")
        proof.update(weakSuiteGreen=True, strengthenedSuiteRed=True, strengthenedFailureIds=sorted(failures),
                     sameStrengthenedTestsAfterRepair=True, strengthenedSuiteGreen=True,
                     strengthenedTestsSha256=sha(tests_before), repairedProductionSha256=sha(production.read_bytes()),
                     boundaryRegressionChecksPassed=True, repeatedExampleBytesIdentical=True,
                     combinedPatchMatchesStagedRepair=True, disposableCopiesRemoved=True)
    require(inventory(source) == before and goal_path.read_bytes() == goal
            and inventory(wheels) == wheels_before, "Protected source/Goal/offline cache changed")
    proof.update(status="PASS", sourceInputsUnchanged=True, offlineWheelCacheUnchanged=True,
                 solutionPatchSha256=sha((Path(__file__).resolve().parent / "solution.patch").read_bytes()),
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
    proof = {"version": 1, "task": NEUTRAL, "referenceKind": "AI-prepared worked repair and test walkthrough",
             "startedAt": utc_now(), "checks": [], "sourceCommit": SOURCE_COMMIT, "goalSha256": GOAL_SHA256,
             "sourceInputsUnchanged": False, "recorderExecuted": False, "recordingWorkspaceModified": False,
             "paidEligibility": "UNVERIFIED for a fully AI-written repair/test script; no external permission claimed"}
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
