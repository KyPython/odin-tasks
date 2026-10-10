import importlib.util
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('worked_sync', Path(__file__).resolve().parents[1] / 'scripts/sync_worked_plans.py')
s = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s)
REPO = Path(__file__).resolve().parents[1]
COMMIT = 'a' * 40
RUN = '12345'
NEUTRAL = 'quote-calculator'


class WorkedReferencePreservation(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.runtime = self.root / 'runtime'
        self.runtime.mkdir()
        self.commit, self.run_id = COMMIT, RUN
        (self.runtime / 'cloud-proof.json').write_text(json.dumps({'sourceCommit': COMMIT, 'runId': RUN}))
        registry = json.loads((REPO / 'runtime/task-registry.json').read_text())
        self.task = next(task for task in registry['tasks'] if task['neutral'] == NEUTRAL)
        registry['tasks'] = [self.task]
        (self.runtime / 'task-registry.json').write_text(json.dumps(registry))
        manifest = json.loads((REPO / 'runtime/runtime-manifest.json').read_text())
        manifest['projects'] = [project for project in manifest['projects'] if project['neutral'] == NEUTRAL]
        (self.runtime / 'runtime-manifest.json').write_text(json.dumps(manifest))
        goal = self.runtime / self.task['goalFile']
        goal.parent.mkdir()
        goal.write_bytes((REPO / 'runtime' / self.task['goalFile']).read_bytes())
        self.payload = self.root / 'payload'
        self.payload.mkdir()
        self.folder = self.payload / NEUTRAL
        self.folder.mkdir()
        route = (REPO / 'packs/routes' / (NEUTRAL + '.md')).read_bytes()
        (self.folder / 'recording-sequence.md').write_bytes(route)
        (self.folder / 'walkthrough.md').write_bytes((REPO / 'walkthroughs' / NEUTRAL / 'walkthrough.md').read_bytes())
        (self.folder / 'solution.patch').write_bytes((REPO / 'walkthroughs' / NEUTRAL / 'solution.patch').read_bytes())
        identity = {'neutral': self.task['neutral'], 'taskId': self.task['id'], 'sourceRepo': self.task['sourceRepo'],
                    'sourceCommit': self.task['commit'], 'goalSha256': self.task['goalSha256'],
                    'routeSha256': s.sha(self.folder / 'recording-sequence.md'), 'rehearsalExitCode': 0,
                    'recorderExecuted': False, 'recordingWorkspaceModified': False, 'paidWalkthroughPermissionVerified': False}
        (self.folder / 'identity.json').write_text(json.dumps(identity))
        observed = json.loads((REPO / 'walkthroughs' / NEUTRAL / 'verification.json').read_text())
        observed['solutionPatchSha256'] = s.sha(self.folder / 'solution.patch')
        (self.folder / 'cloud-verification.json').write_text(json.dumps(observed))
        proof = {'version': 1, 'repository': s.REPOSITORY, 'sourceCommit': COMMIT, 'runId': RUN,
                 'runUrl': f'https://github.com/{s.REPOSITORY}/actions/runs/{RUN}', 'plans': [NEUTRAL],
                 'starterCloudProofSha256': s.sha(self.runtime / 'cloud-proof.json'),
                 'starterInputsUnchanged': True, 'workedRepairsVerifiedInDisposableCopies': True,
                 'recorderExecuted': False, 'recordingWorkspaceModified': False, 'paidWalkthroughPermissionVerified': False}
        (self.payload / 'worked-plans-proof.json').write_text(json.dumps(proof))
        self.dest = self.root / 'TaskWorkPlans'
        self.archive = self.root / 'plans.tar.gz'
        self.checksum = self.root / 'plans.sha256'
        self.package()

    def package(self):
        manifest = self.payload / 'worked-plans-manifest.json'
        if manifest.exists():
            manifest.unlink()
        for path in self.payload.rglob('*'):
            path.chmod(0o755 if path.is_dir() else 0o644)
        manifest.write_text(json.dumps({'version': 1, 'files': s.inventory(self.payload)}))
        with tarfile.open(self.archive, 'w:gz') as archive:
            archive.add(self.payload, arcname='.')
        self.checksum.write_text(s.sha(self.archive) + '  plans.tar.gz\n')

    def install(self):
        return s.sync(self.archive, self.checksum, self.commit, self.run_id, self.runtime, self.dest, True)

    def next_revision(self):
        self.commit, self.run_id = 'd' * 40, '67890'
        (self.runtime / 'cloud-proof.json').write_text(json.dumps({'sourceCommit': self.commit, 'runId': self.run_id}))
        proof_path = self.payload / 'worked-plans-proof.json'
        proof = json.loads(proof_path.read_text())
        proof.update(sourceCommit=self.commit, runId=self.run_id,
                     runUrl=f'https://github.com/{s.REPOSITORY}/actions/runs/{self.run_id}',
                     starterCloudProofSha256=s.sha(self.runtime / 'cloud-proof.json'))
        proof_path.write_text(json.dumps(proof))

    def assert_valid_payload_inventory(self):
        actual = s.inventory(self.payload)
        actual.pop('worked-plans-manifest.json')
        self.assertEqual(actual, json.loads((self.payload / 'worked-plans-manifest.json').read_text())['files'])

    def test_verified_install_and_retry_reuse_exact_reference(self):
        first = self.install()
        before = {str(p): p.stat().st_mtime_ns for p in self.dest.rglob('*')}
        again = self.install()
        self.assertTrue(first['synced'])
        self.assertEqual(again['operation'], 'noop')
        self.assertEqual(before, {str(p): p.stat().st_mtime_ns for p in self.dest.rglob('*')})
        self.assertEqual(list(self.root.glob('TaskWorkPlans.previous-*')), [])

    def test_corrupt_archive_or_mismatched_starter_is_refused_before_install(self):
        self.archive.write_bytes(self.archive.read_bytes() + b'changed')
        with self.assertRaises(ValueError):
            self.install()
        self.assertFalse(self.dest.exists())
        self.package()
        (self.runtime / 'cloud-proof.json').write_text(json.dumps({'sourceCommit': 'd' * 40, 'runId': RUN}))
        with self.assertRaises(ValueError):
            self.install()
        self.assertFalse(self.dest.exists())

    def test_edited_plan_or_receipt_is_preserved(self):
        self.install()
        path = self.dest / NEUTRAL / 'walkthrough.md'
        path.write_text('My actual notes must survive.\n')
        with self.assertRaises(ValueError):
            self.install()
        self.assertEqual(path.read_text(), 'My actual notes must survive.\n')
        shutil_spec = s.inventory(self.payload)[NEUTRAL + '/walkthrough.md']
        path.write_text((self.folder / 'walkthrough.md').read_text())
        self.assertEqual(s.sha(path), shutil_spec['sha256'])
        receipt = self.dest / 'worked-plans-sync-receipt.json'
        value = json.loads(receipt.read_text())
        value['paidWalkthroughPermissionVerified'] = True
        receipt.write_text(json.dumps(value))
        with self.assertRaises(ValueError):
            self.install()
        self.assertTrue(json.loads(receipt.read_text())['paidWalkthroughPermissionVerified'])

    def test_goal_conflict_cannot_be_hidden_by_a_valid_inventory(self):
        path = self.folder / 'identity.json'
        value = json.loads(path.read_text())
        value['goalSha256'] = 'f' * 64
        path.write_text(json.dumps(value))
        self.package()
        with self.assertRaises(ValueError):
            self.install()
        self.assertFalse(self.dest.exists())

    def test_modified_actual_goal_cannot_reuse_unchanged_registry_and_proof(self):
        registry_before = (self.runtime / 'task-registry.json').read_bytes()
        identity_before = (self.folder / 'identity.json').read_bytes()
        observed_before = (self.folder / 'cloud-verification.json').read_bytes()
        goal = self.runtime / self.task['goalFile']
        goal.write_bytes(goal.read_bytes() + b'Changed human Goal.\n')
        self.assert_valid_payload_inventory()
        with self.assertRaisesRegex(ValueError, 'Exact task Goal input differs'):
            self.install()
        self.assertFalse(self.dest.exists())
        self.assertEqual((self.runtime / 'task-registry.json').read_bytes(), registry_before)
        self.assertEqual((self.folder / 'identity.json').read_bytes(), identity_before)
        self.assertEqual((self.folder / 'cloud-verification.json').read_bytes(), observed_before)

    def test_altered_patch_with_valid_new_inventory_preserves_existing_reference(self):
        self.install()
        before = s.inventory(self.dest)
        patch = self.folder / 'solution.patch'
        patch.write_bytes(patch.read_bytes() + b'\nChanged packaged repair.\n')
        self.next_revision()
        self.package()
        self.assert_valid_payload_inventory()
        with self.assertRaisesRegex(ValueError, 'Packaged solution differs'):
            self.install()
        self.assertEqual(s.inventory(self.dest), before)
        self.assertEqual(list(self.root.glob('TaskWorkPlans.previous-*')), [])

    def test_altered_walkthrough_route_with_valid_inventory_is_refused(self):
        walkthrough = self.folder / 'walkthrough.md'
        original = walkthrough.read_text()
        phrase = 'This prepared plan uses a test-first check of the quote calculation.'
        self.assertEqual(original.count(phrase), 1)
        walkthrough.write_text(original.replace(phrase, 'This changed route bypasses the verified plan.'))
        self.package()
        self.assert_valid_payload_inventory()
        with self.assertRaisesRegex(ValueError, 'Worked narration/code sequence differs'):
            self.install()
        self.assertFalse(self.dest.exists())

    def test_altered_packaged_route_cannot_reuse_identity_digest(self):
        route = self.folder / 'recording-sequence.md'
        route.write_text(route.read_text().replace('Keep the opener under 20 seconds.', 'Skip the verified opening limit.'))
        self.package()
        self.assert_valid_payload_inventory()
        with self.assertRaisesRegex(ValueError, 'Worked narration/code sequence differs'):
            self.install()
        self.assertFalse(self.dest.exists())

    def test_valid_new_revision_archives_prior_owned_output_without_changes(self):
        self.install()
        before = {p.relative_to(self.dest).as_posix(): p.read_bytes() for p in self.dest.rglob('*') if p.is_file()}
        walkthrough = self.folder / 'walkthrough.md'
        walkthrough.write_text(walkthrough.read_text() + '\nFixture administrative revision outside the recording route.\n')
        self.next_revision()
        self.package()
        result = self.install()
        previous = Path(result['previousPlans'])
        self.assertTrue(previous.is_dir())
        self.assertEqual({p.relative_to(previous).as_posix(): p.read_bytes() for p in previous.rglob('*') if p.is_file()}, before)
        self.assertEqual(result['sourceCommit'], self.commit)
        self.assertEqual((self.dest / NEUTRAL / 'walkthrough.md').read_bytes(), walkthrough.read_bytes())
        self.assertEqual(self.install()['operation'], 'noop')

    def test_missing_registered_plan_is_refused_before_install(self):
        registry = json.loads((REPO / 'runtime/task-registry.json').read_text())
        other = next(task for task in registry['tasks'] if task['neutral'] == 'batch-command')
        registry['tasks'] = [self.task, other]
        (self.runtime / 'task-registry.json').write_text(json.dumps(registry))
        manifest = json.loads((REPO / 'runtime/runtime-manifest.json').read_text())
        manifest['projects'] = [project for project in manifest['projects']
                                if project['neutral'] in {NEUTRAL, other['neutral']}]
        (self.runtime / 'runtime-manifest.json').write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, 'Every registered task requires'):
            self.install()
        self.assertFalse(self.dest.exists())

    def test_hold_rehearsal_cannot_claim_readiness_with_valid_inventory(self):
        path = self.folder / 'cloud-verification.json'
        actual = json.loads(path.read_text())
        actual['status'] = 'HOLD'
        path.write_text(json.dumps(actual))
        self.package()
        self.assert_valid_payload_inventory()
        with self.assertRaisesRegex(ValueError, 'Missing actual bound rehearsal evidence'):
            self.install()
        self.assertFalse(self.dest.exists())

    def test_traversal_and_symlink_archive_members_are_refused(self):
        for name, kind in [('../escape', tarfile.REGTYPE), ('link', tarfile.SYMTYPE)]:
            with self.subTest(name=name):
                with tarfile.open(self.archive, 'w:gz') as archive:
                    item = tarfile.TarInfo(name)
                    item.type = kind
                    item.mode = 0o644
                    item.size = 1 if kind == tarfile.REGTYPE else 0
                    item.linkname = '/outside' if kind == tarfile.SYMTYPE else ''
                    archive.addfile(item, io.BytesIO(b'x') if item.size else None)
                self.checksum.write_text(s.sha(self.archive) + '\n')
                with self.assertRaises(ValueError):
                    self.install()
                self.assertFalse(self.dest.exists())
                self.assertFalse((self.root.parent / 'escape').exists())


if __name__ == '__main__':
    unittest.main()
