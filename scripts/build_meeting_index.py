#!/usr/bin/env python3
"""Build latest links, visit history, source excerpts and Word image assets.

Runs during Pages deployment using only the standard library. Each visit keeps
its own latest PDF and DOCX; consolidated date ranges remain one source record.
Overview fields are literal excerpts, never estimated or combined across visits.
"""
from __future__ import annotations
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path, PurePosixPath
from urllib.parse import quote
import json
import re
import zipfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
R = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'
A = '{http://schemas.openxmlformats.org/drawingml/2006/main}'
ALIASES = {'CARLSPAETERHQ':'SPAETER','CARLSPAETER':'SPAETER','SPAETER':'SPAETER',
 'KNAUFINTERFER':'KNAUF','KNAUF':'KNAUF','DUFERCO':'DUFERCO','HFS':'HFS',
 'UPTONSTEEL':'UPTON','UPTON':'UPTON','BELMONT':'BELMONT','TOPTUBES':'TOPTUBES',
 'STEELALLOY':'STEELALLOY','WILLIAMKING':'WILLIAMKING','COOPERJACKSON':'COOPERJACKSON'}

def text(el):
    return re.sub(r'\s+', ' ', ' '.join(''.join(t.text or '' for t in p.iter(W+'t')) for p in el.iter(W+'p'))).strip()

def parse_name(name):
    m = re.match(r'^(\d{4}[-.]\d{2}[-.]\d{2})(?:_(\d{2}))?[_\s-]+(.+)\.(pdf|docx)$', name, re.I)
    if not m:
        return None
    date, end, body, ext = m.groups()
    date = date.replace('.', '-')
    end_date = date[:8]+end if end else date
    try:
        datetime.strptime(date, '%Y-%m-%d'); datetime.strptime(end_date, '%Y-%m-%d')
        if end_date < date: return None
    except ValueError:
        return None
    meeting = re.search(r'(?:^|[_\s-])Meeting[_\s-]*Record(?:[_\s-]*r(\d+))?$', body, re.I)
    if not meeting:
        return None
    label = body[:meeting.start()].strip('_ -')
    normal = re.sub(r'[^A-Z0-9]', '', label.upper())
    customer = next((v for k,v in ALIASES.items() if normal.startswith(k)), normal)
    if not customer: return None
    kind = '晚餐交流' if re.search('Dinner', label, re.I) else '結束會議' if re.search('Clos(?:e|ing)', label, re.I) else '會議紀錄'
    if end: kind = '合併會議紀錄'
    revision = int(meeting.group(1) or 0)
    return customer, {'id':f'{date}_{end_date}_{kind}', 'date':date, 'end_date':end_date,
       'label':(date if date == end_date else date+' ～ '+end_date)+'｜'+kind,
       'kind':kind, 'revision':revision, 'ext':ext.lower(), 'name':name,
       'url':'meeting_records/'+quote(name), 'version':f'r{revision}' if revision else '未標版本'}

def read_word(path, asset_root):
    overview = {'procurement':[], 'import_ratio':[], 'downstream':[], 'products':[], 'outlook':[]}
    media, seen, section, attachment = [], set(), '', ''
    with zipfile.ZipFile(path) as z:
        body = ET.fromstring(z.read('word/document.xml')).find(W+'body')
        rels = {}
        if 'word/_rels/document.xml.rels' in z.namelist():
            for rel in ET.fromstring(z.read('word/_rels/document.xml.rels')):
                if rel.get('TargetMode') != 'External': rels[rel.get('Id')] = rel.get('Target', '')
        blocks = list(body) if body is not None else []
        for pos, block in enumerate(blocks):
            value = text(block)
            if block.tag == W+'p':
                if re.match(r'^[一二三四五六七八九十]+[、.\s]', value) and len(value)<90: section=value
                if re.match(r'^附件', value) and len(value)<100: attachment=value; section=value
                if re.search('市場行情|需求展望|市場展望', section) and value != section and value and not attachment and (len(value)>40 or '。' in value):
                    overview['outlook'].append({'label':section, 'text':value})
            elif block.tag == W+'tbl' and not attachment:
                for tr in block.findall(W+'tr'):
                    cells=[text(tc) for tc in tr.findall(W+'tc')]
                    if len(cells)<2: continue
                    label=cells[0]; excerpt='；'.join(x for x in cells[1:] if x)
                    if not excerpt: continue
                    if re.search('公司營運|採購概況',section):
                        for key, pattern in [('procurement',r'採購與庫存|年採購|採購量|用鋼量'),
                                             ('import_ratio',r'採購來源|進口比|進口比例|進口料|進口占'),
                                             ('downstream',r'下游|客群'),('products',r'產品組合|主要產品')]:
                            if re.search(pattern,label): overview[key].append({'label':label,'text':excerpt})
                    if re.search('市場行情|需求展望|市場展望',section) and re.search('展望|下游需求|價格形成|需求與',label):
                        overview['outlook'].append({'label':label,'text':excerpt})
            for blip in block.iter(A+'blip'):
                rid=blip.get(R+'embed'); target=rels.get(rid, '')
                member=PurePosixPath('word')/target if not target.startswith('/') else PurePosixPath(target.lstrip('/'))
                # Resolve '..' safely inside the ZIP; never use document paths on disk.
                import posixpath
                member=posixpath.normpath(str(member))
                if member not in z.namelist() or member in seen: continue
                ext=PurePosixPath(member).suffix.lower()
                if ext not in {'.png','.jpg','.jpeg','.gif','.webp'}: continue
                seen.add(member); data=z.read(member)
                if len(data)<3000: continue
                asset_root.mkdir(parents=True,exist_ok=True)
                dest=asset_root/(sha256(data).hexdigest()[:20]+ext)
                dest.write_bytes(data)
                after=text(blocks[pos+1]) if pos+1<len(blocks) and blocks[pos+1].tag==W+'p' else ''
                caption=after if after and not re.match(r'^附件',after) and len(after)<600 else attachment or '會議紀錄圖片'
                kind='card' if '名片' in attachment else 'photo' if re.search('合照|拜訪照片',attachment) else 'other'
                media.append({'url':str(dest.relative_to(ROOT)), 'kind':kind, 'caption':caption, 'section':attachment})
    return overview, media

def build(root=None):
    global ROOT
    if root is not None: ROOT=Path(root)
    customers={}
    for path in sorted((ROOT/'meeting_records').glob('*')):
        parsed=parse_name(path.name)
        if not parsed or not path.is_file(): continue
        key,item=parsed; group=customers.setdefault(key,{'visits':[]})
        visit=next((v for v in group['visits'] if v['id']==item['id']),None)
        if visit is None:
            visit={k:item[k] for k in ['id','date','end_date','label','kind']};group['visits'].append(visit)
        ext=item['ext']; existing=visit.get(ext)
        if existing is None or (item['revision'],item['name'].lower())>(existing['revision'],existing['name'].lower()):
            visit[ext]={k:item[k] for k in ['date','end_date','name','url','revision','version']}
            visit[ext]['visit_id']=item['id']
    for key,group in customers.items():
        group['visits'].sort(key=lambda v:(v['end_date'],v['date'],v['id']),reverse=True)
        for visit in group['visits']:
            pdf,word=visit.get('pdf'),visit.get('docx')
            visit['version_mismatch']=bool(pdf and word and pdf['revision']!=word['revision'])
            if word:
                try:
                    visit['overview'],visit['media']=read_word(ROOT/'meeting_records'/word['name'],ROOT/'meeting_media'/key/sha256(word['name'].encode()).hexdigest()[:10])
                except (zipfile.BadZipFile,ET.ParseError,KeyError,OSError) as e:
                    visit['extraction_error']=str(e)[:160]
        for ext in ['pdf','docx']:
            candidate=next((v[ext] for v in group['visits'] if v.get(ext)),None)
            if candidate: group[ext]=candidate
        pdf,word=group.get('pdf'),group.get('docx')
        group['version_mismatch']=bool(pdf and word and (pdf['visit_id'],pdf['revision'])!=(word['visit_id'],word['revision']))
    payload={'schema_version':'2.0','generated_at':datetime.now(timezone.utc).isoformat(timespec='seconds'),'source':'meeting_records/','customers':customers}
    (ROOT/'meeting_records_index.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'Built meeting index: {len(customers)} customers, {sum(len(v["visits"]) for v in customers.values())} visits')
    return payload

if __name__ == '__main__': build()
