#!/usr/bin/env python3
"""Build the published latest-meeting index from versioned PDF/DOCX files.

Run during BOTH Pages deployment workflows. No credentials or external services.
Convention: YYYY-MM-DD_CUSTOMER_Meeting_Record_rN.pdf|docx
Legacy unversioned files (e.g. Duferco_Dinner_Meeting_Record.pdf) are supported.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / "meeting_records"
OUTPUT = ROOT / "meeting_records_index.json"
DATE = re.compile(r"^(?P<date>\d{4}[-.]\d{2}[-.]\d{2})[_\s-]+(?P<body>.+)\.(?P<ext>pdf|docx)$", re.I)
MEETING = re.compile(r"(?:^|[_\s-])Meeting[_\s-]*Record(?:[_\s-]*r(?P<revision>\d+))?$", re.I)
ALIAS = {
    "SPAETER": "SPAETER", "CARLSPAETER": "SPAETER",
    "KNAUF": "KNAUF", "KNAUFINTERFER": "KNAUF",
    "DUFERCO": "DUFERCO", "HFS": "HFS",
    "UPTON": "UPTON", "UPTONSTEEL": "UPTON",
    "BELMONT": "BELMONT", "TOPTUBES": "TOPTUBES",
    "STEELALLOY": "STEELALLOY",
}
def key_for(label: str) -> str:
    norm = re.sub(r"[^A-Z0-9]", "", label.upper())
    for alias, canonical in sorted(ALIAS.items(), key=lambda a: -len(a[0])):
        if norm.startswith(alias):
            return canonical
    return norm

latest = {}
if FOLDER.is_dir():
    for path in sorted(FOLDER.iterdir()):
        if not path.is_file():
            continue
        mat = DATE.match(path.name)
        if not mat:
            continue
        body = mat.group("body")
        meeting = MEETING.search(body)
        if not meeting:
            continue
        customer_part = body[:meeting.start()].strip("_ -")
        if not customer_part:
            continue
        customer_key = key_for(customer_part)
        date = mat.group("date").replace(".", "-")
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            continue
        ext = mat.group("ext").lower()
        revision = int(meeting.group("revision") or 0)
        item = {
            "name": path.name,
            "url": "meeting_records/" + quote(path.name),
            "date": date,
            "version": "r" + str(revision) if revision else "未標版本",
            "revision": revision,
        }
        candidate = (date, revision, path.name.lower())
        group = latest.setdefault(customer_key, {})
        existing = group.get(ext)
        if existing is None or candidate > (existing["date"], existing["revision"], existing["name"].lower()):
            group[ext] = item

for item in latest.values():
    pdf, word = item.get("pdf"), item.get("docx")
    item["version_mismatch"] = bool(pdf and word and (pdf["date"], pdf["revision"]) != (word["date"], word["revision"]))

payload = {
    "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    "source": "meeting_records/",
    "customers": latest,
}
OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"Built {OUTPUT.name}: {len(latest)} customers; " +
      ", ".join(f"{key}: {v.get('pdf', {}).get('version', '—')} PDF / {v.get('docx', {}).get('version', '—')} Word" for key,v in sorted(latest.items())))
