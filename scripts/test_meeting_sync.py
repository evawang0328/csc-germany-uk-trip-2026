#!/usr/bin/env python3
"""Regression checks for source-bound automatic follow-up extraction."""
from pathlib import Path
import tempfile
import unittest
from xml.sax.saxutils import escape
import zipfile
from extract_meeting_followups import rows_from_docx, source_row_published, DISPLAY
from build_meeting_index import parse_name

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

if __name__ == "__main__":
    unittest.main()
