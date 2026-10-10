"""Fault-injection checks for safe morning selection and paired installation."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('morning', ROOT / 'runtime/TaskWorkMorning.py')
morning = importlib.util.module_from_spec(spec)
spec.loader.exec_module(morning)
OLD, NEW, NEXT = 'a' * 40, 'b' * 40, 'c' * 40


class MorningTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(dir=Path(tempfile.gettempdir()).resolve())
        self.root = Path(self.temporary.name)
        self.shared = self.root / 'Shared'
        self.shared.mkdir()
        self.proof = {'sourceCommit': OLD, 'runId': '1', 'repository': morning.REPOSITORY,
                      'runUrl': f'https://github.com/{morning.REPOSITORY}/actions/runs/1'}
        self.registry = {'tasks': [{'neutral': 'existing-task'}]}
        self.good = {'id': 3, 'head_sha': NEW, 'head_branch': morning.BRANCH,
                     'status': 'completed', 'conclusion': 'success'}

    def tearDown(self):
        self.temporary.cleanup()

    def write(self, path, content):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(content) + '\n' if isinstance(content, (dict, list)) else content)
        path.chmod(0o644)

    def contents(self, root):
        return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob('*') if p.is_file()}

    def refresh(self, responses):
        with mock.patch.object(morning, 'verify_installed', return_value=(self.proof, {'tasks': []})), \
             mock.patch.object(morning, 'command', side_effect=[json.dumps(x) for x in responses]) as commands:
            result = morning.refresh(self.shared)
        return result, commands

    def test_never_installs_old_failed_or_other_branch_build(self):
        runs = [dict(self.good, id=9, head_sha=OLD), dict(self.good, id=8, conclusion='failure'),
                dict(self.good, id=7, head_branch='other'), dict(self.good, id=6, status='in_progress'), self.good]
        self.assertEqual(morning.candidate(NEW, runs), self.good)
        self.assertIsNone(morning.candidate(NEXT, runs))
        with self.assertRaisesRegex(ValueError, 'current cloud head'):
            morning.candidate('not-a-sha', runs)

    def test_current_head_is_no_download_no_rebuild(self):
        result, commands = self.refresh([{'object': {'sha': OLD}}, {'workflow_runs': [dict(self.good, head_sha=OLD)]}])
        self.assertIn('without download or rebuild', result['state'])
        self.assertEqual(commands.call_count, 2)
        self.assertTrue(all(call.args[0][1] == 'api' for call in commands.call_args_list))
        self.assertEqual(result['installedCommit'], OLD)

    def test_failed_or_missing_current_build_preserves_verified_kit(self):
        result, commands = self.refresh([{'object': {'sha': NEW}}, {'workflow_runs': [dict(self.good, conclusion='failure')]}])
        self.assertIn('latest 30', result['state'])
        self.assertEqual(result['installedCommit'], OLD)
        self.assertEqual(commands.call_count, 2)

    def test_force_pushed_behind_or_diverged_head_never_downloads(self):
        for status in ('behind', 'diverged', 'identical'):
            with self.subTest(status=status):
                result, commands = self.refresh([{'object': {'sha': NEW}}, {'workflow_runs': [self.good]},
                                                 {'status': status, 'merge_base_commit': {'sha': OLD}}])
                self.assertIn('not a forward descendant', result['state'])
                self.assertEqual(result['installedCommit'], OLD)
                self.assertEqual(commands.call_count, 3)

    def test_projection_noop_preserves_time_and_holds_edits(self):
        output = self.shared / 'TaskWorkMorning'
        morning.write_projection(output, {'status.json': b'{}'})
        before = {p.name: p.stat().st_mtime_ns for p in output.iterdir()}
        morning.write_projection(output, {'status.json': b'{}'})
        self.assertEqual(before, {p.name: p.stat().st_mtime_ns for p in output.iterdir()})
        (output / 'status.json').write_bytes(b'human note')
        with self.assertRaisesRegex(ValueError, 'Edited'):
            morning.write_projection(output, {'status.json': b'new'})
        self.assertEqual((output / 'status.json').read_bytes(), b'human note')

    def test_unmanaged_or_foreign_projection_is_preserved(self):
        output = self.shared / 'TaskWorkMorning'; output.mkdir()
        (output / 'human.txt').write_text('keep')
        with self.assertRaisesRegex(ValueError, 'Unmanaged'):
            morning.write_projection(output, {'status.json': b'{}'})
        self.assertEqual((output / 'human.txt').read_text(), 'keep')
        with mock.patch.object(morning.os, 'getuid', return_value=os.getuid() + 1):
            with self.assertRaisesRegex(ValueError, 'owned lock'):
                morning.write_projection(output, {'status.json': b'{}'})

    def test_projection_staging_write_failure_keeps_entire_old_projection(self):
        output = self.shared / 'TaskWorkMorning'
        morning.write_projection(output, {'status.json': b'old', 'index.html': b'old html'})
        before = self.contents(output); original = Path.write_bytes
        def failed(path, content):
            if path.name == 'index.html': raise OSError('simulated disk full')
            return original(path, content)
        with mock.patch.object(Path, 'write_bytes', failed):
            with self.assertRaisesRegex(OSError, 'disk full'):
                morning.write_projection(output, {'status.json': b'new', 'index.html': b'new html'})
        self.assertEqual(self.contents(output), before)

    def test_projection_publish_failure_restores_old_and_unsafe_keys_cannot_partially_write(self):
        output = self.shared / 'TaskWorkMorning'
        morning.write_projection(output, {'status.json': b'old'})
        before = self.contents(output); original = Path.rename
        def failed(path, target):
            if path.name.startswith('.TaskWorkMorning-next-') and target == output:
                raise OSError('simulated publish failure')
            return original(path, target)
        with mock.patch.object(Path, 'rename', failed):
            with self.assertRaisesRegex(OSError, 'publish failure'):
                morning.write_projection(output, {'status.json': b'new'})
        self.assertEqual(self.contents(output), before)
        for name in ('..', '../human', 'projection-receipt.json'):
            with self.assertRaises(ValueError):
                morning.write_projection(output, {'status.json': b'new', name: b'invalid'})
        self.assertEqual(self.contents(output), before)

    def test_replaced_projection_retains_previous_generation_and_public_modes(self):
        output = self.shared / 'TaskWorkMorning'
        morning.write_projection(output, {'status.json': b'old', 'retired.txt': b'old owned file'})
        morning.write_projection(output, {'status.json': b'new'})
        self.assertFalse((output / 'retired.txt').exists())
        backups = list(self.shared.glob('TaskWorkMorning.previous-*'))
        self.assertEqual(len(backups), 1)
        self.assertEqual((backups[0] / 'retired.txt').read_bytes(), b'old owned file')
        self.assertEqual(output.stat().st_mode & 0o777, 0o755)
        self.assertTrue(all(p.stat().st_mode & 0o777 == 0o644 for p in output.iterdir()))

    def test_preparation_status_never_asserts_human_readiness(self):
        status = morning.publish_status(self.shared, 'verified', self.proof, {'tasks': []})
        for key in ('recorderExecuted', 'recordingReady', 'practiceReady', 'unaidedTransferEstablished'):
            self.assertIs(status[key], False)
        self.assertEqual(status['mastery'], 'not_established')
        self.assertEqual(json.loads((self.shared / 'TaskWorkMorning/status.json').read_text()), status)

    def installed_metadata(self):
        runtime = self.shared / 'TaskWorkRuntime'
        self.write(runtime / 'cloud-proof.json', self.proof)
        for name in ('TaskWorkCloudSync.py', 'TaskWorkRegistry.py', 'task-registry.json', 'runtime-manifest.json'):
            self.write(runtime / name, '{}' if name.endswith('.json') else '# unexecuted synthetic fixture\n')
        metadata = {path.name: morning.sha(path) for path in runtime.iterdir()}
        receipt = {'verified': True, 'synced': True, 'repository': morning.REPOSITORY,
                   'sourceCommit': OLD, 'runId': '1', 'runtimeMetadataSha256': metadata}
        self.write(runtime / 'cloud-sync-receipt.json', receipt)
        return runtime, receipt

    def test_unhashed_or_changed_helpers_are_never_imported(self):
        runtime, receipt = self.installed_metadata()
        receipt['runtimeMetadataSha256'].pop('TaskWorkCloudSync.py')
        self.write(runtime / 'cloud-sync-receipt.json', receipt)
        with mock.patch.object(morning, 'module', side_effect=AssertionError('unverified code imported')):
            with self.assertRaisesRegex(ValueError, 'helper/dependency'):
                morning.verify_installed(self.shared)
        receipt['runtimeMetadataSha256']['TaskWorkCloudSync.py'] = '0' * 64
        self.write(runtime / 'cloud-sync-receipt.json', receipt)
        with mock.patch.object(morning, 'module', side_effect=AssertionError('changed code imported')):
            with self.assertRaisesRegex(ValueError, 'Changed runtime'):
                morning.verify_installed(self.shared)

    def test_metadata_traversal_and_unhashed_worked_dependencies_hold(self):
        runtime, receipt = self.installed_metadata()
        receipt['runtimeMetadataSha256']['../outside.py'] = '0' * 64
        self.write(runtime / 'cloud-sync-receipt.json', receipt)
        with mock.patch.object(morning, 'module', side_effect=AssertionError('unverified code imported')):
            with self.assertRaisesRegex(ValueError, 'Unsafe evidence'):
                morning.verify_installed(self.shared)
        receipt['runtimeMetadataSha256'].pop('../outside.py')
        self.write(runtime / 'SyncTaskWorkPlans.py', '# missing hash\n')
        self.write(runtime / 'cloud-sync-receipt.json', receipt)
        with mock.patch.object(morning, 'module', side_effect=AssertionError('unverified code imported')):
            with self.assertRaisesRegex(ValueError, 'helper/dependency'):
                morning.verify_installed(self.shared)

    def pair_fixture(self):
        runtime, plans = self.shared / 'TaskWorkRuntime', self.shared / 'TaskWorkPlans'
        self.write(runtime / 'old-runtime.txt', 'old runtime exactly')
        self.write(plans / 'old-plans.txt', 'old plans exactly')
        self.write(self.shared / 'TaskWorkInputs/existing-task/input.txt', 'original input')
        self.write(self.root / 'Recorder-attempt/actual-work.txt', 'preserve human work')
        staging = self.root / 'incoming'
        self.write(staging / 'TaskWorkRuntime/new-runtime.txt', 'new runtime')
        self.write(staging / 'TaskWorkRuntime/task-registry.json', {'tasks': [{'neutral': 'existing-task'}, {'neutral': 'new-task'}]})
        self.write(staging / 'TaskWorkInputs/new-task/input.txt', 'new original input')
        incoming_plans = self.root / 'incoming-plans/TaskWorkPlans'
        self.write(incoming_plans / 'new-plan.txt', 'new prepared plan')
        receipt = {'files': morning.plan_inventory(incoming_plans), 'sourceCommit': NEW, 'runId': '3', 'synced': True}
        receipt['receiptContentSha256'] = morning.plan_receipt_sha(receipt)
        self.write(incoming_plans / 'worked-plans-sync-receipt.json', receipt)
        sync = SimpleNamespace(verify_contract=mock.Mock(), write_sync_receipt=lambda root, value: self.write(root / 'cloud-sync-receipt.json', value))
        worked = SimpleNamespace(verify_tree=mock.Mock(), inventory=lambda root, omit: morning.plan_inventory(root), receipt_sha=morning.plan_receipt_sha)
        verified = {'sourceCommit': NEW, 'runId': '3', 'verified': True, 'synced': False}
        return staging, incoming_plans, sync, worked, verified

    def test_worked_swap_failure_rolls_back_both_prior_kits_and_new_inputs(self):
        staging, incoming, sync, worked, verified = self.pair_fixture()
        before = {name: self.contents(self.shared / name) for name in ('TaskWorkRuntime', 'TaskWorkPlans', 'TaskWorkInputs')}
        original = Path.rename
        def failed(path, target):
            if path == incoming and target == self.shared / 'TaskWorkPlans':
                raise OSError('simulated second-kit install failure')
            return original(path, target)
        with mock.patch.object(morning, 'verify_installed', return_value=(self.proof, self.registry)), mock.patch.object(Path, 'rename', failed):
            with self.assertRaisesRegex(OSError, 'second-kit'):
                morning.install_pair(sync, worked, staging, incoming, self.shared, NEW, '3', OLD, verified)
        self.assertEqual({name: self.contents(self.shared / name) for name in before}, before)
        self.assertTrue(list(self.shared.glob('TaskWorkRuntime.morning-held-*')))
        self.assertTrue(list(self.shared.glob('new-task.morning-held-*')))
        self.assertEqual((self.root / 'Recorder-attempt/actual-work.txt').read_text(), 'preserve human work')
        self.assertFalse((self.shared / '.TaskWorkPlans.sync.lock').exists())

    def test_post_install_verification_failure_restores_both_previous_generations(self):
        staging, incoming, sync, worked, verified = self.pair_fixture()
        before = {name: self.contents(self.shared / name) for name in ('TaskWorkRuntime', 'TaskWorkPlans', 'TaskWorkInputs')}
        with mock.patch.object(morning, 'verify_installed', side_effect=[(self.proof, self.registry), ValueError('new verification failed')]):
            with self.assertRaisesRegex(ValueError, 'verification failed'):
                morning.install_pair(sync, worked, staging, incoming, self.shared, NEW, '3', OLD, verified)
        self.assertEqual({name: self.contents(self.shared / name) for name in before}, before)
        self.assertTrue(list(self.shared.glob('TaskWorkPlans.morning-held-*')))

    def test_successful_pair_preserves_both_backups_and_writes_actual_durable_receipts(self):
        staging, incoming, sync, worked, verified = self.pair_fixture()
        new_proof = dict(self.proof, sourceCommit=NEW, runId='3')
        with mock.patch.object(morning, 'verify_installed', side_effect=[(self.proof, self.registry), (new_proof, self.registry)]):
            self.assertEqual(morning.install_pair(sync, worked, staging, incoming, self.shared, NEW, '3', OLD, verified)[0], new_proof)
        source_receipt = morning.load(self.shared / 'TaskWorkRuntime/cloud-sync-receipt.json')
        plans_receipt = morning.load(self.shared / 'TaskWorkPlans/worked-plans-sync-receipt.json')
        self.assertTrue(source_receipt['synced'])
        self.assertEqual((Path(source_receipt['previousRuntime']) / 'old-runtime.txt').read_text(), 'old runtime exactly')
        self.assertEqual((Path(plans_receipt['previousPlans']) / 'old-plans.txt').read_text(), 'old plans exactly')
        self.assertEqual(plans_receipt['receiptContentSha256'], morning.plan_receipt_sha(plans_receipt))
        self.assertEqual((self.shared / 'TaskWorkInputs/existing-task/input.txt').read_text(), 'original input')

    def test_head_change_during_download_discards_candidate_without_install(self):
        metadata = {name: __import__('hashlib').sha256(b'fixture').hexdigest()
                    for name in ('SyncTaskWorkPlans.py', 'TaskWorkRegistry.py', 'recording_pack.py')}
        def unpack(archive, target):
            for name in metadata:
                self.write(target / 'TaskWorkRuntime' / name, 'fixture')
        source = SimpleNamespace(process=mock.Mock(return_value={'verified': True, 'archiveSha256': 'd' * 64,
                                 'runtimeMetadataSha256': metadata}), unpack_verified=unpack,
                                 verify_checksum=mock.Mock(return_value='d' * 64))
        worked = SimpleNamespace(sync=mock.Mock())
        responses = [{'object': {'sha': NEW}}, {'workflow_runs': [self.good]},
                     {'status': 'ahead', 'merge_base_commit': {'sha': OLD}}, '', '', {'object': {'sha': NEXT}}, self.good]
        with mock.patch.object(morning, 'verify_installed', return_value=(self.proof, {'tasks': []})), \
             mock.patch.object(morning, 'command', side_effect=[json.dumps(x) for x in responses]) as commands, \
             mock.patch.object(morning, 'module', side_effect=[source, worked]), \
             mock.patch.object(morning.Path, 'home', return_value=self.root), \
             mock.patch.object(morning, 'install_pair', side_effect=AssertionError('stale head installed')):
            result = morning.refresh(self.shared)
        self.assertIn('changed during verification', result['state'])
        self.assertEqual(result['installedCommit'], OLD)
        self.assertFalse(source.process.call_args.kwargs.get('sync', False))
        self.assertEqual(sum(c.args[0][1:3] == ['run', 'download'] for c in commands.call_args_list), 2)
        self.assertFalse(any('dispatch' in c.args[0] or 'rerun' in c.args[0] for c in commands.call_args_list))

    def test_changed_incoming_helper_is_blocked_before_import_or_install(self):
        def unpack(archive, target):
            for name in ('SyncTaskWorkPlans.py', 'TaskWorkRegistry.py', 'recording_pack.py'):
                self.write(target / 'TaskWorkRuntime' / name, 'unverified replacement')
        source = SimpleNamespace(process=mock.Mock(return_value={'verified': True, 'archiveSha256': 'd' * 64,
                                 'runtimeMetadataSha256': {name: '0' * 64 for name in ('SyncTaskWorkPlans.py', 'TaskWorkRegistry.py', 'recording_pack.py')}}),
                                 unpack_verified=unpack, verify_checksum=mock.Mock(return_value='d' * 64))
        responses = [{'object': {'sha': NEW}}, {'workflow_runs': [self.good]},
                     {'status': 'ahead', 'merge_base_commit': {'sha': OLD}}, '', '']
        with mock.patch.object(morning, 'verify_installed', return_value=(self.proof, {'tasks': []})), \
             mock.patch.object(morning, 'command', side_effect=[json.dumps(x) for x in responses]), \
             mock.patch.object(morning, 'module', return_value=source) as imported, \
             mock.patch.object(morning.Path, 'home', return_value=self.root), \
             mock.patch.object(morning, 'install_pair', side_effect=AssertionError('unverified kit installed')):
            with self.assertRaisesRegex(ValueError, 'Changed runtime metadata'):
                morning.refresh(self.shared)
        self.assertEqual(imported.call_count, 1)

    def test_locks_refuse_linked_or_already_running_operations(self):
        path = self.shared / 'lock'; path.symlink_to(self.root / 'human-lock')
        with self.assertRaisesRegex(ValueError, 'linked path'):
            with morning.owned_lock(path): pass
        path.unlink()
        with morning.owned_lock(path):
            with self.assertRaises(BlockingIOError):
                with morning.owned_lock(path): pass


if __name__ == '__main__':
    unittest.main()
