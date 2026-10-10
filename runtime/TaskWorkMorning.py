#!/usr/local/bin/python3
"""Refresh the existing cloud kit; never build worlds or touch human attempts."""
import argparse
from contextlib import ExitStack, contextmanager
import datetime as dt
import fcntl
import hashlib
import html
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
REPOSITORY = 'KyPython/odin-recording-preparation'
BRANCH = 'ci/cloud-preparation'
WORKFLOW = 'build-preparation.yml'
GH = '/opt/homebrew/bin/gh'
SHARED = Path('/Users/Shared')
OWNER = 'taskwork-morning-v1'
sys.dont_write_bytecode = True
sys.path.insert(0, str(HERE))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load(path):
    require(path.is_file() and not path.is_symlink(), 'Missing regular evidence: ' + str(path))
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, 'Duplicate evidence field: ' + key)
            result[key] = value
        return result
    return json.loads(path.read_text(), object_pairs_hook=unique)


def sha(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()


def safe_relative(name):
    path = PurePosixPath(name)
    require(isinstance(name, str) and name and '\\' not in name and not path.is_absolute()
            and path.as_posix() == name and all(part not in ('', '.', '..') for part in path.parts),
            'Unsafe evidence path')
    return name


def plain_path(path):
    require(not any(part.is_symlink() for part in [path, *path.parents]), 'Unsafe linked path: ' + str(path))


def verify_metadata(runtime, metadata, needed):
    require(isinstance(metadata, dict) and needed <= set(metadata), 'Missing helper/dependency runtime integrity map')
    for name, expected in metadata.items():
        safe_relative(name)
        path = runtime / name
        plain_path(path)
        require(path.is_file() and isinstance(expected, str) and re.fullmatch(r'[a-f0-9]{64}', expected)
                and sha(path) == expected, 'Changed runtime metadata; preserving it: ' + name)


def plan_inventory(root):
    plain_path(root)
    require(root.is_dir(), 'Missing reference tree')
    result = {}
    for path in sorted(root.rglob('*')):
        require(not path.is_symlink() and (path.is_file() or path.is_dir()), 'Unexpected reference object')
        if path.is_file() and path.relative_to(root).as_posix() != 'worked-plans-sync-receipt.json':
            name = safe_relative(path.relative_to(root).as_posix())
            result[name] = {'sha256': sha(path), 'mode': stat.S_IMODE(path.stat().st_mode)}
    return result


def plan_receipt_sha(receipt):
    value = {k: v for k, v in receipt.items() if k not in ('receiptContentSha256', 'operation')}
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


@contextmanager
def owned_lock(path, *, create_exclusive=False):
    plain_path(path)
    flags = os.O_WRONLY | os.O_CREAT | getattr(os, 'O_NOFOLLOW', 0)
    if create_exclusive:
        flags |= os.O_EXCL
    descriptor = os.open(path, flags, 0o600)
    try:
        info = os.fstat(descriptor)
        require(stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid(), 'Unsafe owned lock')
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield
    finally:
        os.close(descriptor)
        if create_exclusive:
            path.unlink()


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def command(argv):
    # No credential is printed, copied to Shared, or passed in an argument.
    result = subprocess.run(argv, capture_output=True, text=True, timeout=180,
                            env={**os.environ, 'GH_PROMPT_DISABLED': '1', 'PYTHONDONTWRITEBYTECODE': '1'})
    require(result.returncode == 0, 'Command failed: ' + ' '.join(argv[:4]) + ' (exit ' + str(result.returncode) + ')')
    return result.stdout


def candidate(head, runs):
    """Only a successful current-head build is installable; never downgrade."""
    require(isinstance(head, str) and re.fullmatch(r'[a-f0-9]{40}', head), 'Invalid current cloud head')
    require(isinstance(runs, list), 'Incomplete cloud build response')
    matches = [run for run in runs if run.get('head_sha') == head
               and run.get('head_branch') == BRANCH and run.get('status') == 'completed'
               and run.get('conclusion') == 'success']
    require(all(re.fullmatch(r'[1-9][0-9]*', str(run.get('id', ''))) for run in matches), 'Invalid successful cloud run ID')
    return max(matches, key=lambda run: int(run['id'])) if matches else None


def verify_installed(shared):
    runtime = shared / 'TaskWorkRuntime'
    proof = load(runtime / 'cloud-proof.json')
    receipt = load(runtime / 'cloud-sync-receipt.json')
    require(receipt.get('verified') is True and receipt.get('synced') is True
            and receipt.get('repository') == proof.get('repository') == REPOSITORY
            and receipt.get('sourceCommit') == proof.get('sourceCommit')
            and str(receipt.get('runId')) == str(proof.get('runId')), 'Installed cloud identities differ')
    require(re.fullmatch(r'[a-f0-9]{40}', proof.get('sourceCommit', ''))
            and re.fullmatch(r'[1-9][0-9]*', str(proof.get('runId', '')))
            and proof.get('runUrl') == f"https://github.com/{REPOSITORY}/actions/runs/{proof['runId']}", 'Invalid installed cloud proof identity')
    metadata = receipt.get('runtimeMetadataSha256')
    needed = {'TaskWorkCloudSync.py', 'TaskWorkRegistry.py', 'task-registry.json', 'runtime-manifest.json', 'cloud-proof.json'}
    if (runtime / 'SyncTaskWorkPlans.py').exists():
        needed.update({'SyncTaskWorkPlans.py', 'recording_pack.py'})
    verify_metadata(runtime, metadata, needed)
    # Load installed code only after its recorded cloud integrity has been checked.
    sync = module('morning_cloud_sync', runtime / 'TaskWorkCloudSync.py')
    registry = load(runtime / 'task-registry.json')
    manifest = load(runtime / 'runtime-manifest.json')
    require(sync.scan_tree(shared / 'TaskWorkInputs') == sync.source_inventory(manifest, registry),
            'Shared starter inputs changed; preserve them')
    for task in registry['tasks']:
        sync.verify_goal(task, runtime / task['goalFile'])
    worked = module('morning_worked_sync', runtime / 'SyncTaskWorkPlans.py') if (runtime / 'SyncTaskWorkPlans.py').exists() else None
    plans = shared / 'TaskWorkPlans'
    plan_receipt = load(plans / 'worked-plans-sync-receipt.json')
    require(plan_receipt.get('verified') is True and plan_receipt.get('synced') is True
            and plan_receipt.get('publicationOwner') == 'taskwork-worked-plans-sync-v1'
            and plan_receipt.get('sourceCommit') == proof['sourceCommit']
            and str(plan_receipt.get('runId')) == str(proof['runId']), 'Starter and worked kit identities differ')
    require(plan_receipt_sha(plan_receipt) == plan_receipt.get('receiptContentSha256')
            and plan_inventory(plans) == plan_receipt.get('files'), 'Worked reference files/modes changed; preserve them')
    if worked:
        require(worked.receipt_sha(plan_receipt) == plan_receipt.get('receiptContentSha256')
                and worked.inventory(plans, True) == plan_receipt.get('files'), 'Worked reference files changed; preserve them')
        worked.verify_tree(plans, runtime, proof['sourceCommit'], str(proof['runId']))
    else:
        # Compatibility with the preceding verified kit. Full reference sync is
        # performed by the incoming verified helper before publishing an update.
        require(load(plans / 'worked-plans-proof.json').get('sourceCommit') == proof['sourceCommit'],
                'Prior reference proof identity differs')
    return proof, registry


def write_projection(destination, files):
    """One owned projection; changed/unmanaged outputs are never overwritten."""
    plain_path(destination)
    require(destination.parent.is_dir(), 'Missing morning output parent')
    for name, data in files.items():
        require(safe_relative(name) == name and '/' not in name and name != 'projection-receipt.json'
                and isinstance(data, bytes), 'Unsafe projection filename/data')
    evidence = {'publicationOwner': OWNER, 'files': {name: hashlib.sha256(data).hexdigest() for name, data in files.items()}}
    data = (json.dumps(evidence, sort_keys=True, indent=2) + '\n').encode()
    with owned_lock(destination.parent / ('.' + destination.name + '.projection.lock')):
        receipt_path = destination / 'projection-receipt.json'
        old = load(receipt_path) if receipt_path.exists() else None
        if destination.exists():
            require(destination.is_dir() and destination.stat().st_uid == os.getuid(), 'Morning output belongs to another user')
            if old:
                require(old.get('publicationOwner') == OWNER and isinstance(old.get('files'), dict), 'Another publisher owns morning output')
                for name, expected in old['files'].items():
                    require(safe_relative(name) == name and '/' not in name, 'Unsafe projection receipt path')
                    path = destination / name
                    require(path.is_file() and not path.is_symlink() and stat.S_IMODE(path.stat().st_mode) == 0o644
                            and sha(path) == expected, 'Edited morning output; preserve it: ' + name)
            allowed = set(old['files']) | {'projection-receipt.json'} if old else set()
            require(all(p.name in allowed for p in destination.iterdir()), 'Unmanaged morning output; preserve it')
            if old == evidence and receipt_path.read_bytes() == data:
                return
        stage = Path(tempfile.mkdtemp(prefix='.' + destination.name + '-next-', dir=destination.parent))
        stage.chmod(0o755)
        backup = destination.parent / (destination.name + '.previous-' + stage.name.rsplit('-', 1)[-1])
        require(not backup.exists(), 'Projection backup already exists')
        moved = False
        try:
            for name, content in {**files, 'projection-receipt.json': data}.items():
                (stage / name).write_bytes(content)
                (stage / name).chmod(0o644)
            if destination.exists():
                destination.rename(backup)
                moved = True
            try:
                stage.rename(destination)
            except BaseException:
                if moved:
                    backup.rename(destination)
                raise
        finally:
            if stage.exists():
                shutil.rmtree(stage)


def publish_status(shared, state, proof, registry, remote_head=None):
    current = proof['sourceCommit'] if proof else None
    status = {'version': 1, 'checkedAt': dt.datetime.now(dt.timezone.utc).isoformat(),
              'state': state, 'installedCommit': current, 'remoteHead': remote_head,
              'cloudRunUrl': proof.get('runUrl') if proof else None,
              'registeredTasks': len(registry.get('tasks', [])) if registry else 0,
              'recorderExecuted': False, 'recordingReady': False, 'practiceReady': False,
              'unaidedTransferEstablished': False, 'mastery': 'not_established'}
    page = '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>TaskWork morning</title><style>body{max-width:900px;margin:2rem auto;padding:0 1rem;font:18px/1.55 system-ui}</style><body><h1>TaskWork morning</h1><p>' + html.escape(state) + '</p><p>Checked ' + html.escape(status['checkedAt']) + '. This verifies preparation, not real-account capture readiness.</p>'
    if proof:
        page += '<p><a href="' + html.escape(proof['runUrl'], quote=True) + '">Installed successful cloud build</a> · <code>' + current + '</code></p>'
    page += '<p><a href="../TaskWorkRuntime/process/RECORDER-CODEX-PROMPT.txt">Recorder Codex handoff</a> · <a href="../TaskWorkRuntime/process/REVIEWER-PROMPT.txt">Portable reviewer prompt</a> · <a href="../TaskWorkRuntime/process/RECORDING_REVIEW.md">Review instructions</a> · <a href="../TaskWorkRuntime/process/BOOTCAMP_LEARNING.md">Skills and certification map</a></p><p><a href="https://www.notion.so/3f28621e0a7a81d2b092d5f3f4c537f4">Notion Bootcamp</a> · <a href="../TaskWorkStart/START-HERE.html">Dated shared guide and snapshots</a></p><ul>'
    for task in (registry or {}).get('tasks', []):
        name = task['neutral']
        page += '<li><strong>' + html.escape(name) + '</strong> · <a href="https://www.notion.so/' + task['notionPageId'].replace('-', '') + '">Exact live task script</a> · <a href="../TaskWorkPlans/' + name + '/walkthrough.md">Verified complete worked reference</a></li>'
    page += '</ul><p>Friday 12:45–1:45 PM Eastern is guided practice inside the existing 8–4 shell. SAA-C03 remains the active certification priority. Python/testing worlds are bounded reinforcement and do not establish AWS architecture coverage.</p><p>Local refresh runs at 7:30 AM weekdays and at preparation-account login. A powered-off Mac or logged-out preparation account cannot refresh. The last verified shared kit remains available offline; Recorder-owned setup, authentication and native capture consent are completed in the real Recorder account. Preserve earlier attempts.</p></body></html>\n'
    write_projection(shared / 'TaskWorkMorning', {'status.json': (json.dumps(status, indent=2) + '\n').encode(),
                                                'index.html': page.encode()})
    return status


def install_pair(sync, worked, staging, incoming_plans, shared, commit, run_id, previous_commit, verified):
    """One coordinated swap: restore both prior kits after any install failure.

    Each complete incoming tree is prepared before this critical section. Shared
    starter additions are reversible; existing inputs and recording workspaces
    are never renamed. Failed newly-active trees are preserved, not deleted.
    """
    runtime, plans = shared / 'TaskWorkRuntime', shared / 'TaskWorkPlans'
    cloud_lock = shared / '.TaskWorkCloudSync.lock'
    plan_lock = shared / '.TaskWorkPlans.sync.lock'
    with owned_lock(cloud_lock), owned_lock(plan_lock, create_exclusive=True):
        old_proof, old_registry = verify_installed(shared)
        require(old_proof['sourceCommit'] == previous_commit, 'Installed kit changed during download; retry next refresh')
        sync.verify_contract(staging, shared, commit, run_id)
        worked.verify_tree(incoming_plans, staging / 'TaskWorkRuntime', commit, run_id)
        incoming_receipt = load(incoming_plans / 'worked-plans-sync-receipt.json')
        require(worked.inventory(incoming_plans, True) == incoming_receipt.get('files')
                and worked.receipt_sha(incoming_receipt) == incoming_receipt.get('receiptContentSha256'),
                'Incoming reference preparation changed')
        token = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
        backups = {runtime: shared / ('TaskWorkRuntime.previous-morning-' + token),
                   plans: shared / ('TaskWorkPlans.previous-morning-' + token)}
        require(all(not os.path.lexists(path) for path in backups.values()), 'Prior-kit backup path exists')
        sync.write_sync_receipt(staging / 'TaskWorkRuntime', {**verified, 'synced': True,
                                'previousRuntime': str(backups[runtime])})
        incoming_receipt.update(previousPlans=str(backups[plans]), synced=True,
                                syncedAt=dt.datetime.now(dt.timezone.utc).isoformat())
        incoming_receipt['receiptContentSha256'] = worked.receipt_sha(incoming_receipt)
        receipt_path = incoming_plans / 'worked-plans-sync-receipt.json'
        receipt_path.write_text(json.dumps(incoming_receipt, indent=2) + '\n')
        receipt_path.chmod(0o644)
        incoming_registry = load(staging / 'TaskWorkRuntime/task-registry.json')
        old_names = {task['neutral'] for task in old_registry['tasks']}
        additions = [task['neutral'] for task in incoming_registry['tasks'] if task['neutral'] not in old_names]
        moved_old, moved_new = [], []
        try:
            for current, backup in backups.items():
                current.rename(backup)
                moved_old.append(current)
            for name in additions:
                target = shared / 'TaskWorkInputs' / name
                require(not os.path.lexists(target), 'A new starter destination already exists')
                (staging / 'TaskWorkInputs' / name).rename(target)
                moved_new.append(target)
            for source, target in ((staging / 'TaskWorkRuntime', runtime), (incoming_plans, plans)):
                source.rename(target)
                moved_new.append(target)
            return verify_installed(shared)
        except BaseException:
            # Preserve failed incoming trees, including any intervening edits.
            # Restore prior paths without deleting either kit or any attempts.
            for current in reversed(moved_new):
                held = shared / (current.name + '.morning-held-' + token)
                require(not os.path.lexists(held), 'Held-kit path already exists')
                current.rename(held)
            for current in reversed(moved_old):
                backups[current].rename(current)
            raise


def refresh(shared=SHARED, offline=False):
    proof, registry = verify_installed(shared)
    if offline:
        return publish_status(shared, 'Installed metadata, pinned inputs and worked reference hashes verified; no new cloud read requested', proof, registry)
    head = json.loads(command([GH, 'api', f'repos/{REPOSITORY}/git/ref/heads/{BRANCH}']))['object']['sha']
    runs = json.loads(command([GH, 'api', f'repos/{REPOSITORY}/actions/workflows/{WORKFLOW}/runs?branch={BRANCH}&per_page=30']))['workflow_runs']
    run = candidate(head, runs)
    if not run:
        return publish_status(shared, 'No successful current-head build found in the latest 30 workflow runs; last verified kit preserved', proof, registry, head)
    if proof['sourceCommit'] == head:
        return publish_status(shared, 'Current cloud head and installed kit match; reused verified kit without download or rebuild', proof, registry, head)
    comparison = json.loads(command([GH, 'api', f"repos/{REPOSITORY}/compare/{proof['sourceCommit']}...{head}"]))
    if comparison.get('status') != 'ahead' or comparison.get('merge_base_commit', {}).get('sha') != proof['sourceCommit']:
        return publish_status(shared, 'Cloud head is not a forward descendant of the installed revision; last verified kit preserved', proof, registry, head)
    cache = Path.home() / 'Library/Caches/TaskWorkMorning'
    plain_path(cache)
    cache.mkdir(parents=True, exist_ok=True, mode=0o700)
    require(cache.stat().st_uid == os.getuid(), 'Morning cache belongs to another account')
    with tempfile.TemporaryDirectory(prefix='run-' + str(run['id']) + '-', dir=cache) as temporary:
        download = Path(temporary)
        for prefix in ('taskwork-cloud-macos-arm64-', 'taskwork-worked-plans-macos-arm64-'):
            command([GH, 'run', 'download', str(run['id']), '--repo', REPOSITORY, '--name', prefix + head, '--dir', str(download)])
        # Validate both artifacts before replacing either installed tree.
        # Use the already hash-verified installed source verifier. Load new
        # reference code only from the completely verified incoming artifact.
        sync = module('morning_cloud_sync_new', shared / 'TaskWorkRuntime/TaskWorkCloudSync.py')
        starter_archive = download / 'taskwork-cloud-macos-arm64.tar.gz'
        starter_sum = download / 'taskwork-cloud-macos-arm64.tar.gz.sha256'
        worked_archive = download / 'taskwork-worked-plans-macos-arm64.tar.gz'
        worked_sum = download / 'taskwork-worked-plans-macos-arm64.tar.gz.sha256'
        verified = sync.process(starter_archive, starter_sum, head, str(run['id']), shared=shared)
        staging = download / 'verified'
        staging.mkdir()
        sync.unpack_verified(starter_archive, staging)
        require(sync.verify_checksum(starter_archive, starter_sum) == verified['archiveSha256'],
                'Downloaded starter archive changed between verification steps')
        verify_metadata(staging / 'TaskWorkRuntime', verified.get('runtimeMetadataSha256'),
                        {'SyncTaskWorkPlans.py', 'TaskWorkRegistry.py', 'recording_pack.py'})
        worked = module('morning_worked_sync_new', staging / 'TaskWorkRuntime/SyncTaskWorkPlans.py')
        incoming_plans = download / 'TaskWorkPlans'
        worked.sync(worked_archive, worked_sum, head, str(run['id']), staging / 'TaskWorkRuntime', incoming_plans, True)
        # Re-read after download/verification so an old candidate cannot replace
        # a newer cloud head or a now-invalid workflow result.
        latest = json.loads(command([GH, 'api', f'repos/{REPOSITORY}/git/ref/heads/{BRANCH}']))['object']['sha']
        fresh_run = json.loads(command([GH, 'api', f"repos/{REPOSITORY}/actions/runs/{run['id']}"]))
        if latest != head or candidate(head, [fresh_run]) is None:
            return publish_status(shared, 'Cloud head/build changed during verification; last verified kit preserved', proof, registry, latest)
        proof, registry = install_pair(sync, worked, staging, incoming_plans, shared, head, str(run['id']), proof['sourceCommit'], verified)
    return publish_status(shared, 'Current successful cloud kit synchronized; original starters and human attempts preserved', proof, registry, head)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--offline', action='store_true')
    args = parser.parse_args()
    lock = SHARED / '.TaskWorkMorning.lock'
    with ExitStack() as stack:
        try:
            stack.enter_context(owned_lock(lock))
        except BlockingIOError:
            print('Existing morning refresh owns the lock; no duplicate work')
            return
        try:
            print(json.dumps(refresh(offline=args.offline), indent=2))
        except Exception as exc:
            # A failed check never publishes affirmative kit/readiness facts.
            publish_status(SHARED, 'Refresh HOLD: ' + str(exc), None, None)
            raise


if __name__ == '__main__':
    main()
