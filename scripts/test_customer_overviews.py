"""Check reviewed summaries against the source Word, with quantity/year safeguards."""
from pathlib import Path
from hashlib import sha1
import json
import re
import tempfile
import unittest
import zipfile
import xml.etree.ElementTree as ET
from customer_knowledge import extract_knowledge, generic_knowledge
from test_meeting_sync import write_docx

ROOT = Path(__file__).resolve().parents[1]
FIELDS = ['procurement', 'import_ratio', 'downstream', 'products', 'outlook']
W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'

class CustomerOverviewTests(unittest.TestCase):
    def test_summaries_match_current_word_and_literal_evidence(self):
        summaries = json.loads((ROOT / 'customer_overview_summaries.json').read_text())['summaries']
        self.assertEqual(len({s['source_sha'] for s in summaries}), len(summaries))
        for summary in summaries:
            with self.subTest(customer=summary['customer_key']):
                path = ROOT / 'meeting_records' / summary['source_file']
                if not path.exists():
                    continue  # An administrator may remove a superseded upload.
                raw = path.read_bytes()
                current_sha = sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
                if summary['source_sha'] != current_sha:
                    self.assertEqual(extract_knowledge(path)['source_sha'], current_sha)
                    continue  # Changed Word must be allowed to deploy with literal extraction.
                with zipfile.ZipFile(path) as archive:
                    xml = ET.fromstring(archive.read('word/document.xml'))
                original = re.sub(r'\s+', ' ', ' '.join(''.join(t.text or '' for t in p.iter(W+'t')) for p in xml.iter(W+'p')))
                actual = extract_knowledge(path)
                self.assertEqual(actual['method'], 'reviewed_meeting_summary')
                for key in FIELDS:
                    self.assertTrue(actual['overview'][key], key)
                    self.assertEqual(actual['overview'][key], summary['overview'][key])
                    self.assertTrue(any(e['field'] == key for e in summary['evidence']), key+' original evidence')
                    for fact in actual['overview'][key]:
                        self.assertTrue(fact['text'] and fact['label'] and fact['source_label'])
                        self.assertIn(fact['relation'], ['direct', 'related'])
                for evidence in summary['evidence']:
                    self.assertIn(re.sub(r'\s+', ' ', evidence['quote']).strip(), original)

    def test_quantity_and_year_scopes_are_visible(self):
        rows = {s['customer_key']:s for s in json.loads((ROOT / 'customer_overview_summaries.json').read_text())['summaries']}
        texts = lambda key, field: json.dumps(rows[key]['overview'][field], ensure_ascii=False)
        self.assertIn('非採購量', texts('UPTON', 'procurement'))
        self.assertIn('99%', texts('UPTON', 'import_ratio'))
        self.assertIn('三據點', texts('AMDS', 'procurement'))
        self.assertIn('非境內採購', texts('AMDS', 'import_ratio'))
        self.assertIn('98%', texts('TOPTUBES', 'import_ratio'))
        self.assertIn('口徑待核對', texts('WILLIAMKING', 'procurement'))
        self.assertIn('兩據點', texts('WILLIAMKING', 'procurement'))
        self.assertIn('2023', texts('COOPERJACKSON', 'products'))
        self.assertIn('非全產品', texts('COOPERJACKSON', 'import_ratio'))
        self.assertIn('非全來源採購量', texts('BELMONT', 'procurement'))
        self.assertIn('非全公司', texts('STEELALLOY', 'products'))
        self.assertIn('非 Steelpark 單廠', texts('TATASTEELPARK', 'procurement'))

    def test_unreviewed_revision_falls_back_to_its_own_source(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / '2026-11-16_UPTON_STEEL_Meeting_Record_r99.docx'
            write_docx(path, ['項目', '會談紀要'], [['供應與產品', '年供應約130,000噸，進口料約占97%。'], ['客戶與用途', '服務醫療設備及照明客戶。']], heading='二、公司營運與採購概況')
            result = extract_knowledge(path)
            self.assertEqual(result['method'], 'source_excerpts')
            combined = json.dumps(result['overview'], ensure_ascii=False)
            self.assertIn('130,000', combined)
            self.assertIn('97%', combined)
            self.assertNotIn('99%', combined)

    def test_summary_production_and_import_phrasing_are_recognized(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'meeting.docx'
            write_docx(path, ['項目', '內容'], [['營運規模', '全年產量約35,000–40,000 MT，原料約98%仰賴進口。']], heading='一 、會議摘要')
            result = generic_knowledge(path)
            self.assertTrue(result['overview']['procurement'])
            self.assertTrue(result['overview']['import_ratio'])

if __name__ == '__main__':
    unittest.main()
