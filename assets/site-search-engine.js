/* Full-text keyword matching; shared with Node validation. */
(function(root){
 const normalize=v=>String(v??'').normalize('NFKC').toLowerCase();
 function tokens(q){return [...new Set(normalize(q).trim().split(/\s+/).filter(Boolean))].slice(0,12);}
 function search(rows,q,filters={}){
  const terms=tokens(q);if(!terms.length)return [];
  return rows.map(r=>{
   if(filters.type&&r.type!==filters.type||filters.country&&r.country!==filters.country||filters.customer&&r.customer_key!==filters.customer||filters.from&&(!r.date||r.date<filters.from)||filters.to&&(!r.date||r.date>filters.to))return null;
   const title=normalize(r.title+' '+(r.customer||'')+' '+(r.section||'')),body=normalize(r.text),all=title+' '+body;
   if(!terms.every(t=>all.includes(t)))return null;
   const score=terms.reduce((n,t)=>n+(title.includes(t)?8:0)+(body.includes(t)?2:0),0)+(all.includes(normalize(q))?4:0);
   return {...r,score};
  }).filter(Boolean).sort((a,b)=>filters.sort==='date'?String(b.date||'').localeCompare(String(a.date||''))||b.score-a.score:b.score-a.score||String(b.date||'').localeCompare(String(a.date||'')));
 }
 function snippet(text,q,size=230){
  text=String(text||'');const positions=tokens(q).map(t=>normalize(text).indexOf(t)).filter(i=>i>=0),at=positions.length?Math.min(...positions):0,start=Math.max(0,at-65);
  return (start?'…':'')+text.slice(start,start+size)+(text.length>start+size?'…':'');
 }
 const api={normalize,tokens,search,snippet};if(typeof module!=='undefined')module.exports=api;else root.CSCSearchEngine=api;
})(globalThis);
