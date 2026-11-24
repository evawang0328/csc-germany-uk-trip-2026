(function(){
 const $=id=>document.getElementById(id),engine=window.CSCSearchEngine;
 const panel=$('siteSearch');let rows=[],loaded=false,loading=null,type='',limit=30,lastFocus=null;
 const labels={meeting:'Word 會議紀錄',customer:'客戶資料',followup:'追蹤事項',policy:'市場與政策',document:'Word／PDF 文件',page:'網頁資料'};
 const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const clients=()=>typeof PUBLIC_CLIENTS==='undefined'?[]:PUBLIC_CLIENTS;
 function clientOf(key){return clients().find(c=>meetingKey(c.name)===key);}
 function enrich(r){
  const key=r.customer_key?meetingKey(r.customer_key):'',c=clientOf(key);return {...r,customer_key:key,customer:c?.name||r.customer||'',country:c?.country||r.country||'',title:c&&r.type==='meeting'?c.country+'｜'+c.name:r.title};
 }
 function highlighted(t){
  const terms=engine.tokens($('ssQuery').value);if(!terms.length)return esc(t);
  // Escape first by rendering each plain-text span separately.
  const pattern=new RegExp('('+terms.map(t=>t.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')).join('|')+')','gi');
  return String(t).split(pattern).map((v,i)=>i%2?'<mark>'+esc(v)+'</mark>':esc(v)).join('');
 }
 function safeURL(url){return typeof url==='string'&& !/^(?:[a-z]+:|\/\/|\/|\.\.)/i.test(url)&&!url.includes('\\')?url:'';}
 async function load(){
  if(loaded)return;if(loading)return loading;
  $('ssStatus').textContent='正在載入全文資料…';
  loading=fetch('search_index.json?v='+Date.now(),{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('HTTP '+r.status);return r.json();}).then(data=>{
   rows=data.documents.map(enrich);
   clients().forEach(c=>{
    const k=meetingKey(c.name),record=typeof clientMeetingCard==='function'?clientMeetingCard(c):null;
    rows.push(enrich({id:'client-'+k,type:'customer',title:c.name,customer_key:k,date:record?.date||'',text:[c.profile,c.category,record?.card?.intro,...(record?.card?.highlights||[])].filter(Boolean).join('；'),tab:'clients',section:'客戶概況'}));
   });
   const available=[...new Set(rows.map(r=>r.customer_key).filter(Boolean))];
   $('ssCustomer').innerHTML='<option value="">全部</option>'+available.sort((a,b)=>(clientOf(a)?.name||a).localeCompare(clientOf(b)?.name||b)).map(k=>'<option value="'+esc(k)+'">'+esc(clientOf(k)?.name||k)+'</option>').join('');
   $('ssCoverage').textContent='索引更新：'+new Date(data.generated_at).toLocaleString('zh-TW')+'。每次拜訪採最新版 Word；有 Word 的會議以 Word 全文為準，保留不同拜訪日期。掃描圖片不含文字，需先完成文字辨識。日期／客戶篩選僅顯示具有該項資料的結果。';
   $('ssWarnings').innerHTML=(data.warnings||[]).map(w=>'<li>'+esc(w.file)+'：'+esc(w.reason)+'</li>').join('');
   loaded=true;render();
  }).catch(()=>{$('ssStatus').textContent='全文資料暫時無法載入，請重新開啟搜尋再試。';}).finally(()=>{loading=null;});
  return loading;
 }
 function currentRows(){
  // Reflect current B-4 data, including local edits, using its authoritative view.
  if(!window.CSCCustomerFollowups)return rows;
  const keys=clients().map(c=>({name:c.name,country:c.country})).concat([{name:'中貿',country:''}]);
  let current=[],ready=true;
  keys.forEach(c=>{const items=window.CSCCustomerFollowups.rows(c.name,c.country);if(!items){ready=false;return;}
   items.forEach((x,i)=>current.push(enrich({id:'live-'+(x.id||x.proposal_id||c.name+i),type:'followup',title:x.customer+'｜'+(x.topic||x.category||'追蹤事項'),customer:x.customer,customer_key:meetingKey(x.customer),country:x.country,date:x.visit_date||'',section:'B-4 目前追蹤清單',text:[x.task,x.note,x.owner,x.status].filter(Boolean).join('；'),tab:'followup'})));
  });return ready?rows.filter(r=>r.type!=='followup').concat(current):rows;
 }
 function render(){
  if(!loaded)return;const q=$('ssQuery').value.trim();
  if(!q){$('ssStatus').textContent='輸入關鍵字開始搜尋，例如：DC01、資料中心、進口比率、CBAM。';$('ssResults').innerHTML='';$('ssMore').hidden=true;return;}
  if($('ssFrom').value&&$('ssTo').value&&$('ssFrom').value>$('ssTo').value){$('ssStatus').textContent='起日不可晚於迄日。';return;}
  const result=engine.search(currentRows(),q,{type,country:$('ssCountry').value,customer:$('ssCustomer').value,from:$('ssFrom').value,to:$('ssTo').value,sort:$('ssSort').value});window.CSCSearchResults=result;
  $('ssStatus').textContent='找到 '+result.length+' 筆相關段落'+(result.length?'，顯示 '+Math.min(limit,result.length)+' 筆。':'。請縮短關鍵字或放寬篩選。');
  $('ssResults').innerHTML=result.slice(0,limit).map((r,i)=>{
   const url=safeURL(r.url);return '<article class="ss-result"><span class="ss-tag">'+esc(labels[r.type]||'網頁資料')+'</span><h3>'+highlighted(r.title)+'</h3><div class="ss-meta">'+esc([r.date,r.version,r.section].filter(Boolean).join('｜'))+'</div><p>'+highlighted(engine.snippet(r.text,q))+'</p><details><summary>查看相關段落</summary><p>'+highlighted(r.text)+'</p>'+(r.file?'<div class="ss-meta">來源：'+esc(r.file)+'</div>':'')+'</details><div class="ss-actions">'+(url?'<a target="_blank" rel="noopener noreferrer" href="'+esc(url)+'">'+(r.type==='meeting'?'開啟 Word':'開啟原始文件')+'</a>':'')+(clientOf(r.customer_key)?'<button type="button" data-ss-client="'+i+'">查看客戶</button>':'')+(r.tab?'<button type="button" data-ss-tab="'+i+'">前往相關網頁</button>':'')+'</div></article>';
  }).join('')||'<p class="ss-empty">目前沒有符合條件的資料。</p>';
  $('ssMore').hidden=result.length<=limit;
 }
 function close(){panel.hidden=true;document.body.style.overflow='';lastFocus?.focus();}
 document.querySelectorAll('[data-open-site-search]').forEach(b=>b.addEventListener('click',()=>{lastFocus=b;panel.hidden=false;document.body.style.overflow='hidden';$('ssQuery').focus();load();}));
 $('ssClose').onclick=close;
 panel.addEventListener('click',e=>{if(e.target===panel)close();});
 panel.addEventListener('keydown',e=>{
  if(e.key==='Escape'){e.preventDefault();close();}
  if(e.key==='Tab'){const focusable=[...panel.querySelectorAll('button,input,select,a,summary')].filter(x=>!x.hidden&&x.getClientRects().length);const first=focusable[0],last=focusable.at(-1);if(e.shiftKey&&document.activeElement===first){e.preventDefault();last.focus();}else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first.focus();}}
 });
 $('ssForm').onsubmit=e=>{e.preventDefault();limit=30;loaded?render():load();};
 $('ssTypes').onclick=e=>{const b=e.target.closest('[data-ss-type]');if(!b)return;type=b.dataset.ssType;limit=30;$('ssTypes').querySelectorAll('button').forEach(x=>x.setAttribute('aria-pressed',String(x===b)));render();};
 ['ssCountry','ssCustomer','ssFrom','ssTo','ssSort'].forEach(id=>$(id).onchange=()=>{limit=30;render();});
 $('ssMore').onclick=()=>{limit+=30;render();};
 $('ssResults').onclick=e=>{
  const b=e.target.closest('[data-ss-client],[data-ss-tab]');if(!b)return;
  const r=window.CSCSearchResults[Number(b.dataset.ssClient??b.dataset.ssTab)];close();
  if(b.hasAttribute('data-ss-client')){const i=clients().findIndex(c=>meetingKey(c.name)===r.customer_key);if(i>=0)openClientModal(i);}
  else if(r.tab==='followup'&&r.customer&&window.CSCCustomerFollowups)window.CSCCustomerFollowups.open(r.customer,r.country);
  else document.querySelector('.tabs [data-tab="'+r.tab+'"]')?.click();
 };
 window.addEventListener('customer-followups-ready',()=>{if(!panel.hidden)render();});
})();