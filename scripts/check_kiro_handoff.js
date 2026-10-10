'use strict';
const assert = require('node:assert/strict');
const { approvedRows, resolveApproved } = require('../cloud/kiro-handoff');
const rt = content => [{ text: { content } }];
const page = { id: '3f28621e-0a7a-8141-8d6e-dfb9a5b43054', properties: { Stage: { select: { name: 'Odin approved' } },
  'Fit Gate': { select: { name: 'PASS' } }, Lane: { select: { name: 'Odin monetization' } }, Task: { title: rt('Task') },
  'Approved Goal': { rich_text: rt('Exact goal') }, 'Odin Goal': { rich_text: rt('Exact goal') }, 'Approval ID': { rich_text: rt('ODIN-actual') }, 'Spec Path': { rich_text: rt('specs/odin/task') } } };
assert.equal(approvedRows({ results: [page], has_more: false }).rows.length, 1);
for (const [key, name] of [['Lane', 'Dual-candidate'], ['Stage', 'Candidate'], ['Fit Gate', 'HOLD']]) { const p = structuredClone(page); p.properties[key].select.name = name; assert.equal(approvedRows({ results: [p], has_more: false }).rows.length, 0); }
const changed = structuredClone(page); changed.properties['Approved Goal'].rich_text = rt('Changed'); assert.equal(approvedRows({ results: [changed], has_more: false }).rows.length, 0);
assert.throws(() => approvedRows({ results: [page], has_more: true }), /Incomplete/);
const world = approvedRows({ results: [page], has_more: false }).rows[0];
const issue = { number: 36, state: 'closed', html_url: 'https://github.com/KyPython/ai-governance/issues/36', body: '<!-- ODIN_ROW_ID:' + world.row_id + ' -->' };
const request = { ...world, page1: [issue], page2: [], page3: [] };
assert.equal(resolveApproved(request).existing, true);
assert.equal(resolveApproved({ ...request, page1: [] }).existing, false);
assert.throws(() => resolveApproved({ ...request, page1: [issue, issue] }), /Ambiguous/);
assert.throws(() => resolveApproved({ ...request, page3: Array(100).fill(issue) }), /Incomplete/);
const practice = structuredClone(page);
practice.properties.Stage.select.name = 'Candidate'; practice.properties.Lane.select.name = 'Bootcamp';
practice.properties['Approved Goal'].rich_text = rt(''); practice.properties['Approval ID'].rich_text = rt('');
practice.properties['Bootcamp Status'] = { select: { name: 'World queued' } };
practice.properties['Operator Pack Status'] = { select: { name: 'PENDING' } };
practice.properties['Spec Path'].rich_text = rt('specs/odin-bootcamp/task');
practice.properties['Source Evidence'] = { rich_text: rt('Exact synthetic starter contract and actual baseline evidence.') };
const selectedPractice = approvedRows({ results: [practice], has_more: false }).rows[0];
assert.equal(selectedPractice.workflow_lane, 'bootcamp'); assert.equal(selectedPractice.writeback_stage, 'Candidate');
const specRequest = resolveApproved({ ...selectedPractice, page1: [], page2: [], page3: [] });
const specBody = JSON.parse(specRequest.payload).body;
assert.ok(specBody.includes('ODIN_BOOTCAMP_SPEC_ROW_ID:' + practice.id));
assert.ok(specBody.includes('KIRO_SPEC_EXECUTION_ID:<actual-id>'));
assert.ok(specBody.includes('Odin approval remains pending'));
for (const stage of ['Rejected', 'Awaiting Odin approval']) {
 const held = structuredClone(practice); held.properties.Stage.select.name = stage;
 assert.equal(approvedRows({ results: [held], has_more: false }).rows.length, 0);
}
const alreadyBuilt = structuredClone(practice); alreadyBuilt.properties['Build Issue'] = { url: 'https://github.com/KyPython/ai-governance/issues/196' };
assert.equal(approvedRows({ results: [alreadyBuilt], has_more: false }).rows.length, 0);
const assignedAlreadyBuilt = structuredClone(page); assignedAlreadyBuilt.properties['Build Issue'] = { url: 'https://github.com/KyPython/ai-governance/issues/43' };
assert.equal(approvedRows({ results: [assignedAlreadyBuilt], has_more: false }).rows.length, 0);
process.stdout.write('Approved and internal Kiro-first handoff checks passed\n');
