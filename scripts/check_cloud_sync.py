"""Exercise artifact verification and backup retention in a disposable cloud fixture."""

import argparse
import importlib.util
import json
import os
from pathlib import Path
import shutil
import tempfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("taskwork_sync", ROOT / "runtime/TaskWorkCloudSync.py")
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)


def check(output, archive, checksum):
    assert os.environ.get("GITHUB_ACTIONS") == "true"
    with tempfile.TemporaryDirectory(prefix="taskwork-sync-check-", dir=os.environ["RUNNER_TEMP"]) as temporary:
        shared = Path(temporary)
        for name in ("TaskWorkInputs", "TaskWorkRuntime"):
            shutil.copytree(output / name, shared / name, symlinks=True)
        before_inputs = sync.scan_tree(shared / "TaskWorkInputs")
        before_runtime = sync.scan_tree(shared / "TaskWorkRuntime")
        result = sync.process(archive, checksum, os.environ["GITHUB_SHA"], os.environ["GITHUB_RUN_ID"],
                              sync=True, shared=shared)
        manifest = json.loads((output / "TaskWorkRuntime/runtime-manifest.json").read_text())
        count = sum(len(project["files"]) for project in manifest["projects"])
        assert result["verified"] and result["synced"] and result["sourceFiles"] == count
        assert sync.scan_tree(shared / "TaskWorkInputs") == before_inputs
        assert sync.scan_tree(Path(result["previousRuntime"])) == before_runtime
        installed = sync.scan_tree(shared / "TaskWorkRuntime")
        receipt_spec = installed.pop("cloud-sync-receipt.json")
        assert receipt_spec["kind"] == "file" and receipt_spec["mode"] == 0o644
        assert installed == before_runtime, "Only the actual generated sync receipt may be added"
        receipt_path = shared / "TaskWorkRuntime/cloud-sync-receipt.json"
        durable = sync.read_json(receipt_path.read_bytes(), "Installed sync receipt")
        assert durable == result, "Durable sync receipt must match the actual returned verified result"
        assert durable["runtimeMetadataSha256"], "Receipt must bind verified runtime metadata"
        for relative, digest in durable["runtimeMetadataSha256"].items():
            assert sync.digest(shared / "TaskWorkRuntime" / relative) == digest
        before_receipt = receipt_path.read_bytes()
        project = manifest["projects"][0]
        changed = shared / "TaskWorkInputs" / project["neutral"] / next(iter(project["files"]))
        changed.write_bytes(changed.read_bytes() + b"\nlocal work\n")
        preserved = changed.read_bytes()
        try:
            sync.process(archive, checksum, os.environ["GITHUB_SHA"], os.environ["GITHUB_RUN_ID"],
                         sync=True, shared=shared)
        except sync.VerificationError:
            pass
        else:
            raise AssertionError("Changed input was not preserved")
        assert changed.read_bytes() == preserved
        assert receipt_path.read_bytes() == before_receipt
    print("Cloud artifact sync verified: exact contents plus durable actual receipt, complete backup, unchanged inputs and changed-work refusal.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--checksum", required=True, type=Path)
    args = parser.parse_args()
    check(args.output, args.archive, args.checksum)
