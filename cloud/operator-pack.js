'use strict';

// Shared by the existing Make reviewers. Keep review state separate from capture state.
const crypto = require('node:crypto');
const PRIMARY = '### Recording sequence — follow this order';
function object(value) {
  if (typeof value === 'string') return JSON.parse(value);
  if (!value || typeof value !== 'object') throw new Error('Missing API response');
  return value;
}
function text(value) {
  return (value || []).map(x => x.plain_text ?? x.text?.content ?? '').join('');
}
function rich(value) {
  const parts = [];
  for (let i = 0; i < value.length; i += 1800) parts.push({ type: 'text', text: { content: value.slice(i, i + 1800) } });
  return parts;
}
function managedContent(block) {
  const content = text(block?.paragraph?.rich_text);
  const match = content.match(/^(TASKWORK_OPERATOR_PACK:[a-f0-9-]{36})\nREVISION:([a-f0-9]{64})\nCONTENT_SHA256:([a-f0-9]{64})\n([\s\S]*)$/);
  if (!match || block.has_children || crypto.createHash('sha256').update(match[4]).digest('hex') !== match[3]) {
    throw new Error('Managed pack ownership cannot be verified; preserve manual edits and reconcile');
  }
  return { revision: match[2], content };
}
function selectRows(value, mode) {
  const response = object(value);
  if (response.has_more) throw new Error('Incomplete Task Factory query; paginate before reviewing');
  if (!Array.isArray(response.results)) throw new Error('Missing Task Factory results');
  const rows = [];
  for (const page of response.results) {
    if (page.archived || page.in_trash) continue;
    const p = page.properties || {};
    const select = key => p[key]?.select?.name || '';
    const pack = select('Operator Pack Status');
    if (pack !== 'PENDING' || select('Fit Gate') !== 'PASS') continue;
    const lane = select('Lane');
    const approval = text(p['Approval ID']?.rich_text);
    const approved = text(p['Approved Goal']?.rich_text);
    const goal = text(p['Odin Goal']?.rich_text);
    const bootcamp = ['Bootcamp', 'Dual-candidate'].includes(lane) &&
      select('Stage') === 'Candidate' && select('Bootcamp Status') === 'World building' && !approval && !approved;
    const odin = ['', 'Odin monetization'].includes(lane) && approval && approved && approved === goal &&
      ['Environment building', 'Ready to record'].includes(select('Stage'));
    if (!bootcamp && !odin) continue;
    const issue = p['Build Issue']?.url || '';
    const pr = p['Build PR']?.url || '';
    const match = issue.match(/^https:\/\/github\.com\/KyPython\/ai-governance\/issues\/(\d+)$/);
    if (mode === 'manifest' && (!match || pr)) continue;
    if (mode === 'pr' && !/^https:\/\/github\.com\/KyPython\/ai-governance\/pull\/\d+$/.test(pr)) continue;
    rows.push({ row_id: page.id, row_url: page.url, task: text(p.Task?.title), goal: bootcamp ? goal : approved,
      apps: text(p.Apps?.rich_text), approval_id: approval, spec_path: text(p['Spec Path']?.rich_text),
      issue_number: match ? Number(match[1]) : null, build_pr: pr, lane: bootcamp ? 'Bootcamp' : 'Odin monetization',
      starter_repository: p['Starter Repository']?.url || '', starter_commit: text(p['Starter Commit']?.rich_text),
      cloud_url: p['Cloud Preparation URL']?.url || '', cloud_commit: text(p['Cloud Preparation Commit']?.rich_text) });
  }
  return { rows, count: rows.length };
}
function planContent(input) {
  const blocks = object(input.blocks);
  if (blocks.has_more || !Array.isArray(blocks.results)) throw new Error('Incomplete page block read; do not append');
  const marker = 'TASKWORK_OPERATOR_PACK:' + input.row_id;
  const owned = blocks.results.filter(block => text(block.paragraph?.rich_text).startsWith(marker + '\n'));
  if (owned.length > 1) throw new Error('Multiple managed packs; reconcile before publishing');
  if (owned[0]) managedContent(owned[0]);
  // Existing native scripts are human-readable finalized material, never append a competing pack.
  const native = blocks.results.filter(b => b.type === 'heading_3' && text(b.heading_3?.rich_text) === PRIMARY.slice(4));
  if (native.length) throw new Error('Finalized native route exists; use the targeted publisher');
  let raw = typeof input.raw === 'string' ? input.raw.trim().replace(/^```(?:json)?\s*/i, '').replace(/\s*```$/, '') : input.raw;
  let review;
  try { review = object(raw); } catch { review = { verdict: 'BLOCK', blocker: 'Invalid reviewer JSON' }; }
  const pack = String(review.operator_pack || '');
  const pin = /^https:\/\/github\.com\/KyPython\/[A-Za-z0-9_.-]+$/.test(input.starter_repository || '') && /^[a-f0-9]{40}$/.test(input.starter_commit || '');
  const pass = review.verdict === 'PASS' && pin && pack.split(PRIMARY).length === 2 && pack.length < 100000;
  const blocker = pass ? '' : String(review.blocker || (!pin ? 'Published starter repository and full verified commit are required' : 'One exact primary route is required'));
  const revision = crypto.createHash('sha256').update(JSON.stringify([input.row_id, input.source_ref, input.starter_repository, input.starter_commit, pass, pack, blocker])).digest('hex');
  const body = 'Source review only. Recorder, recording QA and submission checks require live evidence.\n\n' + (pass ? pack : 'BLOCKER: ' + blocker);
  const content = marker + '\nREVISION:' + revision + '\nCONTENT_SHA256:' + crypto.createHash('sha256').update(body).digest('hex') + '\n' + body;
  const paragraph = { rich_text: rich(content) };
  const block = owned[0];
  const unchanged = !!block && text(block.paragraph?.rich_text) === content;
  return { pass, blocker, revision, block_id: block?.id || '',
    content_method: unchanged ? 'GET' : 'PATCH',
    content_url: block ? '/v1/blocks/' + block.id : '/v1/blocks/' + input.row_id + '/children',
    content_body: unchanged ? '' : JSON.stringify(block ? { paragraph } : { children: [{ object: 'block', type: 'paragraph', paragraph }] }) };
}
function propertyWrite(input) {
  const result = object(input.saved);
  const savedBlock = result.results?.[0] || result;
  const blockId = savedBlock.id;
  if (!/^[a-f0-9-]{36}$/.test(blockId || '')) throw new Error('Pack content was not durably saved');
  if ((input.block_id && input.block_id !== blockId) || managedContent(savedBlock).revision !== input.revision) {
    throw new Error('Saved pack content does not match the delivered revision');
  }
  const p = { 'Operator Pack Block ID': { rich_text: rich(blockId) }, 'Operator Pack Revision': { rich_text: rich(input.revision) },
    'Operator Pack Status': { select: { name: input.pass ? 'READY' : 'BLOCKED' } },
    'Environment Review Gate': { checkbox: !!input.pass }, 'No-Solution-Leak Gate': { checkbox: !!input.pass },
    'Operator Pack Evidence': { rich_text: rich('Source review ' + (input.pass ? 'PASS' : 'BLOCKED') + ' | ' + input.source_ref + ' | ' + (input.blocker || 'Actual Recorder checks remain pending')) } };
  // Do not reset prior human observation, hours, review, recording, or submission fields.
  return { property_body: JSON.stringify({ properties: p }) };
}
module.exports = { PRIMARY, object, text, rich, selectRows, planContent, propertyWrite };
