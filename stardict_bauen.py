#!/usr/bin/env python3
"""Baut aus dem Anki-Wortschatz ein StarDict-Woerterbuch fuer KOReader.

StarDict besteht aus drei Dateien:
  .ifo   Kopfdaten
  .idx   Index: Wort, Nullbyte, Offset (4 Byte), Laenge (4 Byte) - Big Endian
  .dict  die Definitionen hintereinander

Der Index muss nach UTF-8-Bytes sortiert sein, sonst findet KOReader nichts.
"""
import json
import struct
import sys
from pathlib import Path

quelle = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/persisch_bekannt.json")
ziel = Path(sys.argv[2] if len(sys.argv) > 2 else Path.home() / "Downloads/kindle_paket/dict/persisch_anki")
name = "Persisch-Deutsch (eigener Wortschatz)"

ziel.mkdir(parents=True, exist_ok=True)
eintraege = json.loads(quelle.read_text(encoding="utf-8"))

# gleiche Stichwoerter zusammenfassen
sammlung = {}
for e in eintraege:
    w = (e.get("word") or "").strip()
    b = (e.get("meaning") or "").strip()
    if not w or not b:
        continue
    sammlung.setdefault(w, [])
    if b not in sammlung[w]:
        sammlung[w].append(b)

woerter = sorted(sammlung.items(), key=lambda kv: kv[0].encode("utf-8"))

dict_bytes = bytearray()
idx_bytes = bytearray()
for wort, bedeutungen in woerter:
    text = "\n".join(bedeutungen).encode("utf-8")
    offset = len(dict_bytes)
    dict_bytes += text
    idx_bytes += wort.encode("utf-8") + b"\x00" + struct.pack(">II", offset, len(text))

basis = ziel / "persisch_anki"
(basis.with_suffix(".dict")).write_bytes(bytes(dict_bytes))
(basis.with_suffix(".idx")).write_bytes(bytes(idx_bytes))
(basis.with_suffix(".ifo")).write_text(
    "StarDict's dict ifo file\n"
    "version=2.4.2\n"
    f"bookname={name}\n"
    f"wordcount={len(woerter)}\n"
    f"idxfilesize={len(idx_bytes)}\n"
    "sametypesequence=m\n"
    "description=Aus dem Anki-Deck Persisch 1 erzeugt\n",
    encoding="utf-8",
)
print(f"{len(woerter)} Stichwoerter -> {ziel}")
for f in sorted(ziel.iterdir()):
    print(f"  {f.name}  {f.stat().st_size} Byte")
