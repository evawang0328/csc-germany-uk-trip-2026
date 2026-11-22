#!/usr/bin/env python3
"""Regression checks for source-bound automatic follow-up extraction."""
from pathlib import Path
import tempfile
import unittest
from xml.sax.saxutils import escape
import zipfile
import json
from unittest.mock import patch
import extract_meeting_followups as extraction
from extract_meeting_followups import rows_from_docx, source_row_published, DISPLAY
from build_meeting_index import parse_name
from customer_knowledge import generic_knowledge

def write_docx(path, header, data, heading="八、中鋼合作方向與後續辦理事項"):
    def paragraph(value):
        return "<w:p><w:r><w:t>" + escape(value) + "</w:t></w:r></w:p>"
    def row(cells):
        return "<w:tr>" + "".join("<w:tc>" + paragraph(v) + "</w:tc>" for v in cells) + "</w:tr>"
    xml = '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>' + paragraph(heading) + "<w:tbl>" + row(header) + "".join(row(values) for values in data) + "</w:tbl></w:body></w:document>"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("word/document.xml", xml)

class FollowupSyncTests(unittest.TestCase):
    def test_william_king_uploaded_filename(self):
        key, record = parse_name("2026-11-17_William_King_Meeting_Record r2.docx")
        self.assertEqual(key, "WILLIAMKING")
        self.assertEqual(record["revision"], 2)
        self.assertEqual(DISPLAY[key], "William King")
    def test_two_column_cooperation_table(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "meeting.docx"
            write_docx(path, ["合作方向", "商機及辦理重點"], [
                ["資料中心冷軋", "優先評估 DC01 2.5 mm × 1,000 mm，取得年度需求。"],
                ["RC 與低碳專案", "取得正式綠鋼定義與 Rittal 計畫，確認查驗進度。"]])
            rows = rows_from_docx(path)
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["topic"], "資料中心冷軋")
            self.assertEqual(rows[0]["row"], 2)
            self.assertIn("Rittal", rows[1]["task"])
            self.assertEqual(rows[0]["owner"], "")
    def test_existing_responsibility_layout(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "meeting.docx"
            write_docx(path, ["議題", "追蹤事項", "責任窗口"], [["規格", "確認厚度與寬度及試料需求", "待指定"]])
            rows = rows_from_docx(path)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["owner"], "待指定")
    def test_description_column_in_followup_section(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "meeting.docx"
            write_docx(path, ["產品／進度", "說明", "PIC"], [
                ["冷軋詢單", "爭取第二季冷軋及特殊強度料續供。", "中貿"],
                ["搪瓷鋼", "追蹤 DC04 ED／EK 加工及品質結果。", "中貿"],
                ["酸洗轉冷軋", "評估特定酸洗規格改用冷軋。", "中貿"]], heading="七、產品商機與後續辦理事項")
            rows = rows_from_docx(path)
            self.assertEqual(len(rows), 3)
            self.assertEqual([row["topic"] for row in rows], ["冷軋詢單", "搪瓷鋼", "酸洗轉冷軋"])
            self.assertTrue(all(row["owner"] == "中貿" for row in rows))
            self.assertTrue(all(row["note"] == "" for row in rows))
            self.assertIn("DC04 ED／EK", rows[1]["task"])
    def test_description_table_outside_followup_is_not_an_action(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "meeting.docx"
            write_docx(path, ["產品／進度", "說明", "PIC"], [["冷軋", "客戶現有產品及加工能力說明。", "中貿"]], heading="三、產品與加工能力")
            self.assertEqual(rows_from_docx(path), [])
    def test_manual_item_reused_only_for_exact_source(self):
        row = {"topic": "RC 與低碳專案", "row": 3}
        published = [{"source": "meeting.docx", "source_sha": "original", "source_row": "3", "task": "RC 與低碳專案｜確認資料"}]
        self.assertTrue(source_row_published(row, "meeting.docx", "original", published))
        self.assertFalse(source_row_published(row, "meeting.docx", "revised", published))
        self.assertFalse(source_row_published({"topic": "其他議題", "row": 3}, "meeting.docx", "original", published))

    def test_latest_customer_table_labels_and_owners(self):
        layouts = [
            (["項目／進度", "規格、商業條件與下一步", "建議主責／協辦"], ["RC材評估", "開發有RC材之AI機櫃專案。", "中貿、中鋼"]),
            (["議題", "客戶需求與商機", "承辦單位"], ["高強度酸洗料", "可結合既有 CR 船期進行供貨評估。", "中貿"]),
            (["案件／進度", "下一步與必要條件", "窗口／建議分工"], ["冷軋詢價", "同意寄送現行詢價並納入每月通知。", "中貿"]),
            (["品項／狀態", "採購條件與限制", "PIC"], ["冷軋約 500 公噸詢單", "已報價，可追蹤對 RC、DC06 之需求。", "中貿"]),
        ]
        for headers, values in layouts:
            with self.subTest(headers=headers), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "meeting.docx"
                write_docx(path, headers, [values])
                rows = rows_from_docx(path)
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0]["topic"], values[0])
                self.assertEqual(rows[0]["task"], values[0] + "｜" + values[1])
                self.assertEqual(rows[0]["owner"], values[2])

    def test_factory_table_is_not_added_to_followups(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "meeting.docx"
            write_docx(path, ["項目", "參訪紀要"], [["製管範圍", "兩條製管線分大小管徑，供工廠參觀。"]])
            self.assertEqual(rows_from_docx(path), [])

    def test_customer_topic_headers_are_not_facts(self):
        for label in ["進度／項目", "項目／進度", "產品／進度", "品項／狀態", "案件／進度"]:
            with self.subTest(label=label), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "meeting.docx"
                write_docx(path, [label, "下一步與判定條件", "承辦窗口"], [["冷軋合作", "評估冷軋尺寸及供貨條件，待確認試料需求。", "中貿"]])
                knowledge = generic_knowledge(path)
                self.assertEqual(len(knowledge["topics"]), 1)
                self.assertEqual(knowledge["topics"][0]["title"], "冷軋合作")
                self.assertIn("試料需求", knowledge["topics"][0]["text"])

    def test_approval_does_not_remove_current_source_row(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            meetings = root / "meeting_records"
            meetings.mkdir()
            filename = "2026-11-16_UPTON_STEEL_Meeting_Record_r2.docx"
            write_docx(meetings / filename, ["項目／進度", "規格、商業條件與下一步", "建議主責／協辦"], [["RC材評估", "開發有RC材之AI機櫃專案。", "中貿、中鋼"]])
            index, current, output = [root / name for name in ["index.json", "official.json", "suggestions.json"]]
            index.write_text(json.dumps({"customers": {"UPTON": {"docx": {"url": "meeting_records/" + filename, "date": "2026-11-16", "version": "r2"}}}}))
            current.write_text(json.dumps({"items": []}))
            with patch.multiple(extraction, MEETINGS=meetings, INDEX=index, CURRENT=current, OUTPUT=output):
                extraction.main()
                first = json.loads(output.read_text())
                proposal = first["proposals"][0]
                official = {"items": [{**proposal, "id": "FU-approved", "status": "已完成", "source_row": "2"}], "reviewed_proposal_ids": [proposal["proposal_id"]]}
                current.write_text(json.dumps(official))
                original = current.read_bytes()
                extraction.main()
                second = json.loads(output.read_text())
            self.assertEqual(len(second["proposals"]), 1)
            self.assertEqual(second["documents"][0]["published_rows"], 1)
            self.assertEqual(second["documents"][0]["source_sha"], proposal["source_sha"])
            self.assertEqual(current.read_bytes(), original)

if __name__ == "__main__":
    unittest.main()
