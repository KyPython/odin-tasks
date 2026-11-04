'use strict';

// Pure functions shared by the existing Make scenario and offline contract checks.
// No credentials, network calls, repository writes, or human-gate promotions.
const REPOSITORY = 'KyPython/ai-governance';
const DATA_SOURCE_ID = '74aac26d-fcbb-45df-b996-561f76b9cec6';
const PAGE_ID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;
const SPEC_PATH = /^specs\/odin-bootcamp\/[a-z0-9]+(?:-[a-z0-9]+)*$/;

function fail(message) {
  throw new Error('Bootcamp handoff blocked: ' + message);
}

function jsonObject(value, label) {
  if (typeof value === 'string') {
    try { value = JSON.parse(value); } catch (_) { fail(label + ' is not valid JSON'); }
  }
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    fail(label + ' is not an object');
  }
  return value;
}

function richText(parts) {
  if (!Array.isArray(parts)) return '';
  return parts.map(function (part) {
    if (typeof part.plain_text === 'string') return part.plain_text;
    return typeof part.text?.content === 'string' ? part.text.content : '';
  }).join('');
}

function textProperty(properties, name, type) {
  return richText(properties[name]?.[type || 'rich_text']);
}

function selectProperty(properties, name) {
  return properties[name]?.select?.name || '';
}

function assertWorld(world) {
  world = jsonObject(world, 'selected world');
  if (!world || !PAGE_ID.test(world.row_id || '')) fail('invalid task row ID');
  if (!['Bootcamp', 'Dual-candidate'].includes(world.lane)) fail('ineligible lane');
  if (world.stage !== 'Candidate' || world.fit !== 'PASS' ||
      world.bootcamp_status !== 'World queued' || world.operator_pack !== 'PENDING') {
    fail('task is not an eligible queued candidate');
  }
  if (world.approval_id || world.approved_goal || world.build_issue) {
    fail('approved or already handed-off task');
  }
  for (const field of ['task', 'goal', 'source_evidence', 'spec_path', 'fingerprint']) {
    if (typeof world[field] !== 'string' || !world[field].trim()) {
      fail('missing ' + field);
    }
  }
  if (!SPEC_PATH.test(world.spec_path)) fail('invalid Bootcamp spec path');
  const spec = /^https:\/\/github\.com\/KyPython\/ai-governance\/pull\/([1-9][0-9]*)$/.exec(world.spec_pr || '');
  if (!spec || !Number.isSafeInteger(Number(spec[1]))) fail('missing canonical Kiro spec PR');
  world.spec_pr_number = Number(spec[1]);
  if (world.task.length > 220 || world.goal.length > 16000 ||
      world.source_evidence.length > 16000 || world.fingerprint.length > 500) {
    fail('task input exceeds handoff limits; do not truncate the contract');
  }
  return world;
}

function selectQueuedWorlds(value) {
  const response = jsonObject(value, 'Notion query');
  if (!Array.isArray(response.results)) fail('Notion results are missing');
  if (response.has_more !== false || response.next_cursor) {
    fail('Notion query is incomplete; fetch all pages before handing off');
  }
  const rows = [];
  const skipped = [];
  const seen = new Set();
  const fingerprints = new Map();
  for (const page of response.results) {
    if (page.in_trash || page.is_archived || page.archived) continue;
    const fingerprint = textProperty(page.properties || {}, 'Duplicate Fingerprint').trim().toLowerCase();
    if (fingerprint) fingerprints.set(fingerprint, (fingerprints.get(fingerprint) || 0) + 1);
  }
  for (const page of response.results) {
    const p = page.properties || {};
    const world = {
      row_id: page.id || '',
      row_url: page.url || '',
      task: textProperty(p, 'Task', 'title'),
      lane: selectProperty(p, 'Lane'),
      stage: selectProperty(p, 'Stage'),
      fit: selectProperty(p, 'Fit Gate'),
      bootcamp_status: selectProperty(p, 'Bootcamp Status'),
      operator_pack: selectProperty(p, 'Operator Pack Status'),
      goal: textProperty(p, 'Odin Goal'),
      approved_goal: textProperty(p, 'Approved Goal'),
      approval_id: textProperty(p, 'Approval ID'),
      source_evidence: textProperty(p, 'Source Evidence'),
      spec_path: textProperty(p, 'Spec Path').trim(),
      spec_pr: p['Spec PR']?.url || '',
      fingerprint: textProperty(p, 'Duplicate Fingerprint').trim().toLowerCase(),
      variation_axis: textProperty(p, 'Variation Axis'),
      apps: textProperty(p, 'Apps'),
      certification_alignment: textProperty(p, 'Certification Alignment'),
      certification_objective_coverage: textProperty(p, 'Certification Objective Coverage'),
      certification_evidence_level: selectProperty(p, 'Certification Evidence Level'),
      bootcamp_capability_ids: textProperty(p, 'Bootcamp Capability IDs'),
      human_transfer_test: textProperty(p, 'Human Transfer Test'),
      build_issue: p['Build Issue']?.url || ''
    };
    if (page.in_trash || page.is_archived || page.archived) {
      skipped.push({ row_id: world.row_id, reason: 'archived task' });
      continue;
    }
    try { assertWorld(world); } catch (error) {
      skipped.push({ row_id: world.row_id, reason: error.message });
      continue;
    }
    if (seen.has(world.row_id)) fail('duplicate row in Notion query');
    seen.add(world.row_id);
    if (fingerprints.get(world.fingerprint) > 1) {
      skipped.push({ row_id: world.row_id, reason: 'duplicate fingerprint requires existing-world recovery' });
      continue;
    }
    rows.push(world);
  }
  return { rows: rows, skipped: skipped, count: rows.length };
}

function worldMarker(world) {
  world = assertWorld(world);
  return 'ODIN_BOOTCAMP_ROW_ID:' + world.row_id;
}

function buildIssueRequest(world) {
  world = assertWorld(world);
  const marker = worldMarker(world);
  const body = [
    '<!-- ' + marker + ' -->',
    '# Synthetic Engineering Bootcamp World',
    'Task Factory row: https://app.notion.com/p/' + world.row_id.replace(/-/g, ''),
    'Spec path: ' + world.spec_path,
    'Human-merged Kiro spec PR: ' + world.spec_pr,
    'Duplicate fingerprint: ' + world.fingerprint,
    'Lane: ' + world.lane,
    '## Exact task Goal', world.goal,
    '## Source contract and verification evidence', world.source_evidence,
    '## Variation axis', world.variation_axis || 'Not specified',
    '## Applications', world.apps || 'Use the applications required by the source contract.',
    '## Human transfer test', world.human_transfer_test || 'Diagnose, implement, verify, and explain the task independently without solution hints.',
    '## Certification mapping', (world.certification_alignment || 'No supported mapping') + ' | Evidence level: ' + (world.certification_evidence_level || 'No supported mapping'),
    '## Certification objective/domain coverage', world.certification_objective_coverage || 'None supported at a finer granularity.',
    '## Human Rebuild capability IDs', world.bootcamp_capability_ids || 'No sealed capability mapping.',
    'These mappings describe the skills being tested. They are not solution instructions and do not establish mastery or certification readiness.',
    '## Starter boundary',
    'Build only the synthetic deterministic starter authorized by the source contract. ' +
      'Include setup, local fixtures, ordinary-path baseline coverage and reproducible commands. ' +
      'Do not provide the human diagnosis, final repair/refactor, decisive final tests, ' +
      'completed deliverable, answer key, hidden reference solution, credentials or private source.',
    'Publish the unchanged starter in one private GitHub repository under KyPython and verify its full 40-character commit SHA. ' +
      'Prepare one complete ODIN_STARTER_MANIFEST JSON object with source_repo, commit, branch, pr_title, ' +
      'pr_url (a real GitHub PR URL, or null if unavailable), and every exact UTF-8 starter file as {path, content_b64, mode}. ' +
      'Full private source bytes may be posted only to a verified private evidence destination. The canonical ai-governance queue is public: ' +
      'do not include private source bytes in that issue, its comments or the connector FINAL RESPONSE. On a public destination, emit only ' +
      'source pins, path/mode/hash inventory and a real private artifact pointer; keep missing authenticated byte review pending. ' +
      'A complete byte manifest must be emitted in the FINAL RESPONSE only when the connector destination is verified private; ' +
      'otherwise retain it as a private cloud artifact for the existing authenticated publication owner. ' +
      'Include ordinary-path baseline commands and actual outcomes. Open a real PR when push is available; verify the URL rather than reporting PR metadata. ' +
      'Reuse an existing pinned source repository and completed output on recovery; never regenerate a world because publication evidence is missing. ' +
      'A cloud task summary, local commit or PR title without published files and source identity is not a consumable artifact. ' +
      'If repository publication or a verified private evidence destination is unavailable, explicitly report the exact blocker and keep publication pending; do not expose private bytes or claim READY.',
    'Preserve the human diagnosis, implementation, verification, professional decisions and narration. ' +
      'Internal Bootcamp construction is not Mercor/Odin approval.'
  ].join('\n\n');
  if (body.length > 60000) fail('issue contract is too long');
  return {
    marker: marker,
    title: '[Bootcamp World] ' + world.task,
    body: body,
    payload: JSON.stringify({ title: '[Bootcamp World] ' + world.task, body: body }),
    search_query: 'repo:' + REPOSITORY + ' is:issue in:body "' + marker + '"'
  };
}

function verifyMergedSpec(world, value, files, requirements) {
  world = assertWorld(world);
  const pr = jsonObject(value, 'Kiro spec PR');
  if (pr.number !== world.spec_pr_number || pr.html_url !== world.spec_pr ||
      pr.base?.repo?.full_name !== REPOSITORY || pr.base?.ref !== 'main' ||
      pr.merged !== true || !pr.merged_at || pr.merged_by?.login !== 'KyPython' ||
      !/^[0-9a-f]{40}$/.test(pr.merge_commit_sha || '')) {
    fail('Kiro spec has not been merged by Ky into the canonical main branch');
  }
  const execution = /(?:^|\s)KIRO_SPEC_EXECUTION_ID:\s*([A-Za-z0-9][A-Za-z0-9_.:/-]{0,255})(?=\s|$)/m.exec(pr.body || '');
  if (!execution) fail('Kiro execution provenance is missing from the spec PR');
  if (typeof files === 'string') files = JSON.parse(files);
  if (!Array.isArray(files) || files.length > 100) fail('merged spec directory is incomplete');
  for (const name of ['requirements.md', 'design.md', 'tasks.md']) {
    const matches = files.filter(file => file.path === world.spec_path + '/' + name && file.type === 'file');
    if (matches.length !== 1 || !/^[0-9a-f]{40}$/.test(matches[0].sha || '')) fail('merged spec is missing ' + name);
  }
  if (typeof requirements !== 'string' || requirements.length > 50000 ||
      !requirements.replace(/\r\n/g, '\n').split(/\n[ \t]*\n/).some(paragraph => paragraph === world.goal) ||
      !requirements.split(/\r?\n/).some(line => line === 'Task Factory row: https://app.notion.com/p/' + world.row_id.replace(/-/g, ''))) {
    fail('merged requirements do not bind the exact Goal and canonical Notion row');
  }
  return { merge_commit: pr.merge_commit_sha, execution_id: execution[1], spec_pr: world.spec_pr };
}

function exactMarker(body, marker) {
  // UUID markers contain only safe regex characters. Require a boundary so prefix matches cannot win.
  const expression = new RegExp('(?:^|\\s|<!--\\s*)' + marker + '(?=\\s|\\||-->|$)');
  return expression.test(String(body || ''));
}

function validateIssue(issue) {
  if (!issue || !Number.isSafeInteger(issue.number) || issue.number <= 0 ||
      !['open', 'closed'].includes(issue.state) || issue.pull_request ||
      issue.html_url !== 'https://github.com/' + REPOSITORY + '/issues/' + issue.number) {
    fail('invalid or wrong-repository issue evidence');
  }
  return issue;
}

function resolveIssue(world, value, canonicalIssueNumber) {
  const request = buildIssueRequest(world);
  const search = jsonObject(value, 'GitHub marker search');
  if (search.incomplete_results !== false || !Array.isArray(search.items) ||
      !Number.isSafeInteger(search.total_count) || search.total_count < 0 ||
      search.total_count !== search.items.length) {
    fail('GitHub marker search is incomplete; fetch all results before creating anything');
  }
  const matches = search.items.filter(function (issue) {
    return !issue.pull_request && exactMarker(issue.body, request.marker);
  }).map(validateIssue);
  let existing;
  if (canonicalIssueNumber !== undefined && canonicalIssueNumber !== null) {
    if (!Number.isSafeInteger(canonicalIssueNumber)) fail('invalid canonical issue number');
    existing = matches.find(function (issue) { return issue.number === canonicalIssueNumber; });
    if (!existing) fail('canonical issue is absent from complete exact-marker evidence');
  } else {
    if (matches.length > 1) fail('multiple exact-marker issues require canonical recovery');
    existing = matches[0];
  }
  if (existing) {
    return {
      action: 'recover',
      existing: true,
      issue_number: existing.number,
      issue_url: existing.html_url,
      issue_state: existing.state,
      marker: request.marker,
      comment_allowed: existing.state === 'open'
    };
  }
  return { action: 'create', existing: false, payload: request.payload, marker: request.marker };
}

function resolveIssueFromInventory(world, value, canonicalIssueNumber) {
  const inventory = jsonObject(value, 'GitHub all-state issue inventory');
  if (inventory.complete !== true || !Array.isArray(inventory.issues) ||
      inventory.has_more === true || inventory.next_cursor) {
    fail('GitHub all-state issue inventory is incomplete');
  }
  // The list endpoint avoids the Search API's indexing lag after issue creation.
  return resolveIssue(world, {
    items: inventory.issues, total_count: inventory.issues.length, incomplete_results: false
  }, canonicalIssueNumber);
}

function verifyCreatedIssue(world, value) {
  const issue = validateIssue(jsonObject(value, 'GitHub created issue'));
  if (!exactMarker(issue.body, worldMarker(world))) fail('created issue lost the task marker');
  return issue;
}

function planCodexComment(world, value, comments, complete) {
  world = assertWorld(world);
  const issue = validateIssue(jsonObject(value, 'GitHub comment target'));
  if (typeof comments === 'string') {
    try { comments = JSON.parse(comments); } catch (_) { fail('issue comments are not valid JSON'); }
  }
  if (!exactMarker(issue.body, worldMarker(world))) fail('comment target belongs to another task');
  if (complete !== true || !Array.isArray(comments)) fail('issue comment history is incomplete');
  if (issue.state === 'closed') return { action: 'skip', reason: 'existing issue is closed' };
  const marker = 'ODIN_BOOTCAMP_CODEX_ROW_ID:' + world.row_id;
  const prior = comments.some(function (comment) {
    const author = comment.user?.login || comment.author?.login || '';
    return /@codex\b/i.test(String(comment.body || '')) ||
      exactMarker(comment.body, marker) || author === 'chatgpt-codex-connector';
  });
  if (prior) return { action: 'skip', reason: 'Codex handoff or result already exists' };
  const body = '<!-- ' + marker + ' -->\n' +
    '@codex Build only the synthetic starter world defined in this issue. Complete the publication contract: ' +
    'one private KyPython starter repository, exact full commit SHA, a real PR URL when available, and one complete ' +
    'ODIN_STARTER_MANIFEST containing source_repo, commit, branch, pr_title, pr_url and every file ' +
    'as {path, content_b64, mode}, plus actual ordinary-path baseline outcomes. The canonical queue is PUBLIC: ' +
    'keep private source bytes out of public issue comments and connector FINAL RESPONSE. Emit the complete byte manifest ' +
    'in FINAL RESPONSE only after verifying a private connector destination; otherwise retain it in a real private cloud ' +
    'artifact and return only source pins/hash inventory/private pointer or an honest access blocker. Reuse prior completed output; never ' +
    'substitute a cloud task summary or PR metadata for published bytes. If publication is blocked, say so and ' +
    'leave readiness pending. Stop before the human diagnosis, final repair/refactor, ' +
    'decisive final tests, completed deliverable or hidden solution.';
  return { action: 'comment', payload: JSON.stringify({ body: body }), marker: marker };
}

function writebackPayload(world, value, date) {
  const issue = validateIssue(jsonObject(value, 'GitHub write-back target'));
  if (!exactMarker(issue.body, worldMarker(world))) fail('write-back issue belongs to another task');
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date || '') ||
      new Date(date + 'T00:00:00Z').toISOString().slice(0, 10) !== date) {
    fail('invalid evidence date');
  }
  // Preserve Lane, Stage, approval/pay/fit, all human gates and review judgments.
  return JSON.stringify({ properties: {
    'Build Issue': { url: issue.html_url },
    'Bootcamp Status': { select: { name: 'World building' } },
    'Last Updated': { date: { start: date } }
  } });
}

const bootcampBuilder = {
  REPOSITORY: REPOSITORY, DATA_SOURCE_ID: DATA_SOURCE_ID, richText: richText,
  selectQueuedWorlds: selectQueuedWorlds, assertWorld: assertWorld, worldMarker: worldMarker,
  buildIssueRequest: buildIssueRequest, resolveIssue: resolveIssue,
  verifyMergedSpec: verifyMergedSpec,
  resolveIssueFromInventory: resolveIssueFromInventory,
  verifyCreatedIssue: verifyCreatedIssue, planCodexComment: planCodexComment,
  writebackPayload: writebackPayload
};
if (typeof module !== 'undefined' && module.exports) module.exports = bootcampBuilder;
