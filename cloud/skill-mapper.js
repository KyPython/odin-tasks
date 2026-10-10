'use strict';
// Existing metadata owner only; never reset attempt or recording evidence.
const crypto = require('node:crypto');
const CAPABILITY_AUTHORITY = {"repository":"https://github.com/KyLamportLogic/human-rebuild-bootcamp","commit":"c9e0db70705c548c6b9ef30a98154aa180c741ad","path":"ideal-ssot/capability-matrix.json","blobSha":"74dfde6bdcab1d9b2475b7f8e9371b32204ef5f1","sha256":"3fdfcfb3ae296da288a50771c355ec5ab9af95d0dabcd63015c7ce687a87acc5","version":"4.1.0","capabilityIds":["architecture-tradeoff-defense","manual-technical-screen-retrieval","asymptotic-complexity-mastery","alternative-design-comparison","invariant-driven-testing","space-time-tradeoff-choice","abstraction-boundary-design","ai-side-effect-governance","fail-close-kill-switch","coding-agent-governance","audit-hash-traceability","systems-thinking-os","oci-container-runtime","host-agnostic-product-code","single-entrypoint-local-dev","shared-platform-boundaries","intent-fidelity-bindings","directory-purpose-minimalism","visitor-copy-integrity","law-propagation-sync","human-agency-boundary","formative-struggle-protocol","professional-docs-pack","provider-sdk-official-clients","dependency-decision-discipline","fleet-safe-rate-limits","agentic-security-defense-basics","learnable-workflow-observability","error-budget-slo-gate","secrets-jit-no-commit","test-pyramid-tdd","ci-cd-fail-closed-pipeline","github-issues-prs-loop","security-baseline-score","container-hardening-score","dependency-floor-score","runtime-path-fidelity-score","auth-coverage-score"]};
function capabilityIds(raw) {
  const ids = typeof raw === 'string' ? JSON.parse(raw) : raw;
  if (!Array.isArray(ids) || ids.length !== CAPABILITY_AUTHORITY.capabilityIds.length ||
      new Set(ids).size !== ids.length || ids.some(id => !CAPABILITY_AUTHORITY.capabilityIds.includes(id))) {
    throw new Error('Capability IDs do not match the verified cloud matrix; refresh the authority before writing');
  }
  return ids;
}

const LEVELS = new Set(['Objective-level', 'Credential/domain-level', 'No supported mapping']);
const MARKER = 'Skill Mapping Revision';
const MAP_FIELDS = ['Certification Alignment', 'Certification Objective Coverage', 'Certification Evidence Level', 'Bootcamp Capability IDs', 'Human Transfer Test', 'Skills Practiced'];
function object(value) {
  const result = typeof value === 'string' ? JSON.parse(value) : value;
  if (!result || typeof result !== 'object') throw new Error('Missing native Notion object');
  return result;
}
function richText(parts) { return (parts || []).map(p => p.plain_text ?? p.text?.content ?? '').join(''); }
function value(page, name) {
  const prop = page.properties?.[name];
  return prop?.select ? prop.select.name || '' : richText(prop?.rich_text || prop?.title);
}
function hash(values) { return crypto.createHash('sha256').update(JSON.stringify(values)).digest('hex'); }
function sourceDigest(page) { return hash([page.id, ...['Task', 'Odin Goal', 'Approved Goal', 'Source Evidence', 'Professional Judgment', 'Skill Gap Focus'].map(n => value(page, n))]); }
function mappingDigest(page) { return hash(MAP_FIELDS.map(n => value(page, n))); }
function revision(page) { return 'SKILL_MAPPING_V1:' + sourceDigest(page) + ':' + mappingDigest(page); }
function complete(page) {
  const level = value(page, 'Certification Evidence Level');
  const cert = value(page, 'Certification Alignment').trim();
  return LEVELS.has(level) && !!value(page, 'Human Transfer Test').trim() &&
    (level === 'No supported mapping' ? !cert : !!cert) &&
    (level !== 'Objective-level' || !!value(page, 'Certification Objective Coverage').trim());
}
function selectMappings(input) {
  const q = object(input);
  if (!Array.isArray(q.results) || q.has_more || q.next_cursor) throw new Error('Incomplete Task Factory mapping inventory; paginate before mapping');
  const rows = [], held = [];
  for (const page of q.results) {
    if (page.archived || page.in_trash || page.is_archived || value(page, 'Stage') === 'Rejected') continue;
    if (!/^[a-f0-9-]{36}$/.test(page.id || '') || !value(page, 'Task').trim()) continue;
    const marker = value(page, MARKER);
    if (marker && marker !== revision(page)) { held.push({ page_id: page.id, reason: 'Source or mapping changed; preserve manual edits and reconcile' }); continue; }
    // Empty capabilities and an explicit unsupported certification mapping are valid outcomes.
    if (complete(page)) continue;
    const row = {
      page_id: page.id, source_digest: sourceDigest(page), task: value(page, 'Task'), stage: value(page, 'Stage'), lane: value(page, 'Lane'),
      goal: value(page, 'Odin Goal'), approved_goal: value(page, 'Approved Goal'), source_evidence: value(page, 'Source Evidence'),
      professional_judgment: value(page, 'Professional Judgment'), existing_skills: value(page, 'Skills Practiced'),
      skill_gap_focus: value(page, 'Skill Gap Focus'), existing_certification_alignment: value(page, 'Certification Alignment'),
      existing_objective_coverage: value(page, 'Certification Objective Coverage'), existing_capabilities: value(page, 'Bootcamp Capability IDs'),
      existing_level: value(page, 'Certification Evidence Level'), existing_transfer_test: value(page, 'Human Transfer Test')
    };
    row.row_json = JSON.stringify(row); rows.push(row);
  }
  return { rows, count: rows.length, held };
}
function parseReview(raw) {
  if (typeof raw === 'string') raw = raw.trim().replace(/^\x60\x60\x60(?:json)?\s*/i, '').replace(/\s*\x60\x60\x60$/, '');
  return object(raw);
}
function rich(content) {
  if (content.length > 1800) throw new Error('Mapping field exceeds its preservation bound');
  return { rich_text: content ? [{ type: 'text', text: { content } }] : [] };
}
function planMissingMapping(input) {
  const ALLOWED=new Set(capabilityIds(input.capability_ids_json));
  const row = object(input.row), page = object(input.latest_page);
  if (page.id !== row.page_id || !/^[a-f0-9-]{36}$/.test(page.id || '')) throw new Error('Fresh mapping page identity mismatch');
  if (page.archived || page.in_trash || page.is_archived || value(page, 'Stage') === 'Rejected' || sourceDigest(page) !== row.source_digest) throw new Error('Source changed during classification; preserve current page');
  const marker = value(page, MARKER);
  if (marker && marker !== revision(page)) throw new Error('Manual mapping changed; preserve and reconcile');
  const url = '/v1/pages/' + page.id;
  if (complete(page)) return { method: 'GET', url, body: '', page_id: page.id, action: 'skip' };
  const out = parseReview(input.raw);
  let proposedLevel = LEVELS.has(out.certification_evidence_level) ? out.certification_evidence_level : 'No supported mapping';
  const proposedObjective = String(out.certification_objective_coverage || '').trim();
  if (proposedLevel === 'Objective-level' && !/\b(?:cpre\.ch\d+|pcap\.[a-z0-9._-]+|objective[_ -]?id\s*[:=]\s*[a-z0-9._-]+)/i.test(proposedObjective)) proposedLevel = 'Credential/domain-level';
  const level = value(page, 'Certification Evidence Level') || proposedLevel;
  if (!LEVELS.has(level)) throw new Error('Preserve unsupported existing evidence level');
  const proposals = {
    'Certification Alignment': level === 'No supported mapping' ? '' : String(out.certification_alignment || '').trim(),
    'Certification Objective Coverage': level === 'No supported mapping' ? '' : proposedObjective,
    'Certification Evidence Level': level,
    'Bootcamp Capability IDs': [...new Set((Array.isArray(out.bootcamp_capability_ids) ? out.bootcamp_capability_ids : []).map(String).filter(id => ALLOWED.has(id)))].join(', '),
    'Human Transfer Test': String(out.human_transfer_test || '').trim(),
    'Skills Practiced': String(out.skills_practiced || '').trim()
  };
  const properties = {}, result = JSON.parse(JSON.stringify(page));
  for (const name of MAP_FIELDS) {
    if (value(page, name).trim()) continue; // Preserve native rich text and all existing judgments.
    const content = proposals[name];
    if (!content) continue; // Explicit empty classifications remain empty, the revision is durable.
    const prop = name === 'Certification Evidence Level' ? { select: { name: content } } : rich(content);
    properties[name] = prop; result.properties[name] = prop;
  }
  if (!complete(result)) throw new Error('Incomplete or contradictory mapping; preserve current metadata');
  if (value(result, 'Certification Evidence Level') === 'Objective-level' && !/\b(?:cpre\.ch\d+|pcap\.[a-z0-9._-]+|objective[_ -]?id\s*[:=]\s*[a-z0-9._-]+)/i.test(value(result, 'Certification Objective Coverage'))) throw new Error('Existing objective claim needs supported explicit coverage; preserve and reconcile');
  properties[MARKER] = rich(revision(result));
  properties['Last Updated'] = { date: { start: new Date().toISOString().slice(0, 10) } };
  return { method: 'PATCH', url, page_id: page.id, body: JSON.stringify({ properties }), revision: revision(result), action: 'fill-missing', filled_fields: Object.keys(properties).filter(n => ![MARKER, 'Last Updated'].includes(n)) };
}
if (typeof module !== 'undefined' && module.exports) module.exports = { selectMappings, planMissingMapping, revision, complete };
