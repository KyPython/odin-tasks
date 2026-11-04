'use strict';
// Shared by the existing authenticated manifest owner. Private bytes never go
// to a public issue/comment, console, source field, or human recording workspace.
const bridgeCrypto = require('node:crypto');
const BRIDGE_LIMITS = {files:50,entries:500,bytes:48000,evidence:50000};
function bridgeObject(value) {
  const result=typeof value==='string'?JSON.parse(value):value;
  if(!result || typeof result!=='object' || Array.isArray(result))throw new Error('Private source bridge: missing object');
  return result;
}
function bridgeRequire(test,message) {if(!test)throw new Error('Private source bridge: '+message);}
function bridgeHash(data,kind='sha256') {return bridgeCrypto.createHash(kind).update(data).digest('hex');}
function bridgeGitHash(type,bytes) {return bridgeHash(Buffer.concat([Buffer.from(type+' '+bytes.length+'\0'),bytes]),'sha1');}
function bridgePath(path) {
  bridgeRequire(typeof path==='string' && path.length<=500 && path && !path.startsWith('/') && !/[\\\x00-\x1f\x7f]/.test(path) && !path.split('/').some(x=>!x||x==='.'||x==='..'),'unsafe source path');
  bridgeRequire(!path.split('/').some(x=>['.git','.aws','.ssh','.venv','node_modules'].includes(x)) && !/(?:^|\/)(?:\.env(?:\..*)?|credentials(?:\.json)?|id_rsa|id_ed25519)$/.test(path),'credential/dependency path is not starter evidence');
  return path;
}
function bridgeIdentity(row,comments) {
  row=bridgeObject(row);
  bridgeRequire(/^[a-f0-9-]{36}$/.test(row.row_id||'') && typeof row.goal==='string' && row.goal.trim(),'exact native row and Goal required');
  let source=row.starter_repository||'',commit=row.starter_commit||'',commentId=null;
  bridgeRequire(!source===!commit,'partial native source pin');
  if(!source) {
    if(typeof comments==='string')comments=JSON.parse(comments);
    bridgeRequire(Array.isArray(comments) && comments.length<100,'incomplete public pointer inventory');
    for(const comment of comments.slice().reverse()) {
      if(!['KyPython','chatgpt-codex-connector[bot]'].includes(comment.user?.login))continue;
      const text=String(comment.body||''),marker=text.lastIndexOf('ODIN_STARTER_MANIFEST');
      if(marker<0)continue;
      const start=text.indexOf('{',marker);if(start<0)continue;
      let depth=0,string=false,escape=false,end=-1;
      for(let i=start;i<text.length;i++){const c=text[i];if(string){if(escape)escape=false;else if(c==='\\')escape=true;else if(c==='"')string=false;continue;}if(c==='"')string=true;else if(c==='{')depth++;else if(c==='}'&&--depth===0){end=i+1;break;}}
      if(end<0)continue;
      let candidate;try{candidate=JSON.parse(text.slice(start,end));}catch{continue;}
      if(candidate.row_id!==row.row_id)continue;
      bridgeRequire(!candidate.files?.some(f=>f.content_b64),'private byte manifests are not accepted from the public queue');
      if(candidate.goal_sha256)bridgeRequire(candidate.goal_sha256===bridgeHash(Buffer.from(row.goal+'\n')),'public pointer Goal mismatch');
      source=candidate.source_repo;commit=candidate.commit;commentId=comment.id;break;
    }
  }
  if(!source)return {found:false,row_id:row.row_id,reason:'Published private source pointer/full commit is not available'};
  bridgeRequire(/^https:\/\/github\.com\/KyPython\/[A-Za-z0-9][A-Za-z0-9_.-]{0,99}$/.test(source) && /^[a-f0-9]{40}$/.test(commit||''),'invalid private source repository/full pin');
  const repo=source.slice('https://github.com/'.length);
  return {found:true,row_id:row.row_id,goal:row.goal,goal_sha256:bridgeHash(Buffer.from(row.goal+'\n')),lane:row.lane,source_repo:source,repository:repo,commit,comment_id:commentId,audit_only:row.audit_only===true,repo_url:'/repos/'+repo,commit_url:'/repos/'+repo+'/git/commits/'+commit,source_ref:source+'/tree/'+commit};
}
function bridgeCommit(input) {
  const selected=bridgeObject(input.selected),repo=bridgeObject(input.repo),commit=bridgeObject(input.commit);
  bridgeRequire(selected.found===true && repo.private===true && repo.full_name===selected.repository && repo.html_url===selected.source_repo,'private repository identity not verified');
  bridgeRequire(commit.sha===selected.commit && /^[a-f0-9]{40}$/.test(commit.tree?.sha||''),'pinned commit identity/tree missing');
  return {...selected,tree_sha:commit.tree.sha,tree_url:'/repos/'+selected.repository+'/git/trees/'+commit.tree.sha};
}
function bridgeTreeHash(entries,parent) {
  const children=entries.filter(e=>(e.path.includes('/')?e.path.slice(0,e.path.lastIndexOf('/')):'')===parent).map(e=>({...e,name:e.path.split('/').at(-1)}));
  children.sort((a,b)=>Buffer.compare(Buffer.from(a.name+(a.type==='tree'?'/':'')),Buffer.from(b.name+(b.type==='tree'?'/':''))));
  return bridgeGitHash('tree',Buffer.concat(children.map(e=>Buffer.concat([Buffer.from(e.mode.replace(/^0+/,'')+' '+e.name+'\0'),Buffer.from(e.sha,'hex')]))));
}
function bridgeTree(input) {
  const selected=bridgeObject(input.selected),tree=bridgeObject(input.tree);
  bridgeRequire(tree.sha===selected.tree_sha && tree.truncated===false && Array.isArray(tree.tree) && tree.tree.length<=BRIDGE_LIMITS.entries,'incomplete or wrong source tree');
  const seen=new Set(),files=[];let bytes=0;
  for(const e of tree.tree){bridgePath(e.path);bridgeRequire(!seen.has(e.path) && /^[a-f0-9]{40}$/.test(e.sha||''),'duplicate/malformed tree entry');seen.add(e.path);
    bridgeRequire(e.type==='tree'&&e.mode==='040000'||e.type==='blob'&&['100644','100755'].includes(e.mode),'symlink/submodule/special source rejected');
    if(e.type==='blob'){bridgeRequire(Number.isSafeInteger(e.size)&&e.size>=0,'missing blob size');bytes+=e.size;files.push({path:e.path,mode:e.mode,blob_sha:e.sha,size:e.size});}
  }
  bridgeRequire(files.length>0 && files.length<=BRIDGE_LIMITS.files && bytes<=BRIDGE_LIMITS.bytes,'source exceeds bounded complete review');
  for(const e of tree.tree){if(e.path.includes('/'))bridgeRequire(tree.tree.some(p=>p.type==='tree'&&p.path===e.path.slice(0,e.path.lastIndexOf('/'))),'orphan tree entry');if(e.type==='tree')bridgeRequire(bridgeTreeHash(tree.tree,e.path)===e.sha,'directory tree hash mismatch');}
  bridgeRequire(bridgeTreeHash(tree.tree,'')===tree.sha,'complete root tree hash mismatch');
  const query='query { repository(owner:"KyPython",name:'+JSON.stringify(selected.repository.split('/')[1])+') { nameWithOwner isPrivate '+files.map((f,i)=>'f'+i+':object(oid:'+JSON.stringify(f.blob_sha)+'){... on Blob{oid byteSize isBinary text}}').join(' ')+' } }';
  return {...selected,files,file_count:files.length,graphql_body:JSON.stringify({query})};
}
function bridgeBlobs(input) {
  const selected=bridgeObject(input.selected),response=bridgeObject(input.blobs),repo=response.data?.repository;
  bridgeRequire(!response.errors?.length && repo?.isPrivate===true && repo.nameWithOwner===selected.repository,'private blob query failed or wrong repository');
  const files=[],parts=[];let total=0;
  for(let i=0;i<selected.files.length;i++){
    const expected=selected.files[i],blob=repo['f'+i];
    bridgeRequire(blob && blob.oid===expected.blob_sha && blob.isBinary===false && typeof blob.text==='string','missing/binary/wrong source blob');
    const bytes=Buffer.from(blob.text,'utf8');bridgeRequire(bytes.toString('utf8')===blob.text && bytes.length===expected.size && blob.byteSize===bytes.length && bridgeGitHash('blob',bytes)===expected.blob_sha,'blob bytes/hash/size mismatch');
    bridgeRequire(!/-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|\b(?:ghp_|gho_|github_pat_|sk_live_|sk_test_|sk-proj-|xoxb-|xoxp-)[A-Za-z0-9_]{20,}|\bAKIA[0-9A-Z]{16}\b/.test(blob.text),'possible secret material; preserve privately and review before promotion');
    const section='FILE: '+expected.path+'\nMODE: '+expected.mode+'\nBLOB_SHA: '+expected.blob_sha+'\n---\n'+blob.text+'\n---';total+=section.length;bridgeRequire(total<=BRIDGE_LIMITS.evidence,'private evidence exceeds complete review bound');parts.push(section);
    files.push({...expected,sha256:bridgeHash(bytes),content_b64:bytes.toString('base64')});
  }
  const inventory=files.map(({content_b64,...f})=>f).sort((a,b)=>a.path.localeCompare(b.path));
  return {schemaVersion:1,...selected,files,file_count:files.length,inventory_sha256:bridgeHash(Buffer.from(JSON.stringify(inventory))),found:!selected.audit_only,verified:true,evidence:parts.join('\n\n'),private_bytes_only:true,sourceInputsModified:false,recordingWorkspaceModified:false,recorderExecuted:false,registrationOrApprovalClaim:false};
}
function bridgeAuditRows(query,pins) {
  query=bridgeObject(query);bridgeRequire(Array.isArray(query.results)&&query.has_more===false&&!query.next_cursor,'incomplete audit inventory');
  const text=p=>(p?.rich_text||p?.title||[]).map(x=>x.plain_text??x.text?.content??'').join('');
  return {rows:pins.map(pin=>{const p=query.results.find(x=>x.id===pin.row_id);bridgeRequire(p&&!p.archived&&!p.in_trash,'audit source page missing');const v=p.properties;bridgeRequire(v['Starter Repository']?.url===pin.source_repo && text(v['Starter Commit'])===pin.commit,'audit pin changed');return {row_id:p.id,goal:text(v['Odin Goal']),lane:v.Lane?.select?.name||'',starter_repository:pin.source_repo,starter_commit:pin.commit,issue_number:pin.issue_number,audit_only:true};}),count:pins.length};
}
function bridgeSummary(input) {
  const proof=bridgeObject(input.proof);
  bridgeRequire(proof.verified===true && proof.private_bytes_only===true,'verified private handoff missing');
  return {schemaVersion:1,row_id:proof.row_id,source_repo:proof.source_repo,commit:proof.commit,tree_sha:proof.tree_sha,goal_sha256:proof.goal_sha256,inventory_sha256:proof.inventory_sha256,file_count:proof.file_count,files:proof.files.map(({content_b64,...f})=>f),verified:true,found:proof.found,audit_only:proof.audit_only,private_bytes_exported_publicly:false,sourceInputsModified:false,recordingWorkspaceModified:false,recorderExecuted:false,registrationOrApprovalClaim:false};
}
function bridgePersistPins(input) {
  const proof=bridgeObject(input.proof),page=bridgeObject(input.native_page),body=bridgeObject(input.property_body);
  bridgeRequire(proof.verified===true && proof.private_bytes_only===true && proof.found===true && proof.audit_only!==true,'only a verified non-audit source may persist pins');
  bridgeRequire(page.id===proof.row_id && !page.archived && !page.in_trash,'fresh native source page identity changed');
  const p=page.properties||{},text=v=>(v?.rich_text||[]).map(x=>x.plain_text??x.text?.content??'').join(''),select=k=>p[k]?.select?.name||'';
  const goal=text(p['Odin Goal']),approval=text(p['Approval ID']),approved=text(p['Approved Goal']);
  bridgeRequire(goal===proof.goal && bridgeHash(Buffer.from(goal+'\n'))===proof.goal_sha256,'fresh native Goal changed');
  const bootcamp=proof.lane==='Bootcamp' && ['Bootcamp','Dual-candidate'].includes(select('Lane')) && select('Stage')==='Candidate' && select('Bootcamp Status')==='World building' && !approval && !approved;
  const odin=proof.lane==='Odin monetization' && ['', 'Odin monetization'].includes(select('Lane')) && approval && approved===goal && ['Environment building','Ready to record'].includes(select('Stage'));
  bridgeRequire(select('Operator Pack Status')==='PENDING' && select('Fit Gate')==='PASS' && (bootcamp||odin),'fresh native eligibility changed; preserve human decisions');
  const source=p['Starter Repository']?.url||'',commit=text(p['Starter Commit']);
  bridgeRequire(!source&&!commit || source===proof.source_repo&&commit===proof.commit,'existing native source pins differ or are partial');
  const allowed=['Operator Pack Block ID','Operator Pack Revision','Operator Pack Status','Environment Review Gate','No-Solution-Leak Gate','Operator Pack Evidence'];
  bridgeRequire(body.properties && Object.keys(body).length===1 && Object.keys(body.properties).every(k=>allowed.includes(k)),'unexpected property write; preserve human fields');
  return {property_body:JSON.stringify({properties:{...body.properties,'Starter Repository':{url:proof.source_repo},'Starter Commit':{rich_text:[{type:'text',text:{content:proof.commit}}]}}})};
}
if(typeof module!=='undefined'&&module.exports)module.exports={bridgeIdentity,bridgeCommit,bridgeTree,bridgeBlobs,bridgeAuditRows,bridgeSummary,bridgePersistPins,bridgeTreeHash,BRIDGE_LIMITS};
