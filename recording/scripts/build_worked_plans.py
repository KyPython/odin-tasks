"""Verify off-screen worked references and package their separate cloud evidence."""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import stat
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'runtime'))
from TaskWorkRegistry import load_json, validate_registry, validate_manifest, verify_goal
from recording_pack import route_from_body, validate_route


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory(root):
    found = {}
    for path in sorted(root.rglob('*')):
        if path.is_symlink() or not (path.is_dir() or path.is_file()):
            raise ValueError('Reference inventories permit regular files/directories only')
        if path.is_file():
            found[path.relative_to(root).as_posix()] = {'sha256': sha(path), 'mode': stat.S_IMODE(path.stat().st_mode)}
    return found


def build(args):
    if os.environ.get('GITHUB_ACTIONS') != 'true' or os.environ.get('GITHUB_REPOSITORY') != 'KyPython/odin-recording-preparation':
        raise ValueError('Cloud reference proof requires the real existing Actions workflow')
    if platform.system() != 'Darwin' or platform.machine() != 'arm64' or sys.version.split()[0] != '3.12.7':
        raise ValueError('Expected the pinned cloud ARM Mac/Python')
    kit = args.starter_kit.resolve()
    source = kit / 'TaskWorkInputs'
    runtime = kit / 'TaskWorkRuntime'
    cloud = json.loads((runtime / 'cloud-proof.json').read_text())
    if cloud['sourceCommit'] != os.environ['GITHUB_SHA'] or str(cloud['runId']) != os.environ['GITHUB_RUN_ID']:
        raise ValueError('Reference verification must use this same run’s actual starter kit')
    before = inventory(source)
    registry = load_json(runtime / 'task-registry.json')
    tasks = validate_registry(registry)
    validate_manifest(load_json(runtime / 'runtime-manifest.json'), registry)
    names = sorted(p.name for p in (ROOT / 'walkthroughs').iterdir() if p.is_dir())
    if set(names) != set(tasks):
        raise ValueError('Every registered task requires one complete worked reference; preserve incomplete stages as pending')
    if args.output.exists():
        raise ValueError('Preserve prior reference output')
    args.output.mkdir(parents=True)
    for name in names:
        plan = ROOT / 'walkthroughs' / name
        for required in ('walkthrough.md', 'solution.patch', 'rehearse.py', 'verification.json'):
            if not (plan / required).is_file() or (plan / required).is_symlink():
                raise ValueError('Incomplete worked reference: ' + name)
        destination = args.output / name
        shutil.copytree(plan, destination)
        task = tasks[name]
        verify_goal(task, runtime / task['goalFile'])
        route = validate_route((ROOT / 'packs/routes' / (name + '.md')).read_text())
        if route_from_body((destination / 'walkthrough.md').read_text()) != route:
            raise ValueError('Worked walkthrough differs from the validated recording sequence: ' + name)
        (destination / 'recording-sequence.md').write_text(route)
        command = [sys.executable, str(plan / 'rehearse.py'), '--inputs', str(source),
                   '--runtime', str(runtime), '--output', str(destination / 'cloud-verification.json')]
        started = dt.datetime.now(dt.timezone.utc).isoformat()
        result = subprocess.run(command, env=os.environ.copy(), capture_output=True, text=True, timeout=360)
        if result.returncode:
            raise ValueError('Worked plan failed: ' + name + '\n' + result.stdout + result.stderr)
        actual = json.loads((destination / 'cloud-verification.json').read_text())
        if not actual or not isinstance(actual, dict):
            raise ValueError('Missing observed rehearsal evidence: ' + name)
        if (actual.get('status') != 'PASS' or actual.get('sourceCommit') != task['commit'] or actual.get('goalSha256') != task['goalSha256']
                or not isinstance(actual.get('checks'), list) or not actual['checks']
                or actual.get('sourceInputsUnchanged') is not True
                or actual.get('recorderExecuted') is not False
                or actual.get('recordingWorkspaceModified') is not False):
            raise ValueError('Unbound or misleading rehearsal proof: ' + name)
        if actual.get('solutionPatchSha256') != sha(destination / 'solution.patch'):
            raise ValueError('Rehearsed patch differs from the packaged solution: ' + name)
        (destination / 'identity.json').write_text(json.dumps({
            'neutral': name, 'taskId': task['id'], 'sourceRepo': task['sourceRepo'],
            'sourceCommit': task['commit'], 'goalSha256': task['goalSha256'],
            'workflowLane': task.get('workflowLane', 'odin'),
            'routeSha256': sha(destination / 'recording-sequence.md'),
            'rehearsalCommand': command, 'rehearsalStartedAt': started, 'rehearsalExitCode': result.returncode,
            'stdout': result.stdout, 'stderr': result.stderr,
            'recorderExecuted': False, 'recordingWorkspaceModified': False,
            'paidWalkthroughPermissionVerified': False,
        }, indent=2) + '\n')
        print('Verified worked plan: ' + name, flush=True)
    if inventory(source) != before:
        raise ValueError('A rehearsal changed original starter inputs')
    shutil.copy2(ROOT / 'docs/WORKED_PLAN_PROCESS.md', args.output / 'WORKED_PLAN_PROCESS.md')
    repository = os.environ['GITHUB_REPOSITORY']
    proof = {'version': 1, 'repository': repository, 'sourceCommit': os.environ['GITHUB_SHA'],
             'runId': os.environ['GITHUB_RUN_ID'],
             'runUrl': f"https://github.com/{repository}/actions/runs/{os.environ['GITHUB_RUN_ID']}",
             'verifiedAt': dt.datetime.now(dt.timezone.utc).isoformat(), 'plans': names,
             'allRegisteredTasksCovered': True,
             'starterCloudProofSha256': sha(runtime / 'cloud-proof.json'),
             'starterInputsUnchanged': True, 'workedRepairsVerifiedInDisposableCopies': True,
             'recorderExecuted': False, 'recordingWorkspaceModified': False,
             'paidWalkthroughPermissionVerified': False}
    (args.output / 'worked-plans-proof.json').write_text(json.dumps(proof, indent=2) + '\n')
    for path in args.output.rglob('*'):
        path.chmod(0o755 if path.is_dir() else 0o644)
    args.output.chmod(0o755)
    (args.output / 'worked-plans-manifest.json').write_text(json.dumps(
        {'version': 1, 'files': inventory(args.output)}, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--starter-kit', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    build(parser.parse_args())
