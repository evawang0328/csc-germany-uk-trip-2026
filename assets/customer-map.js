/* Customer locations: static verified data, lazy map loading, no geocoding on page use. */
(function(global){
 'use strict';
 const normalize=value=>String(value||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
 const sortLocations=items=>items.slice().sort((a,b)=>Number(b.role==='trader')-Number(a.role==='trader')||a.name.localeCompare(b.name,'en'));
 const filterLocations=(items,country,query)=>sortLocations(items.filter(x=>x.country===country&&normalize([x.name,x.alias||'',x.city,x.address].join(' ')).includes(normalize(query).trim())));
 const located=x=>Number.isFinite(x.lat)&&Number.isFinite(x.lng)&&Math.abs(x.lat)<=90&&Math.abs(x.lng)<=180;
 const mapsURL=x=>'https://www.google.com/maps/dir/?api=1&destination='+encodeURIComponent(x.address||x.city+', '+(x.country==='DE'?'Germany':'United Kingdom'));
 if(typeof module!=='undefined'&&module.exports)module.exports={filterLocations,sortLocations,located,mapsURL};
 if(typeof document==='undefined')return;
 const root=document.getElementById('customer-map');if(!root)return;
 const $=id=>document.getElementById(id),esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const countries={DE:'德國',UK:'英國'},centers={DE:[51.4,7.0],UK:[52.6,-1.9]};
 let country='DE',data=[],map=null,cluster=null,selected='',bootPromise=null,loaded=false;
 const markers=new Map(),views={};
 function sourceURL(value){try{const u=new URL(value);return u.protocol==='https:'?u.href:'';}catch{return '';}}
 function list(){return filterLocations(data,country,$('cmSearch').value);}
 function setStatus(text){$('cmStatus').textContent=text;}
 function renderList(){
  const items=list();
  $('cmCountryTitle').textContent=countries[country]+'客戶地點';
  $('cmCount').textContent=items.length+' 個據點';
  $('cmList').innerHTML=items.map(x=>'<button type="button" class="cm-customer'+(x.role==='trader'?' cm-trader':'')+(selected===x.key?' selected':'')+'" data-cm-select="'+esc(x.key)+'" aria-pressed="'+(selected===x.key)+'"><span><strong>'+esc(x.name)+'</strong>'+(x.role==='trader'?'<span class="cm-trader-badge">貿易商</span>':'')+'</span><small>'+esc(x.city)+(located(x)?'':'｜位置待確認')+'</small></button>').join('')||'<p class="cm-empty">沒有符合的客戶，請更換搜尋文字。</p>';
 }
 function popup(x){
  const source=sourceURL(x.source_url);
  return '<div class="cm-popup"><div class="cm-popup-title"><strong>'+esc(x.name)+'</strong><span class="'+(x.role==='trader'?'cm-trader-badge':'cm-customer-badge')+'">'+(x.role==='trader'?'貿易商':'客戶')+'</span></div><p>'+esc(x.address||x.city)+'</p>'+(x.location_note?'<p class="cm-location-note">'+esc(x.location_note)+'</p>':'')+(x.precision==='city'?'<p class="cm-location-note">城市範圍定位；尚未確認精確門牌座標。</p>':'')+'<div class="cm-popup-actions"><button type="button" data-cm-profile="'+esc(x.key)+'">客戶資料</button><a href="'+esc(mapsURL(x))+'" target="_blank" rel="noopener noreferrer">Google Maps 導航</a></div>'+(source?'<a class="cm-source" href="'+esc(source)+'" target="_blank" rel="noopener noreferrer">地址來源</a>':'')+'<span class="cm-source-date">核對：'+esc(x.verified_at||'待確認')+'</span></div>';
 }
 function fit(){
  if(!map)return;
  map.invalidateSize();
  const points=list().filter(located).map(x=>[x.lat,x.lng]);
  if(points.length)map.fitBounds(points,{padding:[44,44],maxZoom:points.length===1?14:11,animate:false});
  else map.setView(centers[country],country==='DE'?8:6,{animate:false});
 }
 function renderMarkers(){
  if(!map)return;
  const postalCredit='UK postcode data: <a href="https://postcodes.io/docs/licences/" target="_blank" rel="noopener noreferrer">Postcodes.io / OS OpenData</a>, © Crown &amp; Royal Mail 2025';
  map.attributionControl.removeAttribution(postalCredit);
  if(country==='UK')map.attributionControl.addAttribution(postalCredit);
  cluster.clearLayers();markers.clear();
  for(const x of list().filter(located)){
   const marker=L.marker([x.lat,x.lng],{title:x.name,alt:x.name,keyboard:true,icon:L.divIcon({className:'cm-pin-icon',html:'<span class="cm-pin'+(x.role==='trader'?' cm-pin-trader':'')+'"></span>',iconSize:[30,36],iconAnchor:[15,33],popupAnchor:[0,-30]})});
   marker.bindTooltip(x.name,{permanent:true,direction:'right',offset:[12,-18],className:'cm-map-label'});
   marker.bindPopup(popup(x),{maxWidth:330,minWidth:230});
   marker.on('click',()=>{selected=x.key;renderList();});
   markers.set(x.key,marker);cluster.addLayer(marker);
  }
 }
 function select(key){
  const x=data.find(row=>row.key===key);if(!x)return;
  selected=key;renderList();
  if(map&&markers.has(key))cluster.zoomToShowLayer(markers.get(key),()=>{map.setView([x.lat,x.lng],Math.max(map.getZoom(),x.precision==='city'?10:14));markers.get(key).openPopup();if(global.matchMedia('(max-width:760px)').matches)$('cmMap').scrollIntoView({behavior:global.matchMedia('(prefers-reduced-motion:reduce)').matches?'auto':'smooth',block:'center'});});
  else{setStatus(x.name+' 的精確座標待確認；可使用 Google Maps 查詢已核對地址。');$('cmAddressDetails').hidden=false;$('cmAddressDetails').innerHTML=popup(x);}
 }
 function loadScript(src){return new Promise((resolve,reject)=>{const s=document.createElement('script');s.src=src;s.onload=resolve;s.onerror=()=>{s.remove();reject(Error('地圖程式無法載入'));};document.head.appendChild(s);});}
 async function boot(){
  if(bootPromise)return bootPromise;
  bootPromise=(async()=>{
   setStatus('正在載入客戶地圖…');
   try{
    if(!loaded){const response=await fetch('customer_locations.json');if(!response.ok)throw Error('客戶地點資料無法載入');const payload=await response.json();if(!Array.isArray(payload.locations))throw Error('地點資料格式有誤');data=payload.locations;loaded=true;renderList();}
    if(!global.L)await loadScript('assets/vendor/leaflet/leaflet.js');
    if(!L.markerClusterGroup)await loadScript('assets/vendor/leaflet-markercluster/leaflet.markercluster.js');
    map=L.map('cmMap',{zoomControl:false,scrollWheelZoom:true,minZoom:3,maxZoom:19});
    L.control.zoom({position:'topright',zoomInTitle:'放大地圖',zoomOutTitle:'縮小地圖'}).addTo(map);
    L.control.scale({imperial:false,position:'bottomleft'}).addTo(map);
    const tiles=L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap</a> contributors'}).addTo(map);
    tiles.on('tileerror',()=>{setStatus('底圖暫時無法完整載入；客戶標記、清單及 Google Maps 連結仍可使用。');});
    cluster=L.markerClusterGroup({maxClusterRadius:45,showCoverageOnHover:false,spiderfyOnMaxZoom:true,iconCreateFunction:group=>L.divIcon({className:'cm-cluster'+(group.getAllChildMarkers().every(m=>data.find(x=>markers.get(x.key)===m)?.role==='trader')?' cm-cluster-trader':''),html:'<span>'+group.getChildCount()+'</span>',iconSize:[40,40]})});
    map.addLayer(cluster);renderMarkers();fit();
    $('cmFallback').hidden=true;
    $('cmAddressDetails').hidden=true;
    setStatus('可拖曳、使用＋／－或觸控縮放；點選數字群組可展開客戶。');
    new ResizeObserver(()=>map?.invalidateSize()).observe($('cmShell'));
   }catch(error){bootPromise=null;setStatus(error.message+'。請重新載入地圖，或由清單使用 Google Maps。');$('cmFallback').hidden=false;renderList();}
  })();return bootPromise;
 }
 function open(){boot().then(()=>{if(map){map.invalidateSize();if(views[country])map.setView(views[country].center,views[country].zoom,{animate:false});else fit();}});}
 function changeCountry(next){
  if(!countries[next]||next===country)return;
  if(map)views[country]={center:map.getCenter(),zoom:map.getZoom()};
  country=next;selected='';$('cmSearch').value='';
  root.querySelectorAll('[data-cm-country]').forEach(b=>{const active=b.dataset.cmCountry===country;b.classList.toggle('active',active);b.setAttribute('aria-selected',String(active));b.tabIndex=active?0:-1;});
  $('cmMap').setAttribute('aria-label',countries[country]+'客戶互動地圖');
  renderList();renderMarkers();
  if(map){if(views[country])map.setView(views[country].center,views[country].zoom,{animate:false});else fit();}
 }
 async function exitFullscreen(){if(document.fullscreenElement)await document.exitFullscreen();$('cmShell').classList.remove('cm-fullscreen');$('cmFullscreen').textContent='全螢幕';$('cmFullscreen').setAttribute('aria-pressed','false');map?.invalidateSize();}
 async function fullscreen(){
  if(document.fullscreenElement||$('cmShell').classList.contains('cm-fullscreen'))return exitFullscreen();
  try{if(!$('cmShell').requestFullscreen)throw Error();await $('cmShell').requestFullscreen();}catch{$('cmShell').classList.add('cm-fullscreen');}
  $('cmFullscreen').textContent='退出全螢幕';$('cmFullscreen').setAttribute('aria-pressed','true');
  map?.invalidateSize();
 }
 root.addEventListener('click',async e=>{
  const countryButton=e.target.closest('[data-cm-country]');if(countryButton){changeCountry(countryButton.dataset.cmCountry);return;}
  const item=e.target.closest('[data-cm-select]');if(item){select(item.dataset.cmSelect);return;}
  const profile=e.target.closest('[data-cm-profile]');if(profile){const x=data.find(x=>x.key===profile.dataset.cmProfile);await exitFullscreen();if(x)global.dispatchEvent(new CustomEvent('customer-map-open-profile',{detail:{key:x.customer_key,name:x.name}}));}
 });
 $('cmSearch').addEventListener('input',()=>{selected='';renderList();renderMarkers();fit();});
 $('cmFit').addEventListener('click',()=>{$('cmSearch').value='';selected='';renderList();renderMarkers();fit();});
 $('cmFullscreen').addEventListener('click',fullscreen);
 $('cmRetry').addEventListener('click',open);
 root.querySelector('[role="tablist"]').addEventListener('keydown',e=>{if(['ArrowLeft','ArrowRight','Home','End'].includes(e.key)){e.preventDefault();changeCountry(e.key==='Home'?'DE':e.key==='End'?'UK':country==='DE'?'UK':'DE');root.querySelector('[data-cm-country="'+country+'"]').focus();}});
 document.addEventListener('keydown',e=>{if(e.key==='Escape'&&$('cmShell').classList.contains('cm-fullscreen'))void exitFullscreen();});
 document.addEventListener('fullscreenchange',()=>{const active=!!document.fullscreenElement||$('cmShell').classList.contains('cm-fullscreen');$('cmFullscreen').textContent=active?'退出全螢幕':'全螢幕';$('cmFullscreen').setAttribute('aria-pressed',String(active));map?.invalidateSize();});
 document.querySelector('.tabs [data-tab="customer-map"]')?.addEventListener('click',open);
 global.CSCCustomerMap={open,showCountry:changeCountry};
})(typeof window!=='undefined'?window:globalThis);
