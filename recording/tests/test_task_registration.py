"""Real Git fixture imports prove additive registration and preservation."""
import argparse
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import register_task as register
import recording_pack as publisher
from test_reusable_preparation import fixture, STDLIB


def git(repository, *args):
    return subprocess.check_output(["git", *args], cwd=repository, stderr=subprocess.DEVNULL).decode().strip()


def inputs(root):
    project_root = root / "preparation"
    fixture(project_root, [STDLIB[0]])
    (project_root / "TaskWorkRuntime").rename(project_root / "runtime")
    (project_root / "TaskWorkInputs").rename(project_root / "inputs")
    source = root / "source"
    source.mkdir()
    (source / "README.md").write_text("Synthetic registration fixture; no task solution.\n")
    (source / "demo.py").write_text("print('fixture')\n")
    git(source, "init")
    git(source, "remote", "add", "origin", "https://github.com/KyPython/registration-fixture")
    git(source, "add", "README.md", "demo.py")
    git(source, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-m", "Fixture source")
    commit = git(source, "rev-parse", "HEAD")
    goal = "As a software engineer, review this synthetic fixture during the recorded task."
    studio = "https://studio.mercor.com/annotator/tasks/task_fixture"
    page = {"metadata": {"type": "page"}, "title": "Fixture task",
            "url": "https://app.notion.com/p/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "page_last_edited_at": "2026-10-07T00:00:00Z",
            "text": "<properties>\n" + json.dumps({"Approval ID": "ODIN-" + "A" * 32,
                     "Approved Goal": goal, "Odin Goal": goal,
                     "Spec PR": "https://github.com/KyPython/ai-governance/pull/999",
                     "Spec Path": "specs/odin-tasks/fixture", "Build Issue": "https://github.com/KyPython/ai-governance/issues/999"}) +
                    "\n</properties>\n<content>\nFixture source " + studio + "\n</content>"}
    page_path = root / "page.json"
    page_path.write_text(json.dumps(page))
    setup = root / "setup.json"
    setup.write_text(json.dumps({"lane": "software", "studioTaskUrl": studio,
                                "dependencyVersions": {}, "dependencyRoots": [],
                                "baseline": [{"argv": ["{python}", "demo.py"], "allowedExitCodes": [0], "contains": "fixture"}]}))
    return argparse.Namespace(command="register", root=project_root, page_json=page_path,
                              source_repo="https://github.com/KyPython/registration-fixture", commit=commit,
                              neutral="new-recording-fixture", profile="python-stdlib", setup_json=setup, source_dir=source)


def native_blank_bootcamp(args):
    """Mirror the real native empty-page frame, retaining its complete ledger."""
    page = json.loads(args.page_json.read_text())
    properties = register.snapshot(page)["properties"]
    properties.update({"Approval ID": "", "Approved Goal": "", "Lane": "Dual-candidate",
                       "Stage": "Candidate", "Fit Gate": "PASS", "Bootcamp Status": "World building",
                       "Spec PR": "", "Spec Path": "specs/odin-bootcamp/fixture",
                       "Starter Repository": args.source_repo, "Starter Commit": args.commit,
                       "Environment Review Gate": "__YES__", "No-Solution-Leak Gate": "__YES__",
                       "Local Starter Gate": "__NO__", "Pre-Record Gate": "__NO__",
                       "Recording QA Gate": "__NO__", "Submission Gate": "__NO__",
                       "Workflow Checklist Gate": "PENDING"})
    page["text"] = ('<page url="' + page["url"] + '">\n<ancestor-path>\n'
                    '<parent-data-source url="collection://bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb" name="Fixture queue"/>\n'
                    '</ancestor-path>\n<properties>\n' + json.dumps(properties) +
                    '\n</properties>\n<iconMetadata>null</iconMetadata>\n' + publisher.NATIVE_BLANK_PAGE + '\n</page>')
    args.page_json.write_text(json.dumps(page))
    recipe = json.loads(args.setup_json.read_text())
    recipe.update(workflowLane="bootcamp", studioTaskUrl="")
    args.setup_json.write_text(json.dumps(recipe))
    return page, properties


class RegistrationContracts(unittest.TestCase):
    def test_native_blank_bootcamp_registers_real_source_then_initializes_once(self):
        with tempfile.TemporaryDirectory() as directory:
            args = inputs(Path(directory))
            page, properties = native_blank_bootcamp(args)
            before = {path.relative_to(args.root).as_posix(): path.read_bytes() for path in args.root.rglob("*") if path.is_file()}
            plan_args = copy.copy(args)
            plan_args.command = "plan"
            planned = register.execute(plan_args)
            self.assertEqual(planned["operation"], "plan")
            self.assertEqual(planned["sourceFiles"], 2)
            self.assertEqual({path.relative_to(args.root).as_posix(): path.read_bytes() for path in args.root.rglob("*") if path.is_file()}, before)
            result = register.execute(args)
            self.assertEqual(result["operation"], "register")
            self.assertEqual(result["project"]["commit"], args.commit)
            self.assertEqual(result["project"]["files"], register.inventory(args.root / "inputs" / args.neutral))
            for relative in result["project"]["files"]:
                pinned = subprocess.check_output(["git", "show", args.commit + ":" + relative], cwd=args.source_dir)
                self.assertEqual((args.root / "inputs" / args.neutral / relative).read_bytes(), pinned)
            task = result["task"]
            self.assertEqual(task["candidateGoal"], properties["Odin Goal"])
            self.assertNotIn("approvedGoal", task)
            self.assertEqual(task["studioTaskUrl"], "")
            self.assertFalse(result["recordingReady"])
            stored = json.loads((args.root / "packs/pages" / (args.neutral + ".json")).read_text())
            self.assertEqual(stored, page)
            empty = publisher.snapshot(stored)
            self.assertEqual(empty["body"], "")
            self.assertEqual(empty["properties"], properties)
            for path, content in before.items():
                if path not in ("runtime/task-registry.json", "runtime/runtime-manifest.json"):
                    self.assertEqual((args.root / path).read_bytes(), content)
            after = {path.relative_to(args.root).as_posix(): (path.read_bytes(), path.stat().st_mtime_ns) for path in args.root.rglob("*") if path.is_file()}
            self.assertEqual(register.execute(args)["operation"], "noop")
            self.assertEqual({path.relative_to(args.root).as_posix(): (path.read_bytes(), path.stat().st_mtime_ns) for path in args.root.rglob("*") if path.is_file()}, after)
            route = publisher.HEADING + "\n**Step 1.** Click Start Recording and minimize TaskRecorder.\n**Step 2.** Perform your own task and verification, then click Stop Recording.\n"
            with self.assertRaises(publisher.PackError):
                publisher.plan_update(task, empty, route)
            first = publisher.plan_update(task, empty, route, initialize=True)
            publisher.assert_plan_current(first, task, empty)
            self.assertEqual(first["operation"], "initialize")
            self.assertNotIn("properties", first["notionUpdate"])
            self.assertFalse(first["trackerPropertiesMutated"])
            readback = copy.deepcopy(page)
            readback["text"] = readback["text"].replace(publisher.NATIVE_BLANK_PAGE, "<content>\n" + route + "\n</content>")
            readback["page_last_edited_at"] = "2026-10-07T00:01:00Z"
            completed = publisher.snapshot(readback)
            self.assertEqual(publisher.verify_readback(first, task, completed), route)
            self.assertEqual(publisher.plan_update(task, completed, route, initialize=True)["operation"], "noop")
            self.assertEqual(completed["properties"], properties)

    def test_native_blank_bootcamp_keeps_goal_source_and_admission_requirements(self):
        with tempfile.TemporaryDirectory() as directory:
            args = inputs(Path(directory))
            page, properties = native_blank_bootcamp(args)
            before = (args.root / "runtime/task-registry.json").read_bytes()
            for key, changed in (("Approval ID", "ODIN-INVENTED"), ("Approved Goal", properties["Odin Goal"]),
                                 ("Odin Goal", ""), ("Lane", "Odin monetization"), ("Fit Gate", "HOLD"),
                                 ("Stage", "Approved"), ("Bootcamp Status", "World queued"),
                                 ("Build Issue", ""), ("Spec Path", "specs/odin-tasks/wrong"),
                                 ("Starter Commit", "c" * 40), ("Starter Repository", "https://github.com/KyPython/wrong-source")):
                invalid = copy.deepcopy(page)
                changed_properties = {**properties, key: changed}
                invalid["text"] = invalid["text"].replace(json.dumps(properties), json.dumps(changed_properties), 1)
                args.page_json.write_text(json.dumps(invalid))
                with self.subTest(key=key), self.assertRaises(ValueError):
                    register.execute(args)
                self.assertEqual((args.root / "runtime/task-registry.json").read_bytes(), before)
                self.assertFalse((args.root / "inputs" / args.neutral).exists())
            args.page_json.write_text(json.dumps(page))
            (args.source_dir / "demo.py").write_text("# human source edit\n")
            with self.assertRaises(ValueError):
                register.execute(args)
            self.assertEqual((args.source_dir / "demo.py").read_text(), "# human source edit\n")
            self.assertEqual((args.root / "runtime/task-registry.json").read_bytes(), before)

    def test_native_blank_odin_page_cannot_invent_required_studio_source(self):
        with tempfile.TemporaryDirectory() as directory:
            args = inputs(Path(directory))
            page = json.loads(args.page_json.read_text())
            properties = register.snapshot(page)["properties"]
            page["text"] = ('<page url="' + page["url"] + '">\n<properties>\n' + json.dumps(properties)
                            + '\n</properties>\n<iconMetadata>null</iconMetadata>\n' + publisher.NATIVE_BLANK_PAGE + '\n</page>')
            args.page_json.write_text(json.dumps(page))
            before = (args.root / "runtime/task-registry.json").read_bytes()
            with self.assertRaisesRegex(ValueError, "Studio task URL must exist"):
                register.execute(args)
            self.assertEqual((args.root / "runtime/task-registry.json").read_bytes(), before)
            self.assertFalse((args.root / "inputs" / args.neutral).exists())

    def test_failed_catalog_install_rolls_back_only_new_task(self):
        with tempfile.TemporaryDirectory() as directory:
            args = inputs(Path(directory))
            before = {path.relative_to(args.root).as_posix(): path.read_bytes() for path in args.root.rglob("*") if path.is_file()}
            original_replace = register.os.replace
            def fail_manifest(source, destination):
                if Path(destination).name == "runtime-manifest.json":
                    raise OSError("simulated manifest installation failure")
                return original_replace(source, destination)
            with patch.object(register.os, "replace", fail_manifest):
                with self.assertRaises(OSError):
                    register.execute(args)
            after = {path.relative_to(args.root).as_posix(): path.read_bytes() for path in args.root.rglob("*") if path.is_file() and path.name != ".task-registration.lock"}
            self.assertEqual(after, before)
            self.assertFalse((args.root / "inputs" / args.neutral).exists())
            register.reviewed_state(args.root)

    def test_bootcamp_registration_keeps_external_approval_empty(self):
        with tempfile.TemporaryDirectory() as directory:
            args = inputs(Path(directory))
            page = json.loads(args.page_json.read_text())
            start, end = page["text"].index("<properties>\n") + len("<properties>\n"), page["text"].index("\n</properties>")
            properties = json.loads(page["text"][start:end])
            properties.update({"Approval ID": "", "Approved Goal": "", "Lane": "Dual-candidate",
                               "Stage": "Candidate", "Fit Gate": "PASS", "Bootcamp Status": "World building",
                               "Spec PR": "", "Spec Path": "specs/odin-bootcamp/fixture"})
            page["text"] = page["text"][:start] + json.dumps(properties) + page["text"][end:]
            args.page_json.write_text(json.dumps(page))
            recipe = json.loads(args.setup_json.read_text())
            recipe.update(workflowLane="bootcamp", studioTaskUrl="")
            args.setup_json.write_text(json.dumps(recipe))
            result = register.execute(args)
            task = result["task"]
            self.assertEqual(task["workflowLane"], "bootcamp")
            self.assertEqual(task["id"], "BOOTCAMP-" + "A" * 32)
            self.assertEqual(task["candidateGoal"], properties["Odin Goal"])
            self.assertNotIn("approvedGoal", task)
            self.assertEqual(task["studioTaskUrl"], "")
            self.assertEqual(register.execute(args)["operation"], "noop")

    def test_plan_writes_nothing_and_registration_retry_is_noop(self):
        with tempfile.TemporaryDirectory() as directory:
            args = inputs(Path(directory))
            before = {path.relative_to(args.root).as_posix(): path.read_bytes() for path in args.root.rglob("*") if path.is_file()}
            plan_args = copy.copy(args)
            plan_args.command = "plan"
            plan = register.execute(plan_args)
            self.assertEqual(plan["operation"], "plan")
            self.assertEqual(plan["sourceFiles"], 2)
            self.assertEqual({path.relative_to(args.root).as_posix(): path.read_bytes() for path in args.root.rglob("*") if path.is_file()}, before)
            result = register.execute(args)
            self.assertEqual(result["operation"], "register")
            self.assertEqual(result["project"]["commit"], args.commit)
            for path, content in before.items():
                if path not in ("runtime/task-registry.json", "runtime/runtime-manifest.json"):
                    self.assertEqual((args.root / path).read_bytes(), content)
            registry, manifest = register.reviewed_state(args.root)
            self.assertEqual(len(registry["tasks"]), 2)
            self.assertEqual(len(manifest["projects"]), 2)
            after = {path.relative_to(args.root).as_posix(): (path.read_bytes(), path.stat().st_mtime_ns) for path in args.root.rglob("*") if path.is_file()}
            self.assertEqual(register.execute(args)["operation"], "noop")
            self.assertEqual({path.relative_to(args.root).as_posix(): (path.read_bytes(), path.stat().st_mtime_ns) for path in args.root.rglob("*") if path.is_file()}, after)

    def test_edited_source_or_old_input_is_preserved_and_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            args = inputs(Path(directory))
            changed = args.source_dir / "demo.py"
            changed.write_text("# human work\n")
            with self.assertRaises(ValueError):
                register.execute(args)
            self.assertEqual(changed.read_text(), "# human work\n")
            old = args.root / "inputs" / STDLIB[0]["neutral"] / "README.md"
            old.write_bytes(old.read_bytes() + b"\nhuman edits\n")
            preserved = old.read_bytes()
            with self.assertRaises(ValueError):
                register.execute(args)
            self.assertEqual(old.read_bytes(), preserved)
            self.assertFalse((args.root / "inputs" / args.neutral).exists())

    def test_conflicting_goal_or_existing_identity_stops_before_registration(self):
        with tempfile.TemporaryDirectory() as directory:
            args = inputs(Path(directory))
            register.execute(args)
            page = json.loads(args.page_json.read_text())
            page["text"] = page["text"].replace("As a software engineer, review this synthetic fixture during the recorded task.", "Changed proposed Goal.")
            args.page_json.write_text(json.dumps(page))
            before = (args.root / "runtime/task-registry.json").read_bytes()
            with self.assertRaises(ValueError):
                register.execute(args)
            self.assertEqual((args.root / "runtime/task-registry.json").read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
