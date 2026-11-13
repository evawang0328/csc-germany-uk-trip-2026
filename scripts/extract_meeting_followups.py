#!/usr/bin/env python3
"""Extract review-only follow-up proposals from the latest customer meeting DOCX.

Runs on every Pages publish after build_meeting_index.py. Nothing is written to
followup_actions.json: administrator approval and GitHub commit are required.

No pip dependencies: Python standard-library zipfile and ElementTree.
"""
from __future__ import annotations

from datetime import datetime, timezone
from difflib import SequenceMatcher
from hashlib import sha256
from pathlib import Path
from urllib.parse import unquote
import json
import re
import zipfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
MEETINGS = ROOT / "meeting_records"
OUTPUT = ROOT / "followup_suggestions.json"
CURRENT = ROOT / "followup_actions.json"
INDEX = ROOT / "meeting_records_index.json"
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
DISPLAY = {
    "SPAETER": "Carl Spaeter HQ",
    "KNAUF": "Knauf",
    "DUFERCO": "Duferco",
    "HFS": "HFS",
    "UPTON": "Upton Steel",
    "BELMONT": "Belmont",
    "TOPTUBES": "Top Tubes",
    "STEELALLOY": "Steel & Alloy",
}
NEAR = re.compile(r"後續|追蹤|待辦|辦理事項|主要工作|待處理|商機.*後續")
HEADER = re.compile(r"議題|事項|主要工作|客戶需求|需求與商機|協辦|責任|窗口|PIC|說明|順序|優先序")
ITEM_HEADER = re.compile(r"追蹤事項|後續辦理|主要工作|客戶需求與商機|待辦事項")
DONE = re.compile(r"已解決|已完成|結案|已辦妥")
UNSAFE = re.compile(r"\b\d{2,3}-\d{2,3}-\d{3,4}\b")  # example phone-like substrings

def normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\u00a0", " ")).strip()

def element_text(el: ET.Element) -> str:
    paragraphs = []
    for p in el.iter(W + "p"):
        pieces = []
        for t in p.iter():
            if t.tag == W + "t" and t.text:
                pieces.append(t.text)
            elif t.tag in (W + "tab", W + "br"):
                pieces.append(" ")
        value = normalize("".join(pieces))
        if value:
            paragraphs.append(value)
    return normalize(" ".join(paragraphs))

def docx_blocks(path: Path) -> list[tuple[str, object]]:
    with zipfile.ZipFile(path) as zf:
        root = ET.fromstring(zf.read("word/document.xml"))
    body = root.find(W + "body")
    output = []
    for block in list(body) if body is not None else []:
        if block.tag == W + "p":
            text = element_text(block)
            if text:
                output.append(("paragraph", text))
        elif block.tag == W + "tbl":
            rows = []
            for tr in block.findall(W + "tr"):
                values = [element_text(tc) for tc in tr.findall(W + "tc")]
                if any(values):
                    rows.append(values)
            if rows:
                output.append(("table", rows))
    return output

def get_col(row: list[str], index: int | None) -> str:
    return row[index].strip() if index is not None and 0 <= index < len(row) else ""

def rows_from_docx(path: Path) -> list[dict]:
    found = []
    heading = ""
    for kind, block in docx_blocks(path):
        if kind == "paragraph":
            text = str(block)
            if (re.match(r"^[一二三四五六七八九十\d]+\s*[、.\s]", text) or NEAR.search(text)) and len(text) < 105:
                heading = text
            continue
        rows = block
        header = rows[0]
        header_text = "|".join(header)
        in_followup_section = bool(NEAR.search(heading))
        explicitly_followup = bool(ITEM_HEADER.search(header_text))
        if not (explicitly_followup or in_followup_section):
            continue
        if not HEADER.search(header_text):
            continue
        headers = [re.sub(r"[\s\u3000]", "", x).upper() for x in header]
        def find_col(*words):
            return next((j for j, x in enumerate(headers) if any(w.upper() in x for w in words)), None)
        owner_idx = find_col("PIC", "責任", "窗口", "協辦")
        issue_idx = find_col("議題", "產品", "類別")
        task_idx = find_col("追蹤事項", "主要工作", "客戶需求與商機", "辦理事項", "需求", "工作內容")
        note_idx = find_col("說明", "備註", "協辦方向")
        status_idx = find_col("狀態", "進度")
        if task_idx is None:
            if not in_followup_section:
                continue
            task_idx = next((i for i in range(len(header)) if i not in [issue_idx, owner_idx, note_idx, status_idx] and not re.search(r"優先|順序|項次", headers[i])), None)
        if task_idx is None:
            continue
        # Ignore tables that are ordinary specification/price tables.
        if not (in_followup_section or explicitly_followup or owner_idx is not None):
            continue
        for ordinal, row in enumerate(rows[1:], 1):
            if all(not x.strip() for x in row):
                continue
            if any(re.search(r"^合計$|^小計$|^總計$|^註[:：]|^備註[:：]", normalize(x)) for x in row[:2]):
                continue
            issue = get_col(row, issue_idx)
            content = get_col(row, task_idx)
            note = get_col(row, note_idx)
            owner = get_col(row, owner_idx)
            status = get_col(row, status_idx)
            if not content or len(content) < 6:
                continue
            # Duplicate header lines or fully merged table notes aren't action items.
            if content in header or content.startswith("資料來源"):
                continue
            if issue and issue != content and not issue.isdigit():
                task = issue + "｜" + content
            else:
                task = content
            # A source can say "已解決" in the PIC column.
            status_hint = "已完成" if DONE.search(status) or DONE.fullmatch(owner.strip()) else ""
            if status_hint:
                owner = "" if DONE.fullmatch(owner.strip()) else owner
            found.append({
                "topic": issue if not issue.isdigit() else "",
                "task": task,
                "owner": owner,
                "note": note,
                "status_hint": status_hint,
                "table_heading": heading,
                "row": ordinal + 1,
            })
    # Keep row positions stable but remove repeated identical rows.
    seen = set()
    unique = []
    for row in found:
        k = normalize(row["task"]).upper()
        if k not in seen:
            seen.add(k)
            unique.append(row)
    return unique

def category_for(topic: str, task: str) -> str:
    s = topic + " " + task
    if re.search("CBAM|EPD|碳排|低碳|綠鋼|RC60|再生料|排放", s, re.I):
        return "CBAM／低碳"
    if re.search("規格|尺寸|試產|試樣|鋼種|產製|酸洗|寬幅|EG", s, re.I):
        return "產品規格"
    if re.search("詢價|報價|採購|商機|汽車用鋼|電磁鋼片", s, re.I):
        return "商機／詢價"
    return "其他"

def similarity(left: str, right: str) -> float:
    """Cautious best-match suggestion; never automatically update an ID."""
    def clean(v):
        return re.sub(r"[\s\W_]", "", v.lower())
    a, b = clean(left), clean(right)
    if not a or not b:
        return 0.0
    direct = SequenceMatcher(None, a, b).ratio()
    # Keep matching of paraphrased records conservative.
    bigrams = lambda v: set(v[i:i + 2] for i in range(len(v) - 1))
    sa, sb = bigrams(a), bigrams(b)
    overlap = 2 * len(sa & sb) / (len(sa) + len(sb)) if sa and sb else 0.0
    return round(max(direct, overlap), 3)

def main():
    idx = json.loads(INDEX.read_text(encoding="utf-8"))
    official = json.loads(CURRENT.read_text(encoding="utf-8"))
    published = official.get("items", [])
    reviewed_ids = set(official.get("reviewed_proposal_ids", []))
    proposals = []
    documents = []
    for customer_key, versions in sorted(idx.get("customers", {}).items()):
        word = versions.get("docx")
        if not word:
            continue
        filename = unquote(word["url"].split("/", 1)[-1])
        path = MEETINGS / filename
        if not path.is_file():
            continue
        customer = DISPLAY.get(customer_key, customer_key.title())
        date = word.get("date", "")
        relevant = [x for x in published if x.get("customer", "").casefold() == customer.casefold()]
        doc_record = {"customer": customer, "file": word["url"], "version": word.get("version"), "date": date}
        try:
            rows = rows_from_docx(path)
        except (ValueError, KeyError, ET.ParseError, zipfile.BadZipFile) as exc:
            doc_record["error"] = str(exc)[:160]
            documents.append(doc_record)
            continue
        doc_record["extracted_rows"] = len(rows)
        documents.append(doc_record)
        for row in rows:
            comparable = row["task"]
            scored = sorted(
                ((similarity(comparable, x.get("task", "") + " " + x.get("note", "")), x) for x in relevant),
                key=lambda tup: tup[0], reverse=True)
            confidence, match = scored[0] if scored else (0, None)
            fingerprint = sha256((customer + "|" + date + "|" + comparable).encode("utf-8")).hexdigest()[:12]
            # ID is deterministic across same document revisions unless text changes;
            # approval UI also checks against existing records.
            classification = "可能與既有事項重疊" if confidence >= 0.42 else "可能新增事項"
            if customer_key + "-" + fingerprint in reviewed_ids:
                continue
            proposals.append({
                "proposal_id": customer_key + "-" + fingerprint,
                "classification": classification,
                "customer": customer,
                "country": "英國" if customer_key in {"UPTON", "BELMONT", "TOPTUBES", "STEELALLOY"} else "德國",
                "visit_date": date,
                "category": category_for(row["topic"], comparable),
                "topic": row["topic"],
                "task": comparable,
                "owner": row["owner"],
                "note": row["note"],
                "status_hint": row["status_hint"],  # Never change status automatically.
                "source": path.name,
                "source_url": word["url"],
                "source_row": row["row"],
                "suggested_match_id": match.get("id") if match and confidence >= 0.42 else None,
                "similarity": confidence,
            })
    # No proposals are applied automatically. No remove/complete operation is inferred
    # from absence of a row in a new Word file.
    payload = {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "review_required": True,
        "message": "自動解析結果僅供人工審核；已發布追蹤事項、狀態與處理歷史保持不變。",
        "documents": documents,
        "proposals": proposals,
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT.name}: {len(documents)} DOCX, {len(proposals)} review suggestions (no official records changed).")

if __name__ == "__main__":
    main()
