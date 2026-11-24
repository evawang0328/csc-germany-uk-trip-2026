"""Integration checks against actual source documents, plus a synthetic Word table."""
from pathlib import Path
import json,tempfile,zipfile,unittest
import build_search_index as search
ROOT=Path(__file__).resolve().parents[1]
class SearchTests(unittest.TestCase):
 def test_word_paragraph_and_table(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'meeting_records').mkdir()
   with zipfile.ZipFile(p/'meeting_records'/'test.docx','w') as z:
    z.writestr('word/document.xml','<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>七、合作商機</w:t></w:r></w:p><w:p><w:r><w:t>資料中心冷軋</w:t></w:r></w:p><w:tbl><w:tr><w:tc><w:p><w:r><w:t>DC01</w:t></w:r></w:p></w:tc><w:tc><w:p><w:r><w:t>2.5 mm</w:t></w:r></w:p></w:tc></w:tr></w:tbl></w:body></w:document>')
   (p/'meeting_records_index.json').write_text(json.dumps({'customers':{'UPTON':{'visits':[{'id':'visit','date':'2026-11-16','docx':{'name':'test.docx','url':'meeting_records/test.docx','version':'r2'}}]}}}))
   (p/'index.html').write_text('<section id="quota" class="panel"><h2>通關資料</h2><input><p>配額餘量</p></section>')
   data=search.build(p);r=data['documents']
   self.assertTrue(any('資料中心冷軋' in x['text'] and x.get('section')=='七、合作商機' for x in r))
   self.assertTrue(any('DC01；2.5 mm'==x['text'] for x in r))
   self.assertTrue(any(x.get('tab')=='quota' and '配額餘量' in x['text'] for x in r))
 def test_live_build_sources(self):
  data=json.loads((ROOT/'search_index.json').read_text());rows=data['documents']
  self.assertGreater(len(rows),50)
  idx=json.loads((ROOT/'meeting_records_index.json').read_text())
  for key,g in idx['customers'].items():
   for v in g['visits']:
    if v.get('docx') and not v.get('extraction_error'):
     self.assertTrue(any(r.get('file')==v['docx']['name'] and r.get('customer_key')==key for r in rows),v['docx']['name'])
  self.assertTrue(any(r.get('tab')=='quota' for r in rows))
if __name__=='__main__':unittest.main()
