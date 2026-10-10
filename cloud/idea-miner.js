'use strict';
function parse(v){let s=typeof v==='string'?v.trim():JSON.stringify(v||{});s=s.replace(/^\`\`\`(?:json)?\s*/i,'').replace(/\s*\`\`\`$/,'');try{return JSON.parse(s)}catch{return {candidates:[]}}}
function obj(v){if(typeof v==='string'){try{return JSON.parse(v)}catch{return {}}}return v||{};}
const CAPABILITY_AUTHORITY = {"repository":"https://github.com/KyLamportLogic/human-rebuild-bootcamp","commit":"c9e0db70705c548c6b9ef30a98154aa180c741ad","path":"ideal-ssot/capability-matrix.json","blobSha":"74dfde6bdcab1d9b2475b7f8e9371b32204ef5f1","sha256":"3fdfcfb3ae296da288a50771c355ec5ab9af95d0dabcd63015c7ce687a87acc5","version":"4.1.0","capabilityIds":["architecture-tradeoff-defense","manual-technical-screen-retrieval","asymptotic-complexity-mastery","alternative-design-comparison","invariant-driven-testing","space-time-tradeoff-choice","abstraction-boundary-design","ai-side-effect-governance","fail-close-kill-switch","coding-agent-governance","audit-hash-traceability","systems-thinking-os","oci-container-runtime","host-agnostic-product-code","single-entrypoint-local-dev","shared-platform-boundaries","intent-fidelity-bindings","directory-purpose-minimalism","visitor-copy-integrity","law-propagation-sync","human-agency-boundary","formative-struggle-protocol","professional-docs-pack","provider-sdk-official-clients","dependency-decision-discipline","fleet-safe-rate-limits","agentic-security-defense-basics","learnable-workflow-observability","error-budget-slo-gate","secrets-jit-no-commit","test-pyramid-tdd","ci-cd-fail-closed-pipeline","github-issues-prs-loop","security-baseline-score","container-hardening-score","dependency-floor-score","runtime-path-fidelity-score","auth-coverage-score"]};
function capabilityIds(raw) {
  const ids = typeof raw === 'string' ? JSON.parse(raw) : raw;
  if (!Array.isArray(ids) || ids.length !== CAPABILITY_AUTHORITY.capabilityIds.length ||
      new Set(ids).size !== ids.length || ids.some(id => !CAPABILITY_AUTHORITY.capabilityIds.includes(id))) {
    throw new Error('Capability IDs do not match the verified cloud matrix; refresh the authority before writing');
  }
  return ids;
}
const ALLOWED=new Set(capabilityIds(input.capability_ids_json));
const LEVELS=new Set(['Objective-level','Credential/domain-level','No supported mapping']);
const out=parse(input.raw), f=obj(input.factory);
if(f.has_more || !Array.isArray(f.results)) throw new Error('Incomplete Task Factory identity inventory; paginate before admitting new ideas');
const normalize=s=>String(s||'').normalize('NFKC').toLowerCase().replace(/[^a-z0-9]+/g,' ').trim().replace(/\s+/g,' ');
const existing=new Set(), variation=new Set(), titles=new Set();
for(const p of (f.results||[])){const pr=p.properties||{};const x=(pr['Duplicate Fingerprint']?.rich_text||[]).map(a=>a.plain_text||'').join('').trim().toLowerCase();if(x)existing.add(normalize(x));const v=(pr['Variation Axis']?.rich_text||[]).map(a=>a.plain_text||a.text?.content||'').join('');if(v)variation.add(normalize(v));const title=(pr.Task?.title||[]).map(a=>a.plain_text||a.text?.content||'').join('');if(title)titles.add(normalize(title));}
const rows=[];
for(const c of (out.candidates||[])){
 const fp=String(c.duplicate_fingerprint||'').trim().toLowerCase(), title=String(c.task||'').trim(), goal=String(c.goal||'').trim(), axis=normalize(c.variation_axis), transfer=String(c.human_transfer_test||'').trim(); const mins=Number(c.target_minutes||0);
 let level=LEVELS.has(c.certification_evidence_level)?c.certification_evidence_level:'No supported mapping';
 const caps=(Array.isArray(c.bootcamp_capability_ids)?c.bootcamp_capability_ids:[]).map(String).filter(x=>ALLOWED.has(x));
 if(!title||!goal||!fp||!axis||!transfer||existing.has(normalize(fp))||variation.has(axis)||titles.has(normalize(title))||mins<20||mins>45||goal.length>1800||fp.length>500) continue;
 if(level==='Objective-level' && !String(c.certification_objective_coverage||'').trim()) continue;
 if(level==='Objective-level' && !/\b(?:cpre\.ch\d+|pcap\.[a-z0-9._-]+|objective[_ -]?id\s*[:=]\s*[a-z0-9._-]+)/i.test(String(c.certification_objective_coverage||''))) level='Credential/domain-level';
 existing.add(normalize(fp)); variation.add(axis); titles.add(normalize(title));
 const spec='specs/odin-bootcamp/'+String(c.spec_slug||title.toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,''));
 const body={parent:{data_source_id:'74aac26d-fcbb-45df-b996-561f76b9cec6'},properties:{
  'Task':{title:[{type:'text',text:{content:title.slice(0,180)}}]},'Stage':{select:{name:'Candidate'}},'Lane':{select:{name:'Dual-candidate'}},'Bootcamp Status':{select:{name:'World queued'}},'Fit Gate':{select:{name:'PASS'}},
  'Odin Goal':{rich_text:[{type:'text',text:{content:goal.slice(0,1800)}}]},'Approved Goal':{rich_text:[]},'Approval ID':{rich_text:[]},
  'Apps':{rich_text:[{type:'text',text:{content:String(c.apps||'Visual Studio Code 1.140 with integrated terminal').slice(0,1800)}}]},
  'Duplicate Fingerprint':{rich_text:[{type:'text',text:{content:fp.slice(0,500)}}]},'Variation Axis':{rich_text:[{type:'text',text:{content:String(c.variation_axis||'').slice(0,1800)}}]},
  'Professional Judgment':{rich_text:[{type:'text',text:{content:String(c.professional_judgment||'').slice(0,1800)}}]},'Skills Practiced':{rich_text:[{type:'text',text:{content:String(c.skills_practiced||'').slice(0,1800)}}]},
  'Certification Alignment':{rich_text:[{type:'text',text:{content:String(c.certification_alignment||'').slice(0,1800)}}]},'Certification Objective Coverage':{rich_text:[{type:'text',text:{content:String(c.certification_objective_coverage||'').slice(0,1800)}}]},
  'Certification Evidence Level':{select:{name:level}},'Bootcamp Capability IDs':{rich_text:[{type:'text',text:{content:caps.join(', ').slice(0,1800)}}]},
  'Human Transfer Test':{rich_text:[{type:'text',text:{content:transfer.slice(0,1800)}}]},'Transfer Synced':{checkbox:false},
  'Skill Gap Focus':{rich_text:[{type:'text',text:{content:String(c.skill_gap_focus||'').slice(0,1800)}}]},'Spec Path':{rich_text:[{type:'text',text:{content:spec.slice(0,1800)}}]},
  'Target Recording Minutes':{number:mins},'Target Tier':{select:{name:mins<25?'15-24':mins<35?'25-34':'35-45:59'}},'AI Input Disclosure':{select:{name:'AI-generated before recording'}},
  'Runbook':{url:'https://app.notion.com/p/3f28621e0a7a81d2b092d5f3f4c537f4'},'Checklist URL':{url:'https://app.notion.com/p/3f28621e0a7a81efb032c2fd7b46aa5b'},'Operator Pack Status':{select:{name:'PENDING'}},'Reviewer Status':{select:{name:'Not recorded'}},
  'Environment Review Gate':{checkbox:false},'No-Solution-Leak Gate':{checkbox:false},'Local Starter Gate':{checkbox:false},'Pre-Record Gate':{checkbox:false},'Recording QA Gate':{checkbox:false},'Submission Gate':{checkbox:false},'Workflow Checklist Gate':{select:{name:'PENDING'}},
  'Source Evidence':{rich_text:[{type:'text',text:{content:('AUTOGENERATED BOOTCAMP CANDIDATE. Starter contract: '+String(c.starter_contract||'')+' Verification: '+String(c.verification||'')+' Distinctness: '+String(c.why_distinct||'')).slice(0,1800)}}]},
  'Last Updated':{date:{start:new Date().toISOString().slice(0,10)}}
 }};
 rows.push({create_body:JSON.stringify(body)});
}
return {rows};
