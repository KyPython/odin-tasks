#!/usr/bin/env python3
"""Offline learning metadata/feedback validation; no tracker or learner writes."""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
OFFICIAL_HOSTS = {'docs.aws.amazon.com', 'pythoninstitute.org', 'istqb.org', 'cpre.ireb.org', 'training.linuxfoundation.org'}
OBJECTIVES = {
    'pcap': {'PCAP-31-03 1.5', 'PCAP-31-03 2.1', 'PCAP-31-03 2.2'},
    'ctfl': {'FL-1.4.4', 'FL-2.2.3', 'FL-4.2.1', 'FL-4.2.2', 'FL-4.2.4'},
    'ctai': {'AI-3.3.1'}, 'saa': set(), 'dva': set(), 'cnpe': set(), 'cpre': set(),
}
REQUIRED_COMMON = {'contract-traceability', 'causal-explanation', 'test-sensitivity', 'controlled-edit',
                   'deterministic-verification', 'tool-file-state', 'evidence-reporting', 'professional-judgment', 'capture-provenance'}
FORBIDDEN_FEEDBACK = {'mastered', 'certificationPassed', 'officialGrade', 'transferCredit', 'Transfer Synced', 'approval', 'humanGate'}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data.encode('utf-8') if isinstance(data, str) else data).hexdigest()


def plain(path):
    require(not path.is_symlink() and path.is_file(), f'Missing plain metadata: {path}')
    return path.read_bytes()


def layout(root, plans=None):
    """Use the existing repository or installed kit, never a preparation home."""
    root = Path(root)
    installed = root.name == 'process'
    runtime = root.parent if installed else root/'runtime'
    return {
        'installed': installed,
        'runtime': runtime,
        'packs': runtime/'packs' if installed else root/'packs',
        'publisher': runtime/'recording_pack.py' if installed else root/'scripts/recording_pack.py',
        'plans': Path(plans) if plans is not None else runtime.parent/'TaskWorkPlans' if installed else root/'walkthroughs',
    }


def publisher(root):
    module_path = layout(root)['publisher']
    plain(module_path)
    spec = importlib.util.spec_from_file_location('LearningPack', module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_map(data, root=ROOT, *, plans=None):
    require(data.get('version') == 1, 'Unsupported learning map version')
    root = Path(root)
    paths = layout(root, plans)
    pack = publisher(root)
    registered, projects = pack.registry_context(paths['runtime']/'task-registry.json', paths['runtime']/'runtime-manifest.json')
    require(set(data.get('tasks', {})) == set(registered), 'Learning map must cover exactly the registered real tasks')
    credentials = data.get('credentials', {})
    active = [k for k,v in credentials.items() if v.get('roadmapStatus') == 'Active now']
    require(active == [data.get('certificationAuthority', {}).get('activeCredentialId')], 'Preserve the single documented active credential')
    for key, credential in credentials.items():
        require(key in OBJECTIVES and re.fullmatch(r'[a-f0-9]{32}', credential.get('notionPageId', '')), 'Credential needs an existing native record')
        require(credential.get('roadmapStatus') in {'Active now', 'Protected external validation'} and type(credential.get('priority')) is int and credential['priority'] > 0, 'Unsupported human certification status/priority')
        require(credential.get('readinessChangeAllowed') is False, 'A preparation map cannot upgrade readiness')
        require(credential.get('officialSources'), 'Credential source missing')
        for source in credential['officialSources']:
            require(urlparse(source.get('url', '')).hostname in OFFICIAL_HOSTS, 'Exact objectives need official primary sources')
            require(set(source.get('objectiveIds', [])) <= OBJECTIVES[key], 'Unsupported official objective identifier')
    authority = data.get('capabilityAuthority', {})
    allowed = authority.get('ids', [])
    require(allowed and len(set(allowed)) == len(allowed), 'Capability authority must contain unique existing IDs')
    require(authority.get('cloudDefaultCommit') and authority.get('cloudMatrixBlobSha') and authority.get('localCommit') and authority.get('localSha256'), 'Distinguish actual cloud/local matrix identities')
    cloud_authority = json.loads(plain(root/authority.get('cloudAuthorityFile','')))
    for key, source in (('cloudDefaultCommit','commit'),('cloudMatrixBlobSha','blobSha'),('cloudMatrixSha256','sha256'),('cloudMatrixVersion','version')):
        require(authority.get(key) == cloud_authority.get(source), 'Capability cloud snapshot identity drift')
    require(set(allowed) == set(cloud_authority.get('capabilityIds',[])) & set(authority.get('localObservedIds',[])), 'Capability IDs must be the sourced cloud/local intersection')
    inventory = data.get('certificationInventory', [])
    require(inventory and len({v.get('notionPageId') for v in inventory}) == len(inventory), 'Native certification inventory is missing or duplicated')
    require(len([v for v in inventory if v.get('roadmapStatus') == 'Active now']) == 1, 'Preserve actual sole active certification in inventory')
    for credential in credentials.values():
        found = next((v for v in inventory if v.get('notionPageId') == credential['notionPageId']), {})
        require(found.get('credential') == credential['name'] and found.get('roadmapStatus') == credential['roadmapStatus'] and found.get('priority') == credential['priority'], 'Mapped credential disagrees with native inventory')
    skills = data.get('skills', {})
    require(REQUIRED_COMMON <= set(skills), 'Required human practice mechanisms are missing')
    for key, skill in skills.items():
        require(re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', key) and all(isinstance(skill.get(k),str) and skill[k].strip() for k in ('name','what','why','how','result','evidenceRequired')), 'Concrete skill WHAT/WHY/HOW/RESULT required')
        require(skill.get('assessmentStatus') == 'unassessed', 'Prepared skills are not assessed human skills')
    for neutral, task in registered.items():
        mapped = data['tasks'][neutral]
        route = pack.validate_route(plain(paths['packs']/'routes'/f'{neutral}.md').decode())
        count = len(re.findall(r'^\*\*Step (\d+)\.\*\*', route, re.M))
        require(count > 1, 'Primary route is missing')
        for key, expected in (('taskId',task['id']),('notionPageId',task['notionPageId']),('sourceRepo',task['sourceRepo']),('sourceCommit',task['commit']),('goalSha256',task['goalSha256']),('routeSha256',sha(route)),('workflowLane',task.get('workflowLane','odin'))):
            require(mapped.get(key) == expected, f'Immutable learning identity drift: {neutral}/{key}')
        goal = plain(paths['runtime']/task['goalFile'])
        require(sha(goal) == task['goalSha256'] and goal.decode().rstrip('\n') == pack.goal_text(task), 'Actual Goal bytes differ from registered identity')
        require(projects[neutral]['commit'] == task['commit'], 'Source manifest pin drift')
        page = pack.snapshot(json.loads(plain(paths['packs']/'pages'/f'{neutral}.json')))
        pack.verify_page(task, page)
        require(mapped.get('humanTransferTest') == page['properties'].get('Human Transfer Test') and mapped.get('humanTransferTestSha256') == sha(mapped['humanTransferTest']), 'Preserve the exact human transfer criterion')
        existing = [v.strip() for v in page['properties'].get('Bootcamp Capability IDs','').split(',') if v.strip()]
        require(mapped.get('capabilityIds') == existing and set(existing) <= set(allowed), 'Preserve existing supported capability mapping')
        level = mapped.get('currentNotionEvidenceLevel')
        require(level == page['properties'].get('Certification Evidence Level') and level in {'Credential/domain-level','Objective-level','No supported mapping'}, 'Do not promote existing Notion evidence labels')
        if level == 'No supported mapping':
            require(not mapped.get('certificationMappings') and mapped.get('unsupportedMappingReason'), 'Preserve an honest unsupported certification mapping')
        require(mapped.get('humanEvidence') == {'guided':'unassessed','unaided':'unassessed','mastery':'unassessed','recordedAttemptAvailable':False,'readinessIncrease':0}, 'No actual human assessment is established by prepared reference proof')
        required = mapped.get('requiredSkills', [])
        ids = [entry.get('skillId') for entry in required]
        require(len(set(ids)) == len(ids) and REQUIRED_COMMON <= set(ids), 'A world omits or repeats required human skills')
        for entry in required:
            require(entry.get('skillId') in skills, 'World references unknown skill')
            require(entry.get('routeSteps') and all(type(n) is int and 1 <= n <= count for n in entry['routeSteps']), 'Skill evidence must reference actual existing route steps')
            require(all(isinstance(entry.get('narration', {}).get(k),str) and entry['narration'][k].strip() for k in ('what','why','how','result')), 'Each skill needs prepared WHAT/WHY/HOW/RESULT narration')
        require(all(mapped.get('narration', {}).get(k) for k in ('what','why','how','result')), 'World narration is incomplete')
        for mapping in mapped.get('certificationMappings', []):
            key = mapping.get('credentialId')
            require(key in credentials and mapping.get('evidenceLevel') in {'Credential/domain-level','Objective-level'}, 'No unsupported credential/objective-level claim')
            if mapping['evidenceLevel'] == 'Objective-level':
                require(level == 'Objective-level' and mapping.get('officialObjectiveReferences'), 'Do not promote domain-level metadata or invent objective-level support')
            require(mapping.get('scope') and mapping.get('notCovered'), 'State partial coverage and the remaining gaps')
            for ref in mapping.get('officialObjectiveReferences', []):
                require(ref.get('id') in OBJECTIVES[key] and ref.get('sourceUrl') in {s['url'] for s in credentials[key]['officialSources']} and 'not a completed human objective' in ref.get('purpose',''), 'Exact objective study reference is unsupported or overclaimed')
        require(mapped.get('remediation', {}).get('existingTask') == neutral and mapped['remediation'].get('mode') == 'proposal-only', 'Remediation must reuse an existing world without auto-credit')
        reference_root = paths['plans']/neutral
        proof_name = 'cloud-verification.json' if paths['installed'] else 'verification.json'
        reference = json.loads(plain(reference_root/proof_name))
        require(reference.get('status') == 'PASS' and reference.get('sourceCommit') == task['commit'] and reference.get('goalSha256') == task['goalSha256'] and reference.get('recorderExecuted') is False and reference.get('recordingWorkspaceModified') is False, 'Prepared technical proof identity is invalid')
        require(mapped.get('preparedReference', {}).get('technicalChecks') == len(reference.get('checks',[])) > 0, 'Technical reference check count mismatch')
        if paths['installed']:
            identity = json.loads(plain(reference_root/'identity.json'))
            expected = {'neutral':neutral, 'taskId':task['id'], 'sourceRepo':task['sourceRepo'],
                        'sourceCommit':task['commit'], 'goalSha256':task['goalSha256'],
                        'routeSha256':sha(route), 'workflowLane':task.get('workflowLane','odin')}
            require(all(identity.get(k) == v for k,v in expected.items()), 'Installed worked reference identity drift')
            require(plain(reference_root/'recording-sequence.md') == route.encode()
                    and pack.route_from_body(plain(reference_root/'walkthrough.md').decode()) == route,
                    'Installed worked reference route drift')
            require(reference.get('sourceInputsUnchanged') is True
                    and reference.get('solutionPatchSha256') == sha(plain(reference_root/'solution.patch')),
                    'Installed worked reference patch/proof drift')
    require(data.get('feedbackContract', {}).get('destinationWritesAllowed') is False, 'Learning feedback cannot write mastery destinations')
    require(data.get('futureTaskAdmission', {}).get('unsupportedMapping') and data['futureTaskAdmission'].get('heldTasks'), 'Future mapping must admit honest unsupported/HOLD outcomes')
    return {'status':'PASS','tasks':len(registered),'skills':len(skills),'credentials':len(credentials),'credentialInventory':len(inventory),'humanMasteryAssessed':False,'remoteWritesPerformed':False}


def validate_feedback(data, neutral, feedback, *, recording_method='guided'):
    """Validate proposals only. This cannot grant official or unaided credit."""
    require(neutral in data['tasks'] and isinstance(feedback,list), 'Feedback needs one registered real task')
    supported = {s['skillId'] for s in data['tasks'][neutral]['requiredSkills']}
    for row in feedback:
        require(isinstance(row,dict) and set(row) == {'skillId','observationKind','finding','evidence','remediationTask'}, 'Only proposal fields are allowed; no mastery/approval/score writes')
        require(row['skillId'] in supported and row['remediationTask'] in data['tasks'], 'Feedback/remediation must reference existing mapped skills/worlds')
        require(row['skillId'] in {s['skillId'] for s in data['tasks'][row['remediationTask']]['requiredSkills']}, 'Remediation world does not practice this skill')
        require(row['observationKind'] in {'guided','unaided'} and row['finding'] in {'needs-practice','unassessed','observed'} and isinstance(row['evidence'],list), 'Unsupported evidence/finding kind')
        if row['finding'] == 'unassessed':
            require(not row['evidence'], 'Unassessed is not a fabricated observation')
            continue
        require(row['evidence'], 'Observed skill/gap needs actual recording evidence')
        require(row['observationKind'] != 'unaided' or recording_method == 'unaided', 'Guided recording cannot create unaided evidence')
        for evidence in row['evidence']:
            require(isinstance(evidence,dict) and set(evidence) == {'timestampStart','timestampEnd','artifact','observation'}, 'Timestamped video/audio observation fields required')
            start, end = evidence['timestampStart'], evidence['timestampEnd']
            require(type(start) in (int,float) and type(end) in (int,float) and 0 <= start <= end and end < float('inf'), 'Recording timestamps must be finite ordered seconds')
            require(isinstance(evidence['artifact'],str) and evidence['artifact'].strip() and isinstance(evidence['observation'],str) and evidence['observation'].strip(), 'Real artifact and actual visible/audible observation required')
            require(Path(evidence['artifact'].split('#',1)[0]).suffix.lower() in {'.mp4','.mov','.mkv','.m4v','.webm','.mp3','.m4a','.wav','.aac','.flac'}, 'Human observation must cite recording media, not code/test logs')
    return {'status':'PASS','proposals':len(feedback),'humanDecisionRequired':True,'masteryCreditGranted':False,'destinationWritesPerformed':False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--map', type=Path, default=ROOT/'learning/skill-map.json')
    parser.add_argument('--plans', type=Path, help='Explicit worked-reference directory; installed default is the sibling TaskWorkPlans kit')
    parser.add_argument('--feedback', type=Path)
    parser.add_argument('--task')
    parser.add_argument('--recording-method',choices=('guided','unaided'),default='guided')
    args = parser.parse_args()
    data = json.loads(plain(args.map))
    result = validate_map(data, plans=args.plans)
    if args.feedback:
        result['feedback'] = validate_feedback(data,args.task,json.loads(plain(args.feedback)),recording_method=args.recording_method)
    print(json.dumps(result))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, KeyError, TypeError, OSError) as exc:
        print(json.dumps({'status':'HOLD','error':str(exc)}))
        raise SystemExit(2)
