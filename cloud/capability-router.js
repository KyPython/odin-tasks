'use strict';
// Actual pinned GitHub cloud matrix; divergent local 4.2 is not silently published.
const CAPABILITY_AUTHORITY = {"repository":"https://github.com/KyLamportLogic/human-rebuild-bootcamp","commit":"c9e0db70705c548c6b9ef30a98154aa180c741ad","path":"ideal-ssot/capability-matrix.json","blobSha":"74dfde6bdcab1d9b2475b7f8e9371b32204ef5f1","sha256":"3fdfcfb3ae296da288a50771c355ec5ab9af95d0dabcd63015c7ce687a87acc5","version":"4.1.0","capabilityIds":["architecture-tradeoff-defense","manual-technical-screen-retrieval","asymptotic-complexity-mastery","alternative-design-comparison","invariant-driven-testing","space-time-tradeoff-choice","abstraction-boundary-design","ai-side-effect-governance","fail-close-kill-switch","coding-agent-governance","audit-hash-traceability","systems-thinking-os","oci-container-runtime","host-agnostic-product-code","single-entrypoint-local-dev","shared-platform-boundaries","intent-fidelity-bindings","directory-purpose-minimalism","visitor-copy-integrity","law-propagation-sync","human-agency-boundary","formative-struggle-protocol","professional-docs-pack","provider-sdk-official-clients","dependency-decision-discipline","fleet-safe-rate-limits","agentic-security-defense-basics","learnable-workflow-observability","error-budget-slo-gate","secrets-jit-no-commit","test-pyramid-tdd","ci-cd-fail-closed-pipeline","github-issues-prs-loop","security-baseline-score","container-hardening-score","dependency-floor-score","runtime-path-fidelity-score","auth-coverage-score"]};
function capabilityIds(raw) {
  const ids = typeof raw === 'string' ? JSON.parse(raw) : raw;
  if (!Array.isArray(ids) || ids.length !== CAPABILITY_AUTHORITY.capabilityIds.length ||
      new Set(ids).size !== ids.length || ids.some(id => !CAPABILITY_AUTHORITY.capabilityIds.includes(id))) {
    throw new Error('Capability IDs do not match the verified cloud matrix; refresh the authority before writing');
  }
  return ids;
}
function decodeCapabilityRouter(input) {
  const q = typeof input.body === 'string' ? JSON.parse(input.body) : input.body;
  if (!q || !Array.isArray(q.results) || q.results.length !== 1 || q.has_more !== false || q.next_cursor) throw new Error('Capability router requires one complete Current row');
  const page=q.results[0], p=page.properties||{}, text=parts=>(parts||[]).map(x=>x.plain_text??x.text?.content??'').join('');
  if (page.archived || page.is_archived || page.in_trash || text(p.Name?.title)!=='Current' ||
      text(p['Matrix Version']?.rich_text).trim()!==CAPABILITY_AUTHORITY.version ||
      text(p['Matrix Blob SHA']?.rich_text).trim()!==CAPABILITY_AUTHORITY.blobSha || p['Source Repo']?.url!==CAPABILITY_AUTHORITY.repository) throw new Error('Capability router differs from verified cloud source; preserve and reconcile');
  const ids=capabilityIds(text(p['Capability IDs JSON']?.rich_text).split(',').map(x=>x.trim()).filter(Boolean));
  return {version:CAPABILITY_AUTHORITY.version,sha:CAPABILITY_AUTHORITY.blobSha,sourceCommit:CAPABILITY_AUTHORITY.commit,ids,ids_json:JSON.stringify(ids),ids_csv:ids.join(', ')};
}
if (typeof module !== 'undefined' && module.exports) module.exports={capabilityIds,decodeCapabilityRouter,CAPABILITY_AUTHORITY};
