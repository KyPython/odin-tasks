'use strict';
function obj(v){if(typeof v==='string'){try{return JSON.parse(v)}catch{return {}}}return v||{};}
const pr=obj(input.pr);
const fs=Array.isArray(obj(input.files))?obj(input.files):[];
if(!pr.merged_at || pr.merged !== true || !/^[a-f0-9]{40}$/.test(pr.head?.sha||'')) throw new Error('Merged PR and full source commit required before source review');
if(!Number.isInteger(pr.changed_files) || pr.changed_files < 1 || pr.changed_files !== fs.length || fs.length >= 100) throw new Error('Incomplete changed-file inventory; inspect the complete published tree');
if(fs.some(f=>typeof f.patch !== 'string' || !f.patch)) throw new Error('Missing file evidence; inspect the complete published tree');
let total=0, parts=[];
for(const f of fs.slice(0,100)){
  const patch=String(f.patch||'');
  const section=['FILE: '+(f.filename||''),'STATUS: '+(f.status||''),'PATCH:',patch].join('\n');
  if(total+section.length>42000) throw new Error('Source evidence exceeds the reviewer cap; inspect the complete published tree');
  parts.push(section); total+=section.length;
}
return {
  task:String(input.task||''), goal:String(input.goal||''), apps:String(input.apps||''),
  spec_path:String(input.spec_path||''), build_pr:String(input.build_pr||''),
  pr_number:pr.number||null, head_sha:pr.head?.sha||'', merged_at:pr.merged_at||'',
  pr_state:pr.state||'', changed_files:pr.changed_files||fs.length,
  evidence:parts.join('\n\n')
};
