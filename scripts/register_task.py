#!/usr/bin/env python3
"""Plan or register one real pinned starter without replacing reviewed tasks.

No starter command, dependency installer, Git hook, cloud mutation or recording
action is executed. A fresh complete Notion fetch supplies approval and Goal;
GitHub supplies the immutable source tree. Registration stays on this branch.
"""
import argparse
import base64
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime"))
from TaskWorkRegistry import (load_json, safe_relative, validate_manifest, validate_registry,
                              validate_internal_bootcamp_admission, baseline_generated_files, goal_text, verify_goal, PROFILES)
from recording_pack import snapshot


def require(condition, message):
    if not condition:
        raise ValueError(message)


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def run(argv, cwd=None):
    result = subprocess.run(argv, cwd=cwd, capture_output=True, timeout=180)
    require(result.returncode == 0, "Read-only Git/GitHub source operation failed: " + " ".join(argv[:3]))
    return result.stdout


def inventory(folder):
    require(folder.is_dir() and not folder.is_symlink(), "Starter input directory is missing or unsafe")
    result = {}
    for path in sorted(folder.rglob("*")):
        require(not path.is_symlink(), "Starter inputs cannot contain symlinks")
        if path.is_dir():
            continue
        require(path.is_file(), "Starter inputs cannot contain special files")
        relative = safe_relative(path.relative_to(folder).as_posix())
        result[relative] = {"sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                            "mode": stat.S_IMODE(path.stat().st_mode)}
    return result


def reviewed_state(root):
    registry_path = root / "runtime/task-registry.json"
    manifest_path = root / "runtime/runtime-manifest.json"
    for path in (registry_path, manifest_path):
        require(path.is_file() and not path.is_symlink(), "Reviewed catalog files must be regular files")
    registry, manifest = load_json(registry_path), load_json(manifest_path)
    tasks = validate_registry(registry)
    projects = validate_manifest(manifest, registry)
    require({path.name for path in (root / "inputs").iterdir()} == set(tasks), "Unmanaged starter input exists")
    for project in projects:
        require(inventory(root / "inputs" / project["neutral"]) == project["files"],
                "An existing pinned starter changed; preserve it and review before registration")
        verify_goal(tasks[project["neutral"]], root / "runtime" / tasks[project["neutral"]]["goalFile"])
    return registry, manifest


def git_tree(repository, commit, destination, expected_url, *, local=False):
    require(re.fullmatch(r"[a-f0-9]{40}", commit) is not None, "A full lowercase source commit is required")
    require(repository.is_dir() and not repository.is_symlink(), "Expected a real source repository")
    remote = run(["git", "remote", "get-url", "origin"], repository).decode().strip()
    require(remote.removesuffix(".git") in (expected_url, expected_url.replace("https://github.com/", "git@github.com:")),
            "Source clone origin differs from the requested GitHub repository")
    actual = run(["git", "rev-parse", commit + "^{commit}"], repository).decode().strip()
    require(actual == commit, "Requested source commit was not resolved exactly")
    if local:
        require(run(["git", "rev-parse", "HEAD"], repository).decode().strip() == commit,
                "Local clone is not at the pinned source commit")
        require(not run(["git", "status", "--porcelain", "--untracked-files=all"], repository),
                "Local source clone has edits or untracked files; preserve it")
    entries = run(["git", "ls-tree", "-rz", "--full-tree", commit], repository).split(b"\0")
    files = {}
    destination.mkdir()
    for entry in entries:
        if not entry:
            continue
        header, raw_name = entry.split(b"\t", 1)
        mode, kind, blob = header.decode("ascii").split()
        relative = safe_relative(raw_name.decode("utf-8"))
        require(kind == "blob" and mode in ("100644", "100755"), "Review an adapter for symlink/submodule starter inputs")
        require(not any(part in (".venv", "node_modules") for part in Path(relative).parts),
                "Dependency trees cannot be registered as starter source")
        content = run(["git", "cat-file", "blob", blob], repository)
        path = destination / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        path.chmod(0o755 if mode == "100755" else 0o644)
        if local:
            original = repository / relative
            require(original.is_file() and not original.is_symlink() and original.read_bytes() == content
                    and stat.S_IMODE(original.stat().st_mode) == stat.S_IMODE(path.stat().st_mode),
                    "Local clone bytes/modes differ from its pinned Git tree")
        files[relative] = {"sha256": hashlib.sha256(content).hexdigest(), "mode": stat.S_IMODE(path.stat().st_mode)}
    require(files, "The source repository has no regular starter files")
    return files


def make_task(page, neutral, source_repo, commit, profile, setup):
    properties = page["properties"]
    require(not properties.get("Starter Repository") or properties["Starter Repository"] == source_repo,
            "Notion source repository contradicts the requested real source")
    require(not properties.get("Starter Commit") or properties["Starter Commit"] == commit,
            "Notion source commit contradicts the requested full pin")
    approval = properties.get("Approval ID")
    workflow_lane = setup.get("workflowLane", "odin")
    require(workflow_lane in ("odin", "bootcamp"), "Unsupported workflow lane")
    if workflow_lane == "odin":
        goal = properties.get("Approved Goal")
        require(isinstance(goal, str) and goal and goal == properties.get("Odin Goal"),
                "The exact Approved Goal and Odin Goal must already agree")
        require(properties.get("Lane", "") in ("", "Odin monetization"), "Notion row belongs to a different workflow lane")
    else:
        if "internalBootcampAdmission" not in setup:
            require(properties.get("Lane") in ("Bootcamp", "Dual-candidate") and properties.get("Stage") == "Candidate"
                    and properties.get("Fit Gate") == "PASS" and properties.get("Bootcamp Status") == "World building",
                    "Bootcamp registration requires the existing Candidate/PASS/World building handoff")
        require(not approval and not properties.get("Approved Goal"), "Bootcamp candidate cannot carry external Odin approval")
        goal = properties.get("Odin Goal")
        require(isinstance(goal, str) and goal.strip(), "Bootcamp candidate Goal is missing")
        approval = "BOOTCAMP-" + page["pageId"].replace("-", "").upper()
    lane = setup.get("lane")
    require(isinstance(lane, str) and lane.strip(), "Supply the task's reviewed professional lane")
    declared_lane = properties.get("Professional Lane")
    require(declared_lane is None or declared_lane == lane, "Professional lane contradicts the Notion source")
    goal_bytes = (goal + "\n").encode("utf-8")
    task = {"neutral": neutral, "originalName": source_repo.rsplit("/", 1)[1],
            "sourceRepo": source_repo, "commit": commit, "id": approval,
            "notionPageId": page["pageId"], "lane": lane,
            "goalFile": "goals/" + neutral + ".txt", "goalSha256": hashlib.sha256(goal_bytes).hexdigest(),
            "specPR": properties.get("Spec PR"), "specPath": properties.get("Spec Path"),
            "buildIssue": properties.get("Build Issue"),
            "manifestCommentId": setup.get("manifestCommentId", ""),
            "studioTaskUrl": setup.get("studioTaskUrl", ""),
            "dependencyProfile": profile, "dependencyVersions": setup.get("dependencyVersions", {}),
            "dependencyRoots": setup.get("dependencyRoots", []), "baseline": setup.get("baseline")}
    if profile == "python-pytest":
        task["requirementsFile"] = setup.get("requirementsFile")
    if workflow_lane == "odin":
        task["approvedGoal"] = goal
        require(all(isinstance(task[key], str) and task[key] for key in ("specPR", "specPath", "buildIssue", "studioTaskUrl")),
                "Real spec, build and Studio source references are required")
        require(task["studioTaskUrl"] in page["body"], "Studio task URL must exist in the complete Notion source")
    else:
        task.update(workflowLane="bootcamp", goalKind="candidate", candidateGoal=goal)
        task["specPR"] = task["specPR"] or ""
        task["studioTaskUrl"] = ""
        require(isinstance(task["buildIssue"], str) and re.fullmatch(r"https://github.com/KyPython/ai-governance/issues/[1-9][0-9]*", task["buildIssue"]),
                "A real canonical Bootcamp build issue is required")
        require(isinstance(task["specPath"], str) and task["specPath"].startswith("specs/odin-bootcamp/"), "Real Bootcamp spec path is required")
        if "internalBootcampAdmission" in setup:
            task["internalBootcampAdmission"] = setup["internalBootcampAdmission"]
            validate_internal_bootcamp_admission(task, properties)
    require(workflow_lane == "bootcamp" or "internalBootcampAdmission" not in setup,
            "Internal Bootcamp authorization cannot change Odin registration")
    comment = task["manifestCommentId"]
    require(not comment or isinstance(comment, str) and comment.isdecimal() and comment in str(properties),
            "Manifest comment reference is absent from Notion evidence")
    validate_registry({"version": 1, "tasks": [task]})
    return task, goal_bytes


def verify_internal_bootcamp_evidence(task, setup):
    """Read actual private review evidence and public human-merge provenance.

    No task execution, spec merge, property write or authorization synthesis is
    performed. The local receipt is an explicit reviewed administrative input.
    """
    admission = validate_internal_bootcamp_admission(task)
    review = admission["kiroReview"]
    receipt_name = setup.get("kiroReviewReceiptFile")
    require(isinstance(receipt_name, str) and receipt_name, "Supply the actual Kiro review receipt file")
    receipt_path = Path(receipt_name)
    require(receipt_path.is_file() and not receipt_path.is_symlink()
            and receipt_path.stat().st_size <= 4 * 1024 * 1024, "Expected a bounded plain Kiro review receipt")
    content = receipt_path.read_bytes()
    require(hashlib.sha256(content).hexdigest() == review["receiptSha256"], "Kiro review receipt bytes differ")
    receipt = load_json(receipt_path)
    published = json.loads(run(["gh", "api", "repos/KyPython/odin-recording-preparation/contents/"
                               + review["receiptPath"] + "?ref=" + review["receiptCommit"]]))
    require(published.get("type") == "file" and published.get("path") == review["receiptPath"]
            and published.get("encoding") == "base64" and isinstance(published.get("content"), str),
            "The actual immutable private Kiro receipt is missing")
    try:
        published_bytes = base64.b64decode("".join(published["content"].split()), validate=True)
    except ValueError as exc:
        raise ValueError("The private Kiro receipt content is not valid base64") from exc
    require(published_bytes == content, "Local Kiro receipt differs from its authenticated private source")
    require(receipt.get("version") == 1 and receipt.get("engine") == "kiro" and receipt.get("status") == "PASS",
            "Actual Kiro PASS receipt is required before registration")
    for key in ("executionId", "inventorySha256", "specCommit"):
        require(receipt.get(key) == review[key], "Actual Kiro receipt identity differs: " + key)
    bindings = receipt.get("bindings", {})
    binding = bindings.get(task["notionPageId"]) if isinstance(bindings, dict) else None
    require(isinstance(binding, dict) and all(binding.get(key) == expected for key, expected in (
        ("rowId", task["notionPageId"]), ("goalSha256", task["goalSha256"]),
        ("specPath", task["specPath"]), ("specPr", task["specPR"]))),
        "Actual Kiro receipt must bind the exact native row, Goal and spec")
    execution = receipt.get("executionEvidence")
    require(isinstance(execution, dict) and set(execution) == {
        "source", "executionTarget", "capturePath", "captureSha256"}
        and execution["source"] == "captured-kiro-cli" and execution["executionTarget"] in ("local", "cloud")
        and execution["capturePath"] == "cloud/kiro-receipts/" + review["executionId"] + ".capture.txt"
        and isinstance(execution["captureSha256"], str) and re.fullmatch(r"[a-f0-9]{64}", execution["captureSha256"]),
        "Actual captured Kiro execution evidence is required")
    captured = json.loads(run(["gh", "api", "repos/KyPython/odin-recording-preparation/contents/"
                              + execution["capturePath"] + "?ref=" + review["receiptCommit"]]))
    require(captured.get("type") == "file" and captured.get("path") == execution["capturePath"]
            and captured.get("encoding") == "base64" and isinstance(captured.get("content"), str),
            "The actual immutable Kiro CLI capture is missing")
    try:
        capture_bytes = base64.b64decode("".join(captured["content"].split()), validate=True)
    except ValueError as exc:
        raise ValueError("The Kiro CLI capture content is not valid base64") from exc
    require(capture_bytes.decode("utf-8").strip()
            and hashlib.sha256(capture_bytes).hexdigest() == execution["captureSha256"],
            "Actual Kiro CLI capture bytes differ from published evidence")
    paths = receipt.get("paths")
    require(isinstance(paths, dict), "Kiro per-file review evidence is missing")
    for path, sha in review["specFiles"].items():
        require(isinstance(paths.get(path), dict) and paths[path].get("status") == "PASS"
                and paths[path].get("sha256") == sha, "Kiro did not PASS the exact spec file: " + path)
    merged = json.loads(run(["gh", "pr", "view", task["specPR"], "--json",
                             "state,mergedAt,mergedBy,mergeCommit,headRefOid,baseRefName,files"]))
    expected = admission["specMerge"]
    require(merged.get("state") == "MERGED" and merged.get("mergedAt") == expected["mergedAt"]
            and merged.get("baseRefName") == "main"
            and isinstance(merged.get("mergedBy"), dict) and merged["mergedBy"].get("login") == "KyPython"
            and merged.get("headRefOid") == review["specCommit"]
            and isinstance(merged.get("mergeCommit"), dict) and merged["mergeCommit"].get("oid") == expected["commit"],
            "The actual spec PR is not merged by KyPython at its recorded commit")
    changed = {entry.get("path") for entry in merged.get("files", []) if isinstance(entry, dict)}
    require(set(review["specFiles"]) <= changed, "The human-merged PR does not contain every reviewed spec file")
    for path, sha in review["specFiles"].items():
        response = json.loads(run(["gh", "api", "repos/KyPython/ai-governance/contents/" + path
                                   + "?ref=" + expected["commit"]]))
        require(response.get("type") == "file" and response.get("path") == path
                and response.get("encoding") == "base64" and isinstance(response.get("content"), str),
                "The reviewed spec file is absent from the real merge commit")
        try:
            spec_bytes = base64.b64decode("".join(response["content"].split()), validate=True)
        except ValueError as exc:
            raise ValueError("The merged spec content is not valid base64") from exc
        require(hashlib.sha256(spec_bytes).hexdigest() == sha, "Merged spec bytes differ from Kiro-reviewed content: " + path)
        if path == task["specPath"] + "/requirements.md":
            text = spec_bytes.decode("utf-8").replace("\r\n", "\n")
            require(goal_text(task) in re.split(r"\n\s*\n", text),
                    "The merged requirements must retain the exact standalone task Goal")
            require("Task Factory row: https://app.notion.com/p/" + task["notionPageId"].replace("-", "") in text.splitlines(),
                    "The merged requirements must bind the exact native task row")


def verify_recipe(task, source):
    profile = task["dependencyProfile"]
    if profile == "python-pytest":
        path = source / task["requirementsFile"]
        require(path.is_file(), "Reviewed pytest requirements file is absent from the real source")
        require(re.search(r"(?m)^pytest==" + re.escape(task["dependencyVersions"]["pytest"]) + r"\s*$", path.read_text()) is not None,
                "Reviewed pytest version is not pinned by the real source")
    elif profile == "pnpm-workspace":
        package = load_json(source / "package.json")
        require(package.get("packageManager") == "pnpm@" + task["dependencyVersions"]["pnpm"], "Source pnpm version differs")
        require(package.get("devDependencies", {}).get("turbo") == task["dependencyVersions"]["turbo"], "Source Turbo version differs")
        require((source / "pnpm-lock.yaml").is_file(), "A real frozen pnpm lock is required")
    elif profile == "node-stdlib":
        package = load_json(source / "package.json")
        require(all(package.get(key, {}) == {} for key in
                    ("dependencies", "devDependencies", "optionalDependencies", "peerDependencies")),
                "Node built-ins cannot conceal package dependencies")
        require(not package.get("packageManager"), "Review an adapter for a managed Node package toolchain")
    generated = set()
    for check in task["baseline"]:
        argv = check["argv"]
        declared = baseline_generated_files(check, profile)
        for relative in declared:
            require(not (source / relative).exists(), "Generated output must not replace starter source")
            require(relative not in generated, "A generated baseline file cannot have competing writers")
            module = source.joinpath(*argv[2].split(".")).with_suffix(".py")
            require(module.is_file(), "Generated output requires its real local source module")
            ancestor = (source / relative).parent
            while ancestor != source:
                require(not ancestor.exists() or ancestor.is_dir(), "Generated output has a source-file parent")
                ancestor = ancestor.parent
        if check.get("env"):
            require((source / "src").is_dir(), "PYTHONPATH=src baseline requires the real src directory")
        for value in argv[1:]:
            if value.endswith((".py", ".sh", ".mjs", ".js", ".cjs", ".json")) and not value.startswith("-"):
                safe_relative(value)
                require((source / value).is_file() or value in generated or value in declared,
                        "Baseline refers to an absent or undeclared generated file: " + value)
        generated.update(declared)


def apply_registration(root, task, project, goal_bytes, source, page_fetch, prior_registry, prior_manifest):
    lock_path = root / ".task-registration.lock"
    descriptor = os.open(lock_path, os.O_WRONLY | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        require(stat.S_ISREG(os.fstat(descriptor).st_mode) and os.fstat(descriptor).st_uid == os.getuid(), "Unsafe registration lock")
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        current_registry, current_manifest = reviewed_state(root)
        require(current_registry == prior_registry and current_manifest == prior_manifest, "Catalog changed after planning; replan")
        targets = (root / "inputs" / task["neutral"], root / "runtime" / task["goalFile"],
                   root / "packs/pages" / (task["neutral"] + ".json"))
        require(not any(os.path.lexists(path) for path in targets), "A new-task destination already exists; preserve it")
        registry = {**current_registry, "tasks": [*current_registry["tasks"], task]}
        manifest = {**current_manifest, "projects": [*current_manifest["projects"], project]}
        validate_manifest(manifest, registry)
        prior = {path: path.read_bytes() for path in (root / "runtime/task-registry.json", root / "runtime/runtime-manifest.json")}
        created = []
        temporaries = []
        try:
            targets[0].mkdir()
            created.append(targets[0])
            shutil.copytree(source, targets[0], dirs_exist_ok=True)
            for path, content in ((targets[1], goal_bytes), (targets[2], json_bytes(page_fetch))):
                path.parent.mkdir(parents=True, exist_ok=True)
                with path.open("xb") as handle:
                    handle.write(content)
                created.append(path)
            for path, content in ((root / "runtime/task-registry.json", json_bytes(registry)),
                                  (root / "runtime/runtime-manifest.json", json_bytes(manifest))):
                temporary = path.with_suffix(path.suffix + ".registration-new")
                require(not os.path.lexists(temporary), "Registration temporary path already exists")
                with temporary.open("xb") as handle:
                    temporaries.append(temporary)
                    handle.write(content)
                os.replace(temporary, path)
            reviewed_state(root)
        except BaseException:
            for path, content in prior.items():
                path.write_bytes(content)
            for path in reversed(created):
                shutil.rmtree(path) if path.is_dir() else path.unlink()
            raise
        finally:
            for path in temporaries:
                if path.exists():
                    path.unlink()
    finally:
        os.close(descriptor)


def execute(args):
    root = args.root.resolve()
    registry, manifest = reviewed_state(root)
    require(re.fullmatch(r"https://github.com/KyPython/[A-Za-z0-9_.-]+", args.source_repo) is not None,
            "Supply the real KyPython GitHub source URL")
    page_fetch = load_json(args.page_json)
    page = snapshot(page_fetch)
    setup = load_json(args.setup_json)
    task, goal_bytes = make_task(page, args.neutral, args.source_repo, args.commit, args.profile, setup)
    if "internalBootcampAdmission" in task:
        verify_internal_bootcamp_evidence(task, setup)
    existing = [item for item in registry["tasks"] if item["neutral"] == task["neutral"] or item["id"] == task["id"] or item["notionPageId"] == task["notionPageId"]]
    if existing:
        require(len(existing) == 1 and existing[0] == task, "Existing task identity is immutable; register a distinct approved revision")
        return {"operation": "noop", "task": task["neutral"], "reason": "The exact reviewed task is already registered"}
    with tempfile.TemporaryDirectory(prefix="task-registration-") as directory:
        temporary = Path(directory)
        repository = args.source_dir.resolve() if args.source_dir else temporary / "repository"
        if args.source_dir is None:
            run(["gh", "repo", "clone", args.source_repo.removeprefix("https://github.com/"), str(repository), "--", "--no-checkout"])
            run(["git", "fetch", "--no-tags", "origin", args.commit], repository)
        source = temporary / "source"
        files = git_tree(repository, args.commit, source, args.source_repo, local=args.source_dir is not None)
        verify_recipe(task, source)
        project = {key: task[key] for key in ("neutral", "originalName", "sourceRepo", "commit")}
        project["files"] = files
        validate_manifest({**manifest, "projects": [*manifest["projects"], project]},
                          {**registry, "tasks": [*registry["tasks"], task]})
        plan = {"operation": "register" if args.command == "register" else "plan", "task": task,
                "project": project, "notionRevision": page["revision"], "sourceFiles": len(files),
                "sourceUnchanged": True, "recordingReady": False,
                "next": "Review one task route, then use the existing cloud workflow; this command does not push or publish"}
        if args.command == "register":
            apply_registration(root, task, project, goal_bytes, source, page_fetch, registry, manifest)
        return plan


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("plan", "register"))
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--page-json", type=Path, required=True)
    parser.add_argument("--source-repo", required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--neutral", required=True)
    parser.add_argument("--profile", choices=sorted(PROFILES), required=True)
    parser.add_argument("--setup-json", type=Path, required=True, help="Reviewed lane, source references, dependency pins and baseline contracts")
    parser.add_argument("--source-dir", type=Path, help="Existing clean clone at the exact SHA; otherwise fetch with gh into a temporary directory")
    args = parser.parse_args()
    try:
        print(json.dumps(execute(args), ensure_ascii=False, indent=2))
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        print("HOLD: " + str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
