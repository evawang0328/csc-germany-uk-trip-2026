#!/usr/bin/env python3
"""Refresh non-paywalled public-news *headlines* only; no hallucinated AI summaries."""
import datetime as dt
import email.utils
import html
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILE = ROOT / 'market_intelligence.json'
TZ = dt.timezone(dt.timedelta(hours=8))
NOW = dt.datetime.now(TZ)
CUTOFF = (NOW - dt.timedelta(days=14)).date()
UA = 'CSC-EU-Market-Brief/1.0 (public headlines / attribution; RSS)' 
MAX_ITEMS = 30

FEEDS = [
 ('EUROMETAL','https://eurometal.net/feed/'),
 ('Eurostat','https://news.google.com/rss/search?q='+urllib.parse.quote('site:ec.europa.eu/eurostat industrial production construction steel')+'&hl=en&gl=GB&ceid=GB:en'),
 ('Destatis','https://news.google.com/rss/search?q='+urllib.parse.quote('site:destatis.de industrial production manufacturing orders 2026')+'&hl=en&gl=GB&ceid=GB:en'),
 ('ONS','https://news.google.com/rss/search?q='+urllib.parse.quote('site:ons.gov.uk construction manufacturing output')+'&hl=en&gl=GB&ceid=GB:en'),
 ('worldsteel','https://news.google.com/rss/search?q='+urllib.parse.quote('site:worldsteel.org crude steel production')+'&hl=en&gl=GB&ceid=GB:en'),
 ('ArcelorMittal','https://news.google.com/rss/search?q='+urllib.parse.quote('site:corporate.arcelormittal.com europe steel earnings')+'&hl=en&gl=GB&ceid=GB:en'),
 ('GOV.UK','https://news.google.com/rss/search?q='+urllib.parse.quote('site:gov.uk steel strategy steel trade measure tariff')+'&hl=en&gl=GB&ceid=GB:en'),
 ('EUROFER','https://news.google.com/rss/search?q='+urllib.parse.quote('site:eurofer.eu steel market outlook demand')+'&hl=en&gl=GB&ceid=GB:en'),
]
KEYWORDS = re.compile(r'\b(steel|metal|coil|HRC|CRC|galvaniz|hot.roll|cold.roll|blast furnace|tariff|quota|manufactur|industrial|automotiv|vehicle|construction|infrastructure|capacity|trade|iron|energy|service centre|service center|scrap|export|production|orders|demand)\b', re.I)
EXCLUDE = re.compile(r'\bseamless (?:pipes?|tubes?)\b', re.I)
PRICE = re.compile(r'price|HRC|CRC|coil|offers?|demand|restock|distribut|service centr|service cent|stockhold',re.I)
DOWNSTREAM = re.compile(r'automotiv|vehicle|machiner|construct|infrastructure|manufactur|industr|new order',re.I)
POLICY = re.compile(r'tariff|quota|trade measure|safeguard|CBAM|anti.dumping|policy|strategy|commission|regulation',re.I)
STEELMAKER = re.compile(r'blast furnace|production|capacity|crude steel|steelmak|investment|plant|ArcelorMittal',re.I)
REGIONS = {
 'DE':re.compile(r'German|Germany|Duisburg|Destatis|Thyssen|Salzgitter', re.I),
 'UK':re.compile(r'UK\b|Britain|British|England|Wales|ONS\b|Tata Steel UK|London|Scunthorpe',re.I),
 'EU':re.compile(r'EU\b|European|Europe|Eurostat|Eurofer|Brussels|ArcelorMittal|Italy|Italian|Nordic|French|Polish|Spanish',re.I)
}

def get_items(source, url):
  request = urllib.request.Request(url, headers={'User-Agent':UA,'Accept':'application/rss+xml,application/xml,text/xml;q=0.9,*/*;q=0.5'})
  with urllib.request.urlopen(request,timeout=18) as response:
    payload=response.read(1_500_000)
  root=ET.fromstring(payload)
  entries=root.findall('.//item')
  result=[]
  for e in entries[:35]:
    def txt(tag):
      el=e.find(tag)
      return ''.join(el.itertext()).strip() if el is not None else ''
    title=html.unescape(re.sub('<[^>]+>','',txt('title'))).strip()
    link=txt('link').strip()
    date_str=txt('pubDate')
    try: published=email.utils.parsedate_to_datetime(date_str).astimezone(TZ).date()
    except Exception: continue
    if not title or published<CUTOFF or published>NOW.date() or not link: continue
    if not KEYWORDS.search(title) or EXCLUDE.search(title): continue
    # Protect source attribution: Google RSS links are to Google news, not falsely labelled publisher URLs.
    if source == 'EUROMETAL' and not urllib.parse.urlsplit(link).netloc.endswith('eurometal.net'): continue
    cat=('政經政策' if POLICY.search(title) else '下游需求' if DOWNSTREAM.search(title) else '價格／供需' if PRICE.search(title) else '產能鋼廠' if STEELMAKER.search(title) else '價格／供需')
    regions=[k for k,pat in REGIONS.items() if pat.search(title)]
    if source in {'Eurostat','worldsteel','EUROFER','ArcelorMittal','EUROMETAL'} and 'EU' not in regions:regions.append('EU')
    if source=='Destatis' and 'DE' not in regions:regions.append('DE')
    if source=='ONS' and 'UK' not in regions:regions.append('UK')
    if source=='GOV.UK' and 'UK' not in regions:regions.append('UK')
    if not regions:regions=['EU']
    implication={'價格／供需':'關注報價、實際成交、服務中心庫存及客戶補庫時間。','產能鋼廠':'關注復產、產能利用率、交期及產量變化。','下游需求':'留意下游客戶實際拉貨及中鋼產品規格需求。','政經政策':'核對最新政策適用範圍與進口成本；以主管機關公告為準。'}[cat]
    result.append({'title':title,'date':published.isoformat(),'source':source,'url':link,'regions':regions,'category':cat,
                   'summary':'來源新聞標題：'+title,'implication':implication})
  return result

def main():
  data=json.loads(FILE.read_text(encoding='utf-8'))
  prior=data.get('items',[])
  found=[]
  errors=[]
  for source,url in FEEDS:
    try:
      items=get_items(source,url)
      found.extend(items)
      print(f'{source}: {len(items)} filtered articles')
    except Exception as exc:
      errors.append(f'{source} ({type(exc).__name__})')
      print(f'Warning: {source}: {exc}',file=sys.stderr)
    time.sleep(0.4)
  if not found:
    # Keep previously verified JSON; do not claim it was refreshed if all sources failed.
    print('No new fetched articles. Retaining existing file unchanged.'); return
  combined=found+prior
  seen=set(); unique=[]
  for row in sorted(combined,key=lambda r:r.get('date',''),reverse=True):
    if not row.get('url') or not row.get('title'):continue
    key=re.sub(r'[^a-z0-9]+','',row['title'].casefold())[:110]
    if key in seen:continue
    seen.add(key);unique.append(row)
  unique=unique[:MAX_ITEMS]
  previous=json.dumps(prior,ensure_ascii=False,sort_keys=True)
  current=json.dumps(unique,ensure_ascii=False,sort_keys=True)
  if previous==current:
    print('No substantive new headlines; keeping existing file.');return
  data['items']=unique
  data['generated_at']=NOW.strftime('%Y-%m-%d %H:%M')
  data['mode']='每日自動蒐集公開標題＋來源連結（不使用付費 AI）'
  data['warning']='部分來源更新失敗：'+', '.join(errors) if errors else ''
  FILE.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
  print(f'Saved {len(unique)} items at {data["generated_at"]}')

if __name__=='__main__':main()
