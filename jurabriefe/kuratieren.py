#!/usr/bin/env python3
"""Rohkarten kuratieren. Loesung muss woertlich im Skript stehen."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

try:
    from claude_client import complete
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from claude_client import complete
from karten import EXTRACTED, OUT, clean

PROMPT = """Du kuratierst Uebungskarten fuer die zweite juristische Staatspruefung.
Grundlage ist ein Abschnitt aus einem Ausbildungsskript und Rohkarten.
Massstab ist die Klausur: klare Ansage, keine Erklaerung.

ABSCHNITT:
{abschnitt}

ROHKARTEN (JSON):
{rohkarten}

Fuer jede Rohkarte:
- verwerfen, wenn die Loesung kein vollstaendiger Formulierungsbaustein,
  Tenorsatz, Loesungsabsatz oder Schema ist, oder die Situation nicht eindeutig ist.
- sonst: FRAGE neu im Bearbeitervermerk-Stil, LOESUNG unveraendert woertlich.
  gewicht 1-3: 3 Tenor/Aufbau/Urteilsstil, 2 Tatbestand, 1 Rubrum.

Nur JSON-Liste ohne Markdown:
[{{"id": "<id>", "frage": "<frage>", "loesung": "<woertlich>", "gewicht": <1-3>}}]"""


def _normal(s: str) -> str:
    s = re.sub(r"[\s\u00a0]+", " ", s)
    s = re.sub(r"(\w)- (\w)", r"\1\2", s)
    s = re.sub(r"[\u201e\u201c\"\u201d\u201a\u2018']", "", s)
    return s.strip().lower()


def woertlich_im_skript(loesung: str, skript: str) -> bool:
    l, s = _normal(loesung), _normal(skript)
    if not l:
        return False
    if l in s:
        return True
    punkte = [re.sub(r"^\d+\.\s*", "", z).strip() for z in loesung.split("\n") if z.strip()]
    return len(punkte) > 1 and all(_normal(p) in s for p in punkte)


def abschnitt_text(skript: str, karten: list[dict]) -> str:
    treffer = [skript.find(k["loesung"][:40]) for k in karten]
    treffer = [t for t in treffer if t >= 0]
    if not treffer:
        return skript[:6000]
    a, b = max(0, min(treffer) - 2500), min(len(skript), max(treffer) + 2500)
    return skript[a:b]


def kuratiere(sid: str, nur_pruefen: bool = False) -> dict:
    skript = clean((EXTRACTED / f"{sid}.txt").read_text(encoding="utf-8", errors="replace"))
    roh = json.loads((OUT / f"{sid}.json").read_text(encoding="utf-8"))["karten"]
    roh = [k for k in roh if woertlich_im_skript(k["loesung"], skript)]
    if nur_pruefen:
        return {"skript": sid, "woertlich": len(roh), "karten": roh}
    fertig, verworfen = [], 0
    for i in range(0, len(roh), 12):
        stapel = roh[i:i + 12]
        antwort = complete(PROMPT.format(abschnitt=abschnitt_text(skript, stapel),
                                         rohkarten=json.dumps(stapel, ensure_ascii=False)),
                           max_tokens=4000)
        antwort = re.sub(r"^```(?:json)?|```$", "", antwort.strip(), flags=re.M).strip()
        try:
            auswahl = json.loads(antwort)
        except json.JSONDecodeError:
            print(f"{sid}: Stapel {i} unlesbar", file=sys.stderr)
            continue
        by_id = {k["id"]: k for k in stapel}
        for a in auswahl:
            r = by_id.get(a.get("id"))
            if not r or not woertlich_im_skript(a.get("loesung", ""), skript):
                verworfen += 1
                continue
            if _normal(a["loesung"]) != _normal(r["loesung"]):
                verworfen += 1
                continue
            fertig.append({**r, "frage": a["frage"].strip(), "gewicht": int(a.get("gewicht", 2))})
    print(f"{sid}: {len(roh)} woertlich -> {len(fertig)} kuratiert, {verworfen} verworfen", file=sys.stderr)
    return {"skript": sid, "karten": fertig}


def main() -> int:
    nur_pruefen = "--pruefen" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    ids = sorted(p.stem for p in OUT.glob("*.json") if ".kuratiert" not in p.name) if "--alle" in sys.argv else args
    if not ids:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    for sid in ids:
        res = kuratiere(sid, nur_pruefen)
        if nur_pruefen:
            print(f"{sid}: {res['woertlich']} Karten bestehen die Woertlichkeitspruefung")
            continue
        (OUT / f"{sid}.kuratiert.json").write_text(
            json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
