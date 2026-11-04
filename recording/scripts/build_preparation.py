"""Build the unchanged recording kit on a real GitHub-hosted ARM Mac."""

import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import stat
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime"))
from TaskWorkRegistry import load_json, validate_registry, validate_manifest, source_count, verify_goal

MANIFEST = load_json(ROOT / "runtime/runtime-manifest.json")
REGISTRY = load_json(ROOT / "runtime/task-registry.json")
TASKS = validate_registry(REGISTRY)
PROJECTS = validate_manifest(MANIFEST, REGISTRY)
NAMES = set(TASKS)


def checksum(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def generated_output_records(folder, baseline):
    records = {}
    for relative in baseline.get("generatedFiles", []):
        path = folder / relative
        ancestor = path.parent
        while ancestor != folder:
            assert ancestor.is_dir() and not ancestor.is_symlink(), "Unsafe declared baseline output parent"
            ancestor = ancestor.parent
        assert path.is_file() and not path.is_symlink(), "Missing regular declared baseline output"
        json.loads(path.read_text())
        records[relative] = {"sha256": checksum(path), "mode": stat.S_IMODE(path.stat().st_mode)}
    return records


def source_check(base):
    assert {p.name for p in base.iterdir()} == NAMES, "Unexpected input projects"
    count = 0
    for project in MANIFEST["projects"]:
        folder = base / project["neutral"]
        expected = project["files"]
        actual = {}
        for item in folder.rglob("*"):
            assert not item.is_symlink(), f"Unexpected source symlink: {item}"
            if item.is_file():
                actual[item.relative_to(folder).as_posix()] = {
                    "sha256": checksum(item), "mode": stat.S_IMODE(item.stat().st_mode)
                }
        assert actual == expected, f"Source bytes/modes differ: {folder.name}"
        count += len(actual)
    assert count == source_count(MANIFEST)
    for task in TASKS.values():
        verify_goal(task, ROOT / "runtime" / task["goalFile"])
    return count


def run(command, environment, cwd=None, allowed=(0,), contains=None):
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    result = subprocess.run(command, cwd=cwd, env=environment, capture_output=True,
                            text=True, timeout=180)
    combined = result.stdout + result.stderr
    evidence = {"command": command, "startedAt": started, "exitCode": result.returncode,
                "stdout": result.stdout, "stderr": result.stderr}
    assert result.returncode in allowed, f"Unexpected exit: {evidence}"
    if contains:
        assert contains in combined, f"Expected baseline evidence absent: {evidence}"
    print(f"Verified: {' '.join(command)} (exit {result.returncode})", flush=True)
    return evidence


def records(base):
    result = {}
    for item in sorted(base.rglob("*")):
        relative = item.relative_to(base).as_posix()
        mode = stat.S_IMODE(item.lstat().st_mode)
        if item.is_symlink():
            result[relative] = {"kind": "symlink", "target": os.readlink(item), "mode": mode}
        elif item.is_dir():
            result[relative] = {"kind": "directory", "mode": mode}
        elif item.is_file():
            result[relative] = {"kind": "file", "sha256": checksum(item), "mode": mode}
        else:
            raise AssertionError(f"Unexpected special file: {item}")
    return result


def build(output):
    assert os.environ.get("GITHUB_ACTIONS") == "true", "Cloud builds require an actual Actions job"
    assert os.environ.get("GITHUB_REPOSITORY") == "KyPython/odin-recording-preparation"
    assert platform.system() == "Darwin" and platform.machine() == "arm64"
    assert sys.version.split()[0] == "3.12.7"
    assert not output.exists(), "Preserve any previous output instead of overwriting"
    input_count = source_check(ROOT / "inputs")
    output.mkdir(parents=True)
    shutil.copytree(ROOT / "inputs", output / "TaskWorkInputs")
    runtime = output / "TaskWorkRuntime"
    shutil.copytree(ROOT / "runtime", runtime)
    if (ROOT / "packs").is_dir():
        shutil.copytree(ROOT / "packs", runtime / "packs")
    if (ROOT / "scripts/recording_pack.py").is_file():
        shutil.copy2(ROOT / "scripts/recording_pack.py", runtime / "recording_pack.py")
    shutil.copy2(ROOT / "scripts/sync_worked_plans.py", runtime / "SyncTaskWorkPlans.py")
    process = runtime / "process"
    process.mkdir()
    for name in ("REUSABLE_TASK_PROCESS.md", "RECORDER-CODEX-PROMPT.txt", "TASK-IDEA-TO-RECORDING-PROMPT.txt",
                 "WORKED_PLAN_PROCESS.md", "RECORDING_REVIEW.md", "REVIEWER-PROMPT.txt",
                 "BOOTCAMP_LEARNING.md", "MORNING_PREPARATION.md", "INTERNAL_BOOTCAMP_ADMISSION.md"):
        shutil.copy2(ROOT / "docs" / name, process / name)
    for name in ("review", "learning"):
        shutil.copytree(ROOT / name, process / name)
    (process / "scripts").mkdir()
    for name in ("package_recording_review.py", "check_learning_map.py"):
        shutil.copy2(ROOT / "scripts" / name, process / "scripts" / name)
    # Keep the inspected cloud owners beside the guide for cross-account handoff.
    # These dated, redacted snapshots never replace a fresh connector read.
    cloud_process = process / "cloud"
    cloud_process.mkdir()
    for name in ("make-processes.json", "make-processes-receipt.json",
                 "companion-processes.json", "companion-processes-receipt.json", "capability-authority.json",
                 "private-source-bridge-receipt.json", "world-preparation-state.json",
                 "world-recovery-inventory.json", "world-preparation-notion-receipt.json"):
        shutil.copy2(ROOT / "cloud" / name, cloud_process / name)
    for name in ("corepack", "pnpm-store", "wheels", "bin"):
        (runtime / name).mkdir()
    for name, target in {"python3": "/usr/local/bin/python3", "node": "/opt/homebrew/bin/node",
                         "corepack": "/opt/homebrew/bin/corepack", "pnpm": "/opt/homebrew/bin/pnpm"}.items():
        (runtime / "bin" / name).symlink_to(target)
    corepack = str(Path(os.environ["COREPACK_EXECUTABLE"]).resolve())
    env = os.environ.copy()
    env["PATH"] = str(Path(os.environ["COREPACK_EXECUTABLE"]).parent) + os.pathsep + env["PATH"]
    env.update(COREPACK_HOME=str(runtime / "corepack"), COREPACK_ENABLE_DOWNLOAD_PROMPT="0",
               COREPACK_DEFAULT_TO_LATEST="0", COREPACK_ENABLE_AUTO_PIN="0",
               PYTHONDONTWRITEBYTECODE="1", PIP_DISABLE_PIP_VERSION_CHECK="1",
               TURBO_TELEMETRY_DISABLED="1")
    node_command = os.environ.get("NODE_EXECUTABLE") or shutil.which("node", path=env["PATH"])
    assert node_command, "The reviewed public Node runtime is required"
    node = str(Path(node_command).resolve(strict=True))
    versions = {"python": sys.version.split()[0]}
    checks = []
    for name, command, expected in [("node", [node, "--version"], "v22.22.0"),
                                     ("corepack", [corepack, "--version"], "0.34.0")]:
        check = run(command, env)
        checks.append(check)
        versions[name] = check["stdout"].strip()
        assert versions[name] == expected
    with tempfile.TemporaryDirectory(prefix="taskwork-check-", dir=os.environ["RUNNER_TEMP"]) as temporary:
        scratch = Path(temporary)
        shutil.copytree(ROOT / "inputs", scratch / "projects")
        projects = scratch / "projects"
        for project in PROJECTS:
            task = TASKS[project["neutral"]]
            folder = projects / project["neutral"]
            task_env = env.copy()
            profile = task["dependencyProfile"]
            if profile == "python-pytest":
                requirements = task["requirementsFile"]
                checks.append(run([sys.executable, "-m", "pip", "download", "--only-binary=:all:",
                                   "--dest", str(runtime / "wheels"), "-r", requirements], task_env, folder))
                checks.append(run([sys.executable, "-m", "venv", ".venv"], task_env, folder))
                checks.append(run([str(folder / ".venv/bin/python"), "-m", "pip", "install", "--no-index", "--find-links",
                                   str(runtime / "wheels"), "-r", requirements], task_env, folder))
                version_check = run([str(folder / ".venv/bin/python"), "-I", "-c", "import pytest; print(pytest.__version__)"], task_env, folder)
                checks.append(version_check)
                assert version_check["stdout"].strip() == task["dependencyVersions"]["pytest"]
            elif profile == "pnpm-workspace":
                check = run([corepack, "pnpm", "--version"], task_env, folder)
                checks.append(check)
                versions["pnpm"] = check["stdout"].strip()
                assert versions["pnpm"] == task["dependencyVersions"]["pnpm"]
                checks.append(run([corepack, "pnpm", "install", "--frozen-lockfile", "--store-dir",
                                   str(runtime / "pnpm-store")], task_env, folder))
                task_env["COREPACK_ENABLE_NETWORK"] = "0"
                version_check = run([corepack, "pnpm", "exec", "turbo", "--version"], task_env, folder)
                checks.append(version_check)
                assert version_check["stdout"].strip() == task["dependencyVersions"]["turbo"]
            if profile == "node-stdlib":
                assert versions["node"] == "v" + task["dependencyVersions"]["node"]
            substitutions = {"{python}": sys.executable, "{venvPython}": str(folder / ".venv/bin/python"),
                             "{corepack}": corepack, "{node}": node}
            for baseline in task["baseline"]:
                command = [substitutions.get(arg, arg) for arg in baseline["argv"]]
                baseline_env = {**task_env, **baseline.get("env", {})}
                observed = run(command, baseline_env, folder, allowed=tuple(baseline.get("allowedExitCodes", [0])),
                               contains=baseline.get("contains"))
                if baseline.get("env"):
                    observed["environmentOverrides"] = baseline["env"]
                if baseline.get("generatedFiles"):
                    observed["generatedFiles"] = generated_output_records(folder, baseline)
                checks.append(observed)
        for project in MANIFEST["projects"]:
            for relative, expected in project["files"].items():
                actual = projects / project["neutral"] / relative
                assert checksum(actual) == expected["sha256"]
                assert stat.S_IMODE(actual.stat().st_mode) == expected["mode"]
        offline = scratch / "offline"
        shutil.copytree(runtime / "corepack", offline / "corepack", symlinks=True)
        shutil.copytree(runtime / "pnpm-store", offline / "pnpm-store", symlinks=True)
        offline_env = env.copy()
        offline_env["COREPACK_HOME"] = str(offline / "corepack")
        offline_env["COREPACK_ENABLE_NETWORK"] = "0"
        for task in TASKS.values():
            if task["dependencyProfile"] == "pnpm-workspace":
                shutil.copytree(ROOT / "inputs" / task["neutral"], offline / task["neutral"])
                checks.append(run([corepack, "pnpm", "install", "--offline", "--frozen-lockfile",
                                   "--store-dir", str(offline / "pnpm-store")], offline_env,
                                   offline / task["neutral"], contains="downloaded 0"))
    assert source_check(output / "TaskWorkInputs") == input_count
    run_id = os.environ["GITHUB_RUN_ID"]
    repository = os.environ["GITHUB_REPOSITORY"]
    proof = {"version": 1, "repository": repository, "sourceCommit": os.environ["GITHUB_SHA"],
             "runId": run_id, "runAttempt": os.environ["GITHUB_RUN_ATTEMPT"],
             "runUrl": f"https://github.com/{repository}/actions/runs/{run_id}",
             "builtAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
             "platform": {"system": platform.system(), "machine": platform.machine(),
                          "version": platform.mac_ver()[0], "imageOS": os.environ.get("ImageOS"),
                          "imageVersion": os.environ.get("ImageVersion")},
             "toolVersions": versions, "sourceFiles": input_count,
             "starterCommits": {p["neutral"]: p["commit"] for p in MANIFEST["projects"]},
             "checks": checks, "repairsApplied": False, "recorderExecuted": False}
    proof_text = json.dumps(proof, indent=2) + "\n"
    (output / "cloud-proof.json").write_text(proof_text)
    (runtime / "cloud-proof.json").write_text(proof_text)
    (runtime / "SETUP.md").write_text(
        "# Cloud-built recording setup\n\n"
        "Sign directly into Recorder. Off-screen, use the installed reusable Codex prompt in process/ "
        "or run /Users/Shared/TaskWorkRuntime/Prepare-TaskWork.command --task <registered-neutral-name>. "
        "Wait for Setup checks passed, then open that task's .code-workspace file in ~/Desktop/TaskWork/. "
        "The helper checks only the selected task; another task's human edits are preserved. A selected "
        "task with edits is held for review instead of reset. Its per-task setup receipt is in "
        "~/Library/Caches/TaskWork/ready-receipts/. Use its matching -goal.txt opening document after comparing the "
        "Goal with the current task source. For Odin complete live TaskRecorder, Studio, Metadata and privacy "
        "checks before capture. Preserve previous work if the helper stops.\n\n"
        f"Cloud build: {proof['runUrl']}\nSource commit: {proof['sourceCommit']}\n"
        f"All {input_count} registered starter files remain unchanged. Offline dependencies and the registered baseline contracts passed "
        "on an ARM Mac; expected incomplete-starter failures remain recorded as failures. Time-dependent outcomes are "
        "observations. No human task repair was performed. The helper has not executed as Recorder; "
        "its live recording readiness remains pending.\n")
    (output / "bundle-manifest.json").write_text(json.dumps(
        {"version": 1, "files": records(output)}, indent=2) + "\n")
    print(proof["runUrl"], flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    parser.add_argument("--validate-sources", action="store_true")
    args = parser.parse_args()
    if args.validate_sources:
        print(f"Validated {source_check(ROOT / 'inputs')} unchanged source files")
    else:
        assert args.output is not None, "--output is required"
        build(args.output.resolve())
