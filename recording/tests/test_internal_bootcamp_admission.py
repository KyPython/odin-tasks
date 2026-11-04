"""Internal practice admission preserves real Odin decisions and original work."""
import base64
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import shutil
import unittest
from unittest.mock import patch

from test_task_registration import inputs, native_blank_bootcamp, register, publisher
from TaskWorkRegistry import ODIN_ADMISSION_FIELDS, validate_registry


def digest(content):
    return hashlib.sha256(content).hexdigest()


def internal_fixture(args, *, stage="Rejected", fit="REJECT"):
    page, properties = native_blank_bootcamp(args)
    properties.update({"Lane": None, "Stage": stage, "Fit Gate": fit,
                       "Bootcamp Status": "Rejected", "Spec PR": "https://github.com/KyPython/ai-governance/pull/999"})
    previous = publisher.snapshot(page)["properties"]
    page["text"] = page["text"].replace(json.dumps(previous), json.dumps(properties), 1)
    args.page_json.write_text(json.dumps(page))
    files = {properties["Spec Path"] + "/" + name: ("Synthetic reviewed " + name + "\n").encode()
             for name in ("requirements.md", "design.md", "tasks.md")}
    files[properties["Spec Path"] + "/requirements.md"] = (
        "# Synthetic fixture requirements\n\n" + properties["Odin Goal"] + "\n\n"
        "Task Factory row: https://app.notion.com/p/" + publisher.snapshot(page)["pageId"].replace("-", "") + "\n").encode()
    execution_id = "sess_bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
    capture_path = "cloud/kiro-receipts/" + execution_id + ".capture.txt"
    capture = b"Synthetic fixture CLI capture only; no actual Kiro execution claim.\n"
    receipt = {"version": 1, "engine": "kiro", "status": "PASS", "executionId": execution_id,
               "inventorySha256": "b" * 64, "specCommit": "c" * 40,
               "bindings": {publisher.snapshot(page)["pageId"]: {
                   "rowId": publisher.snapshot(page)["pageId"],
                   "goalSha256": digest((properties["Odin Goal"] + "\n").encode()),
                   "specPath": properties["Spec Path"], "specPr": properties["Spec PR"]}},
               "executionEvidence": {"source": "captured-kiro-cli", "executionTarget": "local",
                                     "capturePath": capture_path, "captureSha256": digest(capture)},
               "paths": {name: {"status": "PASS", "sha256": digest(content)} for name, content in files.items()}}
    receipt_path = args.setup_json.parent / "actual-kiro-receipt.json"
    receipt_path.write_text(json.dumps(receipt))
    recipe = json.loads(args.setup_json.read_text())
    recipe["kiroReviewReceiptFile"] = str(receipt_path)
    recipe["internalBootcampAdmission"] = {
        "version": 1, "authority": "explicit-user", "scope": "internal-bootcamp-world-preparation",
        "authorizationRef": "session:synthetic-fixture-only", "authorizationTextSha256": "a" * 64,
        "notionPageId": publisher.snapshot(page)["pageId"],
        "goalSha256": digest((properties["Odin Goal"] + "\n").encode()),
        "sourceRepo": args.source_repo, "sourceCommit": args.commit,
        "originalOdinFields": {key: properties[key] for key in ODIN_ADMISSION_FIELDS},
        "kiroReview": {"receiptSha256": digest(receipt_path.read_bytes()),
                       "receiptCommit": "e" * 40,
                       "receiptPath": "cloud/kiro-receipts/" + receipt["executionId"] + ".json",
                       "executionId": receipt["executionId"], "inventorySha256": receipt["inventorySha256"],
                       "specCommit": receipt["specCommit"],
                       "specFiles": {name: digest(content) for name, content in files.items()}},
        "specMerge": {"prUrl": properties["Spec PR"], "commit": "d" * 40,
                      "mergedAt": "2026-10-08T12:00:00Z", "mergedBy": "KyPython"}}
    args.setup_json.write_text(json.dumps(recipe))
    files[recipe["internalBootcampAdmission"]["kiroReview"]["receiptPath"]] = receipt_path.read_bytes()
    files[capture_path] = capture
    return page, properties, recipe, receipt, files


def verified_gh(files, *, state="MERGED", merger="KyPython", changed_bytes=False, head="c" * 40, base="main"):
    original = register.run
    def run(argv, cwd=None):
        if argv[:3] == ["gh", "pr", "view"]:
            return json.dumps({"state": state, "mergedAt": "2026-10-08T12:00:00Z",
                               "mergedBy": {"login": merger}, "mergeCommit": {"oid": "d" * 40},
                               "headRefOid": head,
                               "baseRefName": base,
                               "files": [{"path": name} for name in files if name.startswith("specs/")]}).encode()
        if argv[:2] == ["gh", "api"]:
            path = argv[2].split("/contents/", 1)[1].split("?", 1)[0]
            content = files[path] + (b"Unreviewed content\n" if changed_bytes and path.startswith("specs/") else b"")
            return json.dumps({"type": "file", "path": path, "encoding": "base64",
                               "content": base64.b64encode(content).decode()}).encode()
        return original(argv, cwd)
    return run


class InternalBootcampContracts(unittest.TestCase):
    def test_rejected_and_awaiting_approval_are_additive_internal_practice_only(self):
        for stage, fit in (("Rejected", "REJECT"), ("Awaiting Odin approval", "PASS")):
            with self.subTest(stage=stage), tempfile.TemporaryDirectory() as directory:
                args = inputs(Path(directory))
                page, properties, _, _, files = internal_fixture(args, stage=stage, fit=fit)
                original_page = args.page_json.read_bytes()
                existing = {p.relative_to(args.root).as_posix(): p.read_bytes()
                            for p in args.root.rglob("*") if p.is_file()}
                with patch.object(register, "run", side_effect=verified_gh(files)):
                    result = register.execute(args)
                    task = result["task"]
                    self.assertEqual(register.execute(args)["operation"], "noop")
                self.assertEqual(args.page_json.read_bytes(), original_page)
                self.assertEqual(task["candidateGoal"], properties["Odin Goal"])
                self.assertNotIn("approvedGoal", task)
                self.assertEqual(task["studioTaskUrl"], "")
                self.assertEqual(task["internalBootcampAdmission"]["originalOdinFields"]["Stage"], stage)
                self.assertFalse(result["recordingReady"])
                for name, data in existing.items():
                    if name not in ("runtime/task-registry.json", "runtime/runtime-manifest.json"):
                        self.assertEqual((args.root / name).read_bytes(), data)
                route = publisher.HEADING + "\n**Step 1.** Start Recording for guided internal practice.\n**Step 2.** Stop Recording.\n"
                current = publisher.snapshot(page)
                plan = publisher.plan_update(task, current, route, initialize=True)
                self.assertNotIn("properties", plan["notionUpdate"])
                readback = copy.deepcopy(page)
                readback["text"] = readback["text"].replace(publisher.NATIVE_BLANK_PAGE, "<content>\n" + route + "\n</content>")
                completed = publisher.snapshot(readback)
                publisher.verify_readback(plan, task, completed)
                self.assertEqual(completed["properties"], properties)
                receipt = json.loads(publisher.publication_files(task, completed, route)["receipt.json"])
                self.assertIn("internalBootcampAdmissionSha256", receipt)
                self.assertFalse(receipt["externalApprovalClaimed"])
                self.assertFalse(receipt["recordingReady"])
                self.assertFalse(receipt["practiceReady"])
                cues = Path(directory).resolve() / "owned-cues"
                first_files = publisher.publication_files(task, completed, route)
                self.assertEqual(publisher.safe_publish(cues, task["neutral"], first_files)["operation"], "initialize")
                completed["revision"] = "2026-10-08T12:01:00Z"
                updated_files = publisher.publication_files(task, completed, route)
                self.assertEqual(publisher.safe_publish(cues, task["neutral"], updated_files)["operation"], "update")
                self.assertEqual(publisher.safe_publish(cues, task["neutral"], updated_files)["operation"], "noop")
                changed_task = copy.deepcopy(task)
                changed_task["internalBootcampAdmission"]["authorizationRef"] = "session:changed-authority"
                with self.assertRaisesRegex(publisher.PackError, "authorization"):
                    publisher.assert_plan_current(plan, changed_task, current)
                for key, changed in (("Stage", "Candidate"), ("Fit Gate", "PASS"), ("Lane", "Bootcamp"),
                                     ("Approval ID", "ODIN-INVENTED"), ("Approved Goal", task["candidateGoal"]),
                                     ("Odin Goal", "Changed Goal"), ("Spec PR", "https://github.com/KyPython/ai-governance/pull/888")):
                    if changed == properties.get(key):
                        continue
                    changed_page = copy.deepcopy(completed)
                    changed_page["properties"][key] = changed
                    with self.subTest(key=key), self.assertRaises(publisher.PackError):
                        publisher.verify_page(task, changed_page)

    def test_installed_publisher_uses_packaged_admission_validator(self):
        with tempfile.TemporaryDirectory() as directory:
            args = inputs(Path(directory))
            page, _, recipe, _, _ = internal_fixture(args)
            task, _ = register.make_task(publisher.snapshot(page), args.neutral, args.source_repo, args.commit, args.profile, recipe)
            installed = Path(directory) / "installed/TaskWorkRuntime"
            installed.mkdir(parents=True)
            root = Path(register.__file__).resolve().parents[1]
            shutil.copy2(root / "runtime/TaskWorkRegistry.py", installed / "TaskWorkRegistry.py")
            shutil.copy2(root / "scripts/recording_pack.py", installed / "recording_pack.py")
            spec = importlib.util.spec_from_file_location("InstalledInternalPack", installed / "recording_pack.py")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            module.verify_page(task, module.snapshot(page), require_route=False)
            changed = module.snapshot(page)
            changed["properties"]["Fit Gate"] = "PASS"
            with self.assertRaises(module.PackError):
                module.verify_page(task, changed, require_route=False)

    def test_authorization_cannot_relax_odin_or_change_original_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            args = inputs(Path(directory))
            page, properties, recipe, _, _ = internal_fixture(args)
            base = publisher.snapshot(page)
            for section, key, changed in ((None, "scope", "paid-odin-approval"),
                                          (None, "sourceCommit", "f" * 40), (None, "goalSha256", "f" * 64),
                                          (None, "notionPageId", "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
                                          ("originalOdinFields", "Stage", "Candidate"),
                                          ("originalOdinFields", "Approval ID", "ODIN-INVENTED"),
                                          ("specMerge", "mergedBy", "coding-agent")):
                invalid = copy.deepcopy(recipe)
                target = invalid["internalBootcampAdmission"]
                if section:
                    target = target[section]
                target[key] = changed
                with self.subTest(key=key), self.assertRaises(ValueError):
                    register.make_task(base, args.neutral, args.source_repo, args.commit, args.profile, invalid)
            invalid = copy.deepcopy(recipe)
            invalid.pop("internalBootcampAdmission")
            with self.assertRaises(ValueError):
                register.make_task(base, args.neutral, args.source_repo, args.commit, args.profile, invalid)
            invalid = copy.deepcopy(recipe)
            invalid["workflowLane"] = "odin"
            with self.assertRaises(ValueError):
                register.make_task(base, args.neutral, args.source_repo, args.commit, args.profile, invalid)

    def test_no_actual_kiro_pass_or_human_merge_means_no_registration(self):
        for mode in ("missing-receipt", "receipt-byte-drift", "kiro-fail", "wrong-goal", "missing-cli-evidence", "capture-byte-drift", "capture-whitespace",
                     "open-pr", "agent-merge", "wrong-base", "pr-head-drift", "spec-byte-drift"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                args = inputs(Path(directory))
                _, _, recipe, receipt, files = internal_fixture(args)
                path = Path(recipe["kiroReviewReceiptFile"])
                if mode == "missing-receipt":
                    path.unlink()
                elif mode == "receipt-byte-drift":
                    path.write_bytes(path.read_bytes() + b"\n")
                elif mode in ("kiro-fail", "wrong-goal", "missing-cli-evidence"):
                    if mode == "kiro-fail":
                        receipt["status"] = "FAIL"
                    elif mode == "wrong-goal":
                        next(iter(receipt["bindings"].values()))["goalSha256"] = "f" * 64
                    else:
                        receipt.pop("executionEvidence")
                    path.write_text(json.dumps(receipt))
                    recipe["internalBootcampAdmission"]["kiroReview"]["receiptSha256"] = digest(path.read_bytes())
                    args.setup_json.write_text(json.dumps(recipe))
                    files[recipe["internalBootcampAdmission"]["kiroReview"]["receiptPath"]] = path.read_bytes()
                elif mode == "capture-byte-drift":
                    files[receipt["executionEvidence"]["capturePath"]] += b"Changed capture\n"
                elif mode == "capture-whitespace":
                    files[receipt["executionEvidence"]["capturePath"]] = b" \n\t"
                    receipt["executionEvidence"]["captureSha256"] = digest(b" \n\t")
                    path.write_text(json.dumps(receipt))
                    recipe["internalBootcampAdmission"]["kiroReview"]["receiptSha256"] = digest(path.read_bytes())
                    args.setup_json.write_text(json.dumps(recipe))
                    files[recipe["internalBootcampAdmission"]["kiroReview"]["receiptPath"]] = path.read_bytes()
                before = {p.relative_to(args.root).as_posix(): p.read_bytes()
                          for p in args.root.rglob("*") if p.is_file()}
                with patch.object(register, "run", side_effect=verified_gh(
                        files, state="OPEN" if mode == "open-pr" else "MERGED",
                        merger="coding-agent" if mode == "agent-merge" else "KyPython",
                        head="f" * 40 if mode == "pr-head-drift" else "c" * 40,
                        base="draft-specs" if mode == "wrong-base" else "main",
                        changed_bytes=mode == "spec-byte-drift")):
                    with self.assertRaises(ValueError):
                        register.execute(args)
                self.assertEqual({p.relative_to(args.root).as_posix(): p.read_bytes()
                                  for p in args.root.rglob("*") if p.is_file()}, before)
                self.assertFalse((args.root / "inputs" / args.neutral).exists())

    def test_offline_registry_rejects_missing_review_hash_or_claimed_studio(self):
        with tempfile.TemporaryDirectory() as directory:
            args = inputs(Path(directory))
            page, _, recipe, _, _ = internal_fixture(args)
            task, _ = register.make_task(publisher.snapshot(page), args.neutral, args.source_repo, args.commit, args.profile, recipe)
            for mode in ("missing-file", "studio", "approval"):
                changed = copy.deepcopy(task)
                if mode == "missing-file":
                    changed["internalBootcampAdmission"]["kiroReview"]["specFiles"].pop(next(iter(changed["internalBootcampAdmission"]["kiroReview"]["specFiles"])))
                elif mode == "studio":
                    changed["studioTaskUrl"] = "https://studio.mercor.com/annotator/tasks/invented"
                else:
                    changed["approvedGoal"] = changed["candidateGoal"]
                with self.subTest(mode=mode), self.assertRaises(ValueError):
                    validate_registry({"version": 1, "tasks": [changed]})


if __name__ == "__main__":
    unittest.main()
