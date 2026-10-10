'use strict';
const assert = require('node:assert/strict'), fs = require('node:fs'), path = require('node:path'), crypto = require('node:crypto');
const root = path.resolve(__dirname, '..');
const raw = fs.readFileSync(path.join(root, 'cloud/companion-processes.json'));
const snapshot = JSON.parse(raw), receipt = JSON.parse(fs.readFileSync(path.join(root, 'cloud/companion-processes-receipt.json')));
let checks = 0;
const check = (name, fn) => { try { fn(); checks++; } catch (error) { error.message = name + ': ' + error.message; throw error; } };
const scenario = id => { const s = snapshot.scenarios.find(s => s.scenario.id === id); assert.ok(s); return s; };
const moduleConfig = (id, m) => { const result = scenario(id).modules.find(x => x.id === m); assert.ok(result); return result.config.mapper; };
const capabilityIds=JSON.stringify(require('../cloud/capability-authority.json').capabilityIds);
const run = (id, m, input) => new Function('input', 'require', moduleConfig(id, m).codeEditorJavascript)({capability_ids_json:capabilityIds,...input}, require);
const hash = s => crypto.createHash('sha256').update(s).digest('hex');
const rt = content => ({ rich_text: [{ plain_text: content, text: { content } }] }), select = name => ({ select: { name } });
const query = results => ({ results, has_more: false, next_cursor: null });
const PAGE = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa';
function page(changes = {}) { return { id: PAGE, properties: { Task: { title: [{ plain_text: 'Synthetic mapping fixture' }] }, Stage: select('Candidate'), Lane: select('Bootcamp'),
  'Odin Goal': rt('Synthetic human task'), 'Source Evidence': rt('Synthetic contract'), 'Professional Judgment': rt('Human preserved decision'),
  'Certification Alignment': rt('Existing human mapping'), 'Certification Evidence Level': select('Credential/domain-level'),
  'Certification Objective Coverage': rt(''), 'Bootcamp Capability IDs': rt(''), 'Human Transfer Test': rt(''),
  'Transfer Synced': { checkbox: true }, 'Pre-Record Gate': { checkbox: true }, 'Recording QA Gate': { checkbox: true }, ...changes } }; }
const review = { certification_alignment: 'Do not overwrite existing judgment', certification_objective_coverage: 'Supported domain fixture', certification_evidence_level: 'Credential/domain-level',
  bootcamp_capability_ids: ['invariant-driven-testing', 'invented-capability'], human_transfer_test: 'Diagnose, decide and verify unaided.', skills_practiced: 'Test design' };
const selected = p => run(6551447, 3, { body: query([p]) }).rows[0];
const write = (p, row, out = review) => run(6551447, 6, { row, latest_page: p, raw: out });
check('redacted companion ownership and schema', () => {
  assert.deepEqual(snapshot.scenarios.map(s => s.scenario.id).sort(), [6551447, 6551517]);
  assert.equal(scenario(6551447).scenario.status, 'active'); assert.equal(scenario(6551517).scenario.status, 'active');
  assert.ok(!JSON.stringify(snapshot).includes('__IMTCONN__'));
  assert.equal(receipt.snapshotSha256, hash(raw)); assert.equal(snapshot.taskFactorySchema.properties['Skill Mapping Revision'].type, 'text');
  assert.ok(snapshot.taskFactorySchema.properties['Transfer Synced'].description.includes('reviewed attempt evidence'));
});
for (const [id, modules, filename] of [[6551447, [3, 6], 'skill-mapper.js'], [6551517, [2, 7, 10], 'transfer-router.js'], [6551447,[12],'capability-router.js']]) {
  for (const m of modules) check('exact deployed shared source ' + id + '/' + m, () => {
    const rawSource=fs.readFileSync(path.join(root,'cloud',filename),'utf8');
    const source = (filename==='transfer-router.js'?rawSource.replace(/^if \(typeof module.*module\.exports.*$/m,''):rawSource).trimEnd(), code = moduleConfig(id, m).codeEditorJavascript;
    assert.ok(code.startsWith(source + '\n')); new Function('input', 'require', code);
    const binding = receipt.sourceBindings.find(b => b.scenarioId === id && b.moduleId === m); assert.ok(binding.matches); assert.equal(binding.sourcePrefixSha256, hash(source));
  });
}
check('fresh native page precedes missing-field planning', () => {
  const s = scenario(6551447); assert.equal(s.modules.find(m => m.id === 8).follows, 5); assert.equal(s.modules.find(m => m.id === 6).follows, 8);
  assert.equal(moduleConfig(6551447, 8).method, 'GET'); assert.equal(moduleConfig(6551447, 8).url, '/v1/pages/{{4.page_id}}');
  assert.equal(moduleConfig(6551447, 6).input.find(i => i.name === 'latest_page').value, '{{8.body}}');
  assert.equal(moduleConfig(6551447, 7).method, '{{6.result.method}}'); assert.equal(moduleConfig(6551447, 7).body, '{{6.result.body}}');
  assert.equal(receipt.mapper.executionSettings.sequential, true);
});
check('companion API writes remain serialized and scoped', () => {
  for (const s of snapshot.scenarios) for (const m of s.modules) if (m.module === 'notion:makeApiCall') {
    const map = m.config.mapper; if (map.method !== 'GET') assert.equal(typeof map.body, 'string');
    assert.ok(!map.headers?.some(h => /authorization|token|api.key/i.test(h.key)));
    assert.ok(!/github|slack|email/.test(m.module));
  }
});
check('existing judgments and synchronization flags survive enrichment', () => {
  const p = page(), request = write(p, selected(p)), props = JSON.parse(request.body).properties;
  assert.equal(request.method, 'PATCH'); assert.equal(props['Certification Alignment'], undefined); assert.equal(props['Certification Evidence Level'], undefined);
  assert.equal(props['Professional Judgment'], undefined); assert.equal(props['Transfer Synced'], undefined);
  for (const human of ['Pre-Record Gate', 'Recording QA Gate', 'Local Starter Gate', 'Submission Gate', 'Workflow Checklist Gate', 'Approval ID', 'Approved Goal', 'Approved Pay', 'Reviewer Score', 'Reviewer Notes', 'Stage', 'Lane', 'Bootcamp Status']) assert.equal(props[human], undefined);
  assert.equal(props['Bootcamp Capability IDs'].rich_text[0].text.content, 'invariant-driven-testing'); assert.ok(props['Skill Mapping Revision']);
});
check('fenced reviewer JSON is parsed without rewriting authored text', () => {
  const p = page({ 'Bootcamp Capability IDs': rt('Human authored capability choice') });
  const props = JSON.parse(write(p, selected(p), '```json\n' + JSON.stringify(review) + '\n```').body).properties;
  assert.equal(props['Bootcamp Capability IDs'], undefined);
});
check('native fresh-read text and links are not rewritten', () => {
  const p = page(), row = selected(p), latest = structuredClone(p);
  latest.properties['Human Transfer Test'] = { rich_text: [{ type: 'text', text: { content: 'Human concurrent edit', link: { url: 'https://example.com/evidence' } } }] };
  const request = write(latest, row); assert.equal(request.method, 'GET'); assert.equal(request.body, '');
});
check('durable retry and valid empty classifications are no-ops', () => {
  const p = page(), row = selected(p), saved = structuredClone(p); Object.assign(saved.properties, JSON.parse(write(p, row).body).properties);
  assert.equal(run(6551447, 3, { body: query([saved]) }).count, 0); assert.equal(write(saved, row).method, 'GET');
  const empty = page({ 'Certification Alignment': rt(''), 'Certification Evidence Level': select('No supported mapping'), 'Human Transfer Test': rt('Existing human evidence contract') });
  assert.equal(run(6551447, 3, { body: query([empty]) }).count, 0);
});
check('new unsupported empty mapping receives a durable marker', () => {
  const p = page({ 'Certification Alignment': rt(''), 'Certification Evidence Level': select('') }), row = selected(p);
  const out = { ...review, certification_alignment: '', certification_objective_coverage: '', certification_evidence_level: 'No supported mapping', bootcamp_capability_ids: [] };
  const props = JSON.parse(write(p, row, out).body).properties; assert.equal(props['Certification Alignment'], undefined); assert.equal(props['Bootcamp Capability IDs'], undefined);
  const saved = structuredClone(p); Object.assign(saved.properties, props); assert.equal(run(6551447, 3, { body: query([saved]) }).count, 0);
});
check('source changes and manual revision edits hold without overwrite', () => {
  const p = page(), row = selected(p), changed = structuredClone(p); changed.properties['Odin Goal'] = rt('Human changed Goal');
  assert.throws(() => write(changed, row), /Source changed/);
  const saved = structuredClone(p); Object.assign(saved.properties, JSON.parse(write(p, row).body).properties); saved.properties['Human Transfer Test'] = rt('Human changed mapping');
  assert.equal(run(6551447, 3, { body: query([saved]) }).held.length, 1); assert.throws(() => write(saved, row), /Manual mapping/);
});
check('incomplete or rejected inputs never produce a mapping write', () => {
  assert.throws(() => run(6551447, 3, { body: { ...query([page()]), has_more: true } }), /Incomplete/);
  const rejected = page({ Stage: select('Rejected') }); assert.equal(run(6551447, 3, { body: query([rejected]) }).count, 0);
  assert.throws(() => write(page(), selected(page()), { ...review, human_transfer_test: '' }), /Incomplete/);
});
check('unrecorded review cannot become transfer sync', () => {
  const unrecorded=page({'Transfer Synced':{checkbox:false},'Bootcamp Status':select('Ready to practice'),'Reviewer Status':select('Pass'),'Reviewer Notes':rt('Fixture'),'Reviewer Score':{number:100}});
  const result=run(6551517,2,{body:query([unrecorded])});assert.equal(result.count,0);assert.equal(result.skipped.length,1);
});
check('real existing transfer destination and content-before-sync routing',()=>{
 assert.equal(snapshot.transferDestination.dataSourceId,'a6d74f65-0b06-4d1a-ab64-b4fb5f1a5a52');
 const modules=scenario(6551517).modules;
 assert.equal(modules.find(m=>m.id===9).follows,8);assert.equal(modules.find(m=>m.id===10).follows,9);assert.equal(modules.find(m=>m.id===11).follows,10);
 assert.equal(moduleConfig(6551517,11).body,'{{10.result.body}}');
 assert.equal(receipt.router.executionSettings.sequential,true);assert.equal(receipt.router.masteryEligible,false);
});
check('actual Code result capability mappings and canonical cloud authority',()=>{
 assert.equal(moduleConfig(6551447,6).input.find(x=>x.name==='capability_ids_json').value,'{{12.result.ids_json}}');
 assert.ok(moduleConfig(6551447,5).input.includes('{{12.result.version}}'));assert.ok(moduleConfig(6551447,5).input.includes('{{12.result.ids_csv}}'));
 const authority=require('../cloud/capability-authority.json');
 const p={properties:{Name:{title:[{plain_text:'Current'}]},'Matrix Version':rt(authority.version),'Matrix Blob SHA':rt(authority.blobSha),'Source Repo':{url:authority.repository},'Capability IDs JSON':rt(authority.capabilityIds.join(','))}};
 const result=run(6551447,12,{body:query([p])});assert.deepEqual(result.ids,authority.capabilityIds);
 const changed=structuredClone(p);changed.properties['Matrix Version']=rt('4.2.0');assert.throws(()=>run(6551447,12,{body:query([changed])}),/verified cloud source/);
 assert.throws(()=>run(6551447,6,{row:selected(page()),latest_page:page(),raw:review,capability_ids_json:'[]'}),/verified cloud matrix/);
});
check('observed run evidence and advisory boundary remain truthful',()=>{
 assert.equal(receipt.router.destinationWrites,0);assert.equal(receipt.router.status,'active');assert.equal(receipt.router.transferSyncClaim,false);
 for(const id of [6551447,6551517]){const entry=id===6551447?receipt.mapper:receipt.router;assert.equal(entry.latestExecution.status,'success');assert.ok(entry.latestExecution.startedAt>=scenario(id).scenario.lastEdit);assert.equal(entry.latestExecution.selectorResult.count,0);}
 assert.equal(receipt.humanAttemptPropertiesReset,false);assert.match(receipt.router.advisoryBoundary,/proposal-only/);assert.match(receipt.router.advisoryBoundary,/without synthetic overall Pass/);
});
require('./check_transfer_router.js');
process.stdout.write(checks + ' deployed companion ownership, preservation, mapping and transfer checks passed\n');
