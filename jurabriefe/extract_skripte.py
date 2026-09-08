#!/usr/bin/env python3
"""Lädt Berliner Ausbildungsskripte und zieht den Volltext.

Ausgabe:
  jurabriefe/extracted/<id>.txt
  jurabriefe/extracted/index.json  (Seiten, Zeichenzahl, Kopfzeilen)
"""
from __future__ import annotations

import json
import re
import urllib.request
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).parent
OUT = ROOT / "extracted"
SKRIPTE = ROOT / "skripte.json"
UA = "jurabrief-extractor/1.0"


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def extract_pdf(data: bytes) -> list[str]:
    reader = PdfReader(BytesIO(data))
    pages = []
    for page in reader.pages:
        pages.append(page.extract_text() or "")
    return pages


def headings(text: str) -> list[str]:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    found = []
    for ln in lines:
        if len(ln) < 6 or len(ln) > 90:
            continue
        if re.match(r"^[A-J]\.", ln) or re.match(r"^\d+\.\s", ln):
            found.append(ln)
        elif ln.isupper() and " " in ln:
            found.append(ln)
    return found[:40]


def main() -> None:
    OUT.mkdir(exist_ok=True)
    spec = json.loads(SKRIPTE.read_text(encoding="utf-8"))
    index = []
    for item in spec["skripte"]:
        print(f"lade {item['id']} …", flush=True)
        try:
            raw = fetch(item["url"])
        except Exception as e:
            print(f"  Fehler Download: {e}")
            continue
        pages = extract_pdf(raw)
        text = "\n\n===== SEITE {} =====\n\n".join(
            [""] + pages
        ) if False else "\n\n".join(
            f"===== SEITE {i+1} =====\n{p}" for i, p in enumerate(pages)
        )
        out = OUT / f"{item['id']}.txt"
        out.write_text(text, encoding="utf-8")
        heads = headings(text)
        index.append({
            "id": item["id"],
            "titel": item["titel"],
            "seiten": len(pages),
            "zeichen": len(text),
            "datei": str(out.name),
            "ueberschriften": heads,
        })
        print(f"  {len(pages)} Seiten, {len(text)} Zeichen")
    (OUT / "index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("fertig.")


if __name__ == "__main__":
    main()
