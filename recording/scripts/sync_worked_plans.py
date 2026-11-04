"""Verify and preserve a separately built off-screen worked-reference artifact."""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import sys
import tarfile
import tempfile

REPOSITORY = 'KyPython/odin-recording-preparation'
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'runtime'))
from TaskWorkRegistry import load_json, validate_registry, validate_manifest, verify_goal
from recording_pack import route_from_body, validate_route


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def receipt_sha(receipt):
    content = {k: v for k, v in receipt.items() if k not in ('receiptContentSha256', 'operation')}
    return hashlib.sha256(json.dumps(content, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def inventory(root, omit_receipt=False):
    require(root.is_dir() and not root.is_symlink(), 'Expected a real reference directory')
    result = {}
    for path in sorted(root.rglob('*')):
        require(not path.is_symlink() and (path.is_dir() or path.is_file()), 'Unexpected reference object')
        if path.is_file():
            relative = path.relative_to(root).as_posix()
            if omit_receipt and relative == 'worked-plans-sync-receipt.json':
                continue
            result[relative] = {'sha256': sha(path), 'mode': stat.S_IMODE(path.stat().st_mode)}
    return result


def verify_tree(root, runtime, commit, run_id):
    proof = json.loads((root / 'worked-plans-proof.json').read_text())
    require(proof.get('version') == 1 and proof.get('repository') == REPOSITORY,
            'Expected actual reference cloud identity')
    require(proof.get('sourceCommit') == commit and str(proof.get('runId')) == run_id,
            'Reference cloud commit/run mismatch')
    require(proof.get('runUrl') == f'https://github.com/{REPOSITORY}/actions/runs/{run_id}',
            'Reference cloud URL mismatch')
    require(proof.get('starterInputsUnchanged') is True
            and proof.get('workedRepairsVerifiedInDisposableCopies') is True
            and proof.get('recorderExecuted') is False
            and proof.get('recordingWorkspaceModified') is False
            and proof.get('paidWalkthroughPermissionVerified') is False,
            'Reference proof must preserve the actual recording/permission boundary')
    starter_proof = runtime / 'cloud-proof.json'
    actual = json.loads(starter_proof.read_text())
    require(actual.get('sourceCommit') == commit and str(actual.get('runId')) == run_id,
            'Install the matching verified starter kit first')
    require(sha(starter_proof) == proof.get('starterCloudProofSha256'), 'Starter proof digest differs')
    registry = load_json(runtime / 'task-registry.json')
    tasks = validate_registry(registry)
    validate_manifest(load_json(runtime / 'runtime-manifest.json'), registry)
    names = proof.get('plans')
    require(isinstance(names, list) and names and len(names) == len(set(names)), 'Expected unique verified plans')
    require(set(names) == set(tasks), 'Every registered task requires a verified complete plan')
    require(set(p.name for p in root.iterdir() if p.is_dir()) == set(names), 'Reference folder inventory differs')
    for name in names:
        require(name in tasks and re.fullmatch(r'[a-z][a-z0-9-]*', name), 'Unknown registered plan')
        identity = json.loads((root / name / 'identity.json').read_text())
        task = tasks[name]
        verify_goal(task, runtime / task['goalFile'])
        require(identity.get('neutral') == name and identity.get('taskId') == task['id']
                and identity.get('sourceCommit') == task['commit']
                and identity.get('sourceRepo') == task['sourceRepo']
                and identity.get('goalSha256') == task['goalSha256'], 'Source/Goal identity changed')
        require(identity.get('rehearsalExitCode') == 0 and identity.get('recorderExecuted') is False
                and identity.get('recordingWorkspaceModified') is False
                and identity.get('paidWalkthroughPermissionVerified') is False, 'Reference rehearsal boundary differs')
        observed = json.loads((root / name / 'cloud-verification.json').read_text())
        require(observed.get('status') == 'PASS' and observed.get('sourceCommit') == task['commit'] and observed.get('goalSha256') == task['goalSha256']
                and observed.get('checks') and observed.get('sourceInputsUnchanged') is True
                and observed.get('recorderExecuted') is False
                and observed.get('recordingWorkspaceModified') is False, 'Missing actual bound rehearsal evidence')
        require(observed.get('solutionPatchSha256') == sha(root / name / 'solution.patch'),
                'Packaged solution differs from the actual cloud rehearsal')
        route_path = root / name / 'recording-sequence.md'
        route = validate_route(route_path.read_text())
        require(sha(route_path) == identity.get('routeSha256')
                and route_from_body((root / name / 'walkthrough.md').read_text()) == route,
                'Worked narration/code sequence differs from the validated route')
    return proof


def sync(archive, checksum, commit, run_id, runtime, destination, install=False):
    require(re.fullmatch(r'[0-9a-f]{40}', commit) and run_id.isdecimal(), 'Expected full cloud commit/run')
    require(archive.is_file() and not archive.is_symlink() and archive.stat().st_size <= 20_000_000,
            'Expected a small regular reference archive')
    digest = sha(archive)
    require(re.fullmatch(r'[0-9a-f]{64}', checksum.read_text().split()[0])
            and checksum.read_text().split()[0] == digest, 'Archive SHA-256 failed')
    require(destination.name == 'TaskWorkPlans' and not destination.is_symlink(),
            'Use the separate TaskWorkPlans root')
    require(destination.parent.is_dir() and not destination.parent.is_symlink(), 'Expected a real destination parent')
    lock = destination.parent / '.TaskWorkPlans.sync.lock'
    if install:
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(descriptor)
    try:
        with tempfile.TemporaryDirectory(prefix='.taskwork-plans-', dir=destination.parent) as scratch:
            root = Path(scratch) / 'TaskWorkPlans'
            root.mkdir(mode=0o755)
            paths = set()
            with tarfile.open(archive, 'r:gz') as bundle:
                for item in bundle:
                    require(item.isdir() or item.isfile(), 'Archive links/special files are forbidden')
                    name = item.name.removeprefix('./')
                    if name in ('', '.'):
                        require(item.isdir(), 'Invalid archive root')
                        continue
                    relative = PurePosixPath(name)
                    require(not relative.is_absolute() and '\\' not in name
                            and all(p not in ('', '.', '..') for p in relative.parts)
                            and str(relative) == name and name not in paths, 'Unsafe or repeated archive path')
                    paths.add(name)
                    require(item.size <= 5_000_000, 'Oversized reference member')
                    target = root / name
                    if item.isdir():
                        target.mkdir(parents=True, exist_ok=True, mode=0o755)
                    else:
                        target.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
                        require(item.mode == 0o644, 'Reference files must be mode 0644')
                        with bundle.extractfile(item) as handle:
                            target.write_bytes(handle.read())
                        target.chmod(0o644)
            manifest = json.loads((root / 'worked-plans-manifest.json').read_text())
            require(manifest.get('version') == 1, 'Unsupported reference manifest')
            actual = inventory(root)
            actual.pop('worked-plans-manifest.json')
            require(actual == manifest.get('files'), 'Reference inventory/hash/mode check failed')
            proof = verify_tree(root, runtime, commit, run_id)
            result = {'version': 1, 'publicationOwner': 'taskwork-worked-plans-sync-v1',
                      'sourceCommit': commit, 'runId': run_id, 'archiveSha256': digest,
                      'verified': True, 'synced': False, 'plans': proof['plans'], 'files': inventory(root),
                      'recorderExecuted': False, 'recordingWorkspaceModified': False,
                      'paidWalkthroughPermissionVerified': False}
            if not install:
                return result
            if destination.exists():
                receipt_path = destination / 'worked-plans-sync-receipt.json'
                require(receipt_path.is_file() and not receipt_path.is_symlink(), 'Unmanaged destination; preserve it')
                old = json.loads(receipt_path.read_text())
                require(old.get('publicationOwner') == result['publicationOwner']
                        and old.get('receiptContentSha256') == receipt_sha(old)
                        and inventory(destination, True) == old.get('files'), 'Edited reference work; preserve it')
                if old.get('sourceCommit') == commit and old.get('runId') == run_id and old.get('archiveSha256') == digest:
                    require(old.get('files') == result['files'] and old.get('synced') is True, 'Conflicting existing receipt')
                    return {**old, 'operation': 'noop'}
            result['synced'] = True
            result['syncedAt'] = dt.datetime.now(dt.timezone.utc).isoformat()
            backup = destination.parent / ('TaskWorkPlans.previous-' + dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ'))
            result['previousPlans'] = str(backup) if destination.exists() else None
            result['receiptContentSha256'] = receipt_sha(result)
            (root / 'worked-plans-sync-receipt.json').write_text(json.dumps(result, indent=2) + '\n')
            (root / 'worked-plans-sync-receipt.json').chmod(0o644)
            if destination.exists():
                destination.rename(backup)
            try:
                root.rename(destination)
            except BaseException:
                if backup.exists() and not destination.exists():
                    backup.rename(destination)
                raise
            return result
    finally:
        if install:
            lock.unlink()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('checksum', type=Path)
    parser.add_argument('--commit', required=True)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--runtime', type=Path, default=Path('/Users/Shared/TaskWorkRuntime'))
    parser.add_argument('--output', type=Path, default=Path('/Users/Shared/TaskWorkPlans'))
    parser.add_argument('--sync', action='store_true')
    args = parser.parse_args()
    print(json.dumps(sync(args.archive, args.checksum, args.commit, args.run_id, args.runtime, args.output, args.sync), indent=2))
