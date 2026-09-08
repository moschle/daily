#!/usr/bin/env python3
"""Lädt Berliner Ausbildungsskripte und zieht den Volltext."""
from __future__ import annotations

import json
import os
import re
import time
import urllib.request
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).parent
OUT = ROOT / "extracted"
SKRIPTE = ROOT / "skripte.json"
UA = "Mozilla/5.0 (compatible; jurabrief-extractor/1.1)"
FORCE = os.environ.get("FORCE_EXTRACT") == "1"


def fetch(url: str) -> bytes:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": UA,
            "Referer": "https://www.berlin.de/gerichte/kammergericht/karriere/rechtsreferendariat/",
            "Accept": "application/pdf,*/*",
        },
    )
    with urllib.request.urlopen(req, timeout=90) as resp:
        return resp.read()


def fetch_retry(urls: list[str]) -> bytes:
    last = None
    for url in urls:
        for attempt in range(8):
            try:
                data = fetch(url)
                if data[:4] != b"%PDF":
                    raise RuntimeError(f"keine PDF ({len(data)} bytes)")
                return data
            except Exception as e:
                last = e
                wait = 15 * (attempt + 1)
                print(f"  retry {attempt+1} {url.split('/')[-1][:40]}: {e} — {wait}s", flush=True)
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
        if re.match(r"^[A-J]\.\s", ln) or re.match(r"^\d+\.\s", ln):
            found.append(ln)
        elif ln.isupper() and " " in ln:
            found.append(ln)
    return found[:40]


def main() -> None:
    OUT.mkdir(exist_ok=True)
    spec = json.loads(SKRIPTE.read_text(encoding="utf-8"))
    items = spec["skripte"]
    items = sorted(items, key=lambda it: (OUT / f"{it['id']}.txt").exists())
    index_path = OUT / "index.json"
    index = json.loads(index_path.read_text(encoding="utf-8")) if index_path.exists() else []
    by_id = {e["id"]: e for e in index if "id" in e}

    for item in items:
        dest = OUT / f"{item['id']}.txt"
        if dest.exists() and dest.stat().st_size > 1000 and not FORCE:
            print(f"skip {item['id']} (liegt vor, {dest.stat().st_size} bytes)", flush=True)
            continue
        urls = item.get("urls") or ([item["url"]] if item.get("url") else [])
        print(f"lade {item['id']} …", flush=True)
        try:
            raw = fetch_retry(urls)
        except Exception as e:
            print(f"  Fehler: {e}")
            by_id[item["id"]] = {"id": item["id"], "titel": item["titel"], "fehler": str(e)}
            continue
        pages = extract_pdf(raw)
        text = "\n\n".join(f"===== SEITE {i+1} =====\n{p}" for i, p in enumerate(pages))
        dest.write_text(text, encoding="utf-8")
        by_id[item["id"]] = {
            "id": item["id"],
            "titel": item["titel"],
            "seiten": len(pages),
            "zeichen": len(text),
            "datei": dest.name,
            "ueberschriften": headings(text),
        }
        print(f"  {len(pages)} Seiten, {len(text)} Zeichen")
        time.sleep(8)

    index_path.write_text(
        json.dumps(list(by_id.values()), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("fertig.")


if __name__ == "__main__":
    main()
