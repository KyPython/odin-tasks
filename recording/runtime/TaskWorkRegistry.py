"""Validate the reviewed task catalog and its immutable source-file inventory."""

import hashlib
import json
from pathlib import PurePosixPath
import re


PROFILES = {"python-stdlib", "python-pytest", "pnpm-workspace", "node-stdlib"}
ODIN_ADMISSION_FIELDS = ("Lane", "Stage", "Fit Gate", "Approval ID", "Approved Goal")


def validate_internal_bootcamp_admission(task, properties=None):
    """Validate independent user authorization without changing Odin eligibility.

    This is reviewed administrative evidence, not a human assessment or external
    approval. Registration additionally checks the actual receipt and merged PR.
    Offline consumers retain the same identity and original policy-field guards.
    """
    admission = task.get("internalBootcampAdmission")
    require(isinstance(admission, dict) and set(admission) == {
        "version", "authority", "scope", "authorizationRef", "authorizationTextSha256",
        "notionPageId", "goalSha256", "sourceRepo", "sourceCommit", "originalOdinFields",
        "kiroReview", "specMerge"}, "Incomplete internal Bootcamp authorization")
    require(type(admission["version"]) is int and admission["version"] == 1 and admission["authority"] == "explicit-user"
            and admission["scope"] == "internal-bootcamp-world-preparation",
            "Internal Bootcamp requires explicit user world-preparation authorization")
    require(isinstance(admission["authorizationRef"], str) and admission["authorizationRef"].strip()
            and len(admission["authorizationRef"]) <= 500,
            "Missing actual user authorization reference")
    require(isinstance(admission.get("authorizationTextSha256"), str)
            and re.fullmatch(r"[a-f0-9]{64}", admission["authorizationTextSha256"]) is not None,
            "Missing exact user authorization text digest")
    for key, expected in (("notionPageId", task.get("notionPageId")), ("goalSha256", task.get("goalSha256")),
                          ("sourceRepo", task.get("sourceRepo")), ("sourceCommit", task.get("commit"))):
        require(admission.get(key) == expected, "Internal Bootcamp authorization identity differs: " + key)
    original = admission["originalOdinFields"]
    require(isinstance(original, dict) and set(original) == set(ODIN_ADMISSION_FIELDS)
            and all(value is None or isinstance(value, str) for value in original.values()),
            "Preserve the original Odin policy fields exactly")
    require(original["Approval ID"] == "" and original["Approved Goal"] == "",
            "Internal Bootcamp cannot replace or invent external approval")
    if properties is not None:
        require(all(properties.get(key) == original[key] for key in ODIN_ADMISSION_FIELDS),
                "Original Odin policy fields changed after internal Bootcamp authorization")
    review = admission["kiroReview"]
    require(isinstance(review, dict) and set(review) == {
        "receiptSha256", "receiptCommit", "receiptPath", "executionId", "inventorySha256", "specCommit", "specFiles"},
        "Incomplete actual Kiro review evidence")
    for key in ("receiptSha256", "inventorySha256"):
        require(isinstance(review.get(key), str) and re.fullmatch(r"[a-f0-9]{64}", review[key]) is not None,
                "Missing exact Kiro review digest: " + key)
    require(isinstance(review["executionId"], str)
            and re.fullmatch(r"(?:sess_)?[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}", review["executionId"]),
            "Actual Kiro execution identity is required")
    require(isinstance(review["receiptCommit"], str) and re.fullmatch(r"[a-f0-9]{40}", review["receiptCommit"])
            and review["receiptPath"] == "cloud/kiro-receipts/" + review["executionId"] + ".json",
            "Kiro evidence must retain its immutable canonical private receipt pointer")
    require(isinstance(review.get("specCommit"), str) and re.fullmatch(r"[a-f0-9]{40}", review["specCommit"]) is not None,
            "Actual reviewed spec commit is required")
    spec_path = safe_relative(task.get("specPath", ""))
    require(spec_path.startswith("specs/odin-bootcamp/"), "Internal Bootcamp needs its real spec directory")
    files = review["specFiles"]
    require(isinstance(files, dict) and set(files) == {
        spec_path + "/requirements.md", spec_path + "/design.md", spec_path + "/tasks.md"},
        "Actual Kiro requirements, design and tasks evidence is required")
    require(all(isinstance(value, str) and re.fullmatch(r"[a-f0-9]{64}", value) is not None for value in files.values()),
            "Missing reviewed spec file hashes")
    merge = admission["specMerge"]
    require(isinstance(merge, dict) and set(merge) == {"prUrl", "commit", "mergedAt", "mergedBy"}
            and merge.get("prUrl") == task.get("specPR")
            and isinstance(merge.get("prUrl"), str)
            and re.fullmatch(r"https://github.com/KyPython/ai-governance/pull/[1-9][0-9]*", merge["prUrl"])
            and isinstance(merge.get("commit"), str) and re.fullmatch(r"[a-f0-9]{40}", merge["commit"])
            and merge.get("mergedBy") == "KyPython"
            and isinstance(merge.get("mergedAt"), str)
            and re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z", merge["mergedAt"]),
            "Actual human-merged spec evidence is required")
    require(not task.get("studioTaskUrl"), "Internal Bootcamp cannot claim a Studio assignment")
    return admission


def goal_text(task):
    return task.get("candidateGoal") if task.get("workflowLane", "odin") == "bootcamp" else task.get("approvedGoal")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load_json(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, f"Duplicate catalog key: {key}")
            result[key] = value
        return result
    return json.loads(path.read_text(), object_pairs_hook=unique)


def safe_relative(value):
    require(isinstance(value, str) and value and "\\" not in value, "Invalid relative path")
    path = PurePosixPath(value)
    require(not path.is_absolute() and path.as_posix() == value and
            all(part not in ("", ".", "..", ".git") for part in path.parts), "Unsafe relative path")
    return value


def baseline_generated_files(check, profile):
    """Permit only a declared local Python module's explicit build JSON output."""
    files = check.get("generatedFiles", [])
    require(isinstance(files, list) and all(isinstance(value, str) for value in files)
            and len(files) == len(set(files)), "Invalid generated-file declaration")
    argv = check["argv"]
    if not files:
        require("generatedFiles" not in check and not any(arg == "--output" or arg.startswith("--output=") for arg in argv),
                "Baseline output must have an explicit reviewed generatedFiles declaration")
        return []
    require(profile == "python-stdlib" and len(files) == 1 and len(argv) == 5
            and argv[:2] == ["{python}", "-m"]
            and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+", argv[2])
            and argv[3] == "--output" and argv[4] == files[0],
            "Generated files require the exact reviewed local Python module/output command")
    relative = safe_relative(files[0])
    require(relative.startswith("build/") and relative.endswith(".json"),
            "Generated baseline files must remain JSON under build/")
    return files


def validate_registry(registry):
    require(isinstance(registry, dict) and registry.get("version") == 1, "Unsupported task registry")
    tasks = registry.get("tasks")
    require(isinstance(tasks, list) and tasks, "The reviewed task registry is empty")
    result, ids, pages = {}, set(), set()
    for task in tasks:
        require(isinstance(task, dict), "Invalid task entry")
        neutral = task.get("neutral", "")
        require(isinstance(neutral, str) and len(neutral) <= 80 and re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", neutral), "Unsafe workspace name")
        require(neutral not in result, "Duplicate task workspace")
        task_id = task.get("id", "")
        page = task.get("notionPageId", "")
        require(isinstance(page, str) and re.fullmatch(r"[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}", page) and page not in pages, "Invalid or duplicate Notion task page")
        workflow_lane = task.get("workflowLane", "odin")
        require(workflow_lane in ("odin", "bootcamp"), "Unsupported task workflow lane")
        if workflow_lane == "odin":
            require(isinstance(task_id, str) and re.fullmatch(r"ODIN-[A-F0-9]{32}", task_id), "Invalid Odin approval ID")
            require(not task.get("candidateGoal"), "Odin input must retain the actual approved Goal")
            require("internalBootcampAdmission" not in task, "Odin input cannot use internal Bootcamp authorization")
        else:
            require(task_id == "BOOTCAMP-" + page.replace("-", "").upper(), "Bootcamp identity must derive from its existing task page")
            require(task.get("goalKind") == "candidate" and not task.get("approvedGoal"), "Bootcamp candidate must not invent an approved Goal")
        require(task_id not in ids, "Duplicate task identity")
        require(isinstance(task.get("lane"), str) and task["lane"].strip(), "Missing professional lane")
        original = task.get("originalName", "")
        require(isinstance(original, str) and re.fullmatch(r"[A-Za-z0-9_.-]+", original), "Invalid source repository name")
        require(task.get("sourceRepo") == "https://github.com/KyPython/" + original, "Unexpected source repository")
        require(re.fullmatch(r"[a-f0-9]{40}", task.get("commit", "")) is not None, "A source commit must be pinned")
        require(task.get("goalFile") == "goals/" + neutral + ".txt", "Unexpected Goal input path")
        require(re.fullmatch(r"[a-f0-9]{64}", task.get("goalSha256", "")) is not None, "Missing exact Goal hash")
        require(isinstance(goal_text(task), str) and goal_text(task).strip(), "Missing exact task Goal")
        if "internalBootcampAdmission" in task:
            validate_internal_bootcamp_admission(task)
        profile = task.get("dependencyProfile")
        require(profile in PROFILES, "Unsupported dependency profile; review an adapter before registering this task")
        versions = task.get("dependencyVersions", {})
        require(isinstance(versions, dict), "Invalid dependency version map")
        require(set(versions) == {"python-stdlib": set(), "python-pytest": {"pytest"}, "pnpm-workspace": {"pnpm", "turbo"}, "node-stdlib": {"node"}}[profile], "Review an adapter for additional toolchain version requirements")
        if profile == "node-stdlib":
            require(versions.get("node") == "22.22.0", "Node built-ins require the reviewed public Node 22.22.0 runtime")
        if profile == "python-pytest":
            require(isinstance(versions.get("pytest"), str) and versions["pytest"], "Missing pinned pytest version")
            safe_relative(task.get("requirementsFile", ""))
        if profile == "pnpm-workspace":
            require(isinstance(versions.get("pnpm"), str) and versions["pnpm"] and isinstance(versions.get("turbo"), str) and versions["turbo"], "Missing pinned pnpm/Turbo versions")
        roots = task.get("dependencyRoots", [])
        require(isinstance(roots, list) and len(roots) == len(set(roots)), "Invalid dependency roots")
        for root in roots:
            safe_relative(root)
            require(root == ".venv" or root == "node_modules" or root.endswith("/node_modules"), "Unexpected dependency root")
        require(profile != "python-stdlib" or not roots, "Standard-library setup cannot ignore dependency folders")
        require(profile != "node-stdlib" or not roots, "Node built-ins cannot install dependency folders")
        require(profile != "python-pytest" or roots == [".venv"], "Pytest setup must manage exactly .venv")
        require(profile != "pnpm-workspace" or "node_modules" in roots and ".venv" not in roots, "pnpm setup must manage its node_modules folders")
        baseline = task.get("baseline")
        require(isinstance(baseline, list) and baseline, "Missing reviewed baseline commands")
        for check in baseline:
            require(isinstance(check, dict), "Invalid baseline check")
            argv = check.get("argv")
            require(isinstance(argv, list) and argv and all(isinstance(arg, str) and arg for arg in argv), "Invalid baseline argv")
            require(argv[0] in ("{python}", "{venvPython}", "{corepack}", "{node}", "sh"), "Unsupported baseline executable")
            require((profile == "node-stdlib") == (argv[0] == "{node}"), "Node built-in baselines require their own reviewed profile")
            exits = check.get("allowedExitCodes", [0])
            require(isinstance(exits, list) and exits and all(type(code) is int and 0 <= code <= 255 for code in exits), "Invalid baseline exit contract")
            require(isinstance(check.get("contains", ""), str), "Invalid baseline output contract")
            overrides = check.get("env", {})
            require(isinstance(overrides, dict) and overrides in ({}, {"PYTHONPATH": "src"}), "Unsupported baseline environment; review an adapter")
            require(profile != "node-stdlib" or not overrides, "Node built-in baselines cannot use Python environment overrides")
            baseline_generated_files(check, profile)
        result[neutral] = task
        ids.add(task_id)
        pages.add(page)
    return result


def validate_manifest(manifest, registry):
    tasks = validate_registry(registry)
    require(isinstance(manifest, dict) and manifest.get("version") == 1, "Unsupported source manifest")
    projects = manifest.get("projects")
    require(isinstance(projects, list) and projects, "Empty source manifest")
    seen = set()
    for project in projects:
        require(isinstance(project, dict), "Invalid source project")
        name = project.get("neutral")
        require(name in tasks and name not in seen, "Unknown or duplicate source project")
        task = tasks[name]
        require(all(project.get(key) == task[key] for key in ("originalName", "sourceRepo", "commit")), "Task and source provenance differ")
        files = project.get("files")
        require(isinstance(files, dict) and files, "Missing source file inventory")
        for relative, entry in files.items():
            safe_relative(relative)
            require(not any(part in (".venv", "node_modules") for part in PurePosixPath(relative).parts), "Dependencies cannot be starter inputs")
            require(isinstance(entry, dict) and entry.get("mode") in (0o644, 0o755) and re.fullmatch(r"[a-f0-9]{64}", entry.get("sha256", "")) is not None, "Invalid source hash/mode")
        seen.add(name)
    require(seen == set(tasks), "Task registry and source manifest do not describe the same tasks")
    return projects


def source_count(manifest):
    return sum(len(project["files"]) for project in manifest["projects"])


def select_projects(projects, selector=None):
    if selector is None:
        return projects
    selected = [project for project in projects if project["neutral"] == selector]
    require(len(selected) == 1, "The selected task is not registered exactly once")
    return selected


def verify_goal(task, path):
    require(path.is_file() and not path.is_symlink(), "Exact Goal input is missing or unsafe")
    content = path.read_bytes()
    require(hashlib.sha256(content).hexdigest() == task["goalSha256"] and content.decode("utf-8").strip() == goal_text(task), "Exact task Goal input differs from the reviewed registry")
    return content
