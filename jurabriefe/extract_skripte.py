#!/usr/bin/env python3
"""Lädt Berliner Ausbildungsskripte und zieht den Volltext."""
from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).parent
OUT = ROOT / "extracted"
SKRIPTE = ROOT / "skripte.json"
UA = "Mozilla/5.0 jurabrief-extractor/1.0"


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def fetch_retry(urls: list[str]) -> bytes:
    last = None
    for url in urls:
        for attempt in range(4):
            try:
                return fetch(url)
            except Exception as e:
                last = e
                wait = 8 * (attempt + 1)
                print(f"  retry {attempt+1} {url.split('/')[-1]}: {e} — {wait}s")
                time.sleep(wait)
    raise last  # type: ignore


def extract_pdf(data: bytes) -> list[str]:
    reader = PdfReader(BytesIO(data))
    return [(page.extract_text() or "") for page in reader.pages]


def headings(text: str) -> list[str]:
    found = []
    for ln in text.splitlines():
        ln = ln.strip()
        if len(ln) < 6 or len(ln) > 90:
            continue
        if ln.startswith("===== SEITE"):
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
        urls = item.get("urls") or ([item["url"]] if item.get("url") else [])
        print(f"lade {item['id']} …", flush=True)
        try:
            raw = fetch_retry(urls)
        except Exception as e:
            print(f"  Fehler: {e}")
            index.append({"id": item["id"], "titel": item["titel"], "fehler": str(e)})
            continue
        pages = extract_pdf(raw)
        text = "\n\n".join(f"===== SEITE {i+1} =====\n{p}" for i, p in enumerate(pages))
        out = OUT / f"{item['id']}.txt"
        out.write_text(text, encoding="utf-8")
        index.append({
            "id": item["id"],
            "titel": item["titel"],
            "seiten": len(pages),
            "zeichen": len(text),
            "datei": out.name,
            "ueberschriften": headings(text),
        })
        print(f"  {len(pages)} Seiten, {len(text)} Zeichen")
        time.sleep(3)
    (OUT / "index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("fertig.")


if __name__ == "__main__":
    main()
