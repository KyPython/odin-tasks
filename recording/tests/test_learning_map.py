import copy
import importlib.util
import json
import math
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('learning_checker',ROOT/'scripts/check_learning_map.py')
learning = importlib.util.module_from_spec(spec)
spec.loader.exec_module(learning)


class LearningMapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = json.loads((ROOT/'learning/skill-map.json').read_text())
        cls.registered = learning.publisher(ROOT).registry_context(
            ROOT/'runtime/task-registry.json', ROOT/'runtime/runtime-manifest.json')[0]

    def setUp(self):
        self.data = copy.deepcopy(self.original)

    def installed_fixture(self, parent):
        """Match build_preparation's layout using only real registered metadata."""
        runtime = Path(parent)/'TaskWorkRuntime'
        process = runtime/'process'
        plans = Path(parent)/'TaskWorkPlans'
        shutil.copytree(ROOT/'runtime', runtime)
        shutil.copytree(ROOT/'packs', runtime/'packs')
        shutil.copy2(ROOT/'scripts/recording_pack.py', runtime/'recording_pack.py')
        (process/'scripts').mkdir(parents=True)
        (process/'learning').mkdir()
        (process/'cloud').mkdir()
        shutil.copy2(ROOT/'scripts/check_learning_map.py', process/'scripts/check_learning_map.py')
        shutil.copy2(ROOT/'learning/skill-map.json', process/'learning/skill-map.json')
        shutil.copy2(ROOT/'cloud/capability-authority.json', process/'cloud/capability-authority.json')
        registered, _ = learning.publisher(ROOT).registry_context(ROOT/'runtime/task-registry.json', ROOT/'runtime/runtime-manifest.json')
        for neutral, task in registered.items():
            folder = plans/neutral
            folder.mkdir(parents=True)
            for name in ('walkthrough.md', 'solution.patch'):
                shutil.copy2(ROOT/'walkthroughs'/neutral/name, folder/name)
            # The build's actual offline proof contract is used unchanged.
            shutil.copy2(ROOT/'walkthroughs'/neutral/'verification.json', folder/'cloud-verification.json')
            route = (ROOT/'packs/routes'/f'{neutral}.md').read_bytes()
            (folder/'recording-sequence.md').write_bytes(route)
            identity = {'neutral':neutral, 'taskId':task['id'], 'sourceRepo':task['sourceRepo'],
                        'sourceCommit':task['commit'], 'goalSha256':task['goalSha256'],
                        'routeSha256':learning.sha(route), 'workflowLane':task.get('workflowLane','odin')}
            (folder/'identity.json').write_text(json.dumps(identity))
        return process, plans

    def installed_cli(self, process, *arguments):
        return subprocess.run([sys.executable, '-I', str(process/'scripts/check_learning_map.py'), *arguments],
                              cwd=process.parent.parent, capture_output=True, text=True)

    def test_installed_isolated_cli_uses_public_kit_layout(self):
        with tempfile.TemporaryDirectory() as parent:
            process, _ = self.installed_fixture(parent)
            result = self.installed_cli(process)
            self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
            proof = json.loads(result.stdout)
            self.assertEqual((proof['tasks'], proof['skills']),
                             (len(self.registered), len(self.original['skills'])))
            self.assertFalse(proof['humanMasteryAssessed'])

    def test_installed_authority_is_required_and_remains_source_bound(self):
        with tempfile.TemporaryDirectory() as parent:
            process, _ = self.installed_fixture(parent)
            path = process/'cloud/capability-authority.json'
            authority = json.loads(path.read_text())
            path.unlink()
            result = self.installed_cli(process)
            self.assertEqual(result.returncode, 2, result.stdout+result.stderr)
            self.assertIn('Missing plain metadata', json.loads(result.stdout)['error'])
            authority['commit'] = self.data['capabilityAuthority']['localCommit']
            path.write_text(json.dumps(authority))
            result = self.installed_cli(process)
            self.assertEqual(result.returncode, 2)
            self.assertIn('cloud snapshot identity', json.loads(result.stdout)['error'])

    def test_installed_missing_references_hold_and_explicit_directory_works(self):
        with tempfile.TemporaryDirectory() as parent:
            process, plans = self.installed_fixture(parent)
            moved = plans.with_name('VerifiedReferences')
            plans.rename(moved)
            result = self.installed_cli(process)
            self.assertEqual(result.returncode, 2)
            result = self.installed_cli(process, '--plans', str(moved))
            self.assertEqual(result.returncode, 0, result.stdout+result.stderr)

    def test_installed_reference_patch_and_route_cannot_drift(self):
        with tempfile.TemporaryDirectory() as parent:
            process, plans = self.installed_fixture(parent)
            path = plans/'batch-command/solution.patch'
            original = path.read_bytes()
            path.write_bytes(original+b'Altered patch\n')
            result = self.installed_cli(process)
            self.assertEqual(result.returncode, 2)
            self.assertIn('patch/proof drift', json.loads(result.stdout)['error'])
            path.write_bytes(original)
            path = plans/'batch-command/walkthrough.md'
            path.write_text(path.read_text().replace('**Step 1.**','**Step 1.** Changed narration:',1))
            result = self.installed_cli(process)
            self.assertEqual(result.returncode, 2)
            self.assertIn('route drift', json.loads(result.stdout)['error'])

    def test_all_real_tasks_and_native_certification_inventory(self):
        result = learning.validate_map(self.data)
        self.assertEqual((result['tasks'],result['skills'],result['credentialInventory']),
                         (len(self.registered), len(self.data['skills']), len(self.data['certificationInventory'])))
        self.assertFalse(result['humanMasteryAssessed'])
        self.assertEqual(self.data['credentials']['saa']['roadmapStatus'],'Active now')
        self.assertEqual(self.data['tasks']['threshold-evaluation']['humanEvidence']['unaided'],'unassessed')

    def test_reviewed_unassessed_skill_growth_has_no_fixed_count(self):
        self.data['skills']['additional-fixture-skill'] = copy.deepcopy(
            self.data['skills']['contract-traceability'])
        result = learning.validate_map(self.data)
        self.assertEqual(result['skills'], len(self.original['skills']) + 1)
        self.assertFalse(result['humanMasteryAssessed'])

    def test_missing_existing_or_new_registered_world_is_not_silently_omitted(self):
        missing = next(iter(self.data['tasks']))
        del self.data['tasks'][missing]
        with self.assertRaisesRegex(ValueError, 'exactly the registered real tasks'):
            learning.validate_map(self.data)
        self.data = copy.deepcopy(self.original)
        original_publisher = learning.publisher
        def expanded_registry(root):
            pack = original_publisher(root)
            context = pack.registry_context
            def registry_context(*args):
                tasks, projects = context(*args)
                tasks['new-registration-fixture'] = copy.deepcopy(next(iter(tasks.values())))
                return tasks, projects
            pack.registry_context = registry_context
            return pack
        with patch.object(learning, 'publisher', side_effect=expanded_registry):
            with self.assertRaisesRegex(ValueError, 'exactly the registered real tasks'):
                learning.validate_map(self.data)

    def test_changed_source_identity_is_rejected(self):
        self.data['tasks']['threshold-evaluation']['sourceCommit'] = '0'*40
        with self.assertRaisesRegex(ValueError,'Immutable learning identity'):
            learning.validate_map(self.data)

    def test_changed_route_binding_is_rejected(self):
        self.data['tasks']['batch-command']['routeSha256'] = '0'*64
        with self.assertRaisesRegex(ValueError,'Immutable learning identity'):
            learning.validate_map(self.data)

    def test_actual_goal_bytes_cannot_drift_behind_unchanged_map(self):
        original_plain = learning.plain
        target = ROOT/'runtime/goals/threshold-evaluation.txt'
        def changed_goal(path):
            data = original_plain(path)
            return data+b'Altered Goal\n' if path == target else data
        with patch.object(learning,'plain',side_effect=changed_goal), self.assertRaisesRegex(ValueError,'Actual Goal bytes'):
            learning.validate_map(self.data)

    def test_preserve_existing_capability_ids(self):
        self.data['tasks']['callback-state']['capabilityIds'].append('made-up-capability')
        with self.assertRaisesRegex(ValueError,'existing supported capability'):
            learning.validate_map(self.data)

    def test_cloud_and_local_authorities_cannot_be_conflated(self):
        self.data['capabilityAuthority']['cloudDefaultCommit'] = self.data['capabilityAuthority']['localCommit']
        with self.assertRaisesRegex(ValueError,'cloud snapshot identity'):
            learning.validate_map(self.data)

    def test_unsourced_capability_cannot_enter_intersection(self):
        self.data['capabilityAuthority']['ids'].append('invented-id')
        with self.assertRaisesRegex(ValueError,'sourced cloud/local intersection'):
            learning.validate_map(self.data)

    def test_invented_official_objective_is_rejected(self):
        mapping=self.data['tasks']['threshold-evaluation']['certificationMappings'][1]
        mapping['officialObjectiveReferences'][0]['id']='AI-99.99.99'
        with self.assertRaisesRegex(ValueError,'objective study reference'):
            learning.validate_map(self.data)

    def test_prepared_partial_mapping_cannot_promote_native_level(self):
        self.data['tasks']['quote-calculator']['currentNotionEvidenceLevel']='Objective-level'
        with self.assertRaisesRegex(ValueError,'promote existing Notion'):
            learning.validate_map(self.data)

    def test_future_unsupported_mapping_can_remain_honestly_empty(self):
        self.data['tasks']['quote-calculator']['currentNotionEvidenceLevel']='No supported mapping'
        self.data['tasks']['quote-calculator']['certificationMappings']=[]
        self.data['tasks']['quote-calculator']['unsupportedMappingReason']='The fresh native row explicitly has no supported credential mapping.'
        original_publisher=learning.publisher
        def native_empty_mapping(root):
            pack=original_publisher(root)
            original_snapshot=pack.snapshot
            def snapshot(value):
                page=original_snapshot(value)
                if page['pageId']==self.data['tasks']['quote-calculator']['notionPageId']:
                    page['properties']['Certification Evidence Level']='No supported mapping'
                return page
            pack.snapshot=snapshot
            return pack
        with patch.object(learning,'publisher',side_effect=native_empty_mapping):
            learning.validate_map(self.data)

    def test_technical_proof_is_not_human_mastery(self):
        self.data['tasks']['dispatch-board']['humanEvidence']['mastery']='passed'
        with self.assertRaisesRegex(ValueError,'human assessment'):
            learning.validate_map(self.data)

    def test_narration_and_real_route_steps_are_required(self):
        self.data['tasks']['harbor-workspace']['requiredSkills'][0]['narration']['why']=''
        with self.assertRaisesRegex(ValueError,'narration'):
            learning.validate_map(self.data)
        self.data=copy.deepcopy(self.original)
        self.data['tasks']['harbor-workspace']['requiredSkills'][0]['routeSteps']=[99]
        with self.assertRaisesRegex(ValueError,'actual existing route steps'):
            learning.validate_map(self.data)

    def feedback(self, **changes):
        value={'skillId':'finally-propagation','observationKind':'guided','finding':'needs-practice','evidence':[{'timestampStart':60,'timestampEnd':70,'artifact':'media/attempt.mp4','observation':'The speaker reports that cleanup means the call returns normally, despite the visible propagated exception.'}],'remediationTask':'batch-command'}
        value.update(changes)
        return [value]

    def test_timestamped_guided_observation_is_only_a_proposal(self):
        result=learning.validate_feedback(self.data,'batch-command',self.feedback())
        self.assertTrue(result['humanDecisionRequired'])
        self.assertFalse(result['masteryCreditGranted'])
        self.assertFalse(result['destinationWritesPerformed'])

    def test_observed_gap_needs_actual_media_and_finite_timestamps(self):
        for evidence in ([],[{'timestampStart':1,'timestampEnd':math.inf,'artifact':'attempt.mp4','observation':'Observed behavior'}],[{'timestampStart':1,'timestampEnd':2,'artifact':'tests.log','observation':'Green tests'}]):
            with self.subTest(evidence=evidence),self.assertRaises(ValueError):
                learning.validate_feedback(self.data,'batch-command',self.feedback(evidence=evidence))

    def test_guided_recording_cannot_create_unaided_evidence(self):
        with self.assertRaisesRegex(ValueError,'Guided recording'):
            learning.validate_feedback(self.data,'batch-command',self.feedback(observationKind='unaided'))

    def test_mastery_fields_unknown_skills_or_new_worlds_are_rejected(self):
        cases=(self.feedback(mastered=True),self.feedback(skillId='invented'),self.feedback(remediationTask='new-unbuilt-world'))
        for value in cases:
            with self.subTest(value=value),self.assertRaises(ValueError):
                learning.validate_feedback(self.data,'batch-command',value)

    def test_unassessed_requires_no_fabricated_observation(self):
        learning.validate_feedback(self.data,'batch-command',self.feedback(finding='unassessed',evidence=[]))
        with self.assertRaisesRegex(ValueError,'fabricated observation'):
            learning.validate_feedback(self.data,'batch-command',self.feedback(finding='unassessed'))

    def test_held_candidate_cannot_become_source_bound_world(self):
        self.data['tasks']['unapproved-held-world']=copy.deepcopy(self.data['tasks']['threshold-evaluation'])
        with self.assertRaisesRegex(ValueError,'exactly the registered real tasks'):
            learning.validate_map(self.data)


if __name__ == '__main__':
    unittest.main()
