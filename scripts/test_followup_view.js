// Regression checks against the actual inline view, including restored drafts.
const fs=require('node:fs');
const path=require('node:path');
const assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..');
const html=fs.readFileSync(path.join(root,'index.html'),'utf8');
const keyStart=html.indexOf('function meetingKey(name){');
const keyEnd=html.indexOf('function hasMeetingRecord',keyStart);
const meetingKey=new Function(html.slice(keyStart,keyEnd)+';return meetingKey;')();
const start=html.indexOf(' function allRows(){');
const end=html.indexOf(' // B-4 presentation order only:',start);
assert(start>0&&end>start,'Actual follow-up view must exist');
const view=new Function('baseItems','proposals','wordDocuments','statuses','editing','meetingKey',html.slice(start,end)+';return allRows();');
const render=(items,proposals,documents)=>view(()=>items,proposals,documents,['待處理','處理中','待客戶回覆','已完成'],true,meetingKey);
const doc={customer:'Upton Steel',source_sha:'current',extracted_rows:2,warnings:[]};
const proposals=[
 {proposal_id:'UPTON-1',customer:'Upton Steel',country:'英國',task:'資料中心冷軋｜最新尺寸',owner:'中貿',source_sha:'current',source_row:2},
 {proposal_id:'UPTON-2',customer:'Upton Steel',country:'英國',task:'RC材評估｜開發 AI 機櫃',owner:'中貿、中鋼',source_sha:'current',source_row:3}
];
const stale=[
 {id:'FU-UPTON-old1',customer:'Upton Steel',task:'舊尺寸與需求',owner:'待指定',source_sha:'old',status:'待處理'},
 {id:'FU-UPTON-old2',customer:'Upton Steel',task:'舊 RC 方案',owner:'待指定',source_url:'meeting_records/old.docx',status:'待處理'}
];
assert.equal(render(stale,proposals,[doc]).length,2,'Old saved rows cannot double the current Word');
const manual={id:'FU-manual',customer:'中貿',task:'人工新增 OLAP 統計方式',status:'待處理'};
assert.equal(render([...stale,manual],proposals,[doc]).length,3,'Restored drafts retain manual additions');
const saved={...proposals[0],id:'AUTO-UPTON-1',word_proposal_id:'UPTON-1',task:'人工核對後文字',status:'已完成'};
let rows=render([saved,...stale],proposals,[doc]);
assert.equal(rows.length,2);
assert.equal(rows[0].task,saved.task,'Same-source manual edits remain');
assert.equal(rows[0].status,'已完成');
rows=render([{...saved,source_sha:'old',owner:'舊窗口'}],proposals,[doc]);
assert.equal(rows[0].task,proposals[0].task,'New revision supplies current Word content');
assert.equal(rows[0].owner,'中貿');
assert.equal(rows[0].status,'已完成','Existing progress survives same-row revision');
const oldDuferco={id:'DE-DUF-001',customer:'Duferco',task:'舊會議事項',source_url:'meeting_records/old.pdf',status:'待處理'};
assert.equal(render([oldDuferco],[],[{customer:'Duferco',extracted_rows:0,warnings:[]}]).length,0,'A read latest Word with no actions must not resurrect old actions');
assert.equal(render([oldDuferco],[],[]).length,1,'Unavailable extraction retains fallback');
assert.equal(render([oldDuferco],[],[{customer:'Duferco',extracted_rows:0,warnings:['Needs review']}]).length,1,'Uncertain extraction retains fallback');
const index=fs.readFileSync(path.join(root,'followup_suggestions.json'),'utf8');
const generated=JSON.parse(index),official=JSON.parse(fs.readFileSync(path.join(root,'followup_actions.json'),'utf8'));
rows=render(official.items,generated.proposals,generated.documents);
for(const document of generated.documents){
 if(document.error||document.warnings?.length)continue;
 const visible=rows.filter(x=>meetingKey(x.customer)===meetingKey(document.customer)&&(x.source_sha||x.word_proposal_id||/^(?:meeting_records|cbam_records)\//.test(x.source_url||'')));
 assert.equal(visible.length,document.extracted_rows,document.customer+' current Word row count');
 assert(visible.every(x=>x.source_sha===document.source_sha),document.customer+' current source version');
}
let scripts=0;
for(const match of html.matchAll(/<script\b([^>]*)>([\s\S]*?)<\/script>/g)){
 if(/src=|type="application\/json"/.test(match[1]))continue;
 new Function(match[2]);scripts++;
}
console.log('Follow-up view passed: current Word counts, no stale duplicates, preserved manual drafts and progress; '+scripts+' scripts parsed.');
