"""Observable preservation and incremental-registration contracts for setup tools."""

import copy
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime"))
import PrepareTaskWork as setup
import TaskWorkCloudSync as sync
from TaskWorkRegistry import load_json, validate_registry, validate_manifest, source_count, select_projects

REGISTRY = load_json(ROOT / "runtime/task-registry.json")
MANIFEST = load_json(ROOT / "runtime/runtime-manifest.json")
TASKS = validate_registry(REGISTRY)
PROJECTS = validate_manifest(MANIFEST, REGISTRY)
STDLIB = [project for project in PROJECTS if TASKS[project["neutral"]]["dependencyProfile"] == "python-stdlib"][:2]


def subset(projects):
    names = {project["neutral"] for project in projects}
    manifest = copy.deepcopy(MANIFEST)
    manifest["projects"] = copy.deepcopy(projects)
    registry = {"version": 1, "tasks": [copy.deepcopy(task) for task in REGISTRY["tasks"] if task["neutral"] in names]}
    return manifest, registry


def fixture(root, projects):
    manifest, registry = subset(projects)
    runtime = root / "TaskWorkRuntime"
    runtime.mkdir(parents=True)
    (root / "TaskWorkInputs").mkdir()
    for project in projects:
        shutil.copytree(ROOT / "inputs" / project["neutral"], root / "TaskWorkInputs" / project["neutral"])
        task = TASKS[project["neutral"]]
        goal = runtime / task["goalFile"]
        goal.parent.mkdir(exist_ok=True)
        shutil.copy2(ROOT / "runtime" / task["goalFile"], goal)
    (runtime / "runtime-manifest.json").write_text(json.dumps(manifest))
    (runtime / "task-registry.json").write_text(json.dumps(registry))
    return manifest, registry


class RegistryContracts(unittest.TestCase):
    def test_catalog_uses_variable_task_and_file_counts(self):
        for projects in ([STDLIB[0]], STDLIB, PROJECTS):
            manifest, registry = subset(projects)
            self.assertEqual(validate_manifest(manifest, registry), projects)
            self.assertEqual(source_count(manifest), sum(len(project["files"]) for project in projects))
            inventory = sync.source_inventory(manifest, registry)
            self.assertEqual({name for name, record in inventory.items() if record["kind"] == "file"},
                             {project["neutral"] + "/" + path for project in projects for path in project["files"]})

    def test_unknown_selection_preserves_catalog(self):
        prior = copy.deepcopy(PROJECTS)
        with self.assertRaises(ValueError):
            select_projects(PROJECTS, "unregistered-task")
        self.assertEqual(PROJECTS, prior)

    def test_duplicate_identity_and_unsupported_recipe_are_refused(self):
        duplicated = copy.deepcopy(REGISTRY)
        duplicated["tasks"].append(copy.deepcopy(duplicated["tasks"][0]))
        with self.assertRaises(ValueError):
            validate_registry(duplicated)
        unsupported = copy.deepcopy(REGISTRY)
        unsupported["tasks"][0]["dependencyProfile"] = "unreviewed-command"
        with self.assertRaises(ValueError):
            validate_registry(unsupported)
        private_environment = copy.deepcopy(REGISTRY)
        private_environment["tasks"][0]["baseline"][0]["env"] = {"PYTHONPATH": "/Users/ky/private"}
        with self.assertRaises(ValueError):
            validate_registry(private_environment)


class IncrementalSetupContracts(unittest.TestCase):
    def test_retry_is_identical_and_another_edited_attempt_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            inputs = home / "inputs"
            work = home / "Desktop/TaskWork"
            cache_root = home / "Library/Caches/TaskWork"
            cache = cache_root / "runtimes" / ("0" * 64)
            work.mkdir(parents=True)
            (cache_root / "receipts").mkdir(parents=True)
            for project in STDLIB:
                shutil.copytree(ROOT / "inputs" / project["neutral"], inputs / project["neutral"])
            with patch.multiple(setup, HOME=home, WORK=work, CACHE_ROOT=cache_root, CACHE=cache, INPUTS=inputs, TASKS=TASKS):
                first, second = STDLIB
                setup.prepare_project(first, {})
                edited = work / first["neutral"] / "README.md"
                edited.write_bytes(edited.read_bytes() + b"\nhuman work\n")
                preserved = edited.read_bytes()
                selected = select_projects(STDLIB, second["neutral"])
                self.assertEqual(selected, [second])
                result = setup.prepare_project(selected[0], {})
                receipt = cache_root / "receipts" / (second["neutral"] + ".json")
                prior = receipt.read_bytes()
                self.assertEqual(setup.prepare_project(second, {}), result)
                self.assertEqual(receipt.read_bytes(), prior)
                self.assertEqual(edited.read_bytes(), preserved)
                with self.assertRaises(setup.StopSetup):
                    setup.prepare_project(first, {})
                self.assertEqual(edited.read_bytes(), preserved)
                self.assertEqual(receipt.read_bytes(), prior)

    def test_cache_namespaces_reuse_only_the_selected_task_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "receipts").mkdir()
            older = root / "runtimes" / ("1" * 64)
            older.mkdir(parents=True)
            first, second = STDLIB
            (root / "receipts" / (first["neutral"] + ".json")).write_text(json.dumps({"runtimeCache": "runtimes/" + "1" * 64}))
            with patch.object(setup, "CACHE_ROOT", root):
                self.assertEqual(setup.runtime_cache(first, "2" * 64), (older, False))
                self.assertEqual(setup.runtime_cache(second, "2" * 64), (root / "runtimes" / ("2" * 64), True))


class IncrementalSyncContracts(unittest.TestCase):
    def receipt(self, shared):
        return {"verified": True, "synced": True, "sourceCommit": "0" * 40,
                "runId": "1", "runtime": str(shared / "TaskWorkRuntime"), "previousRuntime": None,
                "recorderExecuted": False}

    def test_actual_receipt_is_installed_with_new_runtime(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shared, staging = root / "shared", root / "staging"
            fixture(shared, [STDLIB[0]])
            fixture(staging, STDLIB)
            prior = sync.scan_tree(shared / "TaskWorkRuntime")
            receipt = self.receipt(shared)
            with patch.object(sync, "verify_contract", lambda *args: None):
                backup = sync.sync_runtime(staging, shared, "0" * 40, "1", receipt)
            durable = load_json(shared / "TaskWorkRuntime/cloud-sync-receipt.json")
            self.assertEqual(durable, {**receipt, "previousRuntime": str(backup)})
            self.assertEqual(sync.scan_tree(backup), prior)
            self.assertEqual((shared / "TaskWorkRuntime/cloud-sync-receipt.json").stat().st_mode & 0o777, 0o644)

    def test_receipt_write_failure_preserves_existing_runtime_and_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shared, staging = root / "shared", root / "staging"
            fixture(shared, [STDLIB[0]])
            fixture(staging, STDLIB)
            prior_inputs = sync.scan_tree(shared / "TaskWorkInputs")
            prior_runtime = sync.scan_tree(shared / "TaskWorkRuntime")
            with patch.object(sync, "verify_contract", lambda *args: None), patch.object(sync, "write_sync_receipt", side_effect=OSError("simulated receipt write failure")):
                with self.assertRaises(OSError):
                    sync.sync_runtime(staging, shared, "0" * 40, "1", self.receipt(shared))
            self.assertEqual(sync.scan_tree(shared / "TaskWorkInputs"), prior_inputs)
            self.assertEqual(sync.scan_tree(shared / "TaskWorkRuntime"), prior_runtime)
            self.assertTrue((staging / "TaskWorkInputs" / STDLIB[1]["neutral"]).is_dir())

    def test_new_task_is_accepted_without_changing_existing_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shared, staging = root / "shared", root / "staging"
            fixture(shared, [STDLIB[0]])
            fixture(staging, STDLIB)
            before = sync.scan_tree(shared / "TaskWorkInputs")
            manifest, _, current, _ = sync.source_contracts(staging, shared)
            self.assertEqual(len(manifest["projects"]), 2)
            self.assertEqual(len(current["projects"]), 1)
            self.assertEqual(sync.scan_tree(shared / "TaskWorkInputs"), before)
            changed = shared / "TaskWorkInputs" / STDLIB[0]["neutral"] / "README.md"
            changed.write_bytes(changed.read_bytes() + b"\nlocal work\n")
            preserved = changed.read_bytes()
            with self.assertRaises(sync.VerificationError):
                sync.source_contracts(staging, shared)
            self.assertEqual(changed.read_bytes(), preserved)

    def test_failed_runtime_install_rolls_back_task_additions(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shared, staging = root / "shared", root / "staging"
            fixture(shared, [STDLIB[0]])
            fixture(staging, STDLIB)
            before = sync.scan_tree(shared / "TaskWorkInputs")
            before_runtime = sync.scan_tree(shared / "TaskWorkRuntime")
            real_rename = sync.os.rename
            def fail_runtime(source, destination):
                if Path(source) == staging / "TaskWorkRuntime":
                    raise OSError("simulated installation failure")
                return real_rename(source, destination)
            with patch.object(sync, "verify_contract", lambda *args: None), patch.object(sync.os, "rename", fail_runtime):
                with self.assertRaises(OSError):
                    sync.sync_runtime(staging, shared, "0" * 40, "1", self.receipt(shared))
            self.assertEqual(sync.scan_tree(shared / "TaskWorkInputs"), before)
            self.assertEqual(sync.scan_tree(shared / "TaskWorkRuntime"), before_runtime)
            self.assertTrue((staging / "TaskWorkInputs" / STDLIB[1]["neutral"]).is_dir())


if __name__ == "__main__":
    unittest.main()
