#!/usr/bin/env python3
"""Lädt Berliner Ausbildungsskripte und zieht den Volltext.

    python extract_skripte.py              # Berlin-PDFs aus skripte.json
    python extract_skripte.py --lokal      # PDFs/TXT aus JURABRIEF_SCANS oder private/scans
    python extract_skripte.py --lokal /pfad
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.request
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).parent
OUT = Path(os.environ["JURABRIEF_EXTRACTED"]) if os.environ.get("JURABRIEF_EXTRACTED") else ROOT / "extracted"
SKRIPTE = ROOT / "skripte.json"
UA = "Mozilla/5.0 (compatible; jurabrief-extractor/1.1)"
FORCE = os.environ.get("FORCE_EXTRACT") == "1"
DEFAULT_SCANS = Path(os.environ["JURABRIEF_SCANS"]) if os.environ.get("JURABRIEF_SCANS") else ROOT.parent / "private" / "scans"


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


def _stem_id(name: str) -> str:
    s = Path(name).stem.lower()
    s = re.sub(r"[^a-z0-9\-]+", "-", s)
    return s.strip("-") or "skript"


def lokal(src: Path) -> None:
    """Lokale PDFs oder bereits OCRte TXT in extracted/ schreiben."""
    OUT.mkdir(exist_ok=True)
    if not src.exists():
        print(f"kein Scan-Ordner: {src}", file=sys.stderr)
        sys.exit(2)
    files = sorted(p for p in src.iterdir() if p.suffix.lower() in {".pdf", ".txt"} and p.is_file())
    if not files:
        print(f"keine PDF/TXT in {src}", file=sys.stderr)
        sys.exit(2)
    index_path = OUT / "index.json"
    index = json.loads(index_path.read_text(encoding="utf-8")) if index_path.exists() else []
    by_id = {e["id"]: e for e in index if "id" in e}
    for pfad in files:
        sid = _stem_id(pfad.name)
        dest = OUT / f"{sid}.txt"
        if dest.exists() and dest.stat().st_size > 1000 and not FORCE:
            print(f"skip {sid} (liegt vor)", flush=True)
            continue
        print(f"lokal {sid} …", flush=True)
        if pfad.suffix.lower() == ".txt":
            raw_text = pfad.read_text(encoding="utf-8", errors="replace")
            if "===== SEITE" in raw_text:
                text = raw_text
                seiten = raw_text.count("===== SEITE")
            else:
                abschnitte = re.split(r"\n\s*\n", raw_text)
                text = "\n\n".join(f"===== SEITE {i+1} =====\n{a}" for i, a in enumerate(abschnitte[:400]) if a.strip())
                seiten = min(400, max(1, raw_text.count("\f") + 1))
        else:
            pages = extract_pdf(pfad.read_bytes())
            text = "\n\n".join(f"===== SEITE {i+1} =====\n{p}" for i, p in enumerate(pages))
            seiten = len(pages)
        dest.write_text(text, encoding="utf-8")
        by_id[sid] = {
            "id": sid,
            "titel": pfad.stem,
            "seiten": seiten,
            "zeichen": len(text),
            "datei": dest.name,
            "quelle": "lokal",
            "ueberschriften": headings(text),
        }
        print(f"  {seiten} Seiten, {len(text)} Zeichen -> {dest}")
    index_path.write_text(json.dumps(list(by_id.values()), ensure_ascii=False, indent=2), encoding="utf-8")
    print("fertig (lokal).")


def main() -> None:
    if "--lokal" in sys.argv:
        args = [a for a in sys.argv[1:] if a != "--lokal"]
        src = Path(args[0]).expanduser() if args else DEFAULT_SCANS
        lokal(src)
        return

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
