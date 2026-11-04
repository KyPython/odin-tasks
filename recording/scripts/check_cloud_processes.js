'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const builder = require('../cloud/bootcamp-builder.js');
const ROW = '3f28621e-0a7a-8141-8d6e-dfb9a5b43054';

function page(overrides) {
  const text = function (content) { return { rich_text: [{ plain_text: content }] }; };
  const select = function (name) { return { select: { name: name } }; };
  return {
    id: ROW, url: 'https://app.notion.com/' + ROW.replace(/-/g, ''),
    properties: Object.assign({
      Task: { title: [{ plain_text: 'Cursor pagination repair' }] },
      Lane: select('Dual-candidate'), Stage: select('Candidate'), 'Fit Gate': select('PASS'),
      'Bootcamp Status': select('World queued'), 'Operator Pack Status': select('PENDING'),
      'Odin Goal': text('Diagnose the client and verify its documented contract.'),
      'Source Evidence': text('Synthetic API contract; deterministic fixtures and ordinary-path tests.'),
      'Spec Path': text('specs/odin-bootcamp/cursor-pagination-aggregator-contract-repair'),
      'Spec PR': { url: 'https://github.com/KyPython/ai-governance/pull/201' },
      'Duplicate Fingerprint': text('api-contract|cursor-pagination|termination-state|ordered-deduplication'),
      'Approved Goal': text(''), 'Approval ID': text(''), 'Build Issue': { url: null }
    }, overrides || {})
  };
}

function query(pages, overrides) {
  return Object.assign({ results: pages, has_more: false, next_cursor: null }, overrides || {});
}

function world() { return builder.selectQueuedWorlds(query([page()])).rows[0]; }
function issue(number, state, rowId) {
  return {
    number: number || 58, state: state || 'open',
    html_url: 'https://github.com/KyPython/ai-governance/issues/' + (number || 58),
    body: '<!-- ODIN_BOOTCAMP_ROW_ID:' + (rowId || ROW) + ' -->'
  };
}
function search(items, overrides) {
  return Object.assign({ items: items, total_count: items.length, incomplete_results: false }, overrides || {});
}

test('Kiro first holds missing, unmerged, wrong-source and incomplete specifications', function () {
  for (const url of [null, '', 'https://github.com/Other/repo/pull/1', 'https://github.com/KyPython/ai-governance/pull/201?x=1']) {
    assert.equal(builder.selectQueuedWorlds(query([page({ 'Spec PR': { url } })])).count, 0);
  }
  const selected = world();
  const pr = { number: 201, html_url: selected.spec_pr, base: { ref: 'main', repo: { full_name: builder.REPOSITORY } },
    merged: true, merged_at: '2026-10-08T00:00:00Z', merged_by: { login: 'KyPython' },
    merge_commit_sha: 'a'.repeat(40), body: 'KIRO_SPEC_EXECUTION_ID: fixture-execution-201' };
  const files = ['requirements.md', 'design.md', 'tasks.md'].map(name => ({ path: selected.spec_path + '/' + name, type: 'file', sha: 'b'.repeat(40) }));
  const requirements = selected.goal + '\n\nTask Factory row: https://app.notion.com/p/' + selected.row_id.replace(/-/g, '');
  assert.equal(builder.verifyMergedSpec(selected, pr, files, requirements).merge_commit, pr.merge_commit_sha);
  for (const change of [{ merged: false }, { merged_at: null }, { merged_by: { login: 'bot' } }, { body: '' },
    { number: 42 }, { base: { ref: 'other', repo: { full_name: builder.REPOSITORY } } }]) {
    assert.throws(() => builder.verifyMergedSpec(selected, { ...pr, ...change }, files, requirements), /blocked/);
  }
  assert.throws(() => builder.verifyMergedSpec(selected, pr, files.slice(0, 2), requirements), /missing tasks/);
  assert.throws(() => builder.verifyMergedSpec(selected, pr, files, 'Other Goal\n' + selected.row_id), /exact Goal/);
  assert.throws(() => builder.verifyMergedSpec(selected, pr, files, selected.goal), /canonical Notion row/);
});

test('mixed factory output cannot build approved Odin, HOLD, rejected or wrong-lane rows', function () {
  const pages = [
    page(),
    page({ Lane: { select: { name: 'Bootcamp' } } }),
    page({ Lane: { select: { name: 'Odin monetization' } } }),
    page({ 'Fit Gate': { select: { name: 'HOLD' } } }),
    page({ Stage: { select: { name: 'Rejected' } } }),
    page({ Stage: { select: { name: 'Environment building' } } }),
    page({ 'Approved Goal': { rich_text: [{ plain_text: 'Approved contract' }] } }),
    page({ 'Approval ID': { rich_text: [{ plain_text: 'ODIN-EXTERNAL' }] } }),
    page({ 'Build Issue': { url: 'https://github.com/KyPython/ai-governance/issues/58' } }),
    page({ 'Bootcamp Status': { select: { name: 'World building' } } }),
    page({ 'Operator Pack Status': { select: { name: 'READY' } } })
  ];
  pages.forEach(function (item, index) {
    item.id = ROW.slice(0, 24) + String(index + 1).padStart(12, '0');
    item.properties['Duplicate Fingerprint'] = { rich_text: [{ plain_text: 'mixed-world-' + index }] };
  });
  const selected = builder.selectQueuedWorlds(query(pages));
  assert.equal(selected.count, 2);
  assert.equal(selected.skipped.length, 9);
});

test('each full contract input is required; invalid paths and archived rows are skipped', function () {
  for (const field of ['Odin Goal', 'Source Evidence', 'Spec Path', 'Duplicate Fingerprint']) {
    assert.equal(builder.selectQueuedWorlds(query([page({ [field]: { rich_text: [] } })])).count, 0);
  }
  assert.equal(builder.selectQueuedWorlds(query([page({
    'Spec Path': { rich_text: [{ plain_text: 'specs/odin-bootcamp/../../secret' }] }
  })])).count, 0);
  const archived = page(); archived.in_trash = true;
  assert.equal(builder.selectQueuedWorlds(query([archived])).count, 0);
});

test('incomplete or malformed Notion reads fail closed even when eligible rows are present', function () {
  for (const response of [
    query([page()], { has_more: true }),
    query([page()], { next_cursor: 'next' }),
    { results: [page()] }, { results: null }, 'not json'
  ]) assert.throws(function () { builder.selectQueuedWorlds(response); }, /blocked/);
  assert.throws(function () { builder.selectQueuedWorlds(query([page(), page()])); }, /duplicate row/);
});

test('another existing world with the same fingerprint blocks duplicate construction', function () {
  const existing = page({ 'Bootcamp Status': { select: { name: 'World building' } } });
  existing.id = '3f28621e-0a7a-81bc-abb6-c65d74863966';
  const selected = builder.selectQueuedWorlds(query([page(), existing]));
  assert.equal(selected.count, 0);
  assert.ok(selected.skipped.some(function (row) { return /duplicate fingerprint/.test(row.reason); }));
});

test('full rich-text contract and shell-like text survive JSON serialization without evaluation', function () {
  const p = page();
  const goal = 'Quote "contract"\n$(touch /tmp/never-execute) ' + String.fromCharCode(96) + 'literal' + String.fromCharCode(96);
  p.properties['Odin Goal'].rich_text = [
    { plain_text: goal.slice(0, 12) }, { text: { content: goal.slice(12) } }
  ];
  const selected = builder.selectQueuedWorlds(JSON.stringify(query([p]))).rows[0];
  assert.equal(selected.goal, goal);
  const request = builder.buildIssueRequest(selected);
  assert.equal(JSON.parse(request.payload).body, request.body);
  assert.ok(request.body.includes(goal));
  assert.ok(request.body.includes(selected.source_evidence));
  assert.ok(request.body.includes(selected.spec_path));
  assert.ok(request.body.includes(selected.fingerprint));
});

test('initial create then recovery after failed Notion write opens no second issue', function () {
  const selected = world();
  assert.equal(builder.resolveIssue(selected, search([])).action, 'create');
  const recovered = builder.resolveIssue(selected, search([issue()]));
  assert.equal(recovered.action, 'recover');
  assert.equal(recovered.issue_number, 58);
  assert.equal(recovered.payload, undefined);
});

test('complete all-state issue inventory recovers a new issue before search indexing catches up', function () {
  const selected = world();
  const recovered = builder.resolveIssueFromInventory(selected, { issues: [issue()], complete: true });
  assert.equal(recovered.action, 'recover');
  assert.equal(recovered.issue_number, 58);
  assert.throws(function () {
    builder.resolveIssueFromInventory(selected, { issues: [], complete: false });
  }, /incomplete/);
});

test('closed issues recover without another build; exact row marker excludes substring hits', function () {
  const closed = builder.resolveIssue(world(), search([issue(58, 'closed')]));
  assert.equal(closed.action, 'recover');
  assert.equal(closed.comment_allowed, false);
  const wrong = issue(); wrong.body += 'suffix';
  wrong.body = 'ODIN_BOOTCAMP_ROW_ID:' + ROW + 'extra';
  assert.equal(builder.resolveIssue(world(), search([wrong])).action, 'create');
  assert.equal(builder.resolveIssue(world(), search([issue(59, 'open',
    '3f28621e-0a7a-81bc-abb6-c65d74863966')])).action, 'create');
});

test('search incompleteness and ambiguous duplicate markers block creation', function () {
  for (const response of [
    search([], { incomplete_results: true }),
    search([], { total_count: 1 }),
    { items: [], total_count: 0 },
    search([issue(), issue(84)])
  ]) assert.throws(function () { builder.resolveIssue(world(), response); }, /blocked/);
  const chosen = builder.resolveIssue(world(), search([issue(), issue(84)]), 58);
  assert.equal(chosen.issue_number, 58);
  assert.throws(function () { builder.resolveIssue(world(), search([issue(84)]), 58); }, /canonical/);
});

test('wrong-repository and pull-request evidence never authorize recovery or write-back', function () {
  const wrong = issue(); wrong.html_url = 'https://github.com/other/repo/issues/58';
  assert.throws(function () { builder.resolveIssue(world(), search([wrong])); }, /wrong-repository/);
  assert.throws(function () { builder.writebackPayload(world(), wrong, '2026-10-07'); }, /wrong-repository/);
  const pr = issue(); pr.pull_request = {};
  assert.equal(builder.resolveIssue(world(), search([pr])).action, 'create');
  assert.throws(function () { builder.verifyCreatedIssue(world(), pr); }, /wrong-repository/);
});

test('published creation must retain exact marker before any downstream comment', function () {
  assert.equal(builder.verifyCreatedIssue(world(), issue()).number, 58);
  assert.throws(function () { builder.verifyCreatedIssue(world(), issue(58, 'open',
    '3f28621e-0a7a-81bc-abb6-c65d74863966')); }, /lost the task marker/);
});

test('retry after a successful Codex comment posts no second comment', function () {
  const first = builder.planCodexComment(world(), issue(), [], true);
  assert.equal(first.action, 'comment');
  const comment = { body: JSON.parse(first.payload).body, user: { login: 'KyPython' } };
  assert.equal(builder.planCodexComment(world(), issue(), [comment], true).action, 'skip');
  assert.equal(builder.planCodexComment(world(), issue(), [{ body: '@codex previous handoff' }], true).action, 'skip');
  assert.equal(builder.planCodexComment(world(), issue(), [{
    body: 'Built starter summary', user: { login: 'chatgpt-codex-connector' }
  }], true).action, 'skip');
  assert.throws(function () { builder.planCodexComment(world(), issue(), [], false); }, /incomplete/);
  assert.equal(builder.planCodexComment(world(), issue(58, 'closed'), [], true).action, 'skip');
  assert.equal(builder.planCodexComment(JSON.stringify(world()), JSON.stringify(issue()),
    JSON.stringify([comment]), true).action, 'skip');
});

test('write-back is a serialized string and preserves human judgments and every approval gate', function () {
  const payload = builder.writebackPayload(world(), issue(), '2026-10-07');
  assert.equal(typeof payload, 'string');
  assert.deepEqual(Object.keys(JSON.parse(payload).properties).sort(),
    ['Bootcamp Status', 'Build Issue', 'Last Updated']);
  assert.equal(JSON.parse(payload).properties['Build Issue'].url, issue().html_url);
  assert.throws(function () { builder.writebackPayload(world(), issue(), '2026-02-30'); }, /invalid evidence date/);
});

test('handoff demands consumable pinned source and does not mistake cloud summaries for publication',()=>{
 const request=builder.buildIssueRequest(world());
 for(const word of ['source_repo','commit','content_b64','pr_url','private GitHub','never regenerate','not a consumable artifact']) assert.ok(request.body.includes(word));
 const plan=builder.planCodexComment(world(),issue(58,'open'),[],true);
 for(const word of ['full commit SHA','ODIN_STARTER_MANIFEST','publication is blocked','Reuse prior completed output']) assert.ok(JSON.parse(plan.payload).body.includes(word));
});

test('public canonical queue cannot receive private starter bytes through connector output',()=>{
 const request=builder.buildIssueRequest(world()),handoff=JSON.parse(builder.planCodexComment(world(),issue(58,'open'),[],true).payload).body;
 for(const body of [request.body,handoff]){assert.ok(body.includes('FINAL RESPONSE'));assert.ok(body.includes('private'));assert.ok(body.includes('public')||body.includes('PUBLIC'));}
 assert.match(request.body,/only when the connector destination is verified private/);
});
