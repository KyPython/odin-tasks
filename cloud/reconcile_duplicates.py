"""Archive and reconcile only the reviewed, reversible duplicate issue closures."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "cloud/duplicate-cleanup-plan.json"
ARCHIVE = ROOT / "cloud/duplicate-cleanup-archive.json"
RECEIPTS = ROOT / "cloud/duplicate-cleanup-receipts.json"
REPO = "KyPython/ai-governance"
PROTECTED = {43, 44, 46, 47, 58, 86}
NOTE_MARKER = "<!-- ODIN_DUPLICATE_RECONCILIATION:v1 -->"


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def api(path, payload=None, method=None):
    command = ["gh", "api", path]
    if method:
        command += ["--method", method]
    if payload is not None:
        command += ["--input", "-"]
    result = subprocess.run(command, input=json.dumps(payload) if payload is not None else None,
                            text=True, capture_output=True, check=True)
    return json.loads(result.stdout)


def save(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def scan(value):
    # Credentials are never read by this script or included in command arguments.
    result = subprocess.run(["gitleaks", "stdin", "--no-banner", "--redact", "--exit-code", "2"],
                            input=json.dumps(value, ensure_ascii=False),
                            text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError("Archive secret scan failed; no issue mutations were attempted.")


def approved_plan():
    plan = json.loads(PLAN.read_text())
    if plan["repository"] != REPO:
        raise RuntimeError("Unexpected repository")
    groups = {number: group for group in plan["groups"] for number in group["closeNumbers"]}
    if len(groups) != 114 or PROTECTED.intersection(groups):
        raise RuntimeError("Closure set differs from the reviewed plan")
    return plan, groups


def graphql_snapshot(numbers):
    snapshots = {}
    for offset in range(0, len(numbers), 10):
        batch = numbers[offset:offset + 10]
        fields = []
        for number in batch:
            fields.append("i" + str(number) + ": issue(number:" + str(number) + ") { "
                          "number title body state url createdAt updatedAt "
                          "comments(first:100) { totalCount pageInfo {hasNextPage endCursor} "
                          "nodes {id body url createdAt updatedAt author {login}} } }")
        query = 'query { repository(owner:"KyPython",name:"ai-governance") { ' + " ".join(fields) + " } }"
        result = api("graphql", {"query": query})
        if result.get("errors"):
            raise RuntimeError("GitHub archive query returned errors")
        for number in batch:
            item = result["data"]["repository"]["i" + str(number)]
            if not item:
                raise RuntimeError("Missing proposed issue " + str(number))
            connection = item["comments"]
            if connection["pageInfo"]["hasNextPage"] or len(connection["nodes"]) != connection["totalCount"]:
                raise RuntimeError("Incomplete comments for issue " + str(number))
            snapshots[str(number)] = item
        print("Archived snapshot", min(offset + 10, len(numbers)), "/", len(numbers), flush=True)
    return snapshots


def exact_marker(body, row_id):
    return re.search(r"(?:^|\s|<!--\s*)ODIN_BOOTCAMP_ROW_ID:" + re.escape(row_id) +
                     r"(?=\s|\||-->|$)", body or "") is not None


def archive_only():
    plan, groups = approved_plan()
    snapshots = graphql_snapshot(sorted(set(groups) | {58, 86}))
    for number, group in groups.items():
        if not exact_marker(snapshots[str(number)]["body"], group["rowId"]):
            raise RuntimeError("Row marker no longer matches issue " + str(number))
    archive = {"schemaVersion": 1, "repository": REPO, "capturedAt": timestamp(),
               "plan": plan, "issues": snapshots, "freshBeforeClosure": {},
               "note": "Original bodies and complete comments are preserved. Canonical issues 58 and 86 are protected."}
    scan(archive)
    save(ARCHIVE, archive)
    print("Complete archive passed gitleaks:", len(snapshots), "issues", flush=True)


def complete_comments(number):
    result = subprocess.run(["gh", "api", "--paginate", "--slurp",
                             "repos/" + REPO + "/issues/" + str(number) + "/comments?per_page=100"],
                            text=True, capture_output=True, check=True)
    pages = json.loads(result.stdout)
    if not isinstance(pages, list) or any(not isinstance(page, list) for page in pages):
        raise RuntimeError("Invalid comment page evidence")
    return [item for page in pages for item in page]


def reconciliation(group):
    if group["canonical"]:
        reference = "https://github.com/" + REPO + "/issues/" + str(group["canonical"]["number"])
        summary = "Canonical build: " + reference + "."
    elif group["existingBuildIssue"]:
        summary = "Invalid Bootcamp lane. Authoritative Odin build: " + group["existingBuildIssue"] + "."
    else:
        reference = "https://app.notion.com/p/" + group["rowId"].replace("-", "")
        summary = "Invalid Bootcamp lane; task is not admitted for construction. Task Factory: " + reference + "."
    return NOTE_MARKER + "\n> Automation reconciliation: " + summary + (
        " Existing output/comments preserved; do not start another build.\n\n---\n\n")


def execute():
    _, groups = approved_plan()
    archive = json.loads(ARCHIVE.read_text())
    if archive["repository"] != REPO or set(map(str, groups)) - set(archive["issues"]):
        raise RuntimeError("Archive is incomplete for the reviewed closure set")
    scan(archive)
    receipts = json.loads(RECEIPTS.read_text()) if RECEIPTS.exists() else {
        "schemaVersion": 1, "repository": REPO, "startedAt": timestamp(), "issues": []}
    completed = {entry["number"] for entry in receipts["issues"]}
    previous_patch = 0.0
    for position, number in enumerate(sorted(groups), 1):
        if number in completed:
            continue
        group = groups[number]
        current = api("repos/" + REPO + "/issues/" + str(number))
        if current.get("pull_request") or not exact_marker(current["body"], group["rowId"]):
            raise RuntimeError("Unexpected live issue evidence: " + str(number))
        comments = complete_comments(number)
        fresh = {"issue": current, "comments": comments, "capturedAt": timestamp()}
        scan(fresh)
        archive["freshBeforeClosure"][str(number)] = fresh
        save(ARCHIVE, archive)
        original_body = current["body"]
        updated_body = original_body if NOTE_MARKER in original_body else reconciliation(group) + original_body
        delay = 2.0 - (time.monotonic() - previous_patch)
        if delay > 0:
            time.sleep(delay)
        result = api("repos/" + REPO + "/issues/" + str(number),
                     {"body": updated_body, "state": "closed", "state_reason": "not_planned"}, "PATCH")
        previous_patch = time.monotonic()
        if result["state"] != "closed" or result["body"] != updated_body:
            raise RuntimeError("Closure/body verification failed: " + str(number))
        receipt = {"number": number, "url": result["html_url"], "rowId": group["rowId"],
                   "state": result["state"], "stateReason": result.get("state_reason"),
                   "verifiedAt": timestamp(), "updatedAt": result["updated_at"],
                   "originalBodySha256": hashlib.sha256(original_body.encode()).hexdigest(),
                   "reconciledBodySha256": hashlib.sha256(updated_body.encode()).hexdigest(),
                   "archivedCommentsBeforeClosure": len(comments),
                   "canonical": group.get("canonical"), "authoritativeBuild": group.get("existingBuildIssue")}
        receipts["issues"].append(receipt)
        save(RECEIPTS, receipts)
        print("Closed and verified", number, "(" + str(position) + "/114)", flush=True)
    receipts["completedAt"] = timestamp()
    receipts["closedCount"] = len(receipts["issues"])
    save(RECEIPTS, receipts)
    print("Reconciliation complete:", receipts["closedCount"], "closures", flush=True)


def verify():
    _, groups = approved_plan()
    snapshots = graphql_snapshot(sorted(set(groups) | PROTECTED))
    archive = json.loads(ARCHIVE.read_text())
    receipts = json.loads(RECEIPTS.read_text())
    for number, group in groups.items():
        current = snapshots[str(number)]
        fresh = archive["freshBeforeClosure"][str(number)]
        if current["state"] != "CLOSED" or NOTE_MARKER not in current["body"]:
            raise RuntimeError("Final closure verification failed: " + str(number))
        original = fresh["issue"]["body"]
        if current["body"] != original and not current["body"].endswith(original):
            raise RuntimeError("Original body no longer preserved: " + str(number))
        before = {comment["html_url"]: comment["body"] for comment in fresh["comments"]}
        after = {comment["url"]: comment["body"] for comment in current["comments"]["nodes"]}
        if any(after.get(url) != body for url, body in before.items()):
            raise RuntimeError("Comment preservation verification failed: " + str(number))
    scan(snapshots)
    archive["verifiedAfterClosure"] = snapshots
    archive["verifiedAt"] = timestamp()
    save(ARCHIVE, archive)
    receipts["finalVerification"] = {
        "at": timestamp(), "closedCount": len(groups), "bodiesPreserved": True,
        "commentsPreserved": True, "archiveSecretScan": "PASS",
        "protectedIssues": {str(n): snapshots[str(n)]["state"] for n in sorted(PROTECTED)}}
    save(RECEIPTS, receipts)
    print("Verified all114 closures, original bodies/comments, and protected issue states", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["archive", "execute", "verify"])
    args = parser.parse_args()
    {"archive": archive_only, "execute": execute, "verify": verify}[args.action]()
