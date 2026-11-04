#!/usr/bin/env python3
"""Validate, plan and publish one recording route per registered task.

The authenticated Notion connector executes the returned update payload. This
program never asks for credentials, changes tracker gates or writes task work.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import importlib.util
import json
import os
import re
import shutil
import stat
import sys
import tempfile
import uuid
from pathlib import Path


HEADING = "### Recording sequence — follow this order"
NATIVE_BLANK_PAGE = "<blank-page>This page is blank and has no content.</blank-page>"
REGISTRY_VERSION = 1
NATIVE_CHILD = re.compile(r"<(?:page|database|folder|unknown|meeting-notes|transcript|custom-block|synced_block(?:_reference)?)(?:\s|/|>)")
GATES = ("Environment Review Gate", "No-Solution-Leak Gate", "Local Starter Gate",
         "Pre-Record Gate", "Recording QA Gate", "Submission Gate", "Workflow Checklist Gate")
IDENTITY_FIELDS = ("taskId", "notionPageId", "sourceRepo", "sourceCommit", "goalSha256",
                   "routeSha256", "workflowLane", "goalKind")


class PackError(ValueError):
    pass


def digest(data: bytes | str) -> str:
    return hashlib.sha256(data.encode("utf-8") if isinstance(data, str) else data).hexdigest()


def json_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def goal_text(task: dict) -> str:
    lane = task.get("workflowLane", "odin")
    if lane == "odin":
        return task["approvedGoal"]
    if lane == "bootcamp" and task.get("goalKind") == "candidate":
        return task["candidateGoal"]
    raise PackError("Unsupported workflow lane or missing candidate Goal evidence")


def load_json(path: Path) -> dict:
    if path.is_symlink() or not path.is_file():
        raise PackError(f"Expected a plain JSON file: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise PackError(f"Expected a JSON object: {path}")
    return data


def normalize_id(value: str) -> str:
    try:
        return str(uuid.UUID(value))
    except (ValueError, AttributeError) as exc:
        raise PackError("Invalid Notion page ID") from exc


def page_id_from_url(url: str) -> str:
    match = re.search(r"([a-fA-F0-9]{32}|[a-fA-F0-9]{8}(?:-[a-fA-F0-9]{4}){3}-[a-fA-F0-9]{12})(?:[/?#]|$)", url)
    if not match:
        raise PackError("Notion fetch did not supply a page UUID")
    return normalize_id(match.group(1))


def snapshot(value: dict) -> dict:
    """Accept a native Notion fetch result, including its MCP wrapper."""
    if value.get("isError"):
        raise PackError("Notion fetch returned an error")
    if "structuredContent" in value:
        value = value["structuredContent"]
    elif isinstance(value.get("content"), list):
        blocks = [c["text"] for c in value["content"] if c.get("type") == "text"]
        if len(blocks) != 1:
            raise PackError("Expected one complete Notion fetch text result")
        value = json.loads(blocks[0])
    if not isinstance(value, dict) or not isinstance(value.get("metadata"), dict) or value["metadata"].get("type") != "page":
        raise PackError("A fetched Notion page is required")
    if value.get("truncated") or value.get("metadata", {}).get("truncated"):
        raise PackError("Truncated Notion content cannot be published")
    if (value.get("unknown_block_count", 0) or value.get("unknown_block_ids")
            or value["metadata"].get("unknown_block_count", 0) or value["metadata"].get("unknown_block_ids")):
        raise PackError("Resolve unsupported Notion blocks before claiming a complete export")
    text = value.get("text", "")
    if not isinstance(text, str):
        raise PackError("Native Notion page text is required")
    contents = re.findall(r"<content>\n(.*?)\n</content>", text, flags=re.S)
    properties = list(re.finditer(r"<properties>\n(.*?)\n</properties>", text, flags=re.S))
    if len(properties) != 1:
        raise PackError("Notion fetch must contain exactly one complete properties section")
    props = json.loads(properties[0][1])
    if not isinstance(props, dict):
        raise PackError("Native Notion properties must be an object")
    revision = value.get("page_last_edited_at")
    if not isinstance(revision, str) or not revision:
        raise PackError("Native Notion page revision is required")
    page_id = page_id_from_url(value.get("url", ""))
    framing = text[:properties[0].start()] + text[properties[0].end():]
    blank_tags = re.findall(r"</?blank-page(?:\s[^>]*|)>", framing)
    if len(contents) == 1 and not blank_tags:
        body = contents[0]
    elif not contents and blank_tags == ["<blank-page>", "</blank-page>"]:
        # Native blank pages have no <content> section. Accept only the exact
        # complete native frame; never infer emptiness from absent content.
        preamble = re.match(
            r'\AHere is the result of "fetch" for the Page with URL ([^\s]+) as of '
            r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2}):\n', text)
        if preamble and page_id_from_url(preamble[1]) != page_id:
            raise PackError("Native fetch preamble targets a different page")
        native_frame = text[preamble.end():] if preamble else text
        outer = re.fullmatch(r'<page url="([^"]+)"(?: [^>\n]*)?>\n(.*?)\n</page>\s*', native_frame, re.S)
        frame = (r"(?:<ancestor-path>\n.*?\n</ancestor-path>\n)?"
                 + re.escape(properties[0][0]) + r"\n(?:<iconMetadata>[^\n]*</iconMetadata>\n)?"
                 + re.escape(NATIVE_BLANK_PAGE))
        without_outer = re.sub(r"<page(?:\s[^>\n]*)?>", "", framing, count=1)
        if (not outer or page_id_from_url(outer[1]) != page_id
                or len(re.findall(r"<page(?:\s|>)", framing)) != 1
                or re.search(r"</?content(?:\s|>)", framing)
                or NATIVE_CHILD.search(without_outer)
                or not re.fullmatch(frame, outer[2], re.S)):
            raise PackError("Ambiguous or incomplete native blank page; preserve it for review")
        body = ""
    else:
        raise PackError("Notion fetch must contain one complete content section or its exact native blank-page marker")
    if re.search(r"<unknown(?:\s|>)", body):
        raise PackError("Unsupported Notion content cannot be exported as complete")
    return {"pageId": page_id, "pageUrl": value["url"],
            "title": value.get("title", ""), "revision": revision, "body": body,
            "properties": props, "fetch": value}


def sequence_span(body: str, *, allow_missing: bool = False) -> tuple[int, int] | None:
    """Find the single top-level route, ignoring headings inside fenced code."""
    offset = 0
    fence = None
    starts = []
    headings = []
    for line in body.splitlines(keepends=True):
        bare = line.rstrip("\r\n")
        token = re.match(r"^(`{3,}|~{3,})", bare)
        if token:
            if fence is None:
                fence = token.group(1)[0]
            elif token.group(1)[0] == fence:
                fence = None
        elif fence is None:
            heading = re.match(r"^(#{1,3}) ", bare)
            if heading:
                headings.append(offset)
            if bare == HEADING:
                starts.append(offset)
        offset += len(line)
    if fence is not None:
        raise PackError("Unclosed code fence in operator page")
    if not starts and allow_missing:
        return None
    if len(starts) != 1:
        raise PackError("Expected exactly one primary recording sequence; review duplicate or missing packs")
    start = starts[0]
    end = next((n for n in headings if n > start), len(body))
    return start, end


def route_from_body(body: str) -> str:
    start, end = sequence_span(body)
    return body[start:end].rstrip() + "\n"


def managed_region(page: dict) -> dict | None:
    """Read Make's paragraph only after its original content digest matches.

    Native fetch may escape paragraph markdown or serialize its line breaks as
    <br>. Trying a representation is safe only when the complete original body
    SHA-256 matches; no other content is decoded or rewritten.
    """
    body = page["body"]
    marker = "TASKWORK_OPERATOR_PACK:" + page["pageId"]
    matches = list(re.finditer(r"(?:^|\n)(" + re.escape(marker) + r")(?=\n|<br>)", body))
    if not matches:
        return None
    if len(matches) != 1:
        raise PackError("Multiple managed paragraph markers; reconcile before publishing")
    start = matches[0].start(1)
    fragment = body[start:]
    limit = 220000
    ends = {len(fragment)} if len(fragment) <= limit else set()
    for match in re.finditer(r"\n|<br>", fragment[:limit]):
        ends.add(match.start())
        ends.add(match.end())
    pattern = re.compile(re.escape(marker) + r"\nREVISION:([a-f0-9]{64})\nCONTENT_SHA256:([a-f0-9]{64})\n([\s\S]*)")
    for end in sorted(ends, reverse=True):
        if end < 180:
            continue
        raw = fragment[:end]
        lines = raw.replace("<br>", "\n")
        decoded = re.sub(r"\\([\\*~`$\[\]<>{}|^#])", r"\1", lines)
        for candidate in dict.fromkeys((raw, lines, decoded)):
            match = pattern.fullmatch(candidate)
            if not match or digest(match[3]) != match[2]:
                continue
            route = validate_route(route_from_body(match[3]))
            before, after = body[:start], body[start + end:]
            if sequence_span(before + after, allow_missing=True) is not None:
                raise PackError("Managed paragraph and native route compete; preserve both for review")
            revision = page["properties"].get("Operator Pack Revision")
            if revision and revision != match[1]:
                raise PackError("Managed paragraph revision disagrees with its task ledger")
            return {"start": start, "end": start + end, "route": route,
                    "revision": match[1], "contentSha256": match[2]}
    raise PackError("Managed paragraph ownership digest does not match; preserve edited content")


def page_route(page: dict) -> str:
    owned = managed_region(page)
    return owned["route"] if owned else validate_route(route_from_body(page["body"]))


def page_route_span(page: dict) -> tuple[int, int]:
    owned = managed_region(page)
    return (owned["start"], owned["end"]) if owned else sequence_span(page["body"])


def validate_route(route: str) -> str:
    route = route.rstrip() + "\n"
    span = sequence_span(route)
    if span != (0, len(route)):
        raise PackError("Route file must contain only the one primary recording sequence")
    if NATIVE_CHILD.search(route):
        raise PackError("Managed route cannot move or remove native child content")
    steps = [int(n) for n in re.findall(r"^\*\*Step (\d+)\.\*\*", route, re.M)]
    numbered = [int(n) for n in re.findall(r"^(\d+)\. \*\*", route, re.M)]
    if steps and numbered:
        raise PackError("Route uses two competing numbered step sequences")
    steps = steps or numbered
    if len(steps) < 2 or steps != list(range(1, len(steps) + 1)):
        raise PackError("Recording steps must be contiguous and appear once in execution order")
    if "Start Recording" not in route or not re.search(r"stop TaskRecorder|Stop Recording", route, re.I):
        raise PackError("Route must include its real capture start and stop instructions")
    return route


def default_paths() -> dict[str, Path]:
    here = Path(__file__).resolve().parent
    root = here.parent if here.name == "scripts" else here
    runtime = root / "runtime" if (root / "runtime/runtime-manifest.json").exists() else root
    inputs = root / "inputs" if (root / "inputs").exists() else runtime.parent / "TaskWorkInputs"
    return {"registry": runtime / "task-registry.json", "manifest": runtime / "runtime-manifest.json",
            "inputs": inputs, "pages": runtime.parent / "packs/pages" if runtime.name == "runtime" else runtime / "packs/pages",
            "routes": runtime.parent / "packs/routes" if runtime.name == "runtime" else runtime / "packs/routes"}


def registry_context(registry_path: Path, manifest_path: Path) -> tuple[dict, dict]:
    registry, manifest = load_json(registry_path), load_json(manifest_path)
    module = registry_validator(registry_path.parent)
    tasks = module.validate_registry(registry)
    projects = module.validate_manifest(manifest, registry)
    if isinstance(projects, list):
        projects = {p["neutral"]: p for p in projects}
    return tasks, projects


def registry_validator(runtime: Path | None = None):
    module_path = (runtime or default_paths()["registry"].parent) / "TaskWorkRegistry.py"
    if module_path.is_symlink() or not module_path.is_file():
        raise PackError("The versioned TaskWorkRegistry.py validator is required")
    spec = importlib.util.spec_from_file_location("TaskWorkRegistry", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify_source(task: dict, project: dict, inputs: Path, goal_root: Path) -> None:
    if task["commit"] != project["commit"] or task["sourceRepo"] != project["sourceRepo"]:
        raise PackError("Registry repository pin disagrees with the verified source manifest")
    goal = goal_root / task["goalFile"]
    if goal.is_symlink() or not goal.is_file():
        raise PackError("The exact approved Goal file is missing")
    data = goal.read_bytes()
    if digest(data) != task["goalSha256"] or data.decode("utf-8").rstrip("\n") != goal_text(task):
        raise PackError("The exact Goal bytes disagree with the task registry")
    source = inputs / task["neutral"]
    if source.is_symlink() or not source.is_dir():
        raise PackError("Missing plain starter source directory")
    files = {}
    for path in source.rglob("*"):
        if path.is_symlink():
            raise PackError("Source inputs must not contain symlinks")
        if path.is_file():
            files[path.relative_to(source).as_posix()] = path
    if set(files) != set(project["files"]):
        raise PackError("Starter file inventory differs from the pinned manifest")
    for name, path in files.items():
        expected = project["files"][name]
        if digest(path.read_bytes()) != expected["sha256"] or stat.S_IMODE(path.stat().st_mode) != expected["mode"]:
            raise PackError(f"Starter bytes or mode differ: {task['neutral']}/{name}")


def verify_page(task: dict, page: dict, *, require_route: bool = True) -> None:
    if page["pageId"] != normalize_id(task["notionPageId"]):
        raise PackError("Notion page is not the registered task page")
    props = page["properties"]
    workflow = task.get("workflowLane", "odin")
    if workflow == "odin":
        if props.get("Approval ID") != task["id"]:
            raise PackError("Notion approval ID disagrees with the registry")
        if props.get("Approved Goal") != goal_text(task):
            raise PackError("Notion Approved Goal is not the verbatim registered Goal")
    elif workflow == "bootcamp":
        expected_id = "BOOTCAMP-" + page["pageId"].replace("-", "").upper()
        if task["id"] != expected_id or task.get("goalKind") != "candidate":
            raise PackError("Bootcamp identity must derive from its real candidate page")
        if any(key not in props or props[key] != "" for key in ("Approval ID", "Approved Goal")):
            raise PackError("Bootcamp candidate must not invent external approval or an approved Goal")
        if "internalBootcampAdmission" in task:
            try:
                registry_validator().validate_internal_bootcamp_admission(task, props)
            except ValueError as exc:
                raise PackError(str(exc)) from exc
            if props.get("Spec PR") != task.get("specPR") or props.get("Spec Path") != task.get("specPath"):
                raise PackError("Internal Bootcamp source must retain its actual reviewed spec")
        elif (props.get("Lane") not in ("Bootcamp", "Dual-candidate") or props.get("Stage") != "Candidate"
                  or props.get("Fit Gate") != "PASS" or props.get("Bootcamp Status") not in ("World building", "Ready to practice")):
            raise PackError("Bootcamp candidate lane, fit and world state do not support this preparation")
        if not task.get("buildIssue") or props.get("Build Issue") != task["buildIssue"]:
            raise PackError("Bootcamp source must retain its real canonical build issue")
        if task.get("studioTaskUrl"):
            raise PackError("Bootcamp candidate cannot claim an Odin Studio assignment")
    else:
        raise PackError("Unsupported task workflow lane")
    if props.get("Odin Goal") != goal_text(task):
        raise PackError("Notion Goal is not the verbatim registered task Goal")
    for key, expected in (("Starter Repository", task["sourceRepo"]), ("Starter Commit", task["commit"])):
        if props.get(key) and props[key] != expected:
            raise PackError(f"Notion {key} disagrees with the real registered source pin")
    if require_route:
        page_route(page)


def pack_identity(task: dict, route: str) -> dict:
    workflow = task.get("workflowLane", "odin")
    identity = {"taskId": task["id"], "notionPageId": normalize_id(task["notionPageId"]),
                "sourceRepo": task["sourceRepo"], "sourceCommit": task["commit"],
                "goalSha256": task["goalSha256"], "routeSha256": digest(route),
                "workflowLane": workflow, "goalKind": "approved" if workflow == "odin" else "candidate"}
    if "internalBootcampAdmission" in task:
        identity["internalBootcampAdmissionSha256"] = digest(json_bytes(task["internalBootcampAdmission"]))
    identity["packRevision"] = digest(json_bytes(identity))
    return identity


def plan_update(task: dict, page: dict, desired_route: str, *, initialize: bool = False) -> dict:
    verify_page(task, page, require_route=False)
    desired_route = validate_route(desired_route)
    owned = managed_region(page)
    if owned:
        if owned["route"] != desired_route:
            raise PackError("Make owns this managed paragraph; reconcile through its existing block owner")
        return {"version": 1, **pack_identity(task, desired_route), "operation": "noop",
                "expectedPageRevision": page["revision"], "expectedBodySha256": digest(page["body"]),
                "outsideBefore": page["body"][:owned["start"]], "outsideAfter": page["body"][owned["end"]:],
                "managedParagraphRevision": owned["revision"], "notionUpdate": None,
                "trackerPropertiesMutated": False, "recordingReady": False}
    span = sequence_span(page["body"], allow_missing=initialize)
    if span is None:
        before, old, after = "", "", page["body"]
        operation = "initialize"
        update = {"page_id": page["pageId"], "command": "insert_content", "position": {"type": "start"},
                  "content": desired_route, "allow_async": False}
    else:
        start, end = span
        before, old, after = page["body"][:start], page["body"][start:end], page["body"][end:]
        if NATIVE_CHILD.search(old):
            raise PackError("Refusing to replace native child content in a managed route")
        if old.rstrip() == desired_route.rstrip():
            operation, update = "noop", None
        else:
            operation = "update"
            update = {"page_id": page["pageId"], "command": "update_content",
                      "content_updates": [{"old_str": old, "new_str": desired_route}], "allow_async": False}
    return {"version": 1, **pack_identity(task, desired_route), "operation": operation,
            "expectedPageRevision": page["revision"], "expectedBodySha256": digest(page["body"]),
            "outsideBefore": before, "outsideAfter": after, "notionUpdate": update,
            "trackerPropertiesMutated": False, "recordingReady": False}


def assert_plan_current(plan: dict, task: dict, page: dict) -> None:
    """Call immediately before executing a generated Notion update payload."""
    verify_page(task, page, require_route=False)
    if plan.get("notionPageId") != page["pageId"] or plan.get("taskId") != task["id"]:
        raise PackError("Update plan targets another task")
    if (plan.get("sourceCommit") != task["commit"] or plan.get("goalSha256") != task["goalSha256"]
            or plan.get("workflowLane") != task.get("workflowLane", "odin")):
        raise PackError("Update plan predates the current source/Goal pin")
    admission_sha = (digest(json_bytes(task["internalBootcampAdmission"]))
                     if "internalBootcampAdmission" in task else None)
    if plan.get("internalBootcampAdmissionSha256") != admission_sha:
        raise PackError("Update plan predates the current internal Bootcamp authorization")
    if page["revision"] != plan.get("expectedPageRevision") or digest(page["body"]) != plan.get("expectedBodySha256"):
        raise PackError("Notion page changed after planning; fetch and replan before writing")


def verify_readback(plan: dict, task: dict, page: dict) -> str:
    verify_page(task, page)
    route = page_route(page)
    identity = pack_identity(task, route)
    if any(plan.get(key) != value for key, value in identity.items()):
        raise PackError("Notion readback does not match the planned task/source/Goal/route")
    start, end = page_route_span(page)
    owned = managed_region(page)
    if owned and plan.get("managedParagraphRevision") != owned["revision"]:
        raise PackError("Managed paragraph revision changed after planning; reconcile the existing cloud owner")
    if page["body"][:start].rstrip() != plan.get("outsideBefore", "").rstrip():
        raise PackError("Unrelated content before the route changed; review and replan")
    if page["body"][end:].lstrip() != plan.get("outsideAfter", "").lstrip():
        raise PackError("Unrelated content after the route changed; review and replan")
    return route


def render_route(text: str) -> str:
    """Escape all content before a small, dependency-free cue-card rendering."""
    result, prose, code, language = [], [], None, ""
    def flush():
        if prose:
            result.append("<p>" + "<br>".join(prose) + "</p>")
            prose.clear()
    for line in text.splitlines():
        if line.startswith("```"):
            flush()
            if code is None:
                code, language = [], line[3:]
            else:
                result.append('<pre data-language="' + html.escape(language, quote=True) + '"><code>'
                              + html.escape("\n".join(code)) + "</code></pre>")
                code = None
        elif code is not None:
            code.append(line)
        elif line.startswith("### "):
            flush()
            result.append("<h2>" + html.escape(line[4:]) + "</h2>")
        elif not line:
            flush()
        else:
            safe = html.escape(line)
            safe = re.sub(r"`([^`]+)`", r"<code>\1</code>", safe)
            safe = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", safe)
            prose.append(safe)
    flush()
    if code is not None:
        raise PackError("Unclosed code fence in route")
    return "\n".join(result)


def recovery_appendix(page: dict) -> str:
    """Keep the page's separate recovery instructions with its printable route."""
    _, route_end = page_route_span(page)
    headings, fence, offset = [], None, 0
    for line in page["body"].splitlines(keepends=True):
        bare = line.rstrip("\r\n")
        token = re.match(r"^(`{3,}|~{3,})", bare)
        if token:
            if fence is None:
                fence = token.group(1)[0]
            elif token.group(1)[0] == fence:
                fence = None
        elif fence is None:
            heading = re.match(r"^#{1,3} (.+)", bare)
            if heading:
                headings.append((offset, heading[1]))
        offset += len(line)
    candidates = [(index, start) for index, (start, title) in enumerate(headings)
                  if start >= route_end and re.search(r"\brecover(?:y|ies)\b", title, re.I)]
    if not candidates:
        return ""
    if len(candidates) != 1:
        raise PackError("Multiple recovery appendices; review before publishing a standalone cue")
    index, start = candidates[0]
    end = headings[index + 1][0] if index + 1 < len(headings) else len(page["body"])
    appendix = page["body"][start:end].rstrip() + "\n"
    if NATIVE_CHILD.search(appendix):
        raise PackError("Recovery appendix contains native child content; preserve it outside the cue")
    return appendix


def publication_files(task: dict, page: dict, route: str, cloud_proof: dict | None = None) -> dict[str, bytes]:
    verify_page(task, page)
    if page_route(page) != route:
        raise PackError("Only the freshly fetched cloud route may be exported")
    props = page["properties"]
    if any(props.get(key) != "__YES__" for key in ("Environment Review Gate", "No-Solution-Leak Gate")):
        raise PackError("Source review and no-solution-leak evidence are required before cue publication")
    cloud = None
    if cloud_proof is not None:
        if (cloud_proof.get("version") != 1 or cloud_proof.get("starterCommits", {}).get(task["neutral"]) != task["commit"]
                or not re.fullmatch(r"[a-f0-9]{40}", cloud_proof.get("sourceCommit", ""))
                or not str(cloud_proof.get("runId", "")).isdigit() or not cloud_proof.get("checks")):
            raise PackError("Cloud evidence does not match the registered source pin")
        expected = f"https://github.com/{cloud_proof.get('repository')}/actions/runs/{cloud_proof['runId']}"
        if cloud_proof.get("runUrl") != expected:
            raise PackError("Cloud run link does not match its recorded identity")
        cloud = {"runId": str(cloud_proof["runId"]), "runUrl": expected,
                 "preparationCommit": cloud_proof["sourceCommit"], "proofSha256": digest(json_bytes(cloud_proof))}
    identity = pack_identity(task, route)
    appendix = recovery_appendix(page)
    cue = route + ("\n" + appendix if appendix else "")
    header = f"OFF-SCREEN ONLY — PRINT OR USE A SECOND DEVICE\n\n{page['title']}\nWorkspace: ~/Desktop/TaskWork/{task['neutral']}.code-workspace\n"
    txt = header + "\n" + cue
    document = '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width">' \
               '<title>' + html.escape(page["title"]) + '</title><style>body{max-width:900px;margin:2rem auto;padding:0 1rem;font:18px/1.55 system-ui}' \
               'pre{background:#eef1f5;padding:1rem;white-space:pre-wrap}code{font-family:monospace}strong{font-weight:700}</style>' \
               '<body><p><strong>OFF-SCREEN ONLY — PRINT OR USE A SECOND DEVICE</strong></p><h1>' \
               + html.escape(page["title"]) + '</h1><p>Workspace: <code>~/Desktop/TaskWork/' \
               + html.escape(task["neutral"]) + '.code-workspace</code></p>' + render_route(cue) + '</body></html>\n'
    goal_name = "approved-goal.txt" if task.get("workflowLane", "odin") == "odin" else "candidate-goal.txt"
    files = {"cue-card.txt": txt.encode("utf-8"), "cue-card.html": document.encode("utf-8"),
             "notion-snapshot.json": json_bytes(page["fetch"]), "notion-snapshot.txt": page["body"].encode("utf-8"),
             goal_name: (goal_text(task) + "\n").encode("utf-8")}
    receipt = {"version": 1, **identity, "pageUrl": page["pageUrl"], "pageLastEditedAt": page["revision"],
               "pageBodySha256": digest(page["body"]), "sourceReviewed": True,
               "cloudEvidence": cloud, "cloudPrepared": cloud is not None,
               "recorderExecuted": False, "setupVerified": False, "recordingReady": False,
               "practiceReady": False, "externalApprovalClaimed": task.get("workflowLane", "odin") == "odin",
               "trackerStateAtExport": {key: props.get(key) for key in GATES},
               "files": {name: digest(data) for name, data in files.items()}}
    files["receipt.json"] = json_bytes(receipt)
    return files


def plain_tree(directory: Path) -> dict[str, bytes]:
    if directory.is_symlink() or not directory.is_dir():
        raise PackError("Publication destination must be a plain directory")
    files = {}
    for path in directory.rglob("*"):
        if path.is_symlink():
            raise PackError("Publication destination contains a symlink; preserve and inspect it")
        if path.is_file():
            files[path.relative_to(directory).as_posix()] = path.read_bytes()
    return files


def safe_publish(output: Path, neutral: str, files: dict[str, bytes]) -> dict:
    """Atomically replace only this publisher's verified output, with history."""
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", neutral):
        raise PackError("Unsafe task workspace name")
    output = output.absolute()
    # Never turn an existing task/workspace folder into a publication root.
    if any(part in {"TaskWork", "TaskWorkInputs", "inputs"} for part in output.parts):
        raise PackError("Cue publication must stay outside recording/source project roots")
    for parent in (output, *output.parents):
        if parent.is_symlink():
            raise PackError("Publication ancestors must not be symlinks")
    output.mkdir(parents=True, exist_ok=True, mode=0o755)
    lock = output / ".publish.lock"
    try:
        lock.mkdir(mode=0o700)
    except FileExistsError as exc:
        raise PackError("Another publication is active; preserve its lock and retry later") from exc
    try:
        tasks = output / "tasks"
        if tasks.is_symlink():
            raise PackError("Publication task directory must not be a symlink")
        tasks.mkdir(exist_ok=True, mode=0o755)
        target = tasks / neutral
        state = output / "state"
        if state.is_symlink():
            raise PackError("Publication state directory must not be a symlink")
        state.mkdir(exist_ok=True, mode=0o755)
        owner = state / f"{neutral}.json"
        if owner.is_symlink():
            raise PackError("Publication state must be a plain file")
        previous = None
        if target.exists() or target.is_symlink():
            old = plain_tree(target)
            if not owner.is_file():
                raise PackError("Existing cue directory has no publisher ownership receipt")
            ownership = load_json(owner)
            if (ownership.get("version") != 1 or ownership.get("neutral") != neutral
                    or ownership.get("files") != {name: digest(data) for name, data in old.items()}):
                raise PackError("Existing cue files or receipt were edited; preserve them and resolve off-screen")
            if old == files:
                return {"operation": "noop", "path": str(target), "files": len(files)}
            try:
                receipt = json.loads(old["receipt.json"])
                expected = receipt["files"]
            except (KeyError, TypeError, ValueError) as exc:
                raise PackError("Existing cue directory is not managed by this publisher") from exc
            if set(old) != {*expected, "receipt.json"} or any(digest(old[name]) != sha for name, sha in expected.items()):
                raise PackError("Existing cue files were edited; preserve them and resolve off-screen")
            old_identity = {key: receipt[key] for key in IDENTITY_FIELDS}
            if "internalBootcampAdmissionSha256" in receipt:
                old_identity["internalBootcampAdmissionSha256"] = receipt["internalBootcampAdmissionSha256"]
            if digest(json_bytes(old_identity)) != receipt.get("packRevision"):
                raise PackError("Existing publisher receipt was edited; preserve it")
            archive = output / "history" / neutral
            if (output / "history").is_symlink() or archive.is_symlink():
                raise PackError("Publication history must not be a symlink")
            archive.mkdir(parents=True, exist_ok=True, mode=0o755)
            previous = archive / (receipt["packRevision"] + "-" + digest(old["receipt.json"])[:16])
            if previous.exists() or previous.is_symlink():
                if plain_tree(previous) != old:
                    raise PackError("Publication history key collision; preserve all files")
                previous = archive / (previous.name + "-" + uuid.uuid4().hex)
        elif owner.exists():
            raise PackError("Publisher state exists without its cue directory; inspect incomplete synchronization")
        stage = Path(tempfile.mkdtemp(prefix=f".{neutral}-", dir=tasks))
        state_stage = state / f".{neutral}-{uuid.uuid4().hex}.json"
        try:
            os.chmod(stage, 0o755)
            for name, data in files.items():
                path = stage / name
                path.write_bytes(data)
                os.chmod(path, 0o644)
            state_stage.write_bytes(json_bytes({"version": 1, "neutral": neutral,
                                               "files": {name: digest(data) for name, data in files.items()}}))
            os.chmod(state_stage, 0o644)
            if previous is not None:
                target.rename(previous)
            try:
                stage.rename(target)
                state_stage.replace(owner)
            except BaseException:
                if target.exists():
                    target.rename(stage)
                if previous is not None:
                    previous.rename(target)
                raise
        finally:
            if stage.exists():
                shutil.rmtree(stage)
            if state_stage.exists():
                state_stage.unlink()
        return {"operation": "update" if previous else "initialize", "path": str(target),
                "history": str(previous) if previous else None, "files": len(files)}
    finally:
        lock.rmdir()


def select_task(tasks: dict, selector: str) -> dict:
    matches = [task for task in tasks.values() if selector in (task["neutral"], task["id"])]
    if len(matches) != 1:
        raise PackError("Select one registered task by stable task ID or neutral workspace name")
    return matches[0]


def main(argv: list[str] | None = None) -> int:
    defaults = default_paths()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("validate", "plan", "assert-current", "publish"))
    parser.add_argument("--registry", type=Path, default=defaults["registry"])
    parser.add_argument("--manifest", type=Path, default=defaults["manifest"])
    parser.add_argument("--inputs-dir", type=Path, default=defaults["inputs"])
    parser.add_argument("--pages-dir", type=Path, default=defaults["pages"])
    parser.add_argument("--routes-dir", type=Path, default=defaults["routes"])
    parser.add_argument("--task")
    parser.add_argument("--page-json", type=Path, help="Fresh native Notion fetch result, not a handwritten page")
    parser.add_argument("--route-file", type=Path)
    parser.add_argument("--plan-json", type=Path)
    parser.add_argument("--initialize", action="store_true", help="Allow first insertion when no primary route exists")
    parser.add_argument("--cloud-proof", type=Path, help="Evidence from an independently verified cloud bundle")
    parser.add_argument("--output", type=Path, help="Dedicated off-screen cue output root")
    args = parser.parse_args(argv)
    tasks, projects = registry_context(args.registry, args.manifest)
    selected = [select_task(tasks, args.task)] if args.task else list(tasks.values())
    if args.command != "validate" and len(selected) != 1:
        raise PackError("This operation requires --task")
    if args.command != "validate" and args.page_json is None:
        raise PackError("Supply --page-json from a fresh Notion fetch; committed snapshots are historical evidence")
    results = []
    for task in selected:
        verify_source(task, projects[task["neutral"]], args.inputs_dir, args.registry.parent)
        page = snapshot(load_json(args.page_json or args.pages_dir / f"{task['neutral']}.json"))
        route_path = args.route_file or args.routes_dir / f"{task['neutral']}.md"
        if route_path.is_symlink() or not route_path.is_file():
            raise PackError("Expected a plain reviewed route file")
        desired = validate_route(route_path.read_text(encoding="utf-8"))
        if args.command == "validate":
            verify_page(task, page)
            if page_route(page) != desired:
                raise PackError("Reviewed route file differs from the exported cloud page")
            results.append({**pack_identity(task, desired), "valid": True, "recordingReady": False})
        elif args.command == "plan":
            print(json_bytes(plan_update(task, page, desired, initialize=args.initialize)).decode("utf-8"), end="")
        elif args.command == "assert-current":
            if args.plan_json is None:
                raise PackError("--plan-json is required")
            assert_plan_current(load_json(args.plan_json), task, page)
            print(json.dumps({"current": True, "taskId": task["id"]}))
        elif args.command == "publish":
            if args.output is None:
                raise PackError("--output is required; source and Recorder project roots are refused")
            if args.plan_json is None:
                raise PackError("--plan-json is required; publish only a verified Notion readback")
            route = verify_readback(load_json(args.plan_json), task, page)
            proof = load_json(args.cloud_proof) if args.cloud_proof else None
            print(json.dumps(safe_publish(args.output, task["neutral"], publication_files(task, page, route, proof))))
    if args.command == "validate":
        print(json.dumps({"tasks": results, "valid": True, "recordingReady": False}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (PackError, ValueError, KeyError, OSError) as exc:
        print(f"HOLD: {exc}", file=sys.stderr)
        raise SystemExit(1)
