'use strict';
// One Kiro spec owner, with separate Odin approval and internal Bootcamp eligibility.
function parse(value) { return typeof value === 'string' ? JSON.parse(value) : value; }
function text(parts) { return (parts || []).map(p => p.plain_text ?? p.text?.content ?? '').join(''); }
function approvedRows(value) {
  const response = parse(value);
  if (!response || response.has_more !== false || response.next_cursor || !Array.isArray(response.results)) throw new Error('Incomplete task ledger');
  const rows = [];
  for (const page of response.results) {
    const p = page.properties || {};
    const approvedGoal = text(p['Approved Goal']?.rich_text), approval = text(p['Approval ID']?.rich_text);
    const candidateGoal = text(p['Odin Goal']?.rich_text), lane = p.Lane?.select?.name || '';
    const odin = p.Stage?.select?.name === 'Odin approved' && ['', 'Odin monetization'].includes(lane) &&
      approval && approvedGoal && approvedGoal === candidateGoal;
    const bootcamp = p.Stage?.select?.name === 'Candidate' && ['Bootcamp', 'Dual-candidate'].includes(lane) &&
      p['Bootcamp Status']?.select?.name === 'World queued' && p['Operator Pack Status']?.select?.name === 'PENDING' &&
      !approval && !approvedGoal && !p['Build Issue']?.url && candidateGoal;
    if (page.archived || page.in_trash || p['Fit Gate']?.select?.name !== 'PASS' || p['Kiro Issue']?.url ||
      p['Spec PR']?.url || p['Build Issue']?.url || p['Build PR']?.url || p['Starter Repository']?.url || text(p['Starter Commit']?.rich_text) || !(odin || bootcamp)) continue;
    const goal = odin ? approvedGoal : candidateGoal;
    const sourceEvidence = text(p['Source Evidence']?.rich_text);
    if (bootcamp && !sourceEvidence.trim()) continue;
    const context = { source_evidence: sourceEvidence, variation_axis: text(p['Variation Axis']?.rich_text),
      human_transfer_test: text(p['Human Transfer Test']?.rich_text), professional_judgment: text(p['Professional Judgment']?.rich_text) };
    if ([goal, ...Object.values(context)].some(value => value.length > 16000)) throw new Error('Kiro input exceeds complete-contract limit');
    const path = text(p['Spec Path']?.rich_text);
    if (!/^specs\/[a-z0-9-]+(?:\/[a-z0-9-]+)*$/.test(path)) throw new Error('Invalid approved spec path');
    if (bootcamp && !/^specs\/odin-bootcamp\/[a-z0-9]+(?:-[a-z0-9]+)*$/.test(path)) throw new Error('Invalid Bootcamp spec path');
    rows.push({ row_id: page.id, row_url: page.url, task: text(p.Task?.title), approval_id: approval, goal, spec_path: path,
      workflow_lane: odin ? 'odin' : 'bootcamp', original_stage: p.Stage.select.name,
      writeback_stage: odin ? 'Kiro spec requested' : p.Stage.select.name, ...context });
  }
  return { rows };
}
function resolveApproved(input) {
  const pages = [input.page1, input.page2, input.page3].map(parse);
  if (pages.some(p => !Array.isArray(p)) || pages[2].length >= 100) throw new Error('Incomplete all-state issue inventory');
  const bootcamp = input.workflow_lane === 'bootcamp';
  const marker = (bootcamp ? 'ODIN_BOOTCAMP_SPEC_ROW_ID:' : 'ODIN_ROW_ID:') + input.row_id;
  const matches = pages.flat().filter(i => !i.pull_request && new RegExp('(?:^|\\s|<!--\\s*)' + marker + '(?=\\s|-->|$)').test(i.body || ''));
  if (matches.length > 1) throw new Error('Ambiguous canonical spec issue');
  const existing = matches[0];
  if (existing && existing.html_url !== 'https://github.com/KyPython/ai-governance/issues/' + existing.number) throw new Error('Wrong issue repository');
  const body = ['<!-- ' + marker + ' -->', bootcamp ? '## Internal Bootcamp candidate; Odin approval remains pending' : '## Externally approved task', '**Notion row:** ' + input.row_url,
    '**Approval ID:** ' + (input.approval_id || 'Empty; internal practice only'), '**Spec path:** `' + input.spec_path + '`', '### Exact task Goal', input.goal,
    '### Source contract and verification evidence', input.source_evidence || 'No additional source evidence supplied; do not invent it.',
    '### Variation axis', input.variation_axis || 'No variation supplied.',
    '### Existing human transfer requirement', input.human_transfer_test || 'Not specified; human evidence remains unassessed.',
    '### Existing professional judgment', input.professional_judgment || 'Human decision pending; do not invent it.',
    '## Kiro contract', 'Write a spec-only PR at `' + input.spec_path + '/` with requirements.md, design.md and tasks.md. ' +
    'Use numbered testable requirements. Assign each implementation task a coder and a different reviewer. Include ' + marker + ' and Relates to #<this issue number> in the PR body. ' +
    'Do not implement the human task solution, diagnosis, final repair, decisive tests, completed deliverable or answer key. ' +
    'Include the exact Goal and Notion row identity in requirements.md. Record your actual Kiro execution identifier as KIRO_SPEC_EXECUTION_ID:<actual-id> in the PR body; never invent one. ' +
    'Keep the Goal as a standalone paragraph and include the literal line Task Factory row: https://app.notion.com/p/' + input.row_id.replace(/-/g, '') + '. ' +
    'After an actual completed Kiro review, the existing authenticated preparation publisher captures the actual CLI output and publishes one private cloud/kiro-receipts/<actual-id>.json and paired .capture.txt at a full immutable preparation-repo commit. ' +
    'The receipt binds actual execution target, exact row/Goal/path/PR and every spec document hash. The publisher adds KIRO_RECEIPT_COMMIT:<actual40> and KIRO_RECEIPT_SHA256:<actual64> as unique PR-body lines. ' +
    'Missing captured evidence, spec PASS, private receipt or human merge remains HOLD; never manufacture a PASS receipt. ' +
    'Downstream automation prepares only the synthetic starter after the real Kiro spec passes and Ky merges the PR. Human judgment and recorded work remain human.', 'Relates to #12.'].join('\n\n');
  if (body.length > 60000) throw new Error('Kiro issue exceeds complete-contract limit');
  return { existing: !!existing, existing_url: existing?.html_url || '',
    payload: JSON.stringify({ title: (bootcamp ? '[Bootcamp Spec] ' : '[Odin Spec] ') + input.task, body, labels: ['kiro'] }) };
}
module.exports = { approvedRows, resolveApproved };
