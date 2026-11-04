'use strict';
function arr(v){if(typeof v==='string'){try{v=JSON.parse(v)}catch{return []}}return Array.isArray(v)?v:[];}
function extract(text){
 const mark=text.lastIndexOf('ODIN_STARTER_MANIFEST'); if(mark<0)return null;
 const s=text.slice(mark); const start=s.indexOf('{'); if(start<0)return null;
 let depth=0,inStr=false,esc=false;
 for(let i=start;i<s.length;i++){
  const ch=s[i];
  if(inStr){if(esc)esc=false;else if(ch==='\\')esc=true;else if(ch==='"')inStr=false;continue;}
  if(ch==='"'){inStr=true;continue;}
  if(ch==='{')depth++;
  if(ch==='}' && --depth===0){try{return JSON.parse(s.slice(start,i+1))}catch{return null;}}
 }
 return null;
}
function dec(b64){
 try{
  if(typeof Buffer!=='undefined') return Buffer.from(String(b64||''),'base64').toString('utf8');
  if(typeof atob==='function') return decodeURIComponent(escape(atob(String(b64||''))));
 }catch(e){}
 return '[UNDECODABLE BASE64]';
}
const comments=arr(input.comments).slice().reverse();
if(comments.length >= 100) throw new Error('Incomplete manifest comment inventory; paginate before review');
let manifest=null,commentId=null;
for(const c of comments){const m=extract(String(c.body||''));if(m&&Array.isArray(m.files)&&m.files.length){manifest=m;commentId=c.id||null;break;}}
if(!manifest)return {found:false,evidence:'',comment_id:null,file_count:0};
let total=0,parts=[],seen=new Set();
for(const f of manifest.files){
 const path=String(f.path||'');
 if(!path || path.startsWith('/') || path.includes(String.fromCharCode(92)) || path.split('/').some(p=>!p || p==='.' || p==='..') || seen.has(path)) throw new Error('Invalid or duplicate starter path');
 seen.add(path);
 if(typeof f.content_b64 !== 'string' || !/^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$/.test(f.content_b64)) throw new Error('Invalid starter encoding');
 const content=dec(f.content_b64);
 if(content==='[UNDECODABLE BASE64]' || (typeof Buffer !== 'undefined' && Buffer.from(content,'utf8').toString('base64') !== f.content_b64)) throw new Error('Binary or incomplete starter evidence; inspect the complete published tree');
 const section='FILE: '+path+'\n---\n'+content+'\n---';
 if(total+section.length>50000) throw new Error('Source evidence exceeds the reviewer cap; inspect the complete published tree');
 parts.push(section); total+=section.length;
}
return {
 found:true,comment_id:commentId,file_count:manifest.files.length,
 branch:String(manifest.branch||''),pr_title:String(manifest.pr_title||''),
 evidence:parts.join('\n\n')
};
