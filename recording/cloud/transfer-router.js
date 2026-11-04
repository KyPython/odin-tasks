'use strict';
// Scores and self-reported unaided declarations never establish mastery.
const crypto = require('node:crypto');
const DESTINATION = 'a6d74f65-0b06-4d1a-ab64-b4fb5f1a5a52';
const GUIDED_REFERENCES = {"3f08621e-0a7a-8132-89fd-e5cad87aba40":"e5652bcb044cd24d2a7d1c2f8bb93b885cea2069","3f08621e-0a7a-81b4-9fd3-f290ce5e6d8b":"ca532d92ec3db02224061b3ceef105b2bc113b27","3f08621e-0a7a-81ed-a36b-dd125c60221c":"c5986e93719cfd4b08a57104576c04a78d1f16ee","3f08621e-0a7a-818f-8a72-f73e8d4e4da0":"2ddf3c8f2a0e054ea2e40ab077c5a48132c34a38","3f28621e-0a7a-8141-8d6e-dfb9a5b43054":"9c829c6ec7f85cf382f97e286bf8acce20a96fe7","3f28621e-0a7a-81bc-abb6-c65d74863966":"aca7a6ac52a9a2dee2d7bc3a0a77dca09f2a6fe5","3f38621e-0a7a-8149-8dd1-c3e0ef4bff3d":"ac4aaa7d95fd07d3bdc58aa88128d24e533ec4c2","3f38621e-0a7a-81ac-95c5-dc0a9aaa211a":"c65f9343be723ea36289db541b8f373883cbfe8a"};
const REVIEW_FIELDS = ['Lane','Bootcamp Status','Reviewer Status','Reviewer Score','Reviewer Notes','Next Skill Action','Workflow Checklist Gate','Recording QA Gate','Review Bundle URL','Starter Repository','Starter Commit','Certification Evidence Level','Certification Alignment','Certification Objective Coverage','Bootcamp Capability IDs','Human Transfer Test','Skills Practiced'];
function semantic(page,name) {
 const p=page.properties?.[name];
 if(p?.select)return p.select.name||'';
 if(typeof p?.checkbox==='boolean')return p.checkbox;
 if(typeof p?.number==='number')return p.number;
 if(typeof p?.url==='string')return p.url;
 return (p?.rich_text||p?.title||[]).map(x=>x.plain_text??x.text?.content??'').join('');
}
function guidance(page) {return GUIDED_REFERENCES[page.id]===semantic(page,'Starter Commit').trim()?'guided':'unknown';}
function reviewKey(page) {return 'ODIN_BOOTCAMP_TRANSFER_V2:'+crypto.createHash('sha256').update(JSON.stringify([page.id,guidance(page),...REVIEW_FIELDS.map(n=>semantic(page,n))])).digest('hex');}
function exposureExplanation(page,status) {
 const reason=guidance(page)==='guided'?'Known AI-prepared guided reference; assisted practice.':'Assistance unknown; conservative exposure classification pending validated independent provenance.';
 return 'Internal reviewed '+status.toLowerCase()+'. '+reason+' No mastery, exam readiness or paid approval established.';
}
function requireExposure(row) {
 if(row.evidence_class!=='Assisted exposure'||row.mastery_eligible!==false||!/^ODIN_BOOTCAMP_TRANSFER_V2:[a-f0-9]{64}$/.test(row.dedup_key||''))throw new Error('Reviewer pass or self-report cannot establish unaided transfer or mastery');
}

function selectTransfer(input) {
'use strict';
const crypto = require('node:crypto');

function object(value) {
  const result = typeof value === 'string' ? JSON.parse(value) : value;
  if (!result || typeof result !== 'object') throw new Error('Missing Task Factory response');
  return result;
}
function text(parts) {
  return (parts || []).map(p => p.plain_text ?? p.text?.content ?? '').join('');
}
function value(page, name) {
  const prop = page.properties?.[name];
  if (prop?.select) return prop.select.name || '';
  if (prop?.checkbox === true) return true;
  if (typeof prop?.number === 'number') return prop.number;
  if (typeof prop?.url === 'string') return prop.url;
  return text(prop?.rich_text || prop?.title);
}
function digest(parts) {
  return crypto.createHash('sha256').update(parts.join('|')).digest('hex');
}

const q = object(input.body ?? input);
if (!Array.isArray(q.results) || q.has_more || q.next_cursor) {
  throw new Error('Incomplete recorded-review inventory; paginate before transfer');
}

const rows = [];
const skipped = [];

for (const page of q.results) {
  if (page.archived || page.in_trash || page.is_archived) continue;
  const lane = value(page, 'Lane');
  const bootcampStatus = value(page, 'Bootcamp Status');
  const reviewerStatus = value(page, 'Reviewer Status');
  const reviewerScore = value(page, 'Reviewer Score');
  const notes = value(page, 'Reviewer Notes').trim();
  const nextSkill = value(page, 'Next Skill Action').trim();
  const workflow = value(page, 'Workflow Checklist Gate');
  const reviewBundle = value(page, 'Review Bundle URL');
  const starterRepo = value(page, 'Starter Repository');
  const starterCommit = value(page, 'Starter Commit').trim();
  const transferSynced = value(page, 'Transfer Synced') === true;
  const recordingQa = value(page, 'Recording QA Gate') === true;
  const evidenceLevel = value(page, 'Certification Evidence Level');
  const certAlignment = value(page, 'Certification Alignment').trim();
  const objectiveCoverage = value(page, 'Certification Objective Coverage').trim();
  const capabilities = value(page, 'Bootcamp Capability IDs').trim();
  const transferTest = value(page, 'Human Transfer Test').trim();
  const skills = value(page, 'Skills Practiced').trim();

  if (transferSynced) continue;

  const mappingOkay =
    ['Objective-level','Credential/domain-level','No supported mapping'].includes(evidenceLevel) &&
    transferTest &&
    (evidenceLevel === 'No supported mapping' ? !certAlignment : !!certAlignment) &&
    (evidenceLevel !== 'Objective-level' || !!objectiveCoverage);

  const evidenceOkay =
    lane === 'Bootcamp' &&
    bootcampStatus === 'Reviewed' &&
    ['Pass','Needs work','Fail'].includes(reviewerStatus) &&
    Number.isFinite(reviewerScore) && reviewerScore >= 0 && reviewerScore <= 100 &&
    notes &&
    recordingQa &&
    ['POST-RECORD PASS','SUBMISSION PASS'].includes(workflow) &&
    /^https:\/\/(?:drive|docs)\.google\.com\//.test(reviewBundle || '') &&
    /^https:\/\/github\.com\/KyPython\/[A-Za-z0-9_.-]+$/.test(starterRepo || '') &&
    /^[a-f0-9]{40}$/.test(starterCommit) &&
    (reviewerStatus === 'Pass' || !!nextSkill);

  if (!mappingOkay || !evidenceOkay) {
    skipped.push({page_id: page.id, reason: !mappingOkay ? 'Mapping incomplete' : 'Reviewed unaided evidence contract incomplete'});
    continue;
  }

  const dedupKey = reviewKey(page);

  rows.push({
    page_id: page.id,
    source_ref: page.id,
    dedup_key: dedupKey,
    date: new Date().toISOString().slice(0,10),
    artifact_url: reviewBundle,
    concepts: skills || 'Reviewed engineering practice',
    certification_alignment: certAlignment,
    objective_coverage: objectiveCoverage,
    evidence_level: evidenceLevel,
    bootcamp_capabilities: capabilities,
    human_transfer_test: transferTest,
    reviewer_status: reviewerStatus,
    reviewer_score: reviewerScore,
    evidence_class: 'Assisted exposure',
    mastery_eligible: false,
    gap: exposureExplanation(page,reviewerStatus),
    next_verification: nextSkill || transferTest,
    row_json: JSON.stringify({
      page_id: page.id,
      source_ref: page.id,
      dedup_key: dedupKey,
      date: new Date().toISOString().slice(0,10),
      artifact_url: reviewBundle,
      concepts: skills || 'Reviewed engineering practice',
      certification_alignment: certAlignment,
      objective_coverage: objectiveCoverage,
      evidence_level: evidenceLevel,
      bootcamp_capabilities: capabilities,
      human_transfer_test: transferTest,
      reviewer_status: reviewerStatus,
      reviewer_score: reviewerScore,
      evidence_class: 'Assisted exposure',
      mastery_eligible: false,
      gap: exposureExplanation(page,reviewerStatus),
      next_verification: nextSkill || transferTest
    })
  });
}
return {rows, count: rows.length, skipped};
}
function planTransfer(input) {
'use strict';

function object(value) {
  const result = typeof value === 'string' ? JSON.parse(value) : value;
  if (!result || typeof result !== 'object') throw new Error('Missing object');
  return result;
}
function rt(content) {
  const s = String(content || '');
  if (s.length > 1800) throw new Error('Transfer field exceeds bound');
  return { rich_text: s ? [{type:'text', text:{content:s}}] : [] };
}
function title(content) {
  return { title: [{type:'text', text:{content:String(content)}}] };
}

const row = object(input.row);
requireExposure(row);
const q = object(input.query);
if (!Array.isArray(q.results) || q.has_more || q.next_cursor) {
  throw new Error('Incomplete transfer-evidence dedup query');
}
if (q.results.length > 1) {
  throw new Error('Duplicate transfer-evidence rows found for dedup key; reconcile before continuing');
}
if (q.results.length === 1) {
  const existing = q.results[0];
  return {
    action:'recover',
    method:'GET',
    url:'/v1/pages/' + existing.id,
    body:'',
    expected: row,
    page_id: row.page_id,
    dedup_key: row.dedup_key
  };
}

const body = {
  parent:{data_source_id:'a6d74f65-0b06-4d1a-ab64-b4fb5f1a5a52'},
  properties:{
    'Evidence': title('Reviewed practice exposure ' + row.date),
    'Date': {date:{start:row.date}},
    'Source Type': {select:{name:'Odin Bootcamp'}},
    'Source Ref': rt(row.source_ref),
    'Artifact Pointer': {url:row.artifact_url},
    'Concepts Exercised': rt(row.concepts),
    'Certification Alignment': rt(row.certification_alignment),
    'Certification Objective Coverage': rt(row.objective_coverage),
    'Evidence Level': {select:{name:row.evidence_level}},
    'Bootcamp Capability IDs': rt(row.bootcamp_capabilities),
    'Human Transfer Test': rt(row.human_transfer_test),
    'Reviewer Status': {select:{name:row.reviewer_status}},
    'Reviewer Score': {number:row.reviewer_score},
    'Evidence Class': {select:{name:row.evidence_class}},
    'Mastery Eligible': {checkbox:!!row.mastery_eligible},
    'Gap / Corrected Model': rt(row.gap),
    'Next Verification': rt(row.next_verification),
    'Dedup Key': rt(row.dedup_key)
  }
};

return {
  action:'create',
  method:'POST',
  url:'/v1/pages',
  body:JSON.stringify(body),
  expected:row,
  page_id:row.page_id,
  dedup_key:row.dedup_key
};
}
function verifyTransfer(input) {
'use strict';
const crypto = require('node:crypto');

function object(value) {
  const result = typeof value === 'string' ? JSON.parse(value) : value;
  if (!result || typeof result !== 'object') throw new Error('Missing object');
  return result;
}
function text(parts) {
  return (parts || []).map(p => p.plain_text ?? p.text?.content ?? '').join('');
}
function value(page, name) {
  const prop = page.properties?.[name];
  if (prop?.select) return prop.select.name || '';
  if (prop?.checkbox === true) return true;
  if (typeof prop?.number === 'number') return prop.number;
  if (typeof prop?.url === 'string') return prop.url;
  return text(prop?.rich_text || prop?.title);
}
function digest(parts) {
  return crypto.createHash('sha256').update(parts.join('|')).digest('hex');
}

const expected = object(input.expected);
requireExposure(expected);
const evidence = object(input.evidence);
const latest = object(input.latest);

if (latest.id !== expected.page_id) throw new Error('Task Factory row changed identity');
if (value(latest,'Transfer Synced') === true) {
  return {method:'GET',url:'/v1/pages/' + latest.id,body:'',page_id:latest.id,action:'already-synced'};
}

const currentDedup = reviewKey(latest);
if (latest.archived || latest.in_trash || semantic(latest,'Lane')!=='Bootcamp' || semantic(latest,'Bootcamp Status')!=='Reviewed' || semantic(latest,'Recording QA Gate')!==true || !['POST-RECORD PASS','SUBMISSION PASS'].includes(semantic(latest,'Workflow Checklist Gate'))) throw new Error('Actual review or capture gates changed; do not sync');
if (evidence.archived || evidence.in_trash || evidence.parent?.data_source_id !== DESTINATION) throw new Error('Transfer destination identity mismatch');
if (currentDedup !== expected.dedup_key) {
  throw new Error('Reviewed attempt changed after transfer selection; do not sync stale evidence');
}

const checks = [
  ['Dedup Key', expected.dedup_key],
  ['Artifact Pointer', expected.artifact_url],
  ['Concepts Exercised', expected.concepts],
  ['Gap / Corrected Model', expected.gap],
  ['Next Verification', expected.next_verification],
  ['Source Ref', expected.source_ref],
  ['Source Type', 'Odin Bootcamp'],
  ['Evidence Class', 'Assisted exposure'],
  ['Reviewer Status', expected.reviewer_status],
  ['Certification Alignment', expected.certification_alignment],
  ['Certification Objective Coverage', expected.objective_coverage],
  ['Evidence Level', expected.evidence_level],
  ['Bootcamp Capability IDs', expected.bootcamp_capabilities],
  ['Human Transfer Test', expected.human_transfer_test]
];
for (const [name, wanted] of checks) {
  if (String(value(evidence,name) ?? '') !== String(wanted ?? '')) {
    throw new Error('Transfer evidence readback mismatch: ' + name);
  }
}
if (Number(value(evidence,'Reviewer Score')) !== Number(expected.reviewer_score)) {
  throw new Error('Transfer evidence readback mismatch: Reviewer Score');
}
if (evidence.properties?.['Mastery Eligible']?.checkbox !== false) {
  throw new Error('Transfer evidence readback mismatch: Mastery Eligible');
}

return {
  method:'PATCH',
  url:'/v1/pages/' + latest.id,
  page_id:latest.id,
  action:'mark-synced',
  body:JSON.stringify({properties:{
    'Transfer Synced':{checkbox:true},
    'Last Updated':{date:{start:new Date().toISOString().slice(0,10)}}
  }})
};
}
if (typeof module !== 'undefined' && module.exports) module.exports = {selectTransfer,planTransfer,verifyTransfer,reviewKey,guidance,DESTINATION};
