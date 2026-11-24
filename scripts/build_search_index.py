"""Build deployment-time full-text search; original source text only."""
from pathlib import Path
from html.parser import HTMLParser
from datetime import datetime, timezone
import json,re,zipfile
import xml.etree.ElementTree as ET
from urllib.parse import quote
ROOT=Path(__file__).resolve().parents[1]
W='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
def clean(t):return re.sub(r'\s+',' ',str(t)).strip()
class Pages(HTMLParser):
 def __init__(self):super().__init__();self.depth=0;self.skip=0;self.tab='';self.title='';self.buf=[];self.rows=[];self.heading=False
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if tag in ('script','style'):self.skip+=1
  if self.tab:self.depth+=1
  elif tag=='section' and 'id' in a and 'panel' in a.get('class','').split():
   self.tab=a['id'];self.depth=1;self.buf=[]
  if self.tab and tag in ('h2','h3'):self.heading=True
  if self.tab and tag in ('p','tr','li','h2','h3','h4','div'):self.buf.append(' ')
 def handle_endtag(self,tag):
  if tag in ('script','style'):self.skip=max(0,self.skip-1)
  if self.tab:
   if tag in ('h2','h3'):self.heading=False
   # HTML void tags do not have end tags; excluded in start handler below.
   self.depth-=1
   if self.depth==0:
    t=clean(''.join(self.buf))
    if t:self.rows.append((self.tab,t))
    self.tab='';self.buf=[]
 def handle_data(self,data):
  if self.tab and not self.skip:self.buf.append(data+' ')
# Avoid depth changes for void elements.
_original_start=Pages.handle_starttag
def start(self,tag,attrs):
 if tag in ('input','img','br','hr','meta','link','source','wbr','area','base','col','embed','param','track'):return
 _original_start(self,tag,attrs)
Pages.handle_starttag=start
Pages.handle_startendtag=lambda self,tag,attrs:None
def build(root=ROOT):
 rows=[];warnings=[];seen=set();seq=0
 def add(kind,title,text,**meta):
  nonlocal seq
  text=clean(text)
  if not text:return
  identity=(kind,meta.get('url',''),meta.get('section',''),text)
  if identity in seen:return
  seen.add(identity);seq+=1
  rows.append(dict(id=str(seq),type=kind,title=title,text=text,**meta))
 index=json.loads((root/'meeting_records_index.json').read_text())
 for customer,group in index.get('customers',{}).items():
  for v in group.get('visits',[]):
   f=v.get('docx')
   if not f:continue
   path=root/'meeting_records'/f['name'];section='會議內文'
   try:
    with zipfile.ZipFile(path) as z:body=ET.fromstring(z.read('word/document.xml')).find(W+'body')
    def txt(e):return clean(' '.join(''.join(t.text or '' for t in p.iter(W+'t')) for p in e.iter(W+'p')))
    for block in list(body) if body is not None else []:
     value=txt(block)
     if not value:continue
     if block.tag==W+'p':
      if len(value)<110 and (re.match(r'^[一二三四五六七八九十]+[、.\s]',value) or value.startswith('附件')):section=value
      else:add('meeting',customer,value,customer_key=customer,date=v['date'],visit_id=v['id'],section=section,url=f['url'],file=f['name'],version=f['version'])
     elif block.tag==W+'tbl':
      for tr in block.findall(W+'tr'):
       value='；'.join(txt(tc) for tc in tr.findall(W+'tc'))
       add('meeting',customer,value,customer_key=customer,date=v['date'],visit_id=v['id'],section=section,url=f['url'],file=f['name'],version=f['version'])
   except Exception as e:warnings.append(dict(file=str(path.relative_to(root)),reason=str(e)[:160]))
 # Additional uploaded Word files outside the meeting collection.
 for path in root.rglob('*.docx'):
  if path.parent==root/'meeting_records' or any(p.startswith('.') for p in path.relative_to(root).parts):continue
  try:
   with zipfile.ZipFile(path) as z:body=ET.fromstring(z.read('word/document.xml')).find(W+'body')
   for block in list(body) if body is not None else []:
    text=clean(' '.join(t.text or '' for t in block.iter(W+'t')))
    add('document',path.stem,text,section='Word 文件',url=quote(str(path.relative_to(root)),safe='/'),file=path.name)
  except Exception as e:warnings.append(dict(file=str(path.relative_to(root)),reason=str(e)[:160]))
 # All text-bearing PDFs; duplicates of indexed meeting Word are omitted.
 pdfs=list(root.rglob('*.pdf'))
 allowed_meeting_pdfs={v['pdf']['name'] for g in index.get('customers',{}).values() for v in g.get('visits',[]) if v.get('pdf') and not v.get('docx')}
 word_stems={re.sub(r'[^a-z0-9]','',Path(r['file']).stem.lower()) for r in rows if r.get('file')}
 from pypdf import PdfReader
 for path in pdfs:
  if any(part.startswith('.') for part in path.relative_to(root).parts):continue
  if path.parent==root/'meeting_records' and path.name not in allowed_meeting_pdfs:continue
  if re.sub(r'[^a-z0-9]','',path.stem.lower()) in word_stems:continue
  try:
   reader=PdfReader(path);nonempty=False
   for i,page in enumerate(reader.pages):
    text=clean(page.extract_text() or '')
    if text:
     nonempty=True
     for pos in range(0,len(text),1400):
      add('document',path.stem,text[pos:pos+1400],section='第 '+str(i+1)+' 頁',url=quote(str(path.relative_to(root)),safe='/')+'#page='+str(i+1),file=path.name)
   if not nonempty:warnings.append(dict(file=str(path.relative_to(root)),reason='掃描或無文字 PDF，需文字辨識後才能搜尋全文'))
  except Exception as e:warnings.append(dict(file=str(path.relative_to(root)),reason=str(e)[:160]))
 tabs={'tariffs':'歐盟英國關稅查詢','quota':'中鋼銷歐額度及歐英通關','eu-country-quotas':'歐盟配額','uk-quotas':'英國配額','eu-cbam':'歐盟 CBAM','cbam':'UK CBAM','market-intel':'歐德英市場近況'}
 parser=Pages();parser.feed((root/'index.html').read_text())
 for tab,text in parser.rows:
  for pos in range(0,len(text),1100):add('policy' if tab in tabs else 'page',tabs.get(tab,tab),text[pos:pos+1100],tab=tab,section='網頁內容')
 sources={'customs_snapshot.json':'quota','eu_country_quotas.json':'eu-country-quotas','eu_quota.json':'quota','market_intelligence.json':'market-intel','tariffs.json':'tariffs','cbam_interviews.json':'eu-cbam','olap_clients_20261113.json':'orders','order_specs_template.json':'orders','customers.json':'clients','trip-data.json':'schedule','customer_locations.json':'customer-map'}
 def walk(value,label):
  if isinstance(value,list):
   for i,v in enumerate(value):yield from walk(v,label)
  elif isinstance(value,dict):
   scalars={k:v for k,v in value.items() if not isinstance(v,(dict,list)) and v is not None}
   if scalars:yield label+' '+json.dumps(scalars,ensure_ascii=False)
   for k,v in value.items():
    if isinstance(v,(dict,list)):yield from walk(v,label+' / '+k)
  elif value is not None:yield label+' '+str(value)
 for name,tab in sources.items():
  path=root/name
  if not path.exists():continue
  try:
   for value in walk(json.loads(path.read_text()),tabs.get(tab,tab)):
    add('followup' if tab=='followup' else 'customer' if tab=='clients' else 'policy' if tab in tabs else 'page',tabs.get(tab,name),value,tab=tab,file=name,section='網站資料')
  except Exception as e:warnings.append(dict(file=name,reason=str(e)[:160]))
 # Follow-up fallback mirrors Word precedence; the browser replaces it with live B-4 rows.
 suggestions=json.loads((root/'followup_suggestions.json').read_text()) if (root/'followup_suggestions.json').exists() else {}
 actions=json.loads((root/'followup_actions.json').read_text()) if (root/'followup_actions.json').exists() else {}
 proposals=suggestions.get('proposals',[])
 current={re.sub(r'[^A-Z0-9]','',str(x.get('customer','')).upper()) for x in proposals}
 for item in proposals+actions.get('items',[]):
  if item in actions.get('items',[]) and re.sub(r'[^A-Z0-9]','',str(item.get('customer','')).upper()) in current:continue
  add('followup',item.get('customer','')+'｜'+item.get('topic',item.get('category','追蹤事項')),'；'.join(str(item.get(k,'') or '') for k in ['task','note','owner','status']),customer=item.get('customer',''),customer_key=re.sub(r'[^A-Z0-9]','',item.get('customer','').upper()),country=item.get('country',''),date=item.get('visit_date',''),tab='followup',section='B-4 追蹤資料')
 payload=dict(schema_version=1,generated_at=datetime.now(timezone.utc).isoformat(),documents=rows,warnings=warnings)
 (root/'search_index.json').write_text(json.dumps(payload,ensure_ascii=False,separators=(',',':'))+'\n')
 print('Search index:',len(rows),'passages;',len(warnings),'source notices')
 return payload
if __name__=='__main__':build()
