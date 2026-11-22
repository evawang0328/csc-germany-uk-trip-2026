const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..');
const html=fs.readFileSync(path.join(root,'index.html'),'utf8');
const index=JSON.parse(fs.readFileSync(path.join(root,'meeting_records_index.json'),'utf8'));
const source=html.slice(html.indexOf('function profileKnowledgeFields(c){'),html.indexOf('function renderProfileOrders(){'));
assert(source.includes('function renderProfileOverview()'));
const render=new Function('profileState','profileVisits','esc','$','meetingRecordsCache',source+';renderProfileOverview();');
const escape=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
for(const key of ['UPTON','AMDS','TOPTUBES','WILLIAMKING','BELMONT','COOPERJACKSON','STEELALLOY','TATASTEELPARK']){
 const target={innerHTML:''},visits=index.customers[key].visits;
 render({customer:{name:key}},()=>visits,escape,()=>target,index);
 assert(!target.innerHTML.includes('尚未擷取到可對應資料'),key+' has complete overview fields');
 assert(target.innerHTML.includes('knowledge-company-intro'),key+' company summary');
 assert(target.innerHTML.includes('查看來源'),key+' source meeting link');
 assert.equal((target.innerHTML.match(/class="profile-summary-box"/g)||[]).length,4);
 assert(target.innerHTML.includes('Market Outlook'));
}
console.log('Overview display passed: eight UK client pages have company summary, all five populated fields and source meeting links.');
