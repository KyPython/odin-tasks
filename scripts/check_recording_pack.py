#!/usr/bin/env python3
"""Behavior checks for publisher retries, cloud identity and human-work safety."""
import copy
import importlib.util
import json
import pathlib
import re
import tempfile
import unittest


HERE = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("recording_pack", HERE / "recording_pack.py")
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)

PAGE_ID = "3f08621e-0a7a-8132-89fd-e5cad87aba40"
ROUTE = p.HEADING + "\n**Step 1.** Click Start Recording and minimize TaskRecorder.\n**Step 2.** Inspect the actual source, record your own work, then Stop TaskRecorder.\n"
CHILDREN = '\n## Source and references\n<mention-page url="https://app.notion.com/p/12345678901234567890123456789012"/>\n<page url="https://app.notion.com/p/23456789012345678901234567890123">Retained child</page>\n<database url="https://app.notion.com/p/34567890123456789012345678901234">Retained database</database>\n<folder url="https://app.notion.com/p/45678901234567890123456789012345">Retained folder</folder>'


def task():
    goal = "Use your own judgment to inspect the synthetic task."
    return {"id": "ODIN-EXACT-APPROVAL", "neutral": "test-workspace", "notionPageId": PAGE_ID,
            "sourceRepo": "https://github.com/KyPython/synthetic-starter", "commit": "a" * 40,
            "approvedGoal": goal, "goalFile": "goals/test-workspace.txt", "goalSha256": p.digest(goal + "\n")}


def fetch(body=None, revision="2026-10-07T22:16:13.842Z"):
    t = task()
    props = {"Approval ID": t["id"], "Approved Goal": t["approvedGoal"], "Odin Goal": t["approvedGoal"],
             "Environment Review Gate": "__YES__", "No-Solution-Leak Gate": "__YES__",
             "Local Starter Gate": "__NO__", "Pre-Record Gate": "__NO__"}
    return {"metadata": {"type": "page"}, "title": "Synthetic task", "url": f"https://app.notion.com/p/{PAGE_ID.replace('-', '')}",
            "page_last_edited_at": revision, "text": '<page>\n<properties>\n' + json.dumps(props)
            + '\n</properties>\n<content>\n' + (body if body is not None else '## Human context\nKeep this exact wording.\n' + ROUTE + CHILDREN)
            + '\n</content>\n</page>'}


def blank_fetch():
    value = fetch("")
    value["text"] = value["text"].replace("<page>", '<page url="' + value["url"] + '">', 1)
    value["text"] = value["text"].replace(
        "<content>\n\n</content>", "<iconMetadata>null</iconMetadata>\n" + p.NATIVE_BLANK_PAGE)
    return value


class PublisherChecks(unittest.TestCase):
    def setUp(self):
        self.task = task()
        self.page = p.snapshot(fetch())

    def test_exact_cloud_route_is_noop_and_does_not_touch_gates(self):
        plan = p.plan_update(self.task, self.page, ROUTE)
        self.assertEqual(plan["operation"], "noop")
        self.assertIsNone(plan["notionUpdate"])
        self.assertFalse(plan["recordingReady"])
        self.assertFalse(plan["trackerPropertiesMutated"])
        self.assertEqual(p.verify_readback(plan, self.task, self.page), ROUTE)

    def test_one_changed_route_targets_only_the_exact_section(self):
        desired = ROUTE.replace("Inspect the actual source", "Read the actual written contract")
        plan = p.plan_update(self.task, self.page, desired)
        update = plan["notionUpdate"]
        self.assertEqual(update["command"], "update_content")
        self.assertNotIn("properties", update)
        old, new = update["content_updates"][0].values()
        # The connector uses this exact old/new pair, leaving child objects alone.
        changed = self.page["body"].replace(old, new, 1)
        readback = p.snapshot(fetch(changed, "2026-10-07T22:17:13.842Z"))
        self.assertEqual(p.verify_readback(plan, self.task, readback), desired)
        self.assertTrue(readback["body"].endswith(CHILDREN))
        self.assertEqual(p.plan_update(self.task, readback, desired)["operation"], "noop")

    def test_owned_make_paragraph_is_verified_read_only_and_repeatable(self):
        content = "Source review only. Live checks remain pending.\n\n" + ROUTE
        marker = f"TASKWORK_OPERATOR_PACK:{PAGE_ID}\nREVISION:{'d'*64}\nCONTENT_SHA256:{p.digest(content)}\n" + content
        page = p.snapshot(fetch("## User context\nKeep my notes.\n" + marker + CHILDREN))
        page["properties"]["Operator Pack Revision"] = "d" * 64
        p.verify_page(self.task, page)
        plan = p.plan_update(self.task, page, ROUTE)
        self.assertEqual(plan["operation"], "noop")
        self.assertIsNone(plan["notionUpdate"])
        self.assertEqual(p.verify_readback(plan, self.task, page), ROUTE)
        self.assertTrue(p.publication_files(self.task, page, ROUTE)["notion-snapshot.txt"].decode().endswith(CHILDREN))
        with self.assertRaises(p.PackError):
            p.plan_update(self.task, page, ROUTE.replace("Inspect the actual source", "Change the cloud owner's route"))

    def test_make_paragraph_markdown_escape_and_linebreak_adapter_requires_digest(self):
        content = "Source review only.\n\n" + ROUTE
        marker = f"TASKWORK_OPERATOR_PACK:{PAGE_ID}\nREVISION:{'d'*64}\nCONTENT_SHA256:{p.digest(content)}\n" + content
        escaped = __import__('re').sub(r"([\\*~`$\[\]<>{}|^#])", r"\\\1", marker)
        for representation in (marker.replace("\n", "<br>"), escaped, escaped.replace("\n", "<br>")):
            with self.subTest(representation=representation[:80]):
                page = p.snapshot(fetch("## User context\n" + representation + CHILDREN))
                self.assertEqual(p.page_route(page), ROUTE)
                self.assertEqual(p.plan_update(self.task, page, ROUTE)["operation"], "noop")

    def test_manually_edited_make_paragraph_and_wrong_revision_hold(self):
        content = "Source review only.\n\n" + ROUTE
        marker = f"TASKWORK_OPERATOR_PACK:{PAGE_ID}\nREVISION:{'d'*64}\nCONTENT_SHA256:{p.digest(content)}\n" + content
        page = p.snapshot(fetch(marker.replace("Inspect the actual source", "My human edit")))
        with self.assertRaises(p.PackError):
            p.verify_page(self.task, page)
        page = p.snapshot(fetch(marker))
        page["properties"]["Operator Pack Revision"] = "e" * 64
        with self.assertRaises(p.PackError):
            p.verify_page(self.task, page)

    def test_multiple_make_markers_or_competing_native_route_hold(self):
        content = "Source review only.\n\n" + ROUTE
        marker = f"TASKWORK_OPERATOR_PACK:{PAGE_ID}\nREVISION:{'d'*64}\nCONTENT_SHA256:{p.digest(content)}\n" + content
        for body in (marker + "\n" + marker, marker + "\n## More\n" + ROUTE):
            with self.assertRaises(p.PackError):
                p.verify_page(self.task, p.snapshot(fetch(body)))

    def test_notional_initialization_is_once_and_requires_explicit_mode(self):
        page = p.snapshot(fetch("## Approved context\n" + CHILDREN))
        with self.assertRaises(p.PackError):
            p.plan_update(self.task, page, ROUTE)
        plan = p.plan_update(self.task, page, ROUTE, initialize=True)
        self.assertEqual(plan["operation"], "initialize")
        self.assertEqual(plan["notionUpdate"]["position"], {"type": "start"})
        changed = ROUTE + page["body"]
        readback = p.snapshot(fetch(changed))
        p.verify_readback(plan, self.task, readback)
        self.assertEqual(p.plan_update(self.task, readback, ROUTE, initialize=True)["operation"], "noop")

    def test_native_blank_page_initializes_once_without_changing_identity_or_gates(self):
        value = blank_fetch()
        for wrapped in (value, {"structuredContent": value},
                        {"content": [{"type": "text", "text": json.dumps(value)}]}):
            with self.subTest(wrapper=list(wrapped)):
                page = p.snapshot(wrapped)
                self.assertEqual(page["body"], "")
                self.assertEqual(page["properties"], self.page["properties"])
                self.assertEqual(page["fetch"], value)
                with self.assertRaises(p.PackError):
                    p.plan_update(self.task, page, ROUTE)
                plan = p.plan_update(self.task, page, ROUTE, initialize=True)
                p.assert_plan_current(plan, self.task, page)
                self.assertEqual(plan["operation"], "initialize")
                self.assertEqual(plan["notionUpdate"]["command"], "insert_content")
                self.assertEqual(plan["notionUpdate"]["position"], {"type": "start"})
                self.assertNotIn("properties", plan["notionUpdate"])
                self.assertFalse(plan["trackerPropertiesMutated"])
                self.assertFalse(plan["recordingReady"])
                readback = p.snapshot(fetch(ROUTE, "2026-10-07T22:17:13.842Z"))
                self.assertEqual(p.verify_readback(plan, self.task, readback), ROUTE)
                self.assertEqual(p.plan_update(self.task, readback, ROUTE, initialize=True)["operation"], "noop")

    def test_native_blank_marker_cannot_hide_content_or_child_objects(self):
        value = blank_fetch()
        marker = p.NATIVE_BLANK_PAGE
        preamble = ('Here is the result of "fetch" for the Page with URL ' + value["url"]
                    + ' as of ' + value["page_last_edited_at"] + ':\n')
        self.assertEqual(p.snapshot({**value, "text": preamble + value["text"] + '\n \t'})["body"], "")
        for text in ('Human text before the page\n' + value["text"],
                     value["text"] + '\nHuman text after the page',
                     'Human text before the fetch result\n' + preamble + value["text"],
                     preamble + 'Human text before the page\n' + value["text"],
                     preamble + value["text"] + '\nHuman text after the page',
                     preamble.replace(value["url"], 'https://app.notion.com/p/23456789012345678901234567890123') + value["text"]):
            with self.subTest(outside_text=text), self.assertRaises(p.PackError):
                p.snapshot({**value, "text": text})
        unsafe = ["", marker + "\n" + marker, marker.replace("This page is blank", "Unverified page"),
                  marker.replace("<blank-page>", '<blank-page color="gray">'),
                  "<content>\n" + ROUTE + "\n</content>\n" + marker,
                  "<content>\n" + marker, marker + "\n</content>",
                  "Unexported human content\n" + marker]
        unsafe.extend('<' + kind + ' url="existing"/>\n' + marker for kind in
                      ("page", "database", "folder", "unknown", "synced_block_reference", "custom-block"))
        for fragment in unsafe:
            changed = copy.deepcopy(value)
            changed["text"] = changed["text"].replace(marker, fragment, 1)
            with self.subTest(fragment=fragment), self.assertRaises(p.PackError):
                p.snapshot(changed)
        changed = copy.deepcopy(value)
        changed["text"] = changed["text"].replace(
            "<properties>", '<ancestor-path>\n<page url="existing"/>\n</ancestor-path>\n<properties>', 1)
        with self.assertRaises(p.PackError):
            p.snapshot(changed)
        for child in ("unknown", "page", "database", "folder"):
            changed = copy.deepcopy(value)
            changed["text"] = changed["text"].replace(
                "<properties>", '<ancestor-path>\n<' + child + '/>\n</ancestor-path>\n<properties>', 1)
            with self.subTest(hidden_child=child), self.assertRaises(p.PackError):
                p.snapshot(changed)

    def test_native_blank_page_requires_complete_native_metadata_properties_and_revision(self):
        value = blank_fetch()
        for changes in ({"metadata": {}}, {"metadata": None}, {"metadata": {"type": "database"}},
                        {"metadata": {"type": "page", "truncated": True}},
                        {"metadata": {"type": "page", "unknown_block_ids": ["unexported"]}},
                        {"truncated": True}, {"unknown_block_count": 1}, {"unknown_block_ids": ["unexported"]},
                        {"page_last_edited_at": ""}, {"text": None}):
            changed = copy.deepcopy(value)
            changed.update(changes)
            with self.subTest(changes=changes), self.assertRaises(p.PackError):
                p.snapshot(changed)
        for replacement in ('<properties>\n[]\n</properties>', "", '<properties>\n{}\n</properties>\n<properties>\n{}\n</properties>'):
            changed = copy.deepcopy(value)
            changed["text"] = re.sub(r"<properties>\n.*?\n</properties>", lambda _: replacement, changed["text"], flags=re.S)
            with self.subTest(properties=replacement), self.assertRaises(p.PackError):
                p.snapshot(changed)
        for text in (value["text"].replace('</page>', ''), value["text"].replace(
                '<page url="' + value["url"] + '">', '<page url="https://app.notion.com/p/23456789012345678901234567890123">')):
            with self.subTest(text=text), self.assertRaises(p.PackError):
                p.snapshot({**value, "text": text})

    def test_native_blank_page_does_not_bypass_source_or_goal_validation(self):
        page = p.snapshot(blank_fetch())
        for key, changed in (("Approval ID", "ODIN-WRONG"), ("Approved Goal", "Changed Goal"),
                             ("Odin Goal", "Changed Goal"), ("Starter Commit", "b" * 40),
                             ("Starter Repository", "https://github.com/KyPython/wrong-source")):
            invalid = copy.deepcopy(page)
            invalid["properties"][key] = changed
            with self.subTest(key=key), self.assertRaises(p.PackError):
                p.plan_update(self.task, invalid, ROUTE, initialize=True)

    def test_stale_plan_is_rejected_before_connector_write(self):
        plan = p.plan_update(self.task, self.page, ROUTE)
        p.assert_plan_current(plan, self.task, self.page)
        for page in (p.snapshot(fetch(revision="2026-10-07T22:17:13.842Z")),
                     p.snapshot(fetch(self.page["body"].replace("exact wording", "edited wording")))):
            with self.assertRaises(p.PackError):
                p.assert_plan_current(plan, self.task, page)

    def test_unrelated_edit_in_readback_requires_reconciliation(self):
        plan = p.plan_update(self.task, self.page, ROUTE)
        readback = p.snapshot(fetch(self.page["body"].replace("Retained child", "Renamed child")))
        with self.assertRaises(p.PackError):
            p.verify_readback(plan, self.task, readback)

    def test_missing_duplicate_and_embedded_native_routes_hold(self):
        for body in ("No route", ROUTE + "\n" + ROUTE,
                     ROUTE + '\n<page url="https://app.notion.com/p/23456789012345678901234567890123">Child</page>'):
            with self.assertRaises(p.PackError):
                p.validate_route(p.route_from_body(body))
        for native in ("synced_block_reference", "custom-block", "transcript"):
            with self.assertRaises(p.PackError):
                p.validate_route(ROUTE + f'\n<{native} url="existing">Preserve</{native}>')

    def test_contiguous_steps_required_and_heading_inside_code_is_ignored(self):
        with self.assertRaises(p.PackError):
            p.validate_route(ROUTE.replace("Step 2", "Step 3"))
        code = ROUTE + f"```text\n{p.HEADING}\n```\n"
        self.assertEqual(p.route_from_body(code), code)

    def test_fetched_goal_and_approval_cannot_drift(self):
        for key in ("Approval ID", "Approved Goal", "Odin Goal"):
            page = copy.deepcopy(self.page)
            page["properties"][key] += " changed"
            with self.assertRaises(p.PackError):
                p.verify_page(self.task, page)

    def test_optional_source_ledger_cannot_contradict_registered_repo(self):
        for key, value in (("Starter Repository", "https://github.com/KyPython/wrong-repo"), ("Starter Commit", "c" * 40)):
            page = copy.deepcopy(self.page)
            page["properties"][key] = value
            with self.assertRaises(p.PackError):
                p.verify_page(self.task, page)

    def test_bootcamp_candidate_uses_its_own_identity_goal_and_readiness(self):
        t = copy.deepcopy(self.task)
        t.update(workflowLane="bootcamp", goalKind="candidate", candidateGoal=t.pop("approvedGoal"),
                 id="BOOTCAMP-" + PAGE_ID.replace("-", "").upper(), buildIssue="https://github.com/KyPython/ai-governance/issues/86")
        page = copy.deepcopy(self.page)
        page["properties"].update({"Approval ID": "", "Approved Goal": "", "Lane": "Dual-candidate",
                                   "Fit Gate": "PASS", "Stage": "Candidate", "Bootcamp Status": "World building",
                                   "Build Issue": t["buildIssue"]})
        p.verify_page(t, page)
        plan = p.plan_update(t, page, ROUTE)
        self.assertEqual(plan["workflowLane"], "bootcamp")
        self.assertEqual(plan["goalKind"], "candidate")
        files = p.publication_files(t, page, ROUTE)
        self.assertIn("candidate-goal.txt", files)
        self.assertNotIn("approved-goal.txt", files)
        receipt = json.loads(files["receipt.json"])
        self.assertFalse(receipt["externalApprovalClaimed"])
        self.assertFalse(receipt["practiceReady"])
        self.assertFalse(receipt["recordingReady"])
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp).resolve() / "generated-cues"
            p.safe_publish(root, t["neutral"], files)
            page["revision"] = "2026-10-07T22:18:13.842Z"
            self.assertEqual(p.safe_publish(root, t["neutral"], p.publication_files(t, page, ROUTE))["operation"], "update")

    def test_bootcamp_cannot_fabricate_approval_fit_source_or_admission(self):
        t = copy.deepcopy(self.task)
        t.update(workflowLane="bootcamp", goalKind="candidate", candidateGoal=t.pop("approvedGoal"),
                 id="BOOTCAMP-" + PAGE_ID.replace("-", "").upper(), buildIssue="https://github.com/KyPython/ai-governance/issues/86")
        original = copy.deepcopy(self.page)
        original["properties"].update({"Approval ID": "", "Approved Goal": "", "Lane": "Bootcamp",
                                      "Fit Gate": "PASS", "Stage": "Candidate", "Bootcamp Status": "World building",
                                      "Build Issue": t["buildIssue"]})
        for key, value in (("Approval ID", "ODIN-INVENTED"), ("Approved Goal", t["candidateGoal"]),
                           ("Fit Gate", "HOLD"), ("Stage", "Approved"), ("Bootcamp Status", "World queued"),
                           ("Build Issue", "https://github.com/KyPython/ai-governance/issues/999"),
                           ("Starter Commit", "c" * 40), ("Lane", "Odin monetization")):
            page = copy.deepcopy(original)
            page["properties"][key] = value
            with self.subTest(key=key), self.assertRaises(p.PackError):
                p.verify_page(t, page)
        for key, value in (("id", "ODIN-INVENTED"), ("studioTaskUrl", "https://studio.mercor.com/annotator/tasks/invented")):
            changed = copy.deepcopy(t)
            changed[key] = value
            with self.subTest(key=key), self.assertRaises(p.PackError):
                p.verify_page(changed, original)

    def test_wrong_page_or_unavailable_native_facts_hold(self):
        for changes in ({"truncated": True}, {"unknown_block_count": 1}, {"page_last_edited_at": ""},
                        {"url": "https://app.notion.com/p/23456789012345678901234567890123"}):
            value = fetch()
            value.update(changes)
            with self.assertRaises(p.PackError):
                p.verify_page(self.task, p.snapshot(value))
        with self.assertRaises(p.PackError):
            p.snapshot(fetch(ROUTE + '<unknown url="existing"/>'))

    def test_mcp_wrapper_and_full_native_children_survive_snapshot(self):
        value = fetch()
        page = p.snapshot({"content": [{"type": "text", "text": json.dumps(value)}]})
        files = p.publication_files(self.task, page, ROUTE)
        self.assertEqual(json.loads(files["notion-snapshot.json"]), value)
        self.assertTrue(files["notion-snapshot.txt"].decode().endswith(CHILDREN))

    def test_cloud_setup_and_actual_recording_are_distinct(self):
        files = p.publication_files(self.task, self.page, ROUTE)
        receipt = json.loads(files["receipt.json"])
        self.assertTrue(receipt["sourceReviewed"])
        self.assertFalse(receipt["cloudPrepared"])
        self.assertFalse(receipt["recorderExecuted"])
        self.assertFalse(receipt["setupVerified"])
        self.assertFalse(receipt["recordingReady"])
        proof = {"version": 1, "repository": "KyPython/odin-recording-preparation", "runId": "123",
                 "sourceCommit": "b" * 40, "starterCommits": {self.task["neutral"]: self.task["commit"]},
                 "runUrl": "https://github.com/KyPython/odin-recording-preparation/actions/runs/123",
                 "checks": [{"command": ["verify"], "exitCode": 0}]}
        receipt = json.loads(p.publication_files(self.task, self.page, ROUTE, proof)["receipt.json"])
        self.assertTrue(receipt["cloudPrepared"])
        self.assertFalse(receipt["recordingReady"])
        proof["starterCommits"][self.task["neutral"]] = "c" * 40
        with self.assertRaises(p.PackError):
            p.publication_files(self.task, self.page, ROUTE, proof)

    def test_source_review_failure_is_not_published(self):
        self.page["properties"]["No-Solution-Leak Gate"] = "__NO__"
        with self.assertRaises(p.PackError):
            p.publication_files(self.task, self.page, ROUTE)

    def test_html_escapes_untrusted_route_text(self):
        route = ROUTE.replace("Inspect the actual source", '<script>alert("bad")</script>')
        page = p.snapshot(fetch('## Context\n' + route + CHILDREN))
        files = p.publication_files(self.task, page, route)
        text = files["cue-card.html"].decode()
        self.assertNotIn("<script>", text)
        self.assertIn("&lt;script&gt;", text)

    def test_standalone_cues_include_existing_recovery_without_changing_route_or_identity(self):
        baseline = json.loads(p.publication_files(self.task, self.page, ROUTE)["receipt.json"])
        for title in ("Recovery for predictable slips", "Predictable recovery — use only when needed"):
            with self.subTest(title=title):
                appendix = "### " + title + "\nSave All, then repeat the exact failed command.\n"
                page = p.snapshot(fetch(ROUTE + "\n" + appendix + CHILDREN))
                original = copy.deepcopy(page)
                files = p.publication_files(self.task, page, ROUTE)
                text, document = files["cue-card.txt"].decode(), files["cue-card.html"].decode()
                receipt = json.loads(files["receipt.json"])
                self.assertTrue(text.endswith(appendix))
                self.assertIn("<h2>" + title + "</h2>", document)
                self.assertIn("Save All, then repeat the exact failed command.", document)
                self.assertEqual(p.route_from_body(text), ROUTE)
                self.assertEqual(receipt["routeSha256"], baseline["routeSha256"])
                self.assertEqual(receipt["packRevision"], baseline["packRevision"])
                self.assertEqual(receipt["trackerStateAtExport"], baseline["trackerStateAtExport"])
                self.assertNotIn("Retained child", text)
                self.assertNotIn("Retained child", document)
                self.assertEqual(page, original)
                self.assertTrue(files["notion-snapshot.txt"].decode().endswith(CHILDREN))

    def test_recovery_export_ignores_fenced_examples_and_keeps_inline_guidance_once(self):
        examples = "## Source reference\n```markdown\n### Recovery example only\nDo not print this example.\n```\n"
        appendix = "### Recovery for predictable slips\nKeep this real correction.\n"
        page = p.snapshot(fetch(ROUTE + examples + appendix + CHILDREN))
        files = p.publication_files(self.task, page, ROUTE)
        self.assertIn("Keep this real correction.", files["cue-card.txt"].decode())
        self.assertNotIn("Do not print this example.", files["cue-card.txt"].decode())
        inline = ROUTE + "**Deterministic recovery actions**\nSave All before retrying.\n"
        files = p.publication_files(self.task, p.snapshot(fetch(inline + examples + CHILDREN)), inline)
        self.assertEqual(files["cue-card.txt"].decode().count("Save All before retrying."), 1)
        self.assertNotIn("Recovery example only", files["cue-card.html"].decode())

    def test_recovery_with_ambiguous_sections_or_native_children_holds(self):
        for body in (
                ROUTE + "### Recovery for predictable slips\nFirst plan.\n### Other recovery\nSecond plan.\n",
                ROUTE + '### Recovery for predictable slips\n<page url="existing">Preserve child</page>\n'):
            with self.subTest(body=body), self.assertRaises(p.PackError):
                p.publication_files(self.task, p.snapshot(fetch(body)), ROUTE)

    def test_html_escapes_recovery_text_and_keeps_its_command_bytes(self):
        appendix = '### Recovery for predictable slips\n<script>alert("bad")</script>\n```bash\nprintf "safe\\n"\n```\n'
        files = p.publication_files(self.task, p.snapshot(fetch(ROUTE + appendix)), ROUTE)
        self.assertTrue(files["cue-card.txt"].decode().endswith(appendix))
        self.assertNotIn("<script>", files["cue-card.html"].decode())
        self.assertIn("&lt;script&gt;", files["cue-card.html"].decode())
        self.assertIn('printf &quot;safe\\n&quot;', files["cue-card.html"].decode())

    def test_repeat_publish_has_no_duplicate_versions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp).resolve() / "generated-cues"
            files = p.publication_files(self.task, self.page, ROUTE)
            first = p.safe_publish(root, self.task["neutral"], files)
            stat = (root / "tasks/test-workspace/receipt.json").stat()
            second = p.safe_publish(root, self.task["neutral"], files)
            self.assertEqual(first["operation"], "initialize")
            self.assertEqual(second["operation"], "noop")
            self.assertEqual(stat.st_mtime_ns, (root / "tasks/test-workspace/receipt.json").stat().st_mtime_ns)
            self.assertFalse((root / "history").exists())

    def test_changed_publication_keeps_the_previous_cloud_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp).resolve() / "generated-cues"
            old_files = p.publication_files(self.task, self.page, ROUTE)
            p.safe_publish(root, self.task["neutral"], old_files)
            newer = p.snapshot(fetch(revision="2026-10-07T22:18:13.842Z"))
            new_files = p.publication_files(self.task, newer, ROUTE)
            result = p.safe_publish(root, self.task["neutral"], new_files)
            self.assertEqual(result["operation"], "update")
            self.assertEqual(p.plain_tree(pathlib.Path(result["history"])), old_files)
            self.assertEqual(p.plain_tree(root / "tasks/test-workspace"), new_files)

    def test_edited_cues_receipts_and_extra_files_are_preserved(self):
        for edited in ("cue-card.txt", "receipt.json", "my-notes.txt"):
            with self.subTest(edited=edited), tempfile.TemporaryDirectory() as tmp:
                root = pathlib.Path(tmp).resolve() / "generated-cues"
                old = p.publication_files(self.task, self.page, ROUTE)
                p.safe_publish(root, self.task["neutral"], old)
                changed = root / "tasks/test-workspace" / edited
                changed.write_text("Human edit that must survive.")
                observed = p.plain_tree(changed.parent)
                with self.assertRaises(p.PackError):
                    p.safe_publish(root, self.task["neutral"], old)
                self.assertEqual(p.plain_tree(changed.parent), observed)

    def test_unmanaged_cue_destination_is_never_adopted_or_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp).resolve() / "generated-cues"
            target = root / "tasks/test-workspace"
            target.mkdir(parents=True)
            (target / "my-notes.txt").write_text("Keep my work.")
            with self.assertRaises(p.PackError):
                p.safe_publish(root, self.task["neutral"], p.publication_files(self.task, self.page, ROUTE))
            self.assertEqual((target / "my-notes.txt").read_text(), "Keep my work.")

    def test_symlink_roots_and_recording_project_roots_are_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            parent = pathlib.Path(tmp).resolve()
            real = parent / "real"
            real.mkdir()
            link = parent / "link"
            link.symlink_to(real, target_is_directory=True)
            for root in (link / "cues", parent / "Desktop/TaskWork/cues", parent / "TaskWorkInputs/cues"):
                with self.assertRaises(p.PackError):
                    p.safe_publish(root, self.task["neutral"], p.publication_files(self.task, self.page, ROUTE))
            self.assertEqual(list(real.iterdir()), [])

    def test_concurrent_publisher_lock_is_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp).resolve() / "generated-cues"
            (root / ".publish.lock").mkdir(parents=True)
            with self.assertRaises(p.PackError):
                p.safe_publish(root, self.task["neutral"], p.publication_files(self.task, self.page, ROUTE))
            self.assertTrue((root / ".publish.lock").is_dir())

    def test_wrong_source_bytes_modes_inventory_and_goal_stop_export(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp).resolve()
            source = root / "inputs/test-workspace"
            source.mkdir(parents=True)
            (root / "goals").mkdir()
            goal = root / self.task["goalFile"]
            goal.write_text(self.task["approvedGoal"] + "\n")
            starter = source / "README.md"
            starter.write_text("Synthetic starter, not a repaired result.\n")
            starter.chmod(0o644)
            project = {"sourceRepo": self.task["sourceRepo"], "commit": self.task["commit"],
                       "files": {"README.md": {"sha256": p.digest(starter.read_bytes()), "mode": 0o644}}}
            p.verify_source(self.task, project, root / "inputs", root)
            for change, restore in (
                    (lambda: starter.write_text("Changed work."), lambda: starter.write_text("Synthetic starter, not a repaired result.\n")),
                    (lambda: starter.chmod(0o755), lambda: starter.chmod(0o644)),
                    (lambda: (source / "new.txt").write_text("Human notes"), lambda: (source / "new.txt").unlink()),
                    (lambda: goal.write_text("Paraphrased Goal"), lambda: goal.write_text(self.task["approvedGoal"] + "\n"))):
                change()
                with self.assertRaises(p.PackError):
                    p.verify_source(self.task, project, root / "inputs", root)
                restore()
            project["commit"] = "c" * 40
            with self.assertRaises(p.PackError):
                p.verify_source(self.task, project, root / "inputs", root)


if __name__ == "__main__":
    unittest.main(verbosity=2)
