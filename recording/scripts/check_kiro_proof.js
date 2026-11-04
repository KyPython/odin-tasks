'use strict';

const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const test = require('node:test');
const proof = require('../cloud/kiro-proof.js');
const sha = text => crypto.createHash('sha256').update(text, 'utf8').digest('hex');

function fixture() {
  const executionId = '55ad3804-d09b-482c-8a2c-4c0242acaf37';
  const world = { row_id: '11111111-2222-4333-8444-555555555555',
    goal: 'Repair a synthetic local client and verify its documented contract.',
    spec_path: 'specs/odin-bootcamp/synthetic-client',
    spec_pr: 'https://github.com/KyPython/ai-governance/pull/201' };
  const documents = {
    [world.spec_path + '/requirements.md']: '# Requirements\n\n' + world.goal + '\n\n' +
      'Task Factory row: https://app.notion.com/p/' + world.row_id.replace(/-/g, '') + '\n\nR1 SHALL use synthetic local fixtures.\n',
    [world.spec_path + '/design.md']: '# Design\n\nA local fixture seam; no production or private source.\n',
    [world.spec_path + '/tasks.md']: '# Tasks\n\n1. Codex constructs the starter; Cursor reviews R1.\n'
  };
  const captureRaw = 'TEST FIXTURE ONLY: fictional captured Kiro CLI output; no real Kiro execution is claimed.\n';
  const receipt = { version: 1, engine: 'kiro', status: 'PASS', executionId,
    inventorySha256: '1'.repeat(64), specCommit: 'a'.repeat(40),
    paths: Object.fromEntries(Object.entries(documents).map(([p, content]) => [p, { status: 'PASS', sha256: sha(content) }])),
    bindings: { [world.row_id]: { rowId: world.row_id, goalSha256: sha(world.goal + '\n'), specPath: world.spec_path, specPr: world.spec_pr } },
    executionEvidence: { source: 'captured-kiro-cli', executionTarget: 'cloud',
      capturePath: 'cloud/kiro-receipts/' + executionId + '.capture.txt', captureSha256: sha(captureRaw) } };
  const pr = { number: 201, html_url: world.spec_pr,
    base: { ref: 'main', repo: { full_name: 'KyPython/ai-governance' } },
    head: { sha: receipt.specCommit }, merged: true, merged_at: '2026-10-08T00:00:00Z',
    merged_by: { login: 'KyPython' }, merge_commit_sha: 'b'.repeat(40), body: '' };
  const item = { world, pr, receipt, documents, captureRaw, receiptRaw: '' };
  reseal(item);
  return item;
}

function reseal(item) {
  item.receiptRaw = JSON.stringify(item.receipt, null, 2) + '\n';
  item.pr.body = 'KIRO_SPEC_EXECUTION_ID:' + item.receipt.executionId + '\n' +
    'KIRO_RECEIPT_COMMIT:' + 'c'.repeat(40) + '\n' +
    'KIRO_RECEIPT_SHA256:' + sha(item.receiptRaw) + '\n';
}
function verify(item) { return proof.verifyKiroProof(item.world, item.pr, item.receiptRaw, item.documents, item.captureRaw); }

test('trusted location derives one private immutable receipt and ignores arbitrary body URLs', () => {
  const f = fixture(); f.pr.body += 'Receipt URL: https://evil.example/source.json\n';
  const location = proof.parseTrustedReceiptLocation(f.pr);
  assert.equal(location.repository, 'KyPython/odin-recording-preparation');
  assert.equal(location.path, 'cloud/kiro-receipts/' + f.receipt.executionId + '.json');
  assert.equal(location.url, 'https://api.github.com/repos/KyPython/odin-recording-preparation/contents/' + location.path + '?ref=' + 'c'.repeat(40));
  assert.equal(location.captureUrl, 'https://api.github.com/repos/KyPython/odin-recording-preparation/contents/' +
    location.capturePath + '?ref=' + 'c'.repeat(40));
  assert.equal(verify(f).provenanceTrust, 'authenticated-publisher-receipt');
});

test('actual reviewed head can differ from merge commit while all three merged bytes match', () => {
  const f = fixture(); const result = verify(f);
  assert.equal(result.verified, true); assert.notEqual(result.specCommit, result.mergeCommit);
  assert.deepEqual(result.specFiles, Object.fromEntries(Object.entries(f.documents).map(([p, raw]) => [p, sha(raw)])));
});

test('prefixed local Kiro identity remains intact in marker, receipt and private filename', () => {
  const f = fixture(); f.receipt.executionId = 'sess_ef9c3844-0570-409c-baa6-7cc73d898476';
  f.receipt.executionEvidence.executionTarget = 'local';
  f.receipt.executionEvidence.capturePath = 'cloud/kiro-receipts/' + f.receipt.executionId + '.capture.txt'; reseal(f);
  const location = proof.parseTrustedReceiptLocation(f.pr); const result = verify(f);
  assert.equal(location.executionId, f.receipt.executionId);
  assert.equal(location.path, 'cloud/kiro-receipts/sess_ef9c3844-0570-409c-baa6-7cc73d898476.json');
  assert.equal(result.executionId, f.receipt.executionId);
  assert.equal(result.executionTarget, 'local');
  assert.equal(result.capturePath, 'cloud/kiro-receipts/sess_ef9c3844-0570-409c-baa6-7cc73d898476.capture.txt');
  f.receipt.executionId = f.receipt.executionId.slice(5);
  f.receiptRaw = JSON.stringify(f.receipt) + '\n';
  f.pr.body = f.pr.body.replace(/KIRO_RECEIPT_SHA256:[a-f0-9]{64}/, 'KIRO_RECEIPT_SHA256:' + sha(f.receiptRaw));
  assert.throws(() => verify(f), /actual execution/);
});

test('actual nonempty captured bytes are mandatory and cannot be changed independently of receipt', () => {
  for (const raw of [undefined, null, '', '  \n', fixture().captureRaw + 'unobserved output']) {
    const f = fixture(); f.captureRaw = raw; assert.throws(() => verify(f), /exact capture bytes mismatch/);
  }
  const f = fixture(); assert.equal(verify(f).captureSha256, sha(f.captureRaw));
});

test('captured CLI source, target and full actual session filename remain independently bound', () => {
  for (const edit of [e => { e.source = 'self-reported'; }, e => { e.executionTarget = 'unknown'; },
    e => { delete e.executionTarget; }, e => { e.captureSha256 = 'd'.repeat(64); },
    e => { e.capturePath = 'https://example.test/recording.txt'; },
    e => { e.capturePath = 'cloud/kiro-receipts/another-session.capture.txt'; }]) {
    const f = fixture(); edit(f.receipt.executionEvidence); reseal(f);
    assert.throws(() => verify(f), /captured CLI source, target/);
  }
  const f = fixture(); delete f.receipt.executionEvidence; reseal(f);
  assert.throws(() => verify(f), /captured execution evidence/);
  const local = fixture(); local.receipt.executionId = 'sess_ef9c3844-0570-409c-baa6-7cc73d898476';
  local.receipt.executionEvidence.executionTarget = 'local'; reseal(local);
  assert.throws(() => verify(local), /full-session path/);
});

test('execution identifiers cannot become arbitrary filenames, URLs or altered session slugs', () => {
  const uuid = 'ef9c3844-0570-409c-baa6-7cc73d898476';
  for (const id of ['../' + uuid, 'sess_../' + uuid, 'sess_' + uuid + '?ref=main',
    'sess_' + uuid + '/..', 'cloud_' + uuid, 'sess_sess_' + uuid, uuid + 'extra',
    'sess_' + uuid.toUpperCase(), 'https://example.test/' + uuid]) {
    const f = fixture(); f.receipt.executionId = id; reseal(f);
    assert.throws(() => verify(f), /malformed.*KIRO_SPEC_EXECUTION_ID/);
  }
});

test('missing, duplicate and malformed provenance markers fail closed', () => {
  for (const name of ['KIRO_SPEC_EXECUTION_ID', 'KIRO_RECEIPT_COMMIT', 'KIRO_RECEIPT_SHA256']) {
    const missing = fixture(); missing.pr.body = missing.pr.body.split('\n').filter(line => !line.startsWith(name + ':')).join('\n');
    assert.throws(() => verify(missing), /missing, malformed or duplicate/);
    const duplicate = fixture(); duplicate.pr.body += duplicate.pr.body.split('\n').find(line => line.startsWith(name + ':')) + '\n';
    assert.throws(() => verify(duplicate), /duplicate/);
  }
  const invented = fixture(); invented.pr.body = invented.pr.body.replace(invented.receipt.executionId, '<actual-id>');
  assert.throws(() => verify(invented), /malformed/);
  const floating = fixture(); floating.pr.body = floating.pr.body.replace('c'.repeat(40), 'main');
  assert.throws(() => verify(floating), /malformed/);
});

test('canonical repository, human merge and actual immutable PR head remain mandatory', () => {
  for (const edit of [f => { f.pr.base.repo.full_name = 'Other/repo'; }, f => { f.pr.base.ref = 'other'; },
    f => { f.pr.html_url = 'https://github.com/Other/repo/pull/201'; }, f => { f.pr.merged = false; },
    f => { f.pr.merged_by.login = 'kiro-agent[bot]'; }, f => { f.pr.merged_at = null; },
    f => { f.pr.merge_commit_sha = 'main'; }, f => { f.pr.head.sha = 'd'.repeat(40); }]) {
    const f = fixture(); edit(f); assert.throws(() => verify(f), /Kiro proof HOLD/);
  }
});

test('raw receipt bytes, engine, PASS result, execution and inventory cannot be substituted', () => {
  const changed = fixture(); changed.receiptRaw += ' '; assert.throws(() => verify(changed), /raw trusted receipt bytes/);
  for (const edit of [r => { r.engine = 'codex'; }, r => { r.status = 'RUNNING'; },
    r => { r.inventorySha256 = ''; }, r => { r.specCommit = 'd'.repeat(40); }, r => { r.version = 2; }]) {
    const f = fixture(); edit(f.receipt); reseal(f); assert.throws(() => verify(f), /receipt engine/);
  }
  const other = fixture(); other.receipt.executionId = '66ad3804-d09b-482c-8a2c-4c0242acaf37';
  other.receiptRaw = JSON.stringify(other.receipt) + '\n';
  other.pr.body = other.pr.body.replace(/KIRO_RECEIPT_SHA256:[a-f0-9]{64}/, 'KIRO_RECEIPT_SHA256:' + sha(other.receiptRaw));
  assert.throws(() => verify(other), /actual execution/);
});

test('required per-row binding rejects another Goal, PR, row and path even with valid receipt digest', () => {
  for (const key of ['rowId', 'goalSha256', 'specPath', 'specPr']) {
    const f = fixture(); f.receipt.bindings[f.world.row_id][key] += 'changed'; reseal(f);
    assert.throws(() => verify(f), /binding mismatch/);
  }
  for (const bindings of [undefined, [], {}]) {
    const f = fixture(); f.receipt.bindings = bindings; reseal(f); assert.throws(() => verify(f), /bindings|canonical row/);
  }
});

test('Goal binding hashes exact registered Goal file bytes including one final newline', () => {
  const f = fixture();
  assert.equal(f.receipt.bindings[f.world.row_id].goalSha256, sha(f.world.goal + '\n'));
  assert.equal(verify(f).verified, true);
  for (const text of [f.world.goal, f.world.goal + '\n\n', f.world.goal + '\r\n']) {
    const wrong = fixture(); wrong.receipt.bindings[wrong.world.row_id].goalSha256 = sha(text); reseal(wrong);
    assert.throws(() => verify(wrong), /exact Goal.*binding mismatch/);
  }
});

test('each complete real merged document must match its individual Kiro PASS digest', () => {
  for (const filename of ['requirements.md', 'design.md', 'tasks.md']) {
    const key = 'specs/odin-bootcamp/synthetic-client/' + filename;
    const changed = fixture(); changed.documents[key] += 'Unreviewed edit.\n';
    assert.throws(() => verify(changed), /differs from actual Kiro review/);
    const missing = fixture(); delete missing.documents[key]; assert.throws(() => verify(missing), /incomplete/);
    const blocked = fixture(); blocked.receipt.paths[key].status = 'HOLD'; reseal(blocked);
    assert.throws(() => verify(blocked), /differs from actual Kiro review/);
  }
  const extra = fixture(); extra.documents['specs/other/tasks.md'] = 'Wrong scope';
  assert.throws(() => verify(extra), /another scope/);
});

test('reviewed documents cannot bind a Goal substring or a noncanonical identity line', () => {
  for (const alter of [f => f.documents[f.world.spec_path + '/requirements.md'].replace(f.world.goal, f.world.goal + ' Plus another task.'),
    f => f.documents[f.world.spec_path + '/requirements.md'].replace('Task Factory row: ', 'Historical Task Factory row: '),
    f => f.documents[f.world.spec_path + '/requirements.md'].replace(f.world.row_id.replace(/-/g, ''), 'f'.repeat(32))]) {
    const f = fixture(); const key = f.world.spec_path + '/requirements.md'; f.documents[key] = alter(f);
    f.receipt.paths[key].sha256 = sha(f.documents[key]); reseal(f);
    assert.throws(() => verify(f), /exact standalone Goal and canonical row/);
  }
  const crlf = fixture(); const key = crlf.world.spec_path + '/requirements.md'; crlf.documents[key] = crlf.documents[key].replace(/\n/g, '\r\n');
  crlf.receipt.paths[key].sha256 = sha(crlf.documents[key]); reseal(crlf); assert.equal(verify(crlf).verified, true);
});

test('repeat verification preserves all inputs and makes no gate or approval claims', () => {
  const f = fixture(); f.world.actualHumanFields = { Stage: 'Candidate', 'Approval ID': '', 'Pre-Record Gate': false };
  const before = JSON.stringify(f); const first = verify(f); const second = verify(f);
  assert.deepEqual(first, second); assert.equal(JSON.stringify(f), before);
  assert.equal(Object.hasOwn(first, 'recordingReady'), false); assert.equal(Object.hasOwn(first, 'approval'), false);
});

test('same source works as a direct Make Code prefix with Node crypto and no module wrapper', () => {
  const source = fs.readFileSync(path.join(__dirname, '../cloud/kiro-proof.js'), 'utf8');
  const f = fixture(); const context = { require, input: f };
  context.result = vm.runInNewContext('(function () {\n' + source +
    '\nreturn kiroProof.verifyKiroProof(input.world, input.pr, input.receiptRaw, input.documents, input.captureRaw);\n})()', context);
  assert.equal(context.result.verified, true);
  assert.equal(context.result.provenanceTrust, 'authenticated-publisher-receipt');
});
