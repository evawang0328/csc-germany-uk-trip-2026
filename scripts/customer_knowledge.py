"""Customer knowledge from source-bound meeting excerpts, across Word layouts.

Reviewed summaries apply only to the exact document blob checked by the editor.
New revisions use the generic paragraph/table reader until separately reviewed.
No source excerpt changes official follow-up status or reported measurement scope.
"""
from pathlib import Path
from hashlib import sha1
import re
import zipfile
import xml.etree.ElementTree as ET

W='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'

def clean(value):return re.sub(r'\s+',' ',value).strip()
def text(el):return clean(' '.join(''.join(t.text or '' for t in p.iter(W+'t')) for p in el.iter(W+'p')))
def read_entries(path):
    with zipfile.ZipFile(path) as z: body=ET.fromstring(z.read('word/document.xml')).find(W+'body')
    entries=[];section='';last=None
    for block in list(body) if body is not None else []:
        if block.tag==W+'p':
            value=text(block)
            if not value or value.isdigit():continue
            if (re.match(r'^[一二三四五六七八九十]+[、.\s]',value) or value.startswith('附件')) and len(value)<100:
                section=value;last=None;continue
            if not section.startswith('附件'):
                entries.append({'label':section or '會議內文','text':value,'section':section})
        elif block.tag==W+'tbl' and not section.startswith('附件'):
            for tr in block.findall(W+'tr'):
                cells=[text(tc) for tc in tr.findall(W+'tc')]
                if len(cells)<2:continue
                label,value=cells[0],'；'.join(x for x in cells[1:] if x)
                if not value:continue
                if not label and last is not None:
                    last['text']+=' '+value;continue
                # Table headings vary across customer Word templates. They are
                # column labels, never a meeting fact or a historical topic.
                column_label=re.sub(r'\s+', '', label)
                if re.fullmatch(r'(?:項目|議題|面向|階段|產品|品項|案件|進度|狀態|鋼廠)(?:[／/](?:項目|進度|狀態|年度|用途|規格))*',column_label):continue
                if re.search('聯絡|Email|電話|出席人員|與會人員',label,re.I):continue
                last={'label':label,'text':value,'section':section};entries.append(last)
    return entries

def snippets(entry):
    value=re.sub(r'(?:^|\s)\d+[.、]\s*(?=[^\d\s])','\n',entry['text'])
    return [clean(v) for v in re.split(r'\n|[•●]|(?<=。)',value) if len(clean(v))>8]

def generic_knowledge(path):
    entries=read_entries(path);fields={k:[] for k in ['procurement','import_ratio','downstream','products','outlook','company']}
    def add(key,label,value,entry,related=False):
        if not any(x['text']==value for x in fields[key]):fields[key].append({'label':label,'text':value,'relation':'related' if related else 'direct','source_label':entry['label']})
    for e in entries:
        label,section=e['label'],e['section']
        if label=='公司名稱':continue
        if re.search('公司簡介|集團與分工|公司與規模|組織與規模|營運規模|產業',label):add('company',label,e['text'],e)
        if re.search(r'^[一二三四五六七八九十]+[、.\s]*(?:會議|客戶|拜訪)摘要',section) and len(e['text'])>25:add('company','會議摘要',e['text'],e)
        for value in snippets(e):
            business=bool(re.search('公司營運|採購概況|[一二三四五六七八九十]+[、.\s]*(?:會議|客戶|拜訪)摘要',section) or label in {'公司簡介','營運狀況','料源分佈','採購來源','下游與市場','產品組合'})
            if business and re.search(r'(?:年採購|採購量|用鋼量|需求[：:]?\s*\d|需求約\s*\d)',value):add('procurement','採購／全來源需求',value,e)
            elif business and re.search('(?:處理量|年銷量|年量|加工量)',value) and re.search(r'\d',value):
                kind='處理量／目標' if '處理量' in value else '銷量' if '銷量' in value else '加工／營運量'
                add('procurement',kind+'（非整體採購量）',value,e,True)
            if re.search('歷史|過去|回顧',value) and re.search(r'採購中鋼.*\d',value):add('procurement','歷史中鋼採購（非整體採購量）',value,e,True)
            if re.search('採購來源|料源分佈|主要料源|主要合作鋼廠',label+' '+section) or re.search('進口料源|進口占|進口量.*%|%進口料|%.*當地',value):add('import_ratio','進口比率／料源',value,e)
            if re.search('下游|客群|客戶與通路',label) or re.search(r'下游[：:]|下游客戶|客群含|汽車\s*\d.*%',value):add('downstream',label or '下游／客群',value,e)
            if re.search('產品組合|主要產品',label) or re.search('產品組合|冷軋.*佔|鍍鋅.*占|鍍鋅.*佔',value):add('products','產品結構',value,e)
            if re.search('討論主題|展望|市場行情',label+' '+section) and re.search('價格|鋼價|需求|展望|景氣|市場競爭|供應',value):add('outlook',label,value,e)
    for key in fields:fields[key]=fields[key][:4 if key=='outlook' else 2]
    topics=[]
    for entry in entries:
        if re.search('討論主題|合作機會|後續|追蹤|待辦',entry['label']+' '+entry['section']):
            if re.search('後續|追蹤|待辦',entry['section']) and not re.search('會議摘要',entry['section']):
                topics.append({'title':entry['label'],'text':entry['text'],'kind':'會議記載議題','status':'目前辦理狀態待確認','structured':True})
            elif re.search('討論主題|合作機會',entry['label']):
                for title,pattern in [('冷軋合作／報價',r'CR[：:]|冷軋訂單|冷軋.*供應商'),('EG 表面／規格',r'EG[：:]|EG價格|Rolling Mark|Band Mark'),('CBAM 資料需求',r'CBAM.*資料|CBAM.*資訊'),('配額與採購條件',r'配額.*限制|配額.*不確定')]:
                    quotes=[v for v in snippets(entry) if re.search(pattern,v,re.I)]
                    if quotes:topics.append({'title':title,'text':' '.join(quotes[:2]),'kind':'會議討論摘錄','status':'目前辦理狀態待確認'})
    company=fields['company'][0]['text'] if fields['company'] else ''
    # If the document uses a nonstandard summary heading, select its first
    # substantive meeting paragraph instead of silently showing no summary.
    if not company:
        candidates=[e['text'] for e in entries if re.search('摘要|營運概況|公司概況|公司背景',e['section']+' '+e['label']) and len(e['text'])>35]
        if candidates: company=candidates[0]
    intro=(company.split('。')[0][:230]+'。') if company else ''
    return {'overview':fields,'card':{'intro':intro,'highlights':[v[0]['text'] for k in ['procurement','import_ratio'] if (v:=fields[k])]},'topics':topics,'method':'source_excerpts'}

def fact(label,text,related=False):return {'label':label,'text':text,'relation':'related' if related else 'direct'}
def topic(title,text,kind='前次討論議題'):return {'title':title,'text':text,'kind':kind,'status':'本次辦理狀態待確認'}

# Values below were checked against all six currently uploaded DOCX files.
# SHA checks prevent an old summary from being silently attached to a revision.
import json
REVIEWED=json.loads(r'''{
  "5671f9e60b28089565254cba2370dfe907c6bfb2": {
    "card": {
      "intro": "1974 年成立的英國鋼材庫存與裁切業者，提供庫存、加工及隔日配送服務。",
      "highlights": [
        "每月目標處理量約 10,000 噸（非採購量）",
        "冷軋與鍍鋅各占約 35–40%；關注寬幅冷軋合作"
      ]
    },
    "overview": {
      "procurement": [
        {
          "label": "目標處理量（非採購量）",
          "text": "每月目標處理量約 10,000 噸，全年 120,000 噸；每天以自有 30–40 輛貨車運送約 500–530 噸。此為前次紀錄的處理目標與物流量。",
          "relation": "related"
        }
      ],
      "import_ratio": [
        {
          "label": "進口料源（比率未載明）",
          "text": "採購來源多元，包括中鋼、燁輝、裕鐵、CSVC、POSCO、越南鍍鋅廠及 Tata UK；前次紀錄未列整體進口占比。Tata UK 當時交期約 3–4 個月。",
          "relation": "related"
        }
      ],
      "downstream": [
        {
          "label": "客戶數與下游用途",
          "text": "下游客戶逾 1,000 家，包括雷射切割業者；原文未列各產業占比。",
          "relation": "direct"
        }
      ],
      "products": [
        {
          "label": "產品結構",
          "text": "冷軋 CR 約 35–40%、鍍鋅約 35–40%，其他如鍍鋁鋅約 10–15%。",
          "relation": "direct"
        }
      ],
      "outlook": [
        {
          "label": "2026 年 2 月市場觀察",
          "text": "當時冷軋無配額限制，出現冷軋價格低於熱軋／酸洗鋼的情況；進口競爭與配額政策不確定性使採購更複雜。此為前次會議觀察，不代表目前政策。",
          "relation": "direct"
        }
      ]
    },
    "topics": [
      {
        "title": "冷軋合作與寬幅規格",
        "text": "前次希望擴大中鋼冷軋供應，需求較多為 2.4–3.0 mm；關注 1,500 mm 寬規格。當時說明 BA 料寬度可至 1,250 mm；實際可供性須依鋼種與最新技術確認。",
        "kind": "前次合作機會",
        "status": "本次辦理狀態待確認"
      },
      {
        "title": "EG 表面品質／Band Mark",
        "text": "前次客戶表示 EG 表面要求高，當場未接受中鋼 Band Mark；後續是否改善、試樣及接受程度，需在本次拜訪重新確認。",
        "kind": "前次品質障礙",
        "status": "本次辦理狀態待確認"
      }
    ]
  },
  "15d5c3da1edc76e4128a33a0e892a2b0c490adb4": {
    "card": {
      "intro": "英國裁剪加工中心，採員工持股模式；逾 80% 業務以背對背交易降低價格風險。",
      "highlights": [
        "全來源需求約 2,500 MT／月；約 90% 進口料",
        "冷軋約占 70%；關注報價、EG 表面與 CBAM 資料"
      ]
    },
    "overview": {
      "procurement": [
        {
          "label": "全來源月需求",
          "text": "約 2,500 MT／月，其中冷軋約 1,700–1,800 MT（約 70%）；其餘為鍍面、電鍍及少量熱軋。此為客戶全來源需求，不是中鋼訂單。",
          "relation": "direct"
        }
      ],
      "import_ratio": [
        {
          "label": "進口比率與來源",
          "text": "約 90% 進口料、10% 當地料（客戶指定）；進口交期約 5–6 個月。CR 來源含 POSCO、JSW、NSC、CSVC；EG 來源含 POSCO、DONGBUK 及巴西。名稱沿用前次原文。",
          "relation": "direct"
        }
      ],
      "downstream": [
        {
          "label": "下游產業",
          "text": "家電、汽車、包裝、建築及 IT 機櫃。當時暖氣／鍋爐需求較強，油桶波動較大，汽車雖回升仍低於疫情前。",
          "relation": "direct"
        }
      ],
      "products": [
        {
          "label": "產品與加工",
          "text": "冷軋約占 70%，其餘為鍍面、電鍍及少量熱軋；設備為兩條分條線與一條 Blanking，最大分條寬度 1,830 mm、捲重 28 噸。",
          "relation": "direct"
        }
      ],
      "outlook": [
        {
          "label": "2026 年 2 月採購與價格",
          "text": "前次中鋼 CR 報價較 POSCO 高約 US$15–20／MT，尚待協商；EG 當時約 CFR US$780／MT。這些為歷史報價，不能當作目前行情。",
          "relation": "direct"
        },
        {
          "label": "前次需求展望",
          "text": "當時家電暖氣及鍋爐較強，油桶需求波動，汽車回升但低於疫情前；客戶以多元客群分散風險。",
          "relation": "direct"
        }
      ]
    },
    "topics": [
      {
        "title": "冷軋報價競爭力",
        "text": "前次中鋼 CR 報價較 POSCO 高約 US$15–20／MT，是否接受訂單仍需協商；本次應確認最新報價與採購意願。",
        "kind": "前次待協商事項",
        "status": "本次辦理狀態待確認"
      },
      {
        "title": "EG Rolling Mark 接受度",
        "text": "前次明載後續仍要與 STEMCOR 確認客戶是否願意接受中鋼 Rolling Mark；原文未記錄後續結論。",
        "kind": "前次待確認事項",
        "status": "本次辦理狀態待確認"
      },
      {
        "title": "CBAM 資料需求",
        "text": "前次英國客戶因產品出口歐盟而要求 CBAM 資料，並討論既有鋼廠資料期間與營運模式的可比性；需更新目前文件需求。",
        "kind": "前次討論議題",
        "status": "本次辦理狀態待確認"
      },
      {
        "title": "熱軋 1B／1A 配額限制",
        "text": "前次討論熱軋 1B 實際使用限制與 1A 額度不足；屬當時會議紀錄，最新規則須另查核。",
        "kind": "前次討論議題",
        "status": "本次辦理狀態待確認"
      }
    ]
  },
  "6cb07bd91c834d6c33c06a3de5d5e1f2fcdc0116": {
    "card": {
      "intro": "風控嚴謹的鋼材貿易商，採購以配額安全、DDP 成本與通路保護為核心。",
      "highlights": [
        "德國端歷史採購中鋼約 200,000 MT／年（非集團總量）",
        "主要合作料源含 Dexin、PT KP、Hyundai"
      ]
    },
    "overview": {
      "procurement": [
        {
          "label": "歷史中鋼採購（非整體採購量）",
          "text": "客戶回顧德國過去每年採購中鋼約 200,000 MT。這是歷史中鋼合作量，不是 Duferco 集團全年採購量或本次新增訂單。",
          "relation": "related"
        }
      ],
      "import_ratio": [
        {
          "label": "合作料源（進口占比未載明）",
          "text": "HR 與印尼 Dexin、PT KP 合作，CR 來源含 Hyundai；因配額及 CBAM 風險暫停承作越南 HDG。原文未提供整體進口占比。",
          "relation": "related"
        }
      ],
      "downstream": [
        {
          "label": "通路客戶（下游產業比例未載明）",
          "text": "與 SPAETER、HFS 互信較深，亦與 Knauf 合作。客戶表示 2025 年供應 SPAETER 約 250,000 MT，為全來源供貨，非中鋼銷售量。",
          "relation": "related"
        }
      ],
      "products": [
        {
          "label": "合作產品",
          "text": "主要討論熱軋 HR、冷軋 CR 及 HDG；願持續採購中鋼冷軋並拓展高品級鋼材，重視品質、交期與通路保護。",
          "relation": "direct"
        }
      ],
      "outlook": [
        {
          "label": "市場展望與個人判斷",
          "text": "德國流通需求偏弱、低價庫存壓抑報價；Duferco 代表個人看好 2027 Q2 價格並考慮自持庫存，尚非管理決策。雙方認同提高高強度與高品級料比重。",
          "relation": "direct"
        }
      ]
    },
    "topics": []
  },
  "8866b4ced75dcc66388902d4996c7a9f1e8670fc": {
    "card": {
      "intro": "德國多材料經銷與鋼材服務業者，與中鋼經 Duferco 合作逾 20 年。",
      "highlights": [
        "會議所述年採購約 180 萬噸，含鋼材、不鏽鋼及鋁",
        "合作重點：低碳冷熱軋、汽車用鋼與電磁鋼片"
      ]
    },
    "overview": {
      "procurement": [
        {
          "label": "會議所述年採購與庫存",
          "text": "年採購約 180 萬噸，含長條、扁平材、不鏽鋼及鋁；總庫存約 28–30 萬噸。不得當作單一服務中心或僅鋼材的採購量。",
          "relation": "direct"
        }
      ],
      "import_ratio": [
        {
          "label": "進口需求與來源（比率未載明）",
          "text": "客戶估計 2027 年全來源進口 HRC 約 30–40 萬噸、CRC 約 10–12 萬噸、鍍鋅約 10 萬噸，非中鋼訂單。進口來源含臺灣、越南、印尼；未列整體進口比例。",
          "relation": "related"
        }
      ],
      "downstream": [
        {
          "label": "客群與需求",
          "text": "終端用戶占 50–60%；客群涵蓋汽車、營建、機械、農機、家電與資料中心。汽車偏弱，卡車／拖車稼動與厚板業務近期改善。",
          "relation": "direct"
        }
      ],
      "products": [
        {
          "label": "採購與合作產品",
          "text": "長條、扁平材、不鏽鋼及鋁；與中鋼討論低碳冷熱軋、汽車用鋼及電磁鋼片。低碳 DC01 RC60 需求仍須規格、性能與碳排資料評估。",
          "relation": "direct"
        }
      ],
      "outlook": [
        {
          "label": "2027 年需求與價格",
          "text": "預期德國需求大致橫盤，鋼價於目前水準上下約 €20–30／噸波動；配額、價格與可供性仍是進口採購核心限制。",
          "relation": "direct"
        }
      ]
    },
    "topics": []
  },
  "bf5db774d6df42d9b82807bde4cd5f305f72d021": {
    "card": {
      "intro": "Knauf Interfer 以冷軋、鍍鋅及鋼材加工服務為主，具資料中心 EPD 與 EG 試樣合作機會。",
      "highlights": [
        "德國 SSC 6 據點，會議年量約 55 萬噸",
        "進口約 15–20%；冷軋與鍍鋅各約占 25%"
      ]
    },
    "overview": {
      "procurement": [
        {
          "label": "營運年量（非整體採購量）",
          "text": "德國 SSC 6 處據點年量約 55 萬噸，功能性金屬約 15 萬噸。原文是不同業務板塊的年量，未認定為合計採購量。",
          "relation": "related"
        }
      ],
      "import_ratio": [
        {
          "label": "進口比率與來源",
          "text": "進口占 15–20%、歐洲料占 80–85%；既有來源為臺灣、越南，亦採購印度與土耳其料，依價格及可供性調整。",
          "relation": "direct"
        }
      ],
      "downstream": [
        {
          "label": "客群與據點差異",
          "text": "客群含傢俱、家電、汽車、農機與資料中心。Mudersbach 年量 22.5 萬噸、其中傢俱約 15 萬噸，僅屬該據點，不推定為集團比例。",
          "relation": "direct"
        }
      ],
      "products": [
        {
          "label": "產品結構與強項",
          "text": "鍍鋅與冷軋各約占 25%；強項為薄規格、厚鍍層 GI。希望增加 CR／GI 進口，受配額限制。",
          "relation": "direct"
        }
      ],
      "outlook": [
        {
          "label": "2027 年需求與價格展望",
          "text": "下游對漲價的接受度有限，2026 年獲利與銷售困難。2027 年以維持客戶及既有量為主；年初漲價後，夏季可能因餘貨與淡季需求回檔。",
          "relation": "direct"
        }
      ]
    },
    "topics": []
  },
  "272b5ffa6dc1e1b125d801fbb2cf80997c9f075e": {
    "card": {
      "intro": "1992 年成立、由第二代經營的鋼材服務中心，在 Hagen 設兩處加工據點，汽車為主要下游。",
      "highlights": [
        "近期年銷量約 250,000–260,000 MT（非採購量）",
        "本次確認中鋼訂購 3,000 MT；關注 DC06／HC 與酸洗料"
      ]
    },
    "overview": {
      "procurement": [
        {
          "label": "近期年銷量（非採購量）",
          "text": "近期年銷量約 250,000–260,000 MT；2023 曆年加工量曾達 300,000 MT。銷量與加工量各有期間及口徑，不代替整體採購量。",
          "relation": "related"
        }
      ],
      "import_ratio": [
        {
          "label": "進口比率與來源",
          "text": "會中先述進口約 10–15%，回顧歷年則稱約 10–20%；兩種說法並列保留。進口多經 Duferco，主要來源為中鋼及 Hyundai，過去亦採 CSVC 熱浸鍍鋅。",
          "relation": "direct"
        }
      ],
      "downstream": [
        {
          "label": "下游與市場",
          "text": "汽車 40–50%、白色家電 10%、建築 15%、機械 15%、其他 15%；銷售地區德國 75%、外銷 25%。原文區間與比例照列，不自行調整為 100%。",
          "relation": "direct"
        }
      ],
      "products": [
        {
          "label": "產品結構",
          "text": "熱浸鍍鋅約 40–50%、熱軋酸洗約 25–30%、冷軋約 15–20%，其餘包括電鍍鋅、鋁鋅與鋅鎂鍍層材；以現貨為主，另有半年／年度合約。",
          "relation": "direct"
        }
      ],
      "outlook": [
        {
          "label": "2027 年展望",
          "text": "對 2027 年審慎，若缺乏政策或需求刺激，銷量可能小幅下降；部分終端延後或減少拉貨，增加庫存與資金壓力。",
          "relation": "direct"
        }
      ]
    },
    "topics": []
  }
}''')

def extract_knowledge(path):
    raw=path.read_bytes();blob=sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
    generic=generic_knowledge(path);reviewed=REVIEWED.get(blob)
    if reviewed:
        generic['overview'].update(reviewed.get('overview',{}));generic['card']=reviewed['card'];generic['topics']=reviewed.get('topics',[]);generic['method']='reviewed_meeting_summary'
    generic['source_sha']=blob
    return generic
