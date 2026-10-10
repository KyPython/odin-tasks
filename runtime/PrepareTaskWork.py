"""Incremental off-screen Recorder setup; substantive task work is never executed."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import pwd
import re
import shutil
import stat
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from TaskWorkRegistry import load_json, validate_registry, validate_manifest, select_projects, verify_goal

SHARED = Path('/Users/Shared/TaskWorkRuntime')
INPUTS = Path('/Users/Shared/TaskWorkInputs')
HOME = Path('/Users/recorder')
WORK = HOME / 'Desktop/TaskWork'
CACHE_ROOT = HOME / 'Library/Caches/TaskWork'
CACHE = CACHE_ROOT
TASKS = {}
PUBLIC_PYTHON = '/usr/local/bin/python3'
PUBLIC_NODE = '/opt/homebrew/bin/node'
PUBLIC_COREPACK = '/opt/homebrew/bin/corepack'
PUBLIC_PATH = str(CACHE / 'bin') + ':/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin'


class StopSetup(Exception):
    pass


def stop(message):
    raise StopSetup(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode('utf-8')


def digest(path):
    result = hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            result.update(chunk)
    return result.hexdigest()


def private_directory(path):
    if not path.is_relative_to(HOME):
        stop('Refusing a destination outside the Recorder home.')
    for part in [HOME, *reversed(list(path.parents))]:
        if part == HOME or part.is_relative_to(HOME):
            if part.is_symlink():
                stop('A destination parent is a symlink; inspect it manually.')
    if path.is_symlink():
        stop('A destination is a symlink; inspect it manually.')
    path.mkdir(parents=True, exist_ok=True)
    if not path.is_dir() or path.stat().st_uid != os.getuid():
        stop('A destination directory is not owned by Recorder.')


def write_new_or_identical(path, content):
    if path.is_symlink():
        stop('A managed setup file is a symlink; nothing will be overwritten.')
    if path.exists():
        if not path.is_file() or path.read_bytes() != content:
            stop('An existing setup file differs; preserving it without overwrite.')
        return
    with path.open('xb') as output:
        output.write(content)


def tree(root):
    if root.is_symlink() or not root.is_dir():
        stop('A project or cache input is not a plain directory.')
    records = {}
    for base, directories, files in os.walk(root, followlinks=False):
        for name in sorted(directories + files):
            item = Path(base) / name
            relative = item.relative_to(root).as_posix()
            mode = stat.S_IMODE(item.lstat().st_mode)
            if item.is_symlink():
                records[relative] = {'kind': 'symlink', 'target': os.readlink(item), 'mode': mode}
            elif item.is_dir():
                records[relative] = {'kind': 'directory', 'mode': mode}
            elif item.is_file():
                records[relative] = {'kind': 'file', 'sha256': digest(item), 'mode': mode}
            else:
                stop('A project or cache contains a special file.')
    return records


def project_hash(project):
    return hashlib.sha256(canonical(project)).hexdigest()




def validate_source(project, root, allow_dependencies=False):
    records = tree(root)
    expected = project['files']
    expected_directories = set()
    for name in expected:
        parent = PurePosixPath(name).parent
        while parent.as_posix() != '.':
            expected_directories.add(parent.as_posix())
            parent = parent.parent
        entry = records.get(name)
        if entry != {'kind': 'file', 'sha256': expected[name]['sha256'], 'mode': expected[name]['mode']}:
            stop('A source file is missing or changed; preserving all existing work.')
    dependency_roots = TASKS[project['neutral']]['dependencyRoots'] if allow_dependencies else []
    for name, entry in records.items():
        if name in expected:
            continue
        if name in expected_directories and entry['kind'] == 'directory':
            continue
        if any(name == base or name.startswith(base + '/') for base in dependency_roots):
            continue
        stop('The project contains extra files or directories; preserving all existing work.')
    return records


def run(command, env, cwd=None):
    result = subprocess.run(command, cwd=cwd, env=env, text=True, capture_output=True)
    if result.returncode:
        stop('A dependency setup/version check failed. No existing work was reset.\n' + result.stdout[-3000:] + result.stderr[-3000:])
    return result.stdout.strip()


def copy_cache(name):
    source = SHARED / name
    destination = CACHE / name
    marker = CACHE / ('cache-input-' + name + '.json')
    source_records = tree(source)
    source_hash = hashlib.sha256(canonical(source_records)).hexdigest()
    marker_content = canonical({'version': 1, 'sourceHash': source_hash}) + b'\n'
    if destination.exists() or destination.is_symlink():
        if destination.is_symlink() or not destination.is_dir() or destination.stat().st_uid != os.getuid():
            stop('An existing runtime cache is unsafe or not Recorder-owned.')
        if not marker.is_file() or marker.is_symlink() or marker.read_bytes() != marker_content:
            stop('An existing runtime cache is unmanaged or has a different input; preserving it.')
        return
    if marker.exists() or marker.is_symlink():
        stop('An orphaned runtime cache marker requires manual inspection.')
    shutil.copytree(source, destination, symlinks=True)
    if tree(destination) != source_records:
        stop('A copied runtime cache does not match its shared input; inspect it manually.')
    write_new_or_identical(marker, marker_content)


def prepare_project(project, env):
    name = project['neutral']
    source = INPUTS / name
    destination = WORK / name
    task = TASKS[name]
    receipt_path = CACHE_ROOT / 'receipts' / (name + '.json')
    validate_source(project, source)
    prior = None
    if receipt_path.exists() or receipt_path.is_symlink():
        if receipt_path.is_symlink() or not receipt_path.is_file():
            stop('A setup receipt requires manual inspection.')
        prior = json.loads(receipt_path.read_text())
        if prior.get('projectHash') != project_hash(project) or prior.get('taskHash') != project_hash(task):
            stop('The source manifest differs from an existing setup receipt.')
    if destination.exists() or destination.is_symlink():
        current = validate_source(project, destination, allow_dependencies=prior is not None)
        if prior is not None and current != prior.get('tree'):
            stop('A prepared project has changed since setup; preserving all existing work.')
        if prior is None:
            # Source-only folders are reusable; extra dependency/work folders are not.
            validate_source(project, destination)
    else:
        if prior is not None:
            stop('A previous project receipt exists without its workspace; inspect it manually.')
        shutil.copytree(source, destination)
        validate_source(project, destination)
    versions = {}
    if task['dependencyProfile'] == 'node-stdlib':
        versions['node'] = run([PUBLIC_NODE, '--version'], env, destination)
        if versions['node'] != 'v' + task['dependencyVersions']['node']:
            stop('The public Node runtime is not the registered pinned Node version.')
    elif task['dependencyProfile'] == 'python-pytest':
        interpreter = destination / '.venv/bin/python'
        if prior is None:
            run([PUBLIC_PYTHON, '-I', '-m', 'venv', str(destination / '.venv')], env, destination)
            run([str(interpreter), '-I', '-m', 'pip', 'install', '--no-index', '--find-links', str(SHARED / 'wheels'), '-r', task['requirementsFile']], env, destination)
        versions['pytest'] = run([str(interpreter), '-I', '-c', 'import pytest; print(pytest.__version__)'], env, destination)
        if versions['pytest'] != task['dependencyVersions']['pytest']:
            stop('The installed pytest version is not the pinned starter version.')
    elif task['dependencyProfile'] == 'pnpm-workspace':
        versions['pnpm'] = run([PUBLIC_COREPACK, 'pnpm', '--version'], env, destination)
        if versions['pnpm'] != task['dependencyVersions']['pnpm']:
            stop('The package manager is not the registered pinned pnpm version.')
        if prior is None:
            run([PUBLIC_COREPACK, 'pnpm', 'install', '--frozen-lockfile', '--offline', '--store-dir', str(CACHE / 'pnpm-store')], env, destination)
        versions['turbo'] = run([PUBLIC_COREPACK, 'pnpm', 'exec', 'turbo', '--version'], env, destination)
        if versions['turbo'] != task['dependencyVersions']['turbo']:
            stop('The installed Turbo version is not the pinned starter version.')
    final_tree = validate_source(project, destination, allow_dependencies=True)
    if prior is not None and (final_tree != prior['tree'] or versions != prior['dependencyVersions']):
        stop('A managed dependency changed during verification; preserving the existing attempt.')
    receipt = {'version': 2, 'projectHash': project_hash(project), 'taskHash': project_hash(task), 'tree': final_tree, 'dependencyVersions': versions, 'runtimeCache': str(CACHE.relative_to(CACHE_ROOT))}
    write_new_or_identical(receipt_path, canonical(receipt) + b'\n')
    print(name + ': unchanged source and dependency checks passed.')
    return {'sourceCommit': project['commit'], 'projectHash': receipt['projectHash'], 'treeHash': hashlib.sha256(canonical(final_tree)).hexdigest(), 'dependencyVersions': versions}



def runtime_cache(project, seed_hash):
    receipt_path = CACHE_ROOT / 'receipts' / (project['neutral'] + '.json')
    if receipt_path.exists() or receipt_path.is_symlink():
        if receipt_path.is_symlink() or not receipt_path.is_file():
            stop('A task receipt is unsafe; preserving it.')
        receipt = load_json(receipt_path)
        relative = receipt.get('runtimeCache')
        if not isinstance(relative, str) or not re.fullmatch(r'runtimes/[a-f0-9]{64}', relative):
            stop('A legacy or unmanaged task receipt needs an off-screen migration review; preserving it.')
        cache = CACHE_ROOT / relative
        if not cache.is_dir() or cache.is_symlink():
            stop('The task runtime cache is missing or unsafe; preserving its attempt.')
        return cache, False
    return CACHE_ROOT / 'runtimes' / seed_hash, True


def workspace_config(project, task, env):
    interpreter = str(WORK / project['neutral'] / '.venv/bin/python') if task['dependencyProfile'] == 'python-pytest' else PUBLIC_PYTHON
    return {'folders': [{'path': project['neutral']}], 'settings': {
        'chat.disableAIFeatures': True,
        'python.defaultInterpreterPath': interpreter,
        'terminal.integrated.env.osx': {key: env[key] for key in (
            'PATH', 'COREPACK_HOME', 'COREPACK_ENABLE_NETWORK', 'COREPACK_ENABLE_AUTO_PIN',
            'COREPACK_ENABLE_DOWNLOAD_PROMPT', 'PYTHONDONTWRITEBYTECODE', 'npm_config_store_dir',
            'npm_config_cache', 'XDG_CACHE_HOME', 'TMPDIR')},
    }}


def controlled_environment():
    env = os.environ.copy()
    for name in ('PYTHONHOME', 'PYTHONPATH', 'VIRTUAL_ENV', 'CONDA_PREFIX', 'CONDA_DEFAULT_ENV', 'NODE_PATH', 'NODE_OPTIONS', 'PNPM_HOME'):
        env.pop(name, None)
    env.update({'PATH': str(CACHE / 'bin') + ':/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin',
                'COREPACK_HOME': str(CACHE / 'corepack'), 'COREPACK_ENABLE_NETWORK': '0',
                'COREPACK_ENABLE_AUTO_PIN': '0', 'COREPACK_ENABLE_DOWNLOAD_PROMPT': '0',
                'PYTHONDONTWRITEBYTECODE': '1', 'npm_config_store_dir': str(CACHE / 'pnpm-store'),
                'npm_config_cache': str(CACHE / 'npm-cache'), 'XDG_CACHE_HOME': str(CACHE / 'xdg'),
                'TMPDIR': str(CACHE / 'tmp'), 'PIP_NO_INDEX': '1', 'PIP_NO_CACHE_DIR': '1',
                'PIP_DISABLE_PIP_VERSION_CHECK': '1'})
    return env


def prepare_runtime(copy_inputs):
    for suffix in ('', 'bin', 'tmp'):
        private_directory(CACHE / suffix)
    if any(path.name not in ('node', 'corepack', 'pnpm') for path in (CACHE / 'bin').iterdir()):
        stop('The runtime shim folder contains extra files; preserving it.')
    if copy_inputs:
        for name in ('corepack', 'pnpm-store'):
            copy_cache(name)
    for name, command in {'node': 'exec /opt/homebrew/bin/node "$@"', 'corepack': 'exec /opt/homebrew/bin/corepack "$@"', 'pnpm': 'exec /opt/homebrew/bin/corepack pnpm "$@"'}.items():
        shim = CACHE / 'bin' / name
        existed = shim.exists() or shim.is_symlink()
        write_new_or_identical(shim, ('#!/bin/zsh\n' + command + '\n').encode())
        if stat.S_IMODE(shim.stat().st_mode) != 0o755:
            if existed or shim.stat().st_uid != os.getuid():
                stop('A managed runtime shim has changed; preserving it.')
            shim.chmod(0o755)


def main(argv=None):
    global CACHE, TASKS
    if (os.getuid() == 0 or os.geteuid() == 0 or pwd.getpwuid(os.getuid()).pw_name != 'recorder'
            or os.environ.get('HOME') != str(HOME) or any(key.startswith('SUDO_') for key in os.environ)):
        stop('Sign directly into Recorder; root or sudo execution is refused.')
    parser = argparse.ArgumentParser(description='Prepare reviewed task workspaces off-screen without replacing existing work.')
    parser.add_argument('--task', help='Prepare only this neutral task; other attempts are not inspected or changed.')
    args = parser.parse_args(argv)
    if sys.version_info < (3, 11):
        stop('The public Python interpreter must be version 3.11 or later.')
    manifest = load_json(SHARED / 'runtime-manifest.json')
    registry = load_json(SHARED / 'task-registry.json')
    TASKS = validate_registry(registry)
    projects = select_projects(validate_manifest(manifest, registry), args.task)
    if manifest.get('python') != PUBLIC_PYTHON or manifest.get('node') != PUBLIC_NODE or manifest.get('corepack') != PUBLIC_COREPACK:
        stop('The runtime manifest differs from the reviewed public toolchain.')
    for project in projects:
        validate_source(project, INPUTS / project['neutral'])
        verify_goal(TASKS[project['neutral']], SHARED / TASKS[project['neutral']]['goalFile'])
    for folder in (WORK, CACHE_ROOT, CACHE_ROOT / 'receipts', CACHE_ROOT / 'ready-receipts'):
        private_directory(folder)
    seed_records = {name: tree(SHARED / name) for name in ('corepack', 'pnpm-store', 'wheels')}
    seed_hash = hashlib.sha256(canonical(seed_records)).hexdigest()
    for project in projects:
        name = project['neutral']
        task = TASKS[name]
        CACHE, copy_inputs = runtime_cache(project, seed_hash)
        prepare_runtime(copy_inputs)
        env = controlled_environment()
        versions = {'python': sys.version.split()[0], 'node': run([PUBLIC_NODE, '--version'], env), 'corepack': run([PUBLIC_COREPACK, '--version'], env)}
        if not re.fullmatch(r'v22\.[0-9]+\.[0-9]+', versions['node']):
            stop('The public Node runtime must be the reviewed Node 22 toolchain.')
        config = workspace_config(project, task, env)
        workspace_path = WORK / (name + '.code-workspace')
        workspace_bytes = json.dumps(config, indent=2, sort_keys=True).encode() + b'\n'
        goal = verify_goal(task, SHARED / task['goalFile'])
        goal_path = WORK / (name + '-goal.txt')
        # Check user settings/Goal before creating dependencies; never overwrite a different file.
        for path, content in ((workspace_path, workspace_bytes), (goal_path, goal)):
            if path.exists() or path.is_symlink():
                if path.is_symlink() or not path.is_file() or path.read_bytes() != content:
                    stop('A selected task workspace or Goal document differs; preserving it.')
        outcome = prepare_project(project, env)
        write_new_or_identical(workspace_path, workspace_bytes)
        write_new_or_identical(goal_path, goal)
        ready = {'version': 2, 'setupStatus': 'READY', 'recordingReady': False, 'baselineTestsRun': False,
                 'repairsApplied': False, 'user': 'recorder', 'home': str(HOME), 'taskId': task['id'],
                 'toolVersions': versions, 'projects': {name: outcome}, 'goalHashes': {name: hashlib.sha256(goal).hexdigest()},
                 'workspaceSha256': hashlib.sha256(workspace_bytes).hexdigest(), 'runtimeCache': str(CACHE.relative_to(CACHE_ROOT))}
        ready_path = CACHE_ROOT / 'ready-receipts' / (name + '.json')
        if ready_path.exists() or ready_path.is_symlink():
            if ready_path.is_symlink() or not ready_path.is_file():
                stop('A selected task ready receipt is unsafe; preserving it.')
            prior = load_json(ready_path)
            prior.pop('createdAt', None)
            if prior != ready:
                stop('A selected task ready receipt differs; preserving it.')
        else:
            ready['createdAt'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
            write_new_or_identical(ready_path, json.dumps(ready, indent=2, sort_keys=True).encode() + b'\n')
    print('Setup checks passed. Open the matching .code-workspace file from Desktop/TaskWork.')
    print('Per-task setup receipts are in Library/Caches/TaskWork/ready-receipts. Recheck the current task Goal and workflow lane.')
    print('No project tests or repairs were run. Recorder permissions and recording admission still require human verification.')


if __name__ == '__main__':
    try:
        main()
    except (StopSetup, OSError, ValueError, KeyError, TypeError) as error:
        print('STOP: ' + str(error), file=sys.stderr)
        sys.exit(1)
