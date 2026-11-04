"""Bounded built-in toolchain and sequential generated-file contracts."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import subprocess
import sys
import unittest
from unittest.mock import patch

from test_task_registration import register, inputs, git
import build_preparation as builder
from test_reusable_preparation import TASKS, STDLIB, setup
from TaskWorkRegistry import validate_registry


def task(profile="python-stdlib"):
    value = copy.deepcopy(TASKS[STDLIB[0]["neutral"]])
    value.update(dependencyProfile=profile, dependencyVersions={}, dependencyRoots=[],
                 baseline=[{"argv": ["{python}", "-m", "unittest"], "allowedExitCodes": [0]}])
    return value


def generated_task():
    value = task()
    value["baseline"] = [
        {"argv": ["{python}", "-m", "infra.synth", "--output", "build/template.json"],
         "generatedFiles": ["build/template.json"], "allowedExitCodes": [0]},
        {"argv": ["{python}", "-m", "policy.validate", "build/template.json"], "allowedExitCodes": [0]},
    ]
    return value


def source(parent):
    root = Path(parent) / "source"
    (root / "infra").mkdir(parents=True)
    (root / "infra/synth.py").write_text("# Synthetic local module fixture\n")
    (root / "fixtures").mkdir()
    (root / "fixtures/input.json").write_text("{}\n")
    return root


class BaselineAdapterContracts(unittest.TestCase):
    def test_declared_module_output_is_available_only_to_later_checks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = source(directory)
            value = generated_task()
            before = register.inventory(root)
            validate_registry({"version": 1, "tasks": [value]})
            register.verify_recipe(value, root)
            self.assertEqual(register.inventory(root), before)
            self.assertFalse((root / "build/template.json").exists())
            value["baseline"].reverse()
            with self.assertRaisesRegex(ValueError, "undeclared generated"):
                register.verify_recipe(value, root)

    def test_json_source_argument_is_not_mistaken_for_generated_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = source(directory)
            value = task()
            value["baseline"] = [{"argv": ["{python}", "-m", "json.tool", "fixtures/input.json"]}]
            register.verify_recipe(value, root)
            value["baseline"][0]["argv"][-1] = "build/missing.json"
            with self.assertRaises(ValueError):
                register.verify_recipe(value, root)
            value = generated_task()
            (root / "build").mkdir()
            (root / "build/template.json").write_text('{"existing":"source"}\n')
            with self.assertRaisesRegex(ValueError, "replace starter source"):
                register.verify_recipe(value, root)
            self.assertEqual((root / "build/template.json").read_text(), '{"existing":"source"}\n')

    def test_undeclared_traversing_external_or_inconsistent_output_is_refused(self):
        invalid = []
        value = generated_task()
        value["baseline"][0].pop("generatedFiles")
        invalid.append(value)
        for path in ("../outside.json", "/private/tmp/outside.json", "build/../source.json", "node_modules/out.json", "build/output.py"):
            value = generated_task()
            value["baseline"][0]["generatedFiles"] = [path]
            value["baseline"][0]["argv"][-1] = path
            invalid.append(value)
        for argv in (["sh", "script.sh", "--output", "build/template.json"],
                     ["{python}", "-m", "infra.synth", "--output", "build/other.json"],
                     ["{python}", "-c", "pass", "--output", "build/template.json"]):
            value = generated_task()
            value["baseline"][0]["argv"] = argv
            invalid.append(value)
        for value in invalid:
            with self.subTest(argv=value["baseline"][0]["argv"]), self.assertRaises(ValueError):
                validate_registry({"version": 1, "tasks": [value]})

    def test_generated_output_requires_real_module_and_one_writer(self):
        with tempfile.TemporaryDirectory() as directory:
            root = source(directory)
            value = generated_task()
            value["baseline"].insert(1, copy.deepcopy(value["baseline"][0]))
            with self.assertRaisesRegex(ValueError, "competing writers"):
                register.verify_recipe(value, root)
            value = generated_task()
            (root / "infra/synth.py").unlink()
            with self.assertRaisesRegex(ValueError, "real local source module"):
                register.verify_recipe(value, root)

    def test_actual_disposable_generator_output_is_json_hash_bound_and_preserves_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = source(directory)
            (root / "infra/synth.py").write_text(
                "import argparse,json\nfrom pathlib import Path\n"
                "p=argparse.ArgumentParser();p.add_argument('--output');a=p.parse_args()\n"
                "out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)\n"
                "out.write_text(json.dumps({'fixture':'local-only'},sort_keys=True)+'\\n')\n")
            value = generated_task()
            register.verify_recipe(value, root)
            before = register.inventory(root)
            result = subprocess.run([sys.executable, *value["baseline"][0]["argv"][1:]],
                                    cwd=root, capture_output=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            output = root / "build/template.json"
            records = builder.generated_output_records(root, value["baseline"][0])
            self.assertEqual(records["build/template.json"]["sha256"], hashlib.sha256(output.read_bytes()).hexdigest())
            for relative, identity in before.items():
                self.assertEqual(register.inventory(root)[relative], identity)
            output.write_text("invalid JSON\n")
            with self.assertRaises(json.JSONDecodeError):
                builder.generated_output_records(root, value["baseline"][0])
            output.unlink()
            output.symlink_to(root / "fixtures/input.json")
            with self.assertRaises(AssertionError):
                builder.generated_output_records(root, value["baseline"][0])
            output.unlink()
            with self.assertRaises(AssertionError):
                builder.generated_output_records(root, value["baseline"][0])

    def test_node_builtins_require_exact_public_version_and_no_packages(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            value = task("node-stdlib")
            value.update(dependencyVersions={"node": "22.22.0"},
                         baseline=[{"argv": ["{node}", "--test"], "allowedExitCodes": [0]}])
            (root / "package.json").write_text(json.dumps({"type": "module", "engines": {"node": ">=20"}}))
            validate_registry({"version": 1, "tasks": [value]})
            register.verify_recipe(value, root)
            for changed in ({"node": "20.0.0"}, {"node": "22.22.0", "npm": "10"}):
                invalid = {**value, "dependencyVersions": changed}
                with self.assertRaises(ValueError):
                    validate_registry({"version": 1, "tasks": [invalid]})
            for field in ("dependencies", "devDependencies", "optionalDependencies", "peerDependencies"):
                (root / "package.json").write_text(json.dumps({field: {"hidden-package": "1.0.0"}}))
                with self.subTest(field=field), self.assertRaisesRegex(ValueError, "package dependencies"):
                    register.verify_recipe(value, root)
            for profile, executable in (("python-stdlib", "{node}"), ("node-stdlib", "{python}")):
                invalid = task(profile)
                invalid["dependencyVersions"] = {"node": "22.22.0"} if profile == "node-stdlib" else {}
                invalid["baseline"][0]["argv"][0] = executable
                with self.assertRaisesRegex(ValueError, "own reviewed profile"):
                    validate_registry({"version": 1, "tasks": [invalid]})

    def test_node_setup_checks_version_without_install_or_task_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            input_root = home / "inputs"
            project = copy.deepcopy(STDLIB[0])
            name = project["neutral"]
            import shutil
            from test_reusable_preparation import ROOT
            shutil.copytree(ROOT / "inputs" / name, input_root / name)
            work, cache = home / "work", home / "cache"
            work.mkdir()
            (cache / "receipts").mkdir(parents=True)
            value = copy.deepcopy(TASKS[name])
            value.update(dependencyProfile="node-stdlib", dependencyVersions={"node": "22.22.0"}, dependencyRoots=[])
            calls = []
            def run(argv, env, cwd=None):
                calls.append(argv)
                self.assertEqual(argv, [setup.PUBLIC_NODE, "--version"])
                return "v22.22.0"
            with patch.multiple(setup, INPUTS=input_root, WORK=work, CACHE_ROOT=cache,
                                CACHE=cache / "runtime", TASKS={name: value}), patch.object(setup, "run", side_effect=run):
                setup.prepare_project(project, {})
                setup.prepare_project(project, {})
                self.assertEqual(len(calls), 2)
                self.assertEqual(register.inventory(input_root / name), project["files"])
                self.assertEqual(register.inventory(work / name), project["files"])
                with patch.object(setup, "run", return_value="v20.0.0"), self.assertRaises(setup.StopSetup):
                    setup.prepare_project(project, {})

    def test_node_cli_plan_uses_real_git_files_without_running_the_task(self):
        with tempfile.TemporaryDirectory() as directory:
            args = inputs(Path(directory))
            (args.source_dir / "package.json").write_text('{"type":"module"}\n')
            (args.source_dir / "fixture.mjs").write_text("throw new Error('This fixture must not execute while planning');\n")
            git(args.source_dir, "add", "package.json", "fixture.mjs")
            git(args.source_dir, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-m", "Built-ins fixture")
            commit = git(args.source_dir, "rev-parse", "HEAD")
            recipe = json.loads(args.setup_json.read_text())
            recipe.update(dependencyVersions={"node": "22.22.0"}, dependencyRoots=[],
                          baseline=[{"argv": ["{node}", "fixture.mjs"], "allowedExitCodes": [0]}])
            args.setup_json.write_text(json.dumps(recipe))
            before = {p.relative_to(args.root).as_posix(): p.read_bytes() for p in args.root.rglob("*") if p.is_file()}
            result = subprocess.run([sys.executable, "-B", str(Path(register.__file__).resolve()), "plan",
                "--root", str(args.root), "--page-json", str(args.page_json), "--source-repo", args.source_repo,
                "--commit", commit, "--neutral", args.neutral, "--profile", "node-stdlib",
                "--setup-json", str(args.setup_json), "--source-dir", str(args.source_dir)], capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["sourceFiles"], 4)
            self.assertEqual({p.relative_to(args.root).as_posix(): p.read_bytes() for p in args.root.rglob("*") if p.is_file()}, before)


if __name__ == "__main__":
    unittest.main()
