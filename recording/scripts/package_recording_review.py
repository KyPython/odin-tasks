#!/usr/bin/env python3
"""Package an existing human attempt for an advisory review. Never run task code.

Only explicitly selected, invoking-user-owned attempt files are copied. The
original recording ZIP is hashed and copied as opaque bytes, never extracted,
renamed in place, repaired or recompressed. A model's review is evidence, not
external approval, a payment decision or an unaided-transfer credential.
"""
import argparse
import difflib
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import stat
import sys
import tempfile
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent if HERE.name == "scripts" else HERE
REGISTRY_MODULES = ROOT.parent if ROOT.name == "process" else ROOT / "runtime" if HERE.name == "scripts" else HERE
sys.path.insert(0, str(REGISTRY_MODULES))
sys.path.insert(0, str(HERE))
from TaskWorkRegistry import load_json, safe_relative, validate_manifest, validate_registry, verify_goal
from recording_pack import route_from_body

ROLES = {"recordingArchive": "recording", "video": "video", "audio": "audio",
         "deliverablesArchive": "deliverables", "metadata": "metadata",
         "commandLog": "logs", "transcript": "transcript", "recordingLog": "recorder-log"}
DESCRIPTOR_KEYS = {"version", "attemptId", "guidanceMode", "priorWork", "declaredDurationSeconds",
                   "finalWorkspace", *ROLES}
IGNORED_DIRS = {".git", ".venv", "node_modules", "__pycache__", ".pytest_cache", ".turbo"}
STATUSES = {"observed_met", "observed_gap", "unverified", "not_applicable"}
EVIDENCE_CLASSES = {"guided": "guided_practice", "unaided": "self_reported_unaided", "unknown": "unverified"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()


def digest(path):
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def regular(path, owned=False, directory=False):
    path = Path(path).absolute()
    require(not any(p.is_symlink() for p in (path, *path.parents)), "Symlink path is unsafe: " + str(path))
    info = path.stat()
    require(stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode),
            "Expected a regular " + ("directory: " if directory else "file: ") + str(path))
    require(not owned or info.st_uid == os.getuid(),
            "Attempt evidence must belong to the invoking user; run from its real account: " + str(path))
    return path


def file_record(path):
    return {"sha256": digest(path), "bytes": path.stat().st_size}


def tree(root, owned=False, omit_dependencies=False):
    root = regular(root, owned=owned, directory=True)
    files = {}
    for current, directories, names in os.walk(root, followlinks=False):
        directories[:] = sorted(d for d in directories if not omit_dependencies or d not in IGNORED_DIRS)
        for name in directories:
            regular(Path(current) / name, owned=owned, directory=True)
        for name in sorted(names):
            path = regular(Path(current) / name, owned=owned)
            relative = safe_relative(path.relative_to(root).as_posix())
            files[relative] = path
    return files


def archive_headers(path):
    """Read only the central directory; do not extract or rewrite the archive."""
    members, seen = [], set()
    with zipfile.ZipFile(path) as archive:
        require(len(archive.infolist()) <= 100000, "Archive inventory exceeds the review bound; no partial export")
        for entry in archive.infolist():
            name = entry.filename.rstrip("/")
            safe_relative(name)
            require(name not in seen and not any(ord(c) < 32 for c in name)
                    and not re.match(r"^[A-Za-z]:", name), "Duplicate or ambiguous archive member")
            mode = (entry.external_attr >> 16) & 0xFFFF
            require(not stat.S_ISLNK(mode) and not (entry.flag_bits & 1), "Symlink/encrypted archive member is unsupported")
            require(stat.S_IFMT(mode) in (0, stat.S_IFREG, stat.S_IFDIR), "Special archive member is unsupported")
            seen.add(name)
            members.append({"path": entry.filename, "bytes": entry.file_size,
                            "compressedBytes": entry.compress_size, "crc32": f"{entry.CRC:08x}"})
    return {"members": members, "inventoryOnly": True, "crcContentValidationPerformed": False,
            "pngCount": sum(x["path"].lower().endswith(".png") for x in members),
            "eventJsonlPresent": any(Path(x["path"]).name == "event.jsonl" for x in members)}


def command_records(path):
    records = load_json(path)
    require(isinstance(records, list), "Command evidence must be a JSON array, not shell text")
    for entry in records:
        require(isinstance(entry, dict) and isinstance(entry.get("argv"), list) and entry["argv"]
                and all(isinstance(x, str) for x in entry["argv"]), "Command evidence requires literal argv")
        require(type(entry.get("exitCode")) is int and isinstance(entry.get("cwd"), str)
                and all(isinstance(entry.get(key), str) for key in ("stdout", "stderr")),
                "Command evidence requires cwd, exitCode, stdout and stderr")
    return records


def steps(route):
    fence, result, current = None, [], None
    for line in route.splitlines(keepends=True):
        token = re.match(r"^(`{3,}|~{3,})", line)
        if token:
            fence = token[1][0] if fence is None else None if fence == token[1][0] else fence
        match = None if fence else re.match(r"^(?:\*\*Step (\d+)\.\*\*|(\d+)\. \*\*)", line)
        if match:
            current = {"step": int(match[1] or match[2]), "expectedText": ""}
            result.append(current)
        if current:
            current["expectedText"] += line
    require(result and [x["step"] for x in result] == list(range(1, len(result) + 1)), "Canonical route is not contiguous")
    return result


def prepare(args):
    descriptor_path = regular(args.attempt, owned=True)
    attempt = load_json(descriptor_path)
    require(isinstance(attempt, dict) and attempt.get("version") == 1 and not set(attempt) - DESCRIPTOR_KEYS,
            "Unsupported/unknown attempt descriptor fields")
    require(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}", attempt.get("attemptId", "")), "Unsafe attempt ID")
    require(attempt.get("guidanceMode") in ("guided", "unaided", "unknown"), "Declare guided, unaided or unknown")
    require(isinstance(attempt.get("priorWork"), str) and attempt["priorWork"].strip(), "Declare actual prior work/guidance; do not infer it")
    if "declaredDurationSeconds" in attempt:
        require(type(attempt["declaredDurationSeconds"]) in (int, float) and math.isfinite(attempt["declaredDurationSeconds"])
                and attempt["declaredDurationSeconds"] > 0, "Invalid declared duration")
    runtime = regular(args.runtime, directory=True)
    registry = load_json(regular(runtime / "task-registry.json"))
    manifest = load_json(regular(runtime / "runtime-manifest.json"))
    tasks = validate_registry(registry)
    projects = validate_manifest(manifest, registry)
    require(args.task in tasks, "Select an existing registered task")
    task = tasks[args.task]
    project = next(p for p in projects if p["neutral"] == args.task)
    goal = verify_goal(task, regular(runtime / task["goalFile"]))
    source_root = regular(Path(args.inputs) / args.task, directory=True)
    source = tree(source_root)
    require(set(source) == set(project["files"]), "Pinned starter inventory changed")
    for relative, path in source.items():
        require(digest(path) == project["files"][relative]["sha256"]
                and stat.S_IMODE(path.stat().st_mode) == project["files"][relative]["mode"], "Pinned starter bytes/mode changed: " + relative)
    plan_root = regular(Path(args.plans) / args.task, directory=True)
    identity = load_json(regular(plan_root / "identity.json"))
    proof = load_json(regular(plan_root / "cloud-verification.json"))
    route_path = regular(plan_root / "recording-sequence.md")
    route = route_path.read_text()
    binding = {"neutral": task["neutral"], "taskId": task["id"], "sourceRepo": task["sourceRepo"],
               "sourceCommit": task["commit"], "goalSha256": task["goalSha256"],
               "routeSha256": digest(route_path), "workflowLane": task.get("workflowLane", "odin")}
    require(all(identity.get(k) == v for k, v in binding.items()), "Worked reference identity differs from task")
    require(route_from_body(regular(plan_root / "walkthrough.md").read_text()) == route, "Worked route differs from its walkthrough")
    require(proof.get("status") == "PASS" and proof.get("sourceCommit") == task["commit"]
            and proof.get("goalSha256") == task["goalSha256"] and proof.get("checks")
            and proof.get("solutionPatchSha256") == digest(regular(plan_root / "solution.patch"))
            and proof.get("recorderExecuted") is False and proof.get("recordingWorkspaceModified") is False,
            "Reference proof is incomplete or misbound; it cannot substitute for human execution")
    inputs = {"task/starter/" + k: v for k, v in source.items()}
    inputs["task/goal.txt"] = runtime / task["goalFile"]
    for name in ("walkthrough.md", "recording-sequence.md", "identity.json", "solution.patch", "cloud-verification.json"):
        inputs["reference/" + name] = regular(plan_root / name)
    for path in sorted(plan_root.glob("*.patch")):
        inputs["reference/" + path.name] = regular(path)
    for name in ("cloud-proof.json", "cloud-sync-receipt.json", "local-portability-proof.json"):
        path = runtime / name
        if path.exists():
            inputs["preparation-evidence/" + name] = regular(path)
    facts, selected_paths = {}, [descriptor_path]
    for role, folder in ROLES.items():
        if role not in attempt:
            facts[role] = {"state": "not_provided", "humanObservation": "unverified"}
            continue
        require(isinstance(attempt[role], str) and Path(attempt[role]).is_absolute(), "Attempt paths must be explicit and absolute")
        path = regular(attempt[role], owned=True)
        safe_relative(path.name)
        destination = "attempt/" + folder + "/" + path.name
        inputs[destination] = path
        selected_paths.append(path)
        facts[role] = {"state": "provided", "artifact": destination, **file_record(path),
                       "humanObservation": "unverified"}
        if role in ("recordingArchive", "deliverablesArchive"):
            facts[role]["zipHeaders"] = archive_headers(path)
        if role == "commandLog":
            facts[role]["submittedCommandCount"] = len(command_records(path))
            facts[role]["executionIndependentlyObserved"] = False
    workspace = None
    if "finalWorkspace" in attempt:
        require(isinstance(attempt["finalWorkspace"], str) and Path(attempt["finalWorkspace"]).is_absolute(), "Workspace must be explicit and absolute")
        workspace = regular(attempt["finalWorkspace"], owned=True, directory=True)
        require(workspace != source_root, "Select the actual attempt workspace, never the pinned starter")
        selected_paths.append(workspace)
        for relative, path in tree(workspace, owned=True, omit_dependencies=True).items():
            inputs["attempt/final-workspace/" + relative] = path
        facts["finalWorkspace"] = {"state": "provided", "artifact": "attempt/final-workspace/",
                                   "dependencyFoldersOmitted": sorted(IGNORED_DIRS), "humanObservation": "unverified"}
    else:
        facts["finalWorkspace"] = {"state": "not_provided", "humanObservation": "unverified"}
    if args.skill_map:
        skill_path = regular(args.skill_map)
        skill_map = load_json(skill_path)
        require(skill_map.get("version") == 1 and isinstance(skill_map.get("skills"), dict)
                and isinstance(skill_map.get("tasks"), dict) and args.task in skill_map["tasks"], "Unsupported skills registry")
        mapping = skill_map["tasks"][args.task]
        require(all(mapping.get(key) == binding[key] for key in ("taskId", "sourceCommit", "goalSha256", "routeSha256", "workflowLane")),
                "Skill mapping differs from the reviewed task identity")
        require(isinstance(mapping.get("requiredSkills"), list)
                and all(x.get("skillId") in skill_map["skills"] for x in mapping["requiredSkills"]), "Incomplete skill mapping")
        inputs["learning/skill-map.json"] = skill_path
        facts["skillMap"] = {"artifact": "learning/skill-map.json", "proposalOnly": True}
    else:
        skill_map = None
    public_attempt = {k: v for k, v in attempt.items() if k not in ROLES and k != "finalWorkspace"}
    public_attempt["evidenceClass"] = EVIDENCE_CLASSES[attempt["guidanceMode"]]
    facts["sameAttemptCorrespondence"] = "unverified"
    facts["archiveBytePreservation"] = "verified_by_hash_copy_only"
    facts["videoTimingAudioPrivacyAndHumanExecution"] = "unverified"
    return task, project, binding, goal, route, inputs, facts, public_attempt, selected_paths, workspace, source, skill_map


def workspace_diff(source, final):
    lines, changed = [], []
    for relative in sorted(set(source) | set(final)):
        old = source[relative].read_bytes() if relative in source else b""
        new = final[relative].read_bytes() if relative in final else b""
        if old == new and (relative in source) == (relative in final):
            continue
        record = {"path": relative, "change": "added" if relative not in source else "deleted" if relative not in final else "modified",
                  "beforeSha256": hashlib.sha256(old).hexdigest() if relative in source else None,
                  "afterSha256": hashlib.sha256(new).hexdigest() if relative in final else None}
        try:
            a, b = old.decode("utf-8"), new.decode("utf-8")
            require("\x00" not in a + b, "Binary text")
            delta = difflib.unified_diff(a.splitlines(True), b.splitlines(True),
                        fromfile="starter/" + relative if relative in source else "/dev/null",
                        tofile="attempt/" + relative if relative in final else "/dev/null")
            for line in delta:
                lines.append(line if line.endswith("\n") else line + "\n\\ No newline at end of file\n")
        except (UnicodeDecodeError, ValueError):
            record["binaryDifference"] = True
        changed.append(record)
    return "".join(lines).encode(), changed


def verify_bundle(root):
    root = regular(root, directory=True)
    manifest = load_json(regular(root / "manifest.json"))
    require(manifest.get("version") == 1 and isinstance(manifest.get("files"), dict), "Invalid bundle manifest")
    actual = tree(root)
    require(set(actual) == set(manifest["files"]) | {"manifest.json"}, "Bundle inventory changed; preserve/review it")
    for relative, record in manifest["files"].items():
        safe_relative(relative)
        require(file_record(actual[relative]) == record, "Bundle file changed: " + relative)
    core = {k: v for k, v in manifest.items() if k != "bundleId"}
    require(hashlib.sha256(encoded(core)).hexdigest() == manifest["bundleId"], "Bundle identity changed")
    return manifest


def package(args):
    task, project, binding, goal, route, inputs, facts, attempt, selected, workspace, source, skill_map = prepare(args)
    output = Path(args.output).absolute()
    parent = regular(output.parent, owned=True, directory=True)
    require(not output.is_symlink(), "Output cannot be a symlink")
    protected = [Path(args.runtime).absolute(), Path(args.inputs).absolute(), Path(args.plans).absolute(),
                 *selected, *(path.parent for path in selected if path.is_file())]
    require(not any(output == path or path in output.parents or output in path.parents for path in protected),
            "Review output must be separate from all sources and human attempts")
    rubric_path = regular(ROOT / "review/rubric.json")
    schema_path = regular(ROOT / "review/report.schema.json")
    rubric = load_json(rubric_path)
    inputs.update({"rubric.json": rubric_path, "report.schema.json": schema_path,
                   "reviewer-prompt.txt": regular((ROOT / "docs/REVIEWER-PROMPT.txt") if (ROOT / "docs/REVIEWER-PROMPT.txt").is_file()
                                                  else ROOT / "REVIEWER-PROMPT.txt")})
    evidence = {"version": 1, "task": binding, "attempt": attempt, "facts": facts,
                "referenceEvidencePurpose": "Expected prepared plan only; never proof of recorded human execution",
                "canonicalSteps": steps(route), "commandsExecutedByPackager": [], "externalUploadPerformed": False}
    generated = {"task/identity.json": encoded(binding), "task/source-inventory.json": encoded(project),
                 "evidence-index.json": encoded(evidence)}
    if workspace:
        patch, changes = workspace_diff(source, tree(workspace, owned=True, omit_dependencies=True))
        generated["attempt/changes.patch"] = patch
        generated["attempt/changes.json"] = encoded({"changes": changes, "observedHumanExecution": False})
    statuses = [{"id": c["id"], "status": "not_applicable" if task.get("workflowLane", "odin") not in c["lanes"] else "unverified",
                 "reason": "Not an external-lane requirement for this practice attempt." if task.get("workflowLane", "odin") not in c["lanes"] else "No reviewer observation yet.",
                 "evidence": []} for c in rubric["criteria"]]
    template = {"version": 1, "bundleId": "REPLACE_WITH_MANIFEST_BUNDLE_ID", "task": binding,
                "attemptId": attempt["attemptId"], "guidanceMode": attempt["guidanceMode"],
                "evidenceClass": attempt["evidenceClass"],
                "reviewer": {"name": "", "model": "", "capabilities": {"video": False, "audio": False},
                             "coverage": {"video": "none", "audio": "none"}},
                "advisoryOnly": True, "externalApproval": "not_assessed", "payment": "not_assessed",
                "mastery": "not_established", "unaidedTransferEstablished": False,
                "criteria": statuses,
                "stepCoverage": [{"step": s["step"], "status": "unverified", "reason": "No observation yet.", "evidence": []} for s in evidence["canonicalSteps"]],
                "skillFeedback": [], "practiceNext": {"state": "insufficient_evidence", "keep": [], "focus": [], "nextAttempt": ""},
                "limitations": ["No actual recording has been reviewed by this packager.",
                                "Reference/cloud success does not establish human authorship, unaided skill, external acceptance or earnings."]}
    generated["report-template.json"] = encoded(template)
    generated["README.md"] = ("# Advisory recording review bundle\n\n"
        "Read reviewer-prompt.txt, evidence-index.json and rubric.json first. Use report-template.json with report.schema.json. "
        "Replace the template bundleId with manifest.json's actual bundleId. Write the completed report outside this immutable bundle.\n\n"
        "task/ is the exact unworked starter and Goal. reference/ is AI-authored prepared guidance and tested expected results. "
        "attempt/ is only explicitly supplied human-attempt evidence. Every original recording ZIP retains its basename and bytes. "
        "ZIP header inventories do not establish readable frames, media timing, same-attempt correspondence, capture quality, privacy or human execution. "
        "No code, test, archive member or supplied command has been executed. No files have been uploaded.\n\n"
        "For a text-only model, provide the file bundle and optionally a truthful timestamped transcript; screen/audio/privacy/timing judgments remain unverified. "
        "For a capable media model, attach the actual video/audio separately if its interface cannot read them inside a folder. "
        "Review the entire relevant media before a whole-attempt claim; sampled review supports sampled claims only.\n").encode()
    fingerprints = {name: file_record(path) for name, path in inputs.items()}
    files = {**fingerprints, **{name: {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)} for name, data in generated.items()}}
    manifest = {"version": 1, "task": binding, "attempt": attempt, "files": files,
                "recordingArchivesPreserved": True, "humanAttemptModified": False, "commandsExecuted": False,
                "externalUploadPerformed": False, "reviewPerformed": False}
    manifest["bundleId"] = hashlib.sha256(encoded(manifest)).hexdigest()
    if output.exists():
        previous = verify_bundle(output)
        require(previous == manifest, "Existing bundle differs; preserve it and choose another output")
        return {"action": "noop", "output": str(output), "bundleId": manifest["bundleId"], "files": len(files)}
    stage = Path(tempfile.mkdtemp(prefix=".recording-review-", dir=parent))
    try:
        for name, path in inputs.items():
            target = stage / safe_relative(name)
            target.parent.mkdir(parents=True, exist_ok=True)
            with path.open("rb") as incoming, target.open("xb") as outgoing:
                shutil.copyfileobj(incoming, outgoing, 1024 * 1024)
            target.chmod(0o644)
            require(file_record(target) == fingerprints[name] == file_record(path), "Evidence changed during copy: " + name)
        for name, data in {**generated, "manifest.json": encoded(manifest)}.items():
            target = stage / safe_relative(name)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            target.chmod(0o644)
        verify_bundle(stage)
        require(not output.exists(), "Another process prepared this destination; preserve it")
        stage.rename(output)
    finally:
        if stage.exists():
            shutil.rmtree(stage)
    return {"action": "packaged", "output": str(output), "bundleId": manifest["bundleId"], "files": len(files),
            "humanAttemptModified": False, "reviewPerformed": False, "externalUploadPerformed": False}


def schema_validate(value, schema, root=None, location="report"):
    """Validate the shipped schema's small stdlib-only JSON Schema subset."""
    root = root or schema
    if "$ref" in schema:
        ref = schema["$ref"]
        require(ref.startswith("#/"), "Only internal schema references are supported")
        target = root
        for part in ref[2:].split("/"):
            target = target[part.replace("~1", "/").replace("~0", "~")]
        return schema_validate(value, target, root, location)
    expected = schema.get("type")
    predicates = {"object": lambda x: isinstance(x, dict), "array": lambda x: isinstance(x, list),
                  "string": lambda x: isinstance(x, str), "boolean": lambda x: type(x) is bool,
                  "integer": lambda x: type(x) is int, "number": lambda x: type(x) in (int, float) and math.isfinite(x)}
    require(not expected or expected in predicates and predicates[expected](value), "Invalid schema type at " + location)
    if "const" in schema:
        constant = schema["const"]
        require(value == constant and (type(constant) is not bool or type(value) is bool), "Invalid fixed field at " + location)
    if "enum" in schema:
        require(value in schema["enum"], "Unsupported value at " + location)
    if isinstance(value, dict):
        require(set(schema.get("required", [])) <= set(value), "Missing report fields at " + location)
        props = schema.get("properties", {})
        require(schema.get("additionalProperties", True) or not set(value) - set(props), "Unknown report fields at " + location)
        for key in value:
            if key in props:
                schema_validate(value[key], props[key], root, location + "." + key)
    if isinstance(value, list):
        require(len(value) >= schema.get("minItems", 0) and len(value) <= schema.get("maxItems", len(value)), "Invalid list length at " + location)
        for i, item in enumerate(value):
            if "items" in schema:
                schema_validate(item, schema["items"], root, location + f"[{i}]")
    if isinstance(value, str):
        require(len(value) >= schema.get("minLength", 0) and ("pattern" not in schema or re.search(schema["pattern"], value)), "Invalid string at " + location)
    if type(value) in (int, float) and "minimum" in schema:
        require(value >= schema["minimum"], "Invalid numeric bound at " + location)


def validate_report(bundle, report_path):
    manifest = verify_bundle(bundle)
    report = load_json(regular(report_path, owned=True))
    index = load_json(Path(bundle) / "evidence-index.json")
    rubric = load_json(Path(bundle) / "rubric.json")
    schema_validate(report, load_json(Path(bundle) / "report.schema.json"))
    require(report.get("version") == 1 and report.get("bundleId") == manifest["bundleId"]
            and report.get("task") == manifest["task"] and report.get("attemptId") == manifest["attempt"]["attemptId"]
            and report.get("guidanceMode") == manifest["attempt"]["guidanceMode"], "Report identity/attempt does not match bundle")
    require(report["evidenceClass"] == EVIDENCE_CLASSES[report["guidanceMode"]], "Declared assistance class cannot establish independent provenance")
    require(report.get("advisoryOnly") is True and all(report.get(k) == "not_assessed" for k in ("externalApproval", "payment"))
            and report.get("mastery") == "not_established" and report.get("unaidedTransferEstablished") is False,
            "Advisory review cannot award approval, payment, mastery or unaided-transfer credit")
    reviewer = report.get("reviewer", {})
    caps, coverage = reviewer.get("capabilities", {}), reviewer.get("coverage", {})
    require(set(caps) == {"video", "audio"} and all(type(x) is bool for x in caps.values()), "Declare actual media capabilities")
    require(set(coverage) == {"video", "audio"} and all(x in ("none", "sampled", "full") for x in coverage.values()), "Declare actual media coverage")
    require(all(caps[k] or coverage[k] == "none" for k in caps), "Cannot claim unseen media coverage")

    def observations(entry, criterion=None):
        require(entry.get("status") in STATUSES and isinstance(entry.get("reason"), str) and entry["reason"].strip(), "Each finding needs a status and reason")
        evidence = entry.get("evidence")
        require(isinstance(evidence, list), "Each finding needs explicit evidence")
        observed = entry["status"] in ("observed_met", "observed_gap")
        require(not observed or evidence, "Observed findings require actual evidence")
        modes = set()
        for item in evidence:
            artifact = item.get("artifact", "")
            require(artifact in manifest["files"] and isinstance(item.get("observation"), str) and item["observation"].strip(), "Evidence must cite an existing bundle artifact and concrete observation")
            kind = item.get("kind")
            require(kind in ("file", "video", "audio", "submitted_transcript", "submitted_log"), "Unsupported evidence kind")
            modes.add(kind)
            if kind in ("video", "audio"):
                role = "video" if kind == "video" else "audio"
                fact = index["facts"].get(role, {})
                allowed = {fact.get("artifact")}
                if kind == "audio":
                    allowed.add(index["facts"].get("video", {}).get("artifact"))
                require(caps[role] and coverage[role] != "none" and artifact in allowed, "Media observations require that supplied media and actual reviewer access")
                start, end = item.get("timestampStart"), item.get("timestampEnd")
                require(type(start) in (int, float) and type(end) in (int, float)
                        and math.isfinite(start) and math.isfinite(end) and 0 <= start <= end,
                        "Media observations require finite second timestamps")
        if observed and criterion:
            required = criterion["observedEvidence"]
            require(any(mode in modes for mode in required), "Text/preparation evidence cannot establish this criterion")
            if entry["status"] == "observed_met":
                require(set(criterion.get("requiredModalities", [])) <= modes, "All required media modalities must actually be observed")
            if entry["status"] == "observed_met" and criterion.get("wholeAttempt"):
                for mode in required:
                    if mode in modes:
                        require(coverage[mode] == "full", "Sampled review cannot establish a whole-attempt condition")

    criteria = report.get("criteria", [])
    require(isinstance(criteria, list) and len(criteria) == len(rubric["criteria"])
            and {x.get("id") for x in criteria} == {c["id"] for c in rubric["criteria"]}, "Report must cover every rubric criterion exactly once")
    for criterion in rubric["criteria"]:
        entry = next(x for x in criteria if x["id"] == criterion["id"])
        observations(entry, criterion)
        if manifest["task"]["workflowLane"] not in criterion["lanes"]:
            require(entry["status"] == "not_applicable", "Do not impose external Odin requirements on Bootcamp practice")
        if criterion["id"] == "learning.unaided_transfer":
            require(entry["status"] in ("unverified", "not_applicable"), "This advisory review never awards unaided-transfer completion")
    covered = report.get("stepCoverage", [])
    expected = [x["step"] for x in index["canonicalSteps"]]
    require(isinstance(covered, list) and [x.get("step") for x in covered] == expected, "Report must map the actual canonical steps in order")
    for entry in covered:
        observations(entry, {"observedEvidence": ["video"], "wholeAttempt": False})
    feedback = report.get("skillFeedback", [])
    require(isinstance(feedback, list), "Skill feedback must be proposal-only entries")
    skills = None
    if "learning/skill-map.json" in manifest["files"]:
        skills = load_json(Path(bundle) / "learning/skill-map.json")
    for gap in feedback:
        require(isinstance(gap.get("skillId"), str) and gap["skillId"].strip()
                and gap.get("finding") in ("needs-practice", "unassessed", "observed")
                and gap.get("observationKind") in ("guided", "unaided")
                and gap.get("remediationTask") == manifest["task"]["neutral"], "Invalid skill-feedback proposal")
        require(skills is not None and gap["skillId"] in {x["skillId"] for x in skills["tasks"][gap["remediationTask"]]["requiredSkills"]},
                "Skill feedback must use the supplied existing mapping; do not invent skill IDs")
        require(manifest["attempt"]["guidanceMode"] == gap["observationKind"], "Guided/unknown evidence cannot become unaided feedback")
        require(gap["finding"] != "unassessed" or gap["evidence"] == [], "Unassessed skill feedback cannot claim observations")
        proxy = {"status": "unverified" if gap["finding"] == "unassessed" else "observed_gap" if gap["finding"] == "needs-practice" else "observed_met",
                 "reason": "Skill feedback proposal", "evidence": gap.get("evidence")}
        # The skills importer uses the same timestamp fields, without a kind field.
        proxy["evidence"] = [{**x, "kind": "audio" if x["artifact"] == index["facts"].get("audio", {}).get("artifact")
                             or not caps["video"] and caps["audio"] else "video"}
                             for x in (proxy["evidence"] or [])]
        observations(proxy, {"observedEvidence": ["video", "audio"], "wholeAttempt": False})
    require(report.get("practiceNext", {}).get("state") in ("insufficient_evidence", "revisit_guided_practice", "ready_for_next_guided_attempt"), "Practice recommendation cannot be an external verdict")
    if report["practiceNext"]["state"] == "ready_for_next_guided_attempt":
        require(any(x["status"] == "observed_met" for x in covered),
                "Missing/unverified human execution cannot support a readiness recommendation")
    return {"status": "VALID_ADVISORY_REPORT", "bundleId": manifest["bundleId"], "criteria": len(criteria),
            "externalApproval": "not_assessed", "humanFieldsMutated": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    pack = commands.add_parser("package")
    pack.add_argument("--task", required=True)
    pack.add_argument("--attempt", type=Path, required=True)
    pack.add_argument("--output", type=Path, required=True)
    pack.add_argument("--runtime", type=Path, default=Path("/Users/Shared/TaskWorkRuntime"))
    pack.add_argument("--inputs", type=Path, default=Path("/Users/Shared/TaskWorkInputs"))
    pack.add_argument("--plans", type=Path, default=Path("/Users/Shared/TaskWorkPlans"))
    pack.add_argument("--skill-map", type=Path)
    validate = commands.add_parser("validate-report")
    validate.add_argument("--bundle", type=Path, required=True)
    validate.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = package(args) if args.command == "package" else validate_report(args.bundle, args.report)
        print(json.dumps(result, ensure_ascii=False))
    except (ValueError, OSError, zipfile.BadZipFile, KeyError, TypeError) as exc:
        parser.exit(1, "HOLD: " + str(exc) + "\n")


if __name__ == "__main__":
    main()
