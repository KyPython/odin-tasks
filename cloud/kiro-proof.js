'use strict';

// Integrity and identity verification for an authenticated publisher's Kiro receipt.
// The publisher must capture the actual authenticated Kiro session/output before
// recording PASS. A session ID or this normalized receipt alone cannot independently
// prove engine execution. Fetch the derived receipt through the existing private
// GitHub connection at its immutable commit; never accept an arbitrary URL.
// This helper performs no I/O and grants no human, recording or paid-task gates.
const kiroProofCrypto = require('node:crypto');
const KIRO_PROOF_SPEC_REPOSITORY = 'KyPython/ai-governance';
const KIRO_PROOF_RECEIPT_REPOSITORY = 'KyPython/odin-recording-preparation';
const KIRO_PROOF_UUID = /^[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}$/;
const KIRO_PROOF_EXECUTION_PATTERN = '(?:sess_)?[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}';
const KIRO_PROOF_SHA40 = /^[a-f0-9]{40}$/;
const KIRO_PROOF_SHA256 = /^[a-f0-9]{64}$/;
const KIRO_PROOF_DOC_NAMES = ['requirements.md', 'design.md', 'tasks.md'];

function kiroProofFail(message) {
  throw new Error('Kiro proof HOLD: ' + message);
}

function kiroProofObject(value, label) {
  if (typeof value === 'string') {
    try { value = JSON.parse(value); } catch (_) { kiroProofFail(label + ' is not valid JSON'); }
  }
  if (!value || typeof value !== 'object' || Array.isArray(value)) kiroProofFail(label + ' is not an object');
  return value;
}

function kiroProofDigest(value) {
  return kiroProofCrypto.createHash('sha256').update(value, 'utf8').digest('hex');
}

function kiroProofMarker(body, name, pattern) {
  const occurrences = body.match(new RegExp('\\b' + name + '[ \\t]*:', 'g')) || [];
  const expression = new RegExp('(?:^|\\n)[ \\t]*(?:<!--[ \\t]*)?' + name +
    ':[ \\t]*(' + pattern + ')[ \\t]*(?:-->)?[ \\t]*(?=\\r?\\n|$)', 'g');
  const matches = [...body.matchAll(expression)];
  if (occurrences.length !== 1 || matches.length !== 1) kiroProofFail('missing, malformed or duplicate ' + name);
  return matches[0][1];
}

function parseTrustedReceiptLocation(value) {
  const pr = kiroProofObject(value, 'spec PR');
  if (!Number.isSafeInteger(pr.number) || pr.number <= 0 ||
      pr.html_url !== 'https://github.com/' + KIRO_PROOF_SPEC_REPOSITORY + '/pull/' + pr.number ||
      pr.base?.repo?.full_name !== KIRO_PROOF_SPEC_REPOSITORY || pr.base?.ref !== 'main') {
    kiroProofFail('wrong canonical specification repository or PR');
  }
  if (typeof pr.body !== 'string' || pr.body.length > 60000) kiroProofFail('missing or oversized PR provenance body');
  const executionId = kiroProofMarker(pr.body, 'KIRO_SPEC_EXECUTION_ID', KIRO_PROOF_EXECUTION_PATTERN);
  const receiptCommit = kiroProofMarker(pr.body, 'KIRO_RECEIPT_COMMIT', '[a-f0-9]{40}');
  const receiptSha256 = kiroProofMarker(pr.body, 'KIRO_RECEIPT_SHA256', '[a-f0-9]{64}');
  const path = 'cloud/kiro-receipts/' + executionId + '.json';
  const endpoint = '/repos/' + KIRO_PROOF_RECEIPT_REPOSITORY + '/contents/' + path + '?ref=' + receiptCommit;
  const capturePath = 'cloud/kiro-receipts/' + executionId + '.capture.txt';
  const captureEndpoint = '/repos/' + KIRO_PROOF_RECEIPT_REPOSITORY + '/contents/' + capturePath + '?ref=' + receiptCommit;
  return { repository: KIRO_PROOF_RECEIPT_REPOSITORY, executionId, receiptCommit, receiptSha256,
    path, endpoint, url: 'https://api.github.com' + endpoint,
    capturePath, captureEndpoint, captureUrl: 'https://api.github.com' + captureEndpoint };
}

function verifyKiroProof(value, prValue, receiptRaw, documentsValue, captureRaw) {
  const world = kiroProofObject(value, 'world');
  const pr = kiroProofObject(prValue, 'spec PR');
  const location = parseTrustedReceiptLocation(pr);
  if (!KIRO_PROOF_UUID.test(world.row_id || '') || typeof world.goal !== 'string' ||
      !world.goal.trim() || world.goal.length > 16000 ||
      !/^specs\/[a-z0-9-]+(?:\/[a-z0-9-]+)*$/.test(world.spec_path || '') ||
      world.spec_pr !== pr.html_url) {
    kiroProofFail('world identity, exact Goal, spec path or PR does not match');
  }
  if (pr.merged !== true || typeof pr.merged_at !== 'string' ||
      !Number.isFinite(Date.parse(pr.merged_at)) || pr.merged_by?.login !== 'KyPython' ||
      !KIRO_PROOF_SHA40.test(pr.merge_commit_sha || '') || !KIRO_PROOF_SHA40.test(pr.head?.sha || '')) {
    kiroProofFail('specification lacks an actual Ky merge and immutable reviewed head');
  }
  if (typeof receiptRaw !== 'string' || !receiptRaw || receiptRaw.length > 1000000 ||
      kiroProofDigest(receiptRaw) !== location.receiptSha256) {
    kiroProofFail('raw trusted receipt bytes do not match the PR digest');
  }
  const receipt = kiroProofObject(receiptRaw, 'trusted receipt');
  if (receipt.version !== 1 || receipt.engine !== 'kiro' || receipt.status !== 'PASS' ||
      receipt.executionId !== location.executionId || !KIRO_PROOF_SHA256.test(receipt.inventorySha256 || '') ||
      receipt.specCommit !== pr.head.sha || !KIRO_PROOF_SHA40.test(receipt.specCommit || '')) {
    kiroProofFail('receipt engine, actual execution, PASS state, inventory or reviewed head mismatch');
  }
  const evidence = kiroProofObject(receipt.executionEvidence, 'captured execution evidence');
  if (evidence.source !== 'captured-kiro-cli' || !['local', 'cloud'].includes(evidence.executionTarget) ||
      evidence.capturePath !== location.capturePath || !KIRO_PROOF_SHA256.test(evidence.captureSha256 || '') ||
      typeof captureRaw !== 'string' || !captureRaw.trim() || captureRaw.length > 1000000 ||
      kiroProofDigest(captureRaw) !== evidence.captureSha256) {
    kiroProofFail('captured CLI source, target, full-session path or exact capture bytes mismatch');
  }
  const bindings = kiroProofObject(receipt.bindings, 'receipt bindings');
  if (!Object.hasOwn(bindings, world.row_id)) kiroProofFail('receipt has no canonical row binding');
  const binding = kiroProofObject(bindings[world.row_id], 'selected row binding');
  // The registered Goal file preserves the exact native Goal plus one final LF.
  // Bind those file bytes, matching registration and the captured Kiro inventory.
  if (binding.rowId !== world.row_id || binding.goalSha256 !== kiroProofDigest(world.goal + '\n') ||
      binding.specPath !== world.spec_path || binding.specPr !== world.spec_pr) {
    kiroProofFail('receipt row, exact Goal, spec path or PR binding mismatch');
  }
  const paths = kiroProofObject(receipt.paths, 'reviewed paths');
  const documents = kiroProofObject(documentsValue, 'actual merged specification documents');
  const expectedPaths = KIRO_PROOF_DOC_NAMES.map(name => world.spec_path + '/' + name);
  if (Object.keys(documents).length !== expectedPaths.length ||
      Object.keys(documents).some(path => !expectedPaths.includes(path))) {
    kiroProofFail('actual merged document read is incomplete or includes another scope');
  }
  const specFiles = {};
  for (const path of expectedPaths) {
    const content = documents[path];
    if (typeof content !== 'string' || !content.trim() || content.length > 50000) {
      kiroProofFail('missing, truncated or oversized ' + path);
    }
    if (!Object.hasOwn(paths, path)) kiroProofFail('receipt did not review ' + path);
    const reviewed = kiroProofObject(paths[path], 'reviewed document');
    if (reviewed.status !== 'PASS' || !KIRO_PROOF_SHA256.test(reviewed.sha256 || '') ||
        kiroProofDigest(content) !== reviewed.sha256) {
      kiroProofFail('merged document differs from actual Kiro review: ' + path);
    }
    specFiles[path] = reviewed.sha256;
  }
  const requirements = documents[world.spec_path + '/requirements.md'].replace(/\r\n/g, '\n');
  if (!requirements.split(/\n[ \t]*\n/).includes(world.goal.replace(/\r\n/g, '\n')) ||
      !requirements.split('\n').includes('Task Factory row: https://app.notion.com/p/' + world.row_id.replace(/-/g, ''))) {
    kiroProofFail('requirements lack the exact standalone Goal and canonical row identity line');
  }
  return { verified: true, provenanceTrust: 'authenticated-publisher-receipt',
    executionId: receipt.executionId, executionTarget: evidence.executionTarget,
    capturePath: location.capturePath, captureSha256: evidence.captureSha256,
    inventorySha256: receipt.inventorySha256,
    specCommit: receipt.specCommit, mergeCommit: pr.merge_commit_sha,
    receiptCommit: location.receiptCommit, receiptSha256: location.receiptSha256,
    receiptPath: location.path, specFiles };
}

const kiroProof = { parseTrustedReceiptLocation, verifyKiroProof };
if (typeof module !== 'undefined' && module.exports) module.exports = kiroProof;
