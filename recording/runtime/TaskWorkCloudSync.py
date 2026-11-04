#!/usr/local/bin/python3
"""Verify a downloaded TaskWork cloud artifact, then preserve and replace Shared runtime.

No archive content is executed. Original repos and the Recorder home are never opened.
A successful GitHub Actions run/head must be checked before downloading the artifact;
this utility independently checks its checksum, inventory, source files and run proof.
"""
import argparse
import datetime as dt
import fcntl
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
import unicodedata

REPOSITORY = 'KyPython/odin-recording-preparation'
SHARED = Path('/Users/Shared')
MAX_MEMBERS = 250000
MAX_EXPANDED_BYTES = 2 * 1024**3
MAX_FILE_BYTES = 256 * 1024**2
TOOLS = {
    'python3': '/usr/local/bin/python3',
    'node': '/opt/homebrew/bin/node',
    'corepack': '/opt/homebrew/bin/corepack',
    'pnpm': '/opt/homebrew/bin/pnpm',
}
sys.path.insert(0, str(Path(__file__).resolve().parent))
from TaskWorkRegistry import load_json, validate_registry, validate_manifest, source_count, verify_goal



class VerificationError(Exception):
    pass


def require(condition, message):
    if not condition:
        raise VerificationError(message)


def read_json(data, label):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, f'{label}: duplicate JSON key {key!r}')
            result[key] = value
        return result
    try:
        return json.loads(data, object_pairs_hook=unique)
    except (UnicodeError, ValueError) as exc:
        raise VerificationError(f'{label}: invalid JSON: {exc}') from exc


def digest(path):
    result = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            result.update(chunk)
    return result.hexdigest()


def safe_name(name, allow_root=False):
    require(isinstance(name, str) and name, 'Empty archive path')
    require(not name.startswith('/') and '\\' not in name, f'Unsafe archive path: {name!r}')
    require(not any(ord(c) < 32 or ord(c) == 127 for c in name), f'Control character in path: {name!r}')
    while name.startswith('./'):
        name = name[2:]
    name = name.rstrip('/')
    if allow_root and name in ('', '.'):
        return ''
    require(name and all(p not in ('', '.', '..') for p in name.split('/')), f'Unsafe archive path: {name!r}')
    require(PurePosixPath(name).parts[0] in {'TaskWorkInputs', 'TaskWorkRuntime', 'cloud-proof.json', 'bundle-manifest.json'}, f'Unexpected artifact root: {name!r}')
    require('/' not in name or name.split('/')[0] in {'TaskWorkInputs', 'TaskWorkRuntime'}, f'Unexpected artifact path: {name!r}')
    return name


def mode_value(value, label):
    require(type(value) is int and 0 <= value <= 0o777, f'Unsafe file mode for {label}')
    return value


def verify_link(name, target):
    require(isinstance(target, str) and target and '\\' not in target, f'Unsafe link target: {name}')
    require(not any(ord(c) < 32 or ord(c) == 127 for c in target), f'Unsafe link target: {name}')
    if target.startswith('/'):
        tool = name.removeprefix('TaskWorkRuntime/bin/')
        require(name == f'TaskWorkRuntime/bin/{tool}' and TOOLS.get(tool) == target, f'Unapproved absolute symlink: {name} -> {target}')
        return
    # Resolve lexically only. Never follow cache links, even for verification.
    parts = list(PurePosixPath(name).parent.parts)
    for component in target.split('/'):
        if component in ('', '.'):
            continue
        if component == '..':
            require(len(parts) > 1, f'Symlink escapes artifact root: {name} -> {target}')
            parts.pop()
        else:
            parts.append(component)
    require(parts and parts[0] == 'TaskWorkRuntime', f'Symlink escapes runtime: {name} -> {target}')


def scan_tree(root):
    """Inventory without following symlinks, including otherwise-empty directories."""
    result = {}
    def visit(directory, prefix):
        with os.scandir(directory) as entries:
            for entry in entries:
                name = f'{prefix}/{entry.name}' if prefix else entry.name
                info = entry.stat(follow_symlinks=False)
                mode = stat.S_IMODE(info.st_mode)
                path = Path(entry.path)
                if stat.S_ISLNK(info.st_mode):
                    result[name] = {'kind': 'symlink', 'target': os.readlink(path), 'mode': mode}
                elif stat.S_ISDIR(info.st_mode):
                    result[name] = {'kind': 'directory', 'mode': mode}
                    visit(path, name)
                elif stat.S_ISREG(info.st_mode):
                    result[name] = {'kind': 'file', 'sha256': digest(path), 'mode': mode}
                else:
                    raise VerificationError(f'Unsupported filesystem member: {name}')
    require(root.is_dir() and not root.is_symlink(), f'Expected real directory: {root}')
    visit(root, '')
    return result


def verify_checksum(archive, checksum):
    for path in (archive, checksum):
        require(path.is_file() and not path.is_symlink(), f'Expected regular input file: {path}')
    lines = checksum.read_text(encoding='utf-8').splitlines()
    require(len(lines) == 1, 'Checksum file must contain one SHA-256 entry')
    match = re.fullmatch(r'([0-9a-fA-F]{64})(?:[ \t]+\*?([^\r\n]+))?', lines[0])
    require(match is not None, 'Invalid SHA-256 checksum format')
    if match[2]:
        require(match[2] in (archive.name, './' + archive.name), 'Checksum names a different archive')
    value = digest(archive)
    require(value == match[1].lower(), 'Archive SHA-256 does not match checksum')
    return value


def unpack_verified(archive, staging):
    """Validate all archive metadata before writing; extract files before symlinks."""
    try:
        bundle = tarfile.open(archive, mode='r:gz')
    except (OSError, tarfile.TarError) as exc:
        raise VerificationError(f'Cannot open gzip tar archive: {exc}') from exc
    with bundle:
        entries = {}
        folded = set()
        total = 0
        for member in bundle:
            require(len(entries) < MAX_MEMBERS, 'Archive has too many members')
            name = safe_name(member.name, allow_root=True)
            if not name:
                require(member.isdir(), 'Archive root entry must be a directory')
                continue
            require(name not in entries, f'Duplicate archive member: {name}')
            folded_name = unicodedata.normalize('NFC', name).casefold()
            require(folded_name not in folded, f'Case or Unicode alias in archive: {name}')
            folded.add(folded_name)
            require(member.isfile() or member.isdir() or member.issym(), f'Unsupported archive member: {name}')
            require(0 <= member.size <= MAX_FILE_BYTES, f'Archive member too large: {name}')
            total += member.size
            require(total <= MAX_EXPANDED_BYTES, 'Archive expanded size exceeds limit')
            mode_value(member.mode, name)
            if member.issym():
                verify_link(name, member.linkname)
            entries[name] = member
        require('bundle-manifest.json' in entries and entries['bundle-manifest.json'].isfile(), 'Missing regular bundle-manifest.json')
        require(entries['bundle-manifest.json'].size <= 32 * 1024**2, 'Bundle manifest too large')
        stream = bundle.extractfile(entries['bundle-manifest.json'])
        require(stream is not None, 'Cannot read bundle manifest')
        with stream:
            manifest_bytes = stream.read()
        manifest = read_json(manifest_bytes, 'bundle-manifest.json')
        require(isinstance(manifest, dict) and manifest.get('version') == 1 and isinstance(manifest.get('files'), dict), 'Unsupported bundle manifest schema')
        expected = manifest['files']
        require(set(expected) == set(entries) - {'bundle-manifest.json'}, 'Bundle manifest member set differs from archive')
        for name, spec in expected.items():
            require(safe_name(name) == name and isinstance(spec, dict), f'Invalid manifest entry: {name}')
            member = entries[name]
            actual_kind = 'file' if member.isfile() else 'directory' if member.isdir() else 'symlink'
            require(spec.get('kind') == actual_kind, f'Member kind mismatch: {name}')
            require(mode_value(spec.get('mode'), name) == member.mode, f'Member mode mismatch: {name}')
            if actual_kind == 'file':
                require(re.fullmatch(r'[0-9a-f]{64}', spec.get('sha256', '')) is not None, f'Invalid file hash: {name}')
            elif actual_kind == 'symlink':
                require(spec.get('target') == member.linkname, f'Symlink target mismatch: {name}')
        for name in entries:
            for ancestor in PurePosixPath(name).parents:
                if str(ancestor) == '.':
                    continue
                require(str(ancestor) in entries and entries[str(ancestor)].isdir(), f'Missing or non-directory archive ancestor: {name}')
        for root in ('TaskWorkInputs', 'TaskWorkRuntime'):
            require(root in entries and entries[root].isdir() and entries[root].mode == 0o755, f'Missing mode-0755 root: {root}')
        require(entries['bundle-manifest.json'].mode == 0o644, 'Bundle manifest must have mode 0644')
        # All directory ancestors are validated as actual tar directories, so no write follows a link.
        for name, member in sorted(entries.items(), key=lambda item: len(PurePosixPath(item[0]).parts)):
            if member.isdir():
                (staging / name).mkdir(mode=0o700)
        for name, member in entries.items():
            if member.isfile():
                stream = bundle.extractfile(member)
                require(stream is not None, f'Cannot read archive file: {name}')
                with stream, (staging / name).open('xb') as destination:
                    shutil.copyfileobj(stream, destination, length=1024 * 1024)
                os.chmod(staging / name, member.mode)
        for name, member in entries.items():
            if member.issym():
                os.symlink(member.linkname, staging / name)
        for name, member in sorted(entries.items(), key=lambda item: len(PurePosixPath(item[0]).parts), reverse=True):
            if member.isdir():
                os.chmod(staging / name, member.mode)
        actual = scan_tree(staging)
        actual.pop('bundle-manifest.json')
        require(actual == expected, 'Extracted contents differ from bundle manifest (hash, mode or link target)')
        return manifest


def source_inventory(manifest, registry):
    projects = validate_manifest(manifest, registry)
    require(manifest.get('python') == TOOLS['python3'] and manifest.get('node') == TOOLS['node'] and manifest.get('corepack') == TOOLS['corepack'], 'Unexpected runtime tool contract')
    expected = {}
    for project in projects:
        name = project['neutral']
        expected[name] = {'kind': 'directory', 'mode': 0o755}
        for relative, spec in project['files'].items():
            path = f'{name}/{relative}'
            expected[path] = {'kind': 'file', 'sha256': spec['sha256'], 'mode': spec['mode']}
            for parent in PurePosixPath(path).parents:
                if str(parent) != '.':
                    require(str(parent) not in expected or expected[str(parent)]['kind'] == 'directory', f'Source file/directory conflict: {path}')
                    expected[str(parent)] = {'kind': 'directory', 'mode': 0o755}
    return expected


def source_contracts(staging, shared):
    runtime = staging / 'TaskWorkRuntime'
    local_runtime = shared / 'TaskWorkRuntime'
    require(local_runtime.is_dir() and not local_runtime.is_symlink(), 'Local Shared runtime is missing or unsafe')
    manifest = read_json((runtime / 'runtime-manifest.json').read_bytes(), 'Cloud runtime manifest')
    registry = read_json((runtime / 'task-registry.json').read_bytes(), 'Cloud task registry')
    local_manifest_path = local_runtime / 'runtime-manifest.json'
    require(local_manifest_path.is_file() and not local_manifest_path.is_symlink(), 'Local runtime manifest is missing or unsafe')
    local_manifest = read_json(local_manifest_path.read_bytes(), 'Local runtime manifest')
    local_registry_path = local_runtime / 'task-registry.json'
    if local_registry_path.exists() or local_registry_path.is_symlink():
        require(local_registry_path.is_file() and not local_registry_path.is_symlink(), 'Local task registry is unsafe')
        local_registry = read_json(local_registry_path.read_bytes(), 'Local task registry')
    else:
        # The initial four-task kit predates the registry. Bind migration to its exact
        # existing source map and Goal bytes; never rewrite those reviewed inputs.
        local_names = {project['neutral'] for project in local_manifest['projects']}
        local_registry = {'version': 1, 'tasks': [task for task in registry['tasks'] if task['neutral'] in local_names]}
    validate_manifest(manifest, registry)
    validate_manifest(local_manifest, local_registry)
    current_projects = {project['neutral']: project for project in local_manifest['projects']}
    incoming_projects = {project['neutral']: project for project in manifest['projects']}
    current_tasks = validate_registry(local_registry)
    incoming_tasks = validate_registry(registry)
    require(all(name in incoming_projects and incoming_projects[name] == project for name, project in current_projects.items()), 'Cloud kit removes or changes an existing pinned starter; preserve prior work')
    require(all(name in incoming_tasks and incoming_tasks[name] == task for name, task in current_tasks.items()), 'Cloud kit changes an existing reviewed task; register a new revision separately')
    require(scan_tree(shared / 'TaskWorkInputs') == source_inventory(local_manifest, local_registry), 'Existing Shared inputs changed; refusing to replace them')
    require(scan_tree(staging / 'TaskWorkInputs') == source_inventory(manifest, registry), 'Cloud inputs differ from the reviewed source contract')
    return manifest, registry, local_manifest, local_registry


def verify_contract(staging, shared, commit, run_id):
    runtime = staging / 'TaskWorkRuntime'
    local_runtime = shared / 'TaskWorkRuntime'
    manifest, registry, local_manifest, local_registry = source_contracts(staging, shared)
    tasks = validate_registry(registry)
    for filename in ('cloud-proof.json', 'TaskWorkRuntime/cloud-proof.json'):
        path = staging / filename
        require(path.is_file() and not path.is_symlink(), f'Missing regular proof: {filename}')
    proof_bytes = (staging / 'cloud-proof.json').read_bytes()
    require(proof_bytes == (runtime / 'cloud-proof.json').read_bytes(), 'Cloud proof copies differ')
    proof = read_json(proof_bytes, 'cloud-proof.json')
    require(isinstance(proof, dict) and proof.get('version') == 1, 'Unsupported cloud proof schema')
    require(proof.get('repository') == REPOSITORY, 'Unexpected cloud proof repository')
    require(proof.get('sourceCommit') == commit and str(proof.get('runId')) == run_id, 'Cloud proof commit or Actions run does not match expected values')
    require(proof.get('sourceFiles') == source_count(manifest) and proof.get('repairsApplied') is False and proof.get('recorderExecuted') is False, 'Cloud proof violates starter-only or Recorder boundary')
    require(isinstance(proof.get('checks'), list) and proof['checks'], 'Cloud proof has no executed checks')
    platform = proof.get('platform', {})
    require(isinstance(platform, dict) and platform.get('machine') == 'arm64' and platform.get('system') == 'Darwin', 'Cloud build must target Darwin arm64')
    commits = proof.get('starterCommits')
    require(isinstance(commits, dict) and commits == {project['neutral']: project['commit'] for project in manifest['projects']}, 'Cloud proof starter commits differ from pinned inputs')
    require(isinstance(proof.get('toolVersions'), dict) and proof['toolVersions'], 'Cloud proof has no tool-version evidence')
    helper = runtime / 'Prepare-TaskWork.command'
    require(helper.is_file() and not helper.is_symlink() and stat.S_IMODE(helper.stat().st_mode) == 0o755, 'Preparation helper missing or not executable mode 0755')
    for filename in ('PrepareTaskWork.py', 'TaskWorkRegistry.py', 'TaskWorkCloudSync.py', 'recording_pack.py',
                     'task-registry.json', 'runtime-manifest.json', 'process/REUSABLE_TASK_PROCESS.md',
                     'process/RECORDER-CODEX-PROMPT.txt', 'process/TASK-IDEA-TO-RECORDING-PROMPT.txt'):
        path = runtime / filename
        require(path.is_file() and not path.is_symlink(), f'Missing regular runtime metadata: {filename}')
    for tool, target in TOOLS.items():
        path = runtime / 'bin' / tool
        require(path.is_symlink() and os.readlink(path) == target, f'Public tool link mismatch: {tool}')
    for task in tasks.values():
        path = runtime / task['goalFile']
        verify_goal(task, path)
        if task['neutral'] in {project['neutral'] for project in local_manifest['projects']}:
            local = local_runtime / task['goalFile']
            require(local.is_file() and not local.is_symlink() and path.read_bytes() == local.read_bytes(), f'Exact existing Goal document differs: {task["neutral"]}')
    profiles = {task['dependencyProfile'] for task in tasks.values()}
    required_caches = set()
    if 'python-pytest' in profiles:
        required_caches.add('wheels')
    if 'pnpm-workspace' in profiles:
        required_caches.update(('corepack', 'pnpm-store'))
    for cache in ('wheels', 'corepack', 'pnpm-store'):
        path = runtime / cache
        require(path.is_dir() and not path.is_symlink(), f'Missing dependency cache directory: {cache}')
        if cache in required_caches:
            require(bool(scan_tree(path)), f'Empty required dependency cache: {cache}')
    return proof


def write_sync_receipt(runtime, receipt):
    """Add the real install receipt to staging before the transactional rename."""
    path = runtime / 'cloud-sync-receipt.json'
    require(not os.path.lexists(path), 'The incoming cloud artifact already contains a sync receipt')
    with path.open('x', encoding='utf-8') as handle:
        json.dump(receipt, handle, indent=2)
        handle.write('\n')
        handle.flush()
        os.fsync(handle.fileno())
    path.chmod(0o644)


def sync_runtime(staging, shared, commit, run_id, receipt):
    lock_path = shared / '.TaskWorkCloudSync.lock'
    flags = os.O_WRONLY | os.O_CREAT | getattr(os, 'O_NOFOLLOW', 0)
    descriptor = os.open(lock_path, flags, 0o600)
    try:
        info = os.fstat(descriptor)
        require(stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid(), 'Unsafe sync lock file')
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise VerificationError('Another TaskWork cloud sync is running') from exc
        # Recheck source state after taking the lock, immediately before any rename.
        verify_contract(staging, shared, commit, run_id)
        runtime = shared / 'TaskWorkRuntime'
        timestamp = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
        backup = shared / ('TaskWorkRuntime.previous-local-' + timestamp)
        require(not os.path.lexists(backup), 'Backup destination unexpectedly exists')
        durable_receipt = {**receipt, 'previousRuntime': str(backup)}
        require(durable_receipt.get('verified') is True and durable_receipt.get('synced') is True
                and durable_receipt.get('sourceCommit') == commit and str(durable_receipt.get('runId')) == run_id,
                'Install receipt does not match the verified sync operation')
        manifest, registry, current_manifest, _ = source_contracts(staging, shared)
        current_names = {project['neutral'] for project in current_manifest['projects']}
        additions = [project['neutral'] for project in manifest['projects'] if project['neutral'] not in current_names]
        installed = []
        runtime_moved = False
        try:
            # A write failure here leaves current runtime and shared inputs intact.
            # The complete receipt is installed atomically with the new runtime.
            write_sync_receipt(staging / 'TaskWorkRuntime', durable_receipt)
            for name in additions:
                destination = shared / 'TaskWorkInputs' / name
                require(not os.path.lexists(destination), 'A new starter destination already exists')
                os.rename(staging / 'TaskWorkInputs' / name, destination)
                installed.append(name)
            os.rename(runtime, backup)
            runtime_moved = True
            os.rename(staging / 'TaskWorkRuntime', runtime)
        except BaseException:
            if runtime_moved:
                os.rename(backup, runtime)
            for name in reversed(installed):
                os.rename(shared / 'TaskWorkInputs' / name, staging / 'TaskWorkInputs' / name)
            raise
        return backup
    finally:
        os.close(descriptor)


def process(archive, checksum, commit, run_id, *, sync=False, shared=SHARED):
    require(re.fullmatch(r'[0-9a-f]{40}', commit) is not None, 'Expected a full lowercase Git commit SHA')
    require(re.fullmatch(r'[1-9][0-9]*', run_id) is not None, 'Expected a numeric positive Actions run ID')
    require(shared.is_dir() and not shared.is_symlink(), 'Shared root must be a real directory')
    archive_hash = verify_checksum(archive, checksum)
    staging = Path(tempfile.mkdtemp(prefix='.TaskWorkCloudSync-staging-', dir=shared))
    try:
        bundle_manifest = unpack_verified(archive, staging)
        proof = verify_contract(staging, shared, commit, run_id)
        metadata_hashes = {name.removeprefix('TaskWorkRuntime/'): record['sha256']
                           for name, record in bundle_manifest['files'].items()
                           if record.get('kind') == 'file' and
                           (name.startswith('TaskWorkRuntime/') and len(PurePosixPath(name).parts) == 2 or
                            name.startswith('TaskWorkRuntime/process/'))}
        result = {
            'verified': True, 'synced': sync, 'repository': REPOSITORY,
            'sourceCommit': commit, 'runId': run_id, 'archiveSha256': archive_hash,
            'verifiedMembers': len(bundle_manifest['files']), 'sourceFiles': proof['sourceFiles'],
            'runtimeMetadataSha256': metadata_hashes,
            'sourceInputs': 'unchanged; exact cloud match',
            'runtime': str(shared / 'TaskWorkRuntime'),
            'previousRuntime': None,
            'recorderExecuted': False,
        }
        if sync:
            backup = sync_runtime(staging, shared, commit, run_id, result)
            result['previousRuntime'] = str(backup)
        return result
    finally:
        shutil.rmtree(staging)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('checksum', type=Path)
    parser.add_argument('--commit', required=True, help='Expected full Actions head SHA, checked with GitHub before download')
    parser.add_argument('--run-id', required=True, help='Expected successful GitHub Actions run ID')
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--verify-only', action='store_true', help='Verify without replacing Shared runtime (default)')
    mode.add_argument('--sync', action='store_true', help='Preserve old Shared runtime and install verified cloud runtime')
    args = parser.parse_args()
    try:
        result = process(args.archive, args.checksum, args.commit, args.run_id, sync=args.sync)
    except (VerificationError, ValueError, OSError, tarfile.TarError) as exc:
        print(f'STOP: {exc}', file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
