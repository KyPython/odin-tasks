'use strict';

// Offline checks against the captured deployed modules; this script makes no API calls.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const root = path.resolve(__dirname, '..');
const snapshot = JSON.parse(fs.readFileSync(path.join(root, 'cloud/make-processes.json'), 'utf8'));
const receipt = JSON.parse(fs.readFileSync(path.join(root, 'cloud/make-processes-receipt.json'), 'utf8'));
const ids = [6550857, 6547847, 6550231, 6548371, 6550627];
const TASK_SOURCE = '74aac26d-fcbb-45df-b996-561f76b9cec6';
const CERT_SOURCE = 'd0ea98d6-79eb-4f67-b39b-8ce57d282a2e';
let checks = 0;
function check(name, fn) { try { fn(); checks++; } catch (error) { error.message = name + ': ' + error.message; throw error; } }
function scenario(id) { const result = snapshot.scenarios.find(s => s.scenario.id === id); assert.ok(result, 'Missing scenario ' + id); return result; }
function moduleConfig(id, moduleId) { const result = scenario(id).modules.find(m => m.id === moduleId); assert.ok(result, 'Missing module ' + id + '/' + moduleId); return result; }
function mapper(id, moduleId) { return moduleConfig(id, moduleId).config.mapper; }
function code(id, moduleId) { const source = mapper(id, moduleId).codeEditorJavascript; assert.equal(typeof source, 'string'); return source; }
function execute(id, moduleId, input) { return new Function('input', 'require', code(id, moduleId))(input, require); }
function digest(value) { return crypto.createHash('sha256').update(value).digest('hex'); }
function sourcePrefix(filename) {
  const source = fs.readFileSync(path.join(root, 'cloud', filename), 'utf8');
  return ['operator-pack.js', 'kiro-handoff.js'].includes(filename)
    ? source.replace(/^module\.exports = .*;\s*$/m, '').trimEnd()
    : source.trimEnd();
}
function strings(value) {
  if (typeof value === 'string') return [value];
  if (!value || typeof value !== 'object') return [];
  return Object.values(value).flatMap(strings);
}
function ancestors(s, id, seen = new Set()) {
  assert.ok(!seen.has(id), 'Cycle in module order');
  const m = s.modules.find(x => x.id === id); assert.ok(m, 'Missing dependency ' + id);
  const previous = m.follows ?? m.parent?.moduleId;
  if (previous === undefined) return new Set();
  const found = ancestors(s, previous, new Set([...seen, id])); found.add(previous); return found;
}
function checkReferences(s) {
  for (const m of s.modules) {
    const upstream = ancestors(s, m.id);
    for (const value of strings([m.config.mapper, m.filter, m.parent?.conditions])) {
      for (const expression of value.matchAll(/\{\{([\s\S]*?)\}\}/g)) {
        for (const ref of expression[1].matchAll(/(?:^|[^\w])`?(\d+)`?(?=\.|\s*$)/g)) {
          assert.ok(upstream.has(Number(ref[1])), 'Module ' + m.id + ' references missing or later module ' + ref[1]);
        }
      }
    }
  }
}
check('export identity and redaction', () => {
  assert.equal(snapshot.schemaVersion, 1);
  assert.deepEqual(snapshot.scenarios.map(s => s.scenario.id).sort(), ids.slice().sort());
  assert.equal(new Set(snapshot.scenarios.map(s => s.scenario.id)).size, 5);
  assert.equal(receipt.snapshotSha256, digest(fs.readFileSync(path.join(root, 'cloud/make-processes.json'))));
  assert.ok(!JSON.stringify(snapshot).includes('__IMTCONN__'));
  for (const s of snapshot.scenarios) { assert.equal(s.scenario.status, 'active'); assert.equal(s.modules.length, new Set(s.modules.map(m => m.id)).size); }
});
for (const id of ids) {
  check('upstream module references ' + id, () => checkReferences(scenario(id)));
  check('API serialization and code parsing ' + id, () => {
    for (const m of scenario(id).modules) {
      const map = m.config.mapper;
      if (m.module === 'code:ExecuteCode') new Function('input', 'require', map.codeEditorJavascript);
      if (/:(makeApiCall|makeRestApiCall)$/.test(m.module)) {
        assert.equal(typeof map.url, 'string'); assert.equal(typeof map.method, 'string');
        if (map.method !== 'GET') assert.equal(typeof map.body, 'string', 'Object HTTP body in module ' + m.id);
        for (const match of map.url.matchAll(/\/v1\/data_sources\/([^/]+)\/query/g)) {
          assert.ok([TASK_SOURCE, CERT_SOURCE, '78284b86-3652-4bb9-87b0-29bc03f6655b'].includes(match[1]), 'Unknown or malformed Notion authority');
        }
        for (const h of map.headers || []) assert.ok(!/authorization|api[-_]?key|token/i.test(h.key));
      }
    }
  });
}
const bindings = [
  [6550857, 7, 'bootcamp-builder.js'], [6550857, 3, 'bootcamp-builder.js'],
  [6550857, 9, 'bootcamp-builder.js'], [6550857, 11, 'bootcamp-builder.js'],
  [6550857, 3, 'kiro-proof.js'], [6550857, 19, 'kiro-proof.js'],
  [6547847, 2, 'kiro-handoff.js'], [6547847, 5, 'kiro-handoff.js'],
  [6550231, 2, 'operator-pack.js'], [6550231, 11, 'operator-pack.js'], [6550231, 12, 'operator-pack.js'],
  [6548371, 2, 'operator-pack.js'], [6548371, 13, 'operator-pack.js'], [6548371, 14, 'operator-pack.js'],
  [6550627, 5, 'idea-miner.js'], [6550627, 11, 'capability-router.js'], [6548371, 7, 'pr-evidence.js'],
  ...[5,15,17,19,20,11,12].map(id=>[6550231,id,'private-source-bridge.js'])
];
for (const [id, moduleId, filename] of bindings) check('deployed source ' + id + '/' + moduleId, () => {
  const prefix = sourcePrefix(filename), deployed = code(id, moduleId);
  if (['idea-miner.js', 'manifest-evidence.js', 'pr-evidence.js'].includes(filename)) assert.equal(deployed.trimEnd(), prefix, 'Source drift');
  else if (['private-source-bridge.js', 'kiro-proof.js'].includes(filename)) assert.ok(deployed.startsWith(prefix+'\n') || deployed.includes('\n'+prefix+'\n'), 'Embedded verified source drift');
  else assert.ok(deployed.startsWith(prefix + '\n'), 'Source prefix drift in ' + filename);
  const recorded = receipt.sourceBindings.find(b => b.scenarioId === id && b.moduleId === moduleId && b.source === 'cloud/'+filename);
  assert.ok(recorded?.matches); assert.equal(recorded.sourcePrefixSha256, digest(prefix));
  assert.equal(recorded.rawFileSha256, digest(fs.readFileSync(path.join(root, 'cloud', filename))));
  assert.equal(recorded.deployedCodeSha256, digest(deployed));
});
check('complete deployed source binding inventory', () => {
  assert.equal(receipt.sourceBindings.length, bindings.length);
  assert.equal(new Set(receipt.sourceBindings.map(b => [b.scenarioId, b.moduleId, b.source].join('/'))).size, bindings.length);
});
check('all-state bounded issue inventory', () => {
  for (const [id, modules] of [[6550857, [8, 12, 13]], [6547847, [4, 10, 11]]]) {
    modules.forEach((moduleId, index) => {
      const m = mapper(id, moduleId), qs = Object.fromEntries(m.qs.map(q => [q.key, q.value]));
      assert.equal(m.method, 'GET'); assert.equal(m.url, '/repos/KyPython/ai-governance/issues');
      assert.deepEqual(qs, { state: 'all', per_page: '100', page: String(index + 1) });
    });
  }
  assert.equal(JSON.parse(mapper(6550857, 1).body).page_size, 100);
  assert.equal(JSON.parse(mapper(6550857, 1).body).filter, undefined, 'Cross-state fingerprint inventory must be unfiltered');
  assert.deepEqual(JSON.parse(mapper(6547847, 1).body), {page_size: 100}, 'Kiro must read both lanes before selecting');
  assert.equal(JSON.parse(mapper(6550627, 3).body).page_size, 100);
  assert.equal(receipt.limits.githubIssueInventory, 300); assert.equal(receipt.limits.notionQuery, 100);
});
const ROW = '3f28621e-0a7a-8141-8d6e-dfb9a5b43054';
const rt = text => [{ plain_text: text, text: { content: text } }];
function page(changes = {}) {
  const rich = text => ({ rich_text: rt(text) }), select = name => ({ select: { name } });
  return { id: ROW, url: 'https://app.notion.com/' + ROW.replace(/-/g, ''), properties: {
    Task: { title: rt('Cursor contract repair') }, Stage: select('Candidate'), Lane: select('Dual-candidate'),
    'Fit Gate': select('PASS'), 'Bootcamp Status': select('World queued'), 'Operator Pack Status': select('PENDING'),
    'Odin Goal': rich('Diagnose and repair the documented deterministic API contract.'),
    'Source Evidence': rich('Synthetic starter with a bounded contract and ordinary-path tests.'),
    'Spec Path': rich('specs/odin-bootcamp/cursor-pagination-aggregator-contract-repair'),
    'Spec PR': { url: 'https://github.com/KyPython/ai-governance/pull/201' },
    'Variation Axis': rich('Fixture retry contract'), 'Professional Judgment': rich('Choose and explain the bounded repair tradeoff.'),
    'Duplicate Fingerprint': rich('cursor|pagination|contract'), 'Approved Goal': rich(''), 'Approval ID': rich(''),
    'Human Transfer Test': rich('Diagnose and explain the decisive contract independently.'),
    'Certification Alignment': rich('Supported domain fixture'), 'Certification Objective Coverage': rich('Exact supported domain wording'),
    'Certification Evidence Level': select('Credential/domain-level'), 'Bootcamp Capability IDs': rich('invariant-driven-testing'),
    'Build Issue': { url: null }, ...changes
  } };
}
const query = results => ({ results, has_more: false, next_cursor: null });
let world;
// These dummy private captures/receipts are fixtures only, never real Kiro PASS evidence.
function evidenceFile(filePath, raw) {
  const bytes = Buffer.from(raw, 'utf8');
  return {type: 'file', encoding: 'base64', path: filePath, size: bytes.length,
    sha: crypto.createHash('sha1').update('blob ' + bytes.length + '\0').update(bytes).digest('hex'), content: bytes.toString('base64')};
}
function specEvidence(selected, changeReceipt = () => {}, changeCapture = value => value) {
  const executionId = 'sess_11111111-1111-4111-8111-111111111111';
  const capturePath = 'cloud/kiro-receipts/' + executionId + '.capture.txt';
  const captureRaw = changeCapture('SYNTHETIC TEST CAPTURE ONLY: completed fixture specification review.\n');
  const requirements = '# Synthetic requirements\n\n' + selected.goal + '\n\nTask Factory row: https://app.notion.com/p/' + selected.row_id.replace(/-/g, '') + '\n';
  const design = '# Synthetic design\n\nBounded local fixture contract.\n';
  const tasks = '# Synthetic tasks\n\nCoder and distinct reviewer check the starter contract.\n';
  const documents = { [selected.spec_path + '/requirements.md']: requirements, [selected.spec_path + '/design.md']: design, [selected.spec_path + '/tasks.md']: tasks };
  const receiptFixture = {version: 1, engine: 'kiro', status: 'PASS', executionId, inventorySha256: 'a'.repeat(64), specCommit: 'b'.repeat(40),
    bindings: {[selected.row_id]: {rowId: selected.row_id, goalSha256: digest(selected.goal + '\n'), specPath: selected.spec_path, specPr: selected.spec_pr}},
    paths: Object.fromEntries(Object.entries(documents).map(([name, raw]) => [name, {status: 'PASS', sha256: digest(raw)}])),
    executionEvidence: {source: 'captured-kiro-cli', executionTarget: 'local', capturePath, captureSha256: digest(captureRaw)}};
  changeReceipt(receiptFixture);
  const receiptRaw = JSON.stringify(receiptFixture) + '\n';
  const pr = {number: 201, html_url: selected.spec_pr, merged: true, merged_at: '2026-10-08T00:00:00Z', merged_by: {login: 'KyPython'},
    merge_commit_sha: 'c'.repeat(40), head: {sha: 'b'.repeat(40)}, base: {ref: 'main', repo: {full_name: 'KyPython/ai-governance'}},
    body: 'KIRO_SPEC_EXECUTION_ID:' + executionId + '\nKIRO_RECEIPT_COMMIT:' + 'd'.repeat(40) + '\nKIRO_RECEIPT_SHA256:' + digest(receiptRaw) + '\n'};
  return {row: selected, spec_pr: pr, spec_files: Object.entries(documents).map(([name, raw]) => ({path: name, type: 'file', sha: evidenceFile(name, raw).sha})),
    requirements, design, tasks, receipt: evidenceFile('cloud/kiro-receipts/' + executionId + '.json', receiptRaw), capture: evidenceFile(capturePath, captureRaw)};
}
check('deployed builder eligibility and incomplete Notion hold', () => {
  world = execute(6550857, 7, { body: query([page()]) }).rows[0]; assert.ok(world);
  for (const [field, value] of [['Stage', 'Odin approved'], ['Stage', 'Rejected'], ['Lane', 'Odin monetization'], ['Fit Gate', 'HOLD']]) {
    assert.equal(execute(6550857, 7, { body: query([page({ [field]: { select: { name: value } } })]) }).count, 0);
  }
  assert.throws(() => execute(6550857, 7, { body: { ...query([page()]), has_more: true } }), /blocked|Incomplete/);
  assert.equal(execute(6550857, 7, {body: query([page({'Spec PR': {url: null}})])}).count, 0, 'No coding handoff before a real spec PR');
  const request = execute(6550857, 3, specEvidence(world));
  assert.equal(request.spec_proof.verified, true); assert.equal(request.spec_proof.executionTarget, 'local');
  assert.equal(request.spec_proof.specCommit, 'b'.repeat(40)); assert.equal(request.spec_proof.mergeCommit, 'c'.repeat(40));
  const body = JSON.parse(request.payload).body;
  for (const text of ['Diagnose and explain the decisive contract independently.', 'Supported domain fixture', 'Exact supported domain wording', 'invariant-driven-testing']) assert.ok(body.includes(text), 'Lost source mapping or human-transfer metadata');
  assert.ok(body.includes('do not establish mastery or certification readiness'));
});
const issue = { number: 58, state: 'closed', html_url: 'https://github.com/KyPython/ai-governance/issues/58', body: '<!-- ODIN_BOOTCAMP_ROW_ID:' + ROW + ' -->' };
check('deployed recovery uses GET and inventory saturation holds', () => {
  const plan = execute(6550857, 9, { row: world, page1: [issue], page2: [], page3: [] });
  assert.equal(plan.method, 'GET'); assert.equal(plan.issue_number, 58); assert.equal(plan.payload, '');
  assert.throws(() => execute(6550857, 9, { row: world, page1: [], page2: [], page3: Array(100).fill(issue) }), /blocked|Incomplete/);
  assert.equal(mapper(6550857, 4).method, '{{9.result.method}}'); assert.equal(mapper(6550857, 4).body, '{{9.result.payload}}');
});
check('deployed handoff retry skips comments and preserves human fields', () => {
  const result = execute(6550857, 11, { row: world, issue: { ...issue, state: 'open' }, comments: [{ body: '@codex existing handoff' }] });
  assert.equal(result.method, 'GET'); assert.equal(result.action, 'skip'); assert.equal(result.payload, '');
  assert.deepEqual(Object.keys(JSON.parse(result.writeback).properties).sort(), ['Bootcamp Status', 'Build Issue', 'Last Updated']);
  assert.throws(() => execute(6550857, 11, { row: world, issue, comments: Array(100).fill({ body: 'old comment' }) }), /blocked|Incomplete/);
  assert.equal(mapper(6550857, 5).method, '{{11.result.method}}'); assert.equal(mapper(6550857, 6).body, '{{11.result.writeback}}');
});
check('deployed Kiro separate approval lanes and exact Goal ownership', () => {
  const candidate = page({'Spec PR': {url: null}});
  const approved = page({ 'Spec PR': {url: null}, Stage: { select: { name: 'Odin approved' } }, Lane: { select: { name: 'Odin monetization' } },
    'Approval ID': { rich_text: rt('Human-authorized fixture') }, 'Approved Goal': { rich_text: rt(page().properties['Odin Goal'].rich_text[0].plain_text) } });
  const selected = execute(6547847, 2, { body: query([approved, candidate]) }).rows;
  assert.equal(selected.length, 2);
  assert.equal(selected[0].workflow_lane, 'odin'); assert.equal(selected[0].writeback_stage, 'Kiro spec requested');
  assert.equal(selected[1].workflow_lane, 'bootcamp'); assert.equal(selected[1].writeback_stage, 'Candidate');
  assert.equal(execute(6547847, 2, { body: query([page()]) }).rows.length, 0, 'Existing spec cannot create another handoff');
  const alreadyBuilding = structuredClone(approved); alreadyBuilding.properties['Build Issue'] = {url: 'https://github.com/KyPython/ai-governance/issues/58'};
  assert.equal(execute(6547847, 2, {body: query([alreadyBuilding])}).rows.length, 0, 'Approved Odin Build Issue also suppresses a duplicate spec handoff');
  approved.properties['Approved Goal'].rich_text = rt('Different goal');
  assert.equal(execute(6547847, 2, { body: query([approved]) }).rows.length, 0);
  for (const changes of [{'Fit Gate': {select: {name: 'HOLD'}}}, {Stage: {select: {name: 'Rejected'}}}, {'Approval ID': {rich_text: rt('not empty')}},
    {'Source Evidence': {rich_text: []}}, {'Starter Repository': {url: 'https://github.com/KyPython/existing-source'}}, {'Starter Commit': {rich_text: rt('f'.repeat(40))}}]) {
    assert.equal(execute(6547847, 2, {body: query([page({'Spec PR': {url: null}, ...changes})])}).rows.length, 0);
  }
  assert.throws(() => execute(6547847, 2, {body: {...query([candidate]), has_more: true}}), /Incomplete/);
  const handoff = execute(6547847, 5, {...selected[1], page1: [], page2: [], page3: []});
  const body = JSON.parse(handoff.payload).body;
  for (const field of ['source_evidence', 'variation_axis', 'human_transfer_test', 'professional_judgment', 'goal']) assert.ok(body.includes(selected[1][field]), 'Lost exact Kiro contract field ' + field);
  for (const marker of ['ODIN_BOOTCAMP_SPEC_ROW_ID:' + ROW, 'captured', 'KIRO_RECEIPT_SHA256', 'Ky merges']) assert.ok(body.includes(marker));
  const recovered = execute(6547847, 5, {...selected[1], page1: [{number: 200, html_url: 'https://github.com/KyPython/ai-governance/issues/200', body}], page2: [], page3: []});
  assert.equal(recovered.existing, true); assert.equal(recovered.existing_url, 'https://github.com/KyPython/ai-governance/issues/200');
  for (const moduleId of [8, 9]) assert.ok(mapper(6547847, moduleId).body.includes('{{3.writeback_stage}}'), 'Bootcamp Stage must stay unchanged');
});
check('builder requires captured authenticated Kiro proof before any issue create', () => {
  const input = specEvidence(world), before = JSON.stringify(input);
  assert.equal(execute(6550857, 19, {spec_pr: input.spec_pr}).path, input.receipt.path);
  execute(6550857, 3, input); assert.equal(JSON.stringify(input), before, 'Proof verification mutates its contract');
  for (const mutate of [i => delete i.receipt, i => delete i.capture, i => i.spec_pr.merged = false, i => i.spec_pr.merged_by.login = 'AI-worker',
    i => i.spec_pr.base.ref = 'not-main', i => i.spec_pr.head.sha = 'e'.repeat(40), i => i.requirements += '\nUnreviewed edit',
    i => i.design = '', i => i.spec_files.pop(), i => i.spec_pr.body += '\nKIRO_SPEC_EXECUTION_ID:sess_11111111-1111-4111-8111-111111111111']) {
    const changed = structuredClone(input); mutate(changed);
    assert.throws(() => execute(6550857, 3, changed), /HOLD|blocked/);
  }
});
check('builder decoded private bytes validate encoding size UTF-8 and Git blob', () => {
  for (const mutate of [i => i.receipt.encoding = 'utf8', i => i.receipt.path = 'arbitrary/receipt.json', i => i.receipt.content = '@@@',
    i => i.receipt.size++, i => i.receipt.sha = 'e'.repeat(40), i => i.capture.size = 1000001,
    i => {const bytes = Buffer.from([0xff]); i.capture.size = 1; i.capture.content = bytes.toString('base64'); i.capture.sha = crypto.createHash('sha1').update('blob 1\0').update(bytes).digest('hex');}]) {
    const changed = specEvidence(world); mutate(changed);
    assert.throws(() => execute(6550857, 3, changed), /HOLD|blocked/);
  }
});
check('builder proof denies invented PASS goal hashes and blank CLI output', () => {
  for (const changeReceipt of [r => r.engine = 'codex', r => r.status = 'RUNNING', r => r.bindings[ROW].goalSha256 = digest(world.goal),
    r => r.bindings[ROW].specPr = 'https://github.com/KyPython/ai-governance/pull/202', r => r.executionEvidence.source = 'self-claimed-session',
    r => r.executionEvidence.executionTarget = 'invented', r => r.executionEvidence.captureSha256 = 'f'.repeat(64), r => r.specCommit = 'f'.repeat(40)]) {
    assert.throws(() => execute(6550857, 3, specEvidence(world, changeReceipt)), /HOLD|blocked/);
  }
  assert.throws(() => execute(6550857, 3, specEvidence(world, () => {}, () => ' \n\t')), /captured CLI/);
});
check('deployed Kiro-first GET chain and full immutable evidence inputs', () => {
  assert.deepEqual(scenario(6550857).modules.map(m => m.id), [1,7,2,14,15,16,17,18,19,20,21,3,8,12,13,9,4,10,11,5,6]);
  assert.equal(mapper(6550857, 14).url, '/repos/KyPython/ai-governance/pulls/{{2.spec_pr_number}}');
  for (const [moduleId, suffix] of [[15, ''], [16, '/requirements.md'], [17, '/design.md'], [18, '/tasks.md']]) {
    assert.equal(mapper(6550857, moduleId).url, '/repos/KyPython/ai-governance/contents/{{2.spec_path}}' + suffix);
    assert.deepEqual(mapper(6550857, moduleId).qs, [{key: 'ref', value: '{{14.body.merge_commit_sha}}'}]);
    assert.equal(mapper(6550857, moduleId).method, 'GET');
  }
  for (const [moduleId, name] of [[20, 'path'], [21, 'capturePath']]) {
    assert.equal(mapper(6550857, moduleId).url, '/repos/KyPython/odin-recording-preparation/contents/{{19.result.' + name + '}}');
    assert.deepEqual(mapper(6550857, moduleId).qs, [{key: 'ref', value: '{{19.result.receiptCommit}}'}]);
    assert.equal(mapper(6550857, moduleId).method, 'GET');
  }
  assert.deepEqual(mapper(6550857, 3).input, [{name: 'row', value: '{{`2`}}'},
    ...[['spec_pr',14], ['spec_files',15], ['requirements',16], ['design',17], ['tasks',18], ['receipt',20], ['capture',21]].map(([name,id]) => ({name,value:'{{'+id+'.body}}'}))]);
  assert.deepEqual(mapper(6550857, 19).input, [{name: 'spec_pr', value: '{{14.body}}'}]);
  assert.ok(ancestors(scenario(6550857), 4).has(21), 'Private proof must precede issue create');
});
check('manifest and PR ownership are mutually exclusive', () => {
  const ready = page({ 'Bootcamp Status': { select: { name: 'World building' } }, 'Build Issue': { url: issue.html_url } });
  assert.equal(execute(6550231, 2, { body: query([ready]) }).count, 1); assert.equal(execute(6548371, 2, { body: query([ready]) }).count, 0);
  ready.properties['Build PR'] = { url: 'https://github.com/KyPython/ai-governance/pull/200' };
  assert.equal(execute(6550231, 2, { body: query([ready]) }).count, 0); assert.equal(execute(6548371, 2, { body: query([ready]) }).count, 1);
  ready.properties['Fit Gate'].select.name = 'HOLD';
  assert.equal(execute(6548371, 2, { body: query([ready]) }).count, 0);
});
check('deployed reviewers hold incomplete and truncated source evidence', () => {
  const pointer={row_id:ROW,source_repo:'https://github.com/KyPython/fixture',commit:'a'.repeat(40)};
  const inputRow={row_id:ROW,goal:'Exact native Goal',lane:'Bootcamp',comments:[]};
  const comment=value=>({id:1,user:{login:'KyPython'},body:'ODIN_STARTER_MANIFEST\n'+JSON.stringify(value)});
  assert.equal(execute(6550231,5,{...inputRow,comments:[comment(pointer)]}).found,true);
  assert.throws(()=>execute(6550231,5,{...inputRow,comments:Array(100).fill({body:'old comment'})}),/incomplete/);
  assert.throws(()=>execute(6550231,5,{...inputRow,comments:[comment({...pointer,files:[{content_b64:'YWJj'}]})]}),/public queue/);
  assert.throws(()=>execute(6550231,5,{...inputRow,starter_repository:pointer.source_repo,starter_commit:''}),/partial/);
  const input = { pr: { merged: true, merged_at: '2026-10-07T00:00:00Z', head: { sha: 'a'.repeat(40) }, changed_files: 1 }, files: [{ filename: 'starter.py', status: 'added', patch: '+print("starter")' }] };
  assert.equal(execute(6548371, 7, input).changed_files, 1);
  assert.throws(() => execute(6548371, 7, { ...input, pr: { ...input.pr, merged: false } }), /Merged/);
  assert.throws(() => execute(6548371, 7, { ...input, pr: { ...input.pr, changed_files: 2 } }), /Incomplete/);
  assert.throws(() => execute(6548371, 7, { ...input, files: [{ ...input.files[0], patch: '' }] }), /Missing/);
  assert.throws(() => execute(6548371, 7, { ...input, files: [{ ...input.files[0], patch: 'x'.repeat(42001) }] }), /cap/);
});
check('reference check rejects missing modules and reversed order', () => {
  const missing = structuredClone(scenario(6550857)); missing.modules.find(m => m.id === 6).config.mapper.body = '{{999.body}}';
  assert.throws(() => checkReferences(missing), /missing or later/);
  const reversed = structuredClone(scenario(6550231)); reversed.modules.find(m => m.id === 12).follows = 11;
  assert.throws(() => checkReferences(reversed), /missing or later/);
});
for (const [id, planner, content, writer, props] of [[6550231, 11, 9, 12, 8], [6548371, 13, 11, 14, 10]]) {
  check('content is saved before gate properties ' + id, () => {
    assert.ok(ancestors(scenario(id), writer).has(content)); assert.ok(ancestors(scenario(id), props).has(writer));
    assert.equal(mapper(id, content).method, '{{' + planner + '.result.content_method}}');
    assert.equal(mapper(id, writer).input.find(i => i.name === 'saved').value, '{{' + content + '.body}}');
    assert.equal(mapper(id, props).body, '{{' + writer + '.result.property_body}}');
    const input = { row_id: ROW, blocks: query([]), raw: { verdict: 'PASS', operator_pack: '### Recording sequence — follow this order\n1. Open the workspace.' },
      source_ref: 'fixture source', starter_repository: 'https://github.com/KyPython/fixture', starter_commit: 'a'.repeat(40) };
    if(id===6550231){input.native_page=page({'Bootcamp Status':{select:{name:'World building'}}});const goal=input.native_page.properties['Odin Goal'].rich_text[0].plain_text;input.proof={verified:true,private_bytes_only:true,found:true,audit_only:false,row_id:ROW,goal,goal_sha256:digest(goal+'\n'),lane:'Bootcamp',source_repo:input.starter_repository,commit:input.starter_commit};}
    const first = execute(id, planner, input); assert.equal(first.content_method, 'PATCH');
    const block = { id: 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', ...JSON.parse(first.content_body).children[0] };
    const retry = execute(id, planner, { ...input, blocks: query([block]) }); assert.equal(retry.content_method, 'GET'); assert.equal(retry.content_body, '');
    assert.throws(() => execute(id, writer, { ...first, saved: { id: block.id } }), /ownership|saved|revision|Saved/i);
    const write = JSON.parse(execute(id, writer, { ...first, proof:input.proof,native_page:input.native_page,saved: { results: [block] }, source_ref: input.source_ref }).property_body).properties;
    for (const human of ['Local Starter Gate', 'Pre-Record Gate', 'Recording QA Gate', 'Submission Gate', 'Workflow Checklist Gate', 'Approved Goal', 'Approval ID', 'Approved Pay', 'Insightful Hours', 'Reviewer Status', 'Stage', 'Lane', 'Bootcamp Status']) assert.equal(write[human], undefined);
  });
}
check('miner uses verified authority and live property schema', () => {
  assert.equal(mapper(6550627, 1).url, '/v1/data_sources/' + CERT_SOURCE + '/query');
  assert.ok(mapper(6550627, 4).input.includes('{{1.body}}'));
  for (const name of ['Certification Objective Coverage', 'Certification Evidence Level', 'Bootcamp Capability IDs', 'Human Transfer Test', 'Transfer Synced']) assert.ok(snapshot.notionSchemas.taskFactory.properties[name]);
  const candidate = { task: 'Fixture world', goal: 'Unaided repair under a synthetic contract', variation_axis: 'fixture mechanism', duplicate_fingerprint: 'fixture|world',
    human_transfer_test: 'Diagnose, implement, verify and explain unaided.', target_minutes: 30, bootcamp_capability_ids: ['invariant-driven-testing', 'made-up-capability'], certification_evidence_level: 'Credential/domain-level' };
  const out = execute(6550627, 5, { raw: { candidates: [candidate, { ...candidate, task: 'Another title' }] }, factory: query([]), capability_ids_json: JSON.stringify(require('../cloud/capability-authority.json').capabilityIds) });
  assert.equal(out.rows.length, 1); const body = JSON.parse(out.rows[0].create_body), p = body.properties;
  assert.equal(body.parent.data_source_id, TASK_SOURCE); assert.deepEqual(p['Approved Goal'].rich_text, []); assert.deepEqual(p['Approval ID'].rich_text, []);
  for (const name of ['Environment Review Gate', 'No-Solution-Leak Gate', 'Local Starter Gate', 'Pre-Record Gate', 'Recording QA Gate', 'Submission Gate', 'Transfer Synced']) assert.equal(p[name].checkbox, false);
  assert.equal(p['Bootcamp Capability IDs'].rich_text[0].text.content, 'invariant-driven-testing');
  assert.throws(() => execute(6550627, 5, { raw: { candidates: [candidate] }, factory: { ...query([]), has_more: true }, capability_ids_json: JSON.stringify(require('../cloud/capability-authority.json').capabilityIds) }), /Incomplete/);
});
check('private-source bridge API and fresh native write guards',()=>{
 const s=scenario(6550231);
 assert.deepEqual(s.modules.map(m=>m.id),[1,2,3,4,5,13,14,15,16,17,18,19,20,6,10,21,11,9,22,12,8]);
 for(const[id,url]of [[13,'{{5.result.repo_url}}'],[14,'{{5.result.commit_url}}'],[16,'{{15.result.tree_url}}'],[18,'/graphql'],[21,'/v1/pages/{{3.row_id}}'],[22,'/v1/pages/{{3.row_id}}']])assert.equal(mapper(6550231,id).url,url);
 assert.deepEqual(mapper(6550231,16).qs,[{key:'recursive',value:'1'}]);
 assert.equal(mapper(6550231,18).method,'POST');assert.equal(mapper(6550231,18).body,'{{17.result.graphql_body}}');
 assert.equal(mapper(6550231,19).input.find(x=>x.name==='selected').value,'{{17.result}}');
 assert.equal(mapper(6550231,19).input.find(x=>x.name==='blobs').value,'{{18.body}}');
 assert.deepEqual(s.modules.find(m=>m.id===6).filter.conditions,[[{a:'{{19.result.found}}',b:'true',o:'boolean:equal'}]]);
 assert.equal(mapper(6550231,11).input.find(x=>x.name==='starter_repository').value,'{{19.result.source_repo}}');
 assert.equal(mapper(6550231,11).input.find(x=>x.name==='starter_commit').value,'{{19.result.commit}}');
 for(const[id,pageId]of [[11,21],[12,22]]){assert.equal(mapper(6550231,id).input.find(x=>x.name==='source_ref').value,'{{19.result.source_ref}}');assert.equal(mapper(6550231,id).input.find(x=>x.name==='proof').value,'{{19.result}}');assert.equal(mapper(6550231,id).input.find(x=>x.name==='native_page').value,'{{'+pageId+'.body}}');assert.ok(code(6550231,id).includes('bridgePersistPins('));}
 assert.ok(!code(6550231,5).includes('manifest_evidence'));
 assert.ok(mapper(6550231,6).input.includes('Operator Pack READY does not establish registered source'));
});
check('execution evidence does not claim a completed recording or miner run', () => {
  assert.equal(receipt.recordingEvidence, 'pending actual Recorder checks');
  assert.equal(receipt.miner.validation, 'configuration and offline contracts only');
  assert.equal(receipt.miner.forcedRun, false);
  assert.equal(receipt.canonicalRecovery.issue.method, 'GET'); assert.equal(receipt.canonicalRecovery.comment.method, 'GET');
  assert.equal(receipt.canonicalRecovery.issue.issue_number, 86); assert.equal(receipt.canonicalRecovery.comment.action, 'skip');
  for (const id of ids.slice(0, 4)) assert.ok(receipt.executions[String(id)].some(r => r.status === 'success'));
  const cleanup = JSON.parse(fs.readFileSync(path.join(root, 'cloud/duplicate-cleanup-receipts.json')));
  assert.equal(cleanup.finalVerification.closedCount, 114); assert.equal(cleanup.finalVerification.bodiesPreserved, true); assert.equal(cleanup.finalVerification.commentsPreserved, true);
  assert.equal(receipt.duplicateCleanup.verifiedAt, cleanup.finalVerification.at);
});

check('capability output mappings use the actual Code result wrapper',()=>{
 assert.ok(mapper(6550627,4).input.includes('{{11.result.version}}'));
 assert.ok(mapper(6550627,4).input.includes('{{11.result.ids_csv}}'));
 assert.equal(mapper(6550627,5).input.find(x=>x.name==='capability_ids_json').value,'{{11.result.ids_json}}');
 assert.ok(!mapper(6550627,4).input.includes('{{11.ids_csv}}'));
});
process.stdout.write(checks + ' deployed Make source, routing, preservation and evidence checks passed\n');
