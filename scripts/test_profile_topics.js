// Exercise the actual client-topic renderer with current and past visits.
const fs=require('node:fs');
const path=require('node:path');
const assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..');
const html=fs.readFileSync(path.join(root,'index.html'),'utf8');
const start=html.indexOf('function profileHistoricalTopicVisits(');
const end=html.indexOf('function switchProfileTab',start);
assert(start>0&&end>start);
const source=html.slice(start,end);
function render(visits,rows=[]){
 const target={innerHTML:''};
 const state={customer:{name:'Test customer',country:'英國'}};
 const win={CSCCustomerFollowups:{rows:()=>rows}};
 new Function('profileState','window','profileVisits','esc','$',source+';renderProfileTopics();')(state,win,()=>visits,String,()=>target);
 return target.innerHTML;
}
const latest={id:'november',date:'2026-11-17',label:'2026-11-17｜會議紀錄',docx:{},topics:[{title:'最新會議議題',text:'本次冷軋合作及試料',structured:true}]};
const first=render([latest],[{task:'本次冷軋合作',owner:'中貿',status:'待處理',visit_date:latest.date}]);
assert(!first.includes('歷次會議議題'),'First visit must not have a history section');
assert(first.includes('目前追蹤清單')&&first.includes('本次冷軋合作'));
assert(!render([latest],undefined).includes('歷次會議議題'),'Pending follow-up load must not turn the latest meeting into history');
const earlier={id:'february',date:'2026-02-05',label:'2026-02-05｜會議紀錄',docx:{},topics:[{title:'前次合作議題',text:'前次討論冷軋試料'}]};
const repeated=render([earlier,latest]);
assert(repeated.includes('歷次會議議題')&&repeated.includes('前次合作議題'));
assert(!repeated.includes('最新會議議題'),'History must exclude latest topics even when text differs from B-4');
assert(render([latest,{...earlier,date:'2026-11-17'}]).indexOf('歷次會議議題')<0,'No previous visit inferred from same-day documents');
const latestPdf={id:'december',date:'2026-12-01',pdf:{},topics:[]};
assert(render([latest,latestPdf]).includes('最新會議議題'),'Latest PDF-only visit still establishes the current visit date');
const overlap={...earlier,date:'2026-11-16',end_date:'2026-11-18'};
assert(!render([latest,overlap]).includes('歷次會議議題'),'Overlapping consolidated records are not previous visits');
const index=JSON.parse(fs.readFileSync(path.join(root,'meeting_records_index.json'),'utf8'));
for(const key of ['STEELALLOY','WILLIAMKING','TATASTEELPARK','COOPERJACKSON']){
 const visits=index.customers[key]?.visits;
 assert(visits?.length,key+' source must be present');
 if(visits.length===1)assert(!render(visits).includes('歷次會議議題'),key+' first-visit render');
}
console.log('Profile topics passed: first visits, genuine earlier visits, same-day and overlapping records, latest PDF visit.');
