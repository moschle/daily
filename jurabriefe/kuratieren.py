#!/usr/bin/env python3
"""Rohkarten kuratieren. Die Loesung kommt IMMER aus dem Skript, nie aus der API.

Zwei Aenderungen gegenueber dem zweiten Lauf, der 40 gute Karten verloren hat:

1. Die API bekommt die Loesung gar nicht mehr zu sehen und wird auch nicht
   nach ihr gefragt. Sie schreibt die Frage und vergibt ein Gewicht. Vorher
   durfte sie die Loesung "weglassen" — und eine weggelassene Loesung galt
   dem Code als Ablehnung, obwohl die Rohkarte eine woertliche hatte.

2. Laeufe werden zusammengefuehrt, nicht ueberschrieben. Was einmal bestanden
   hat und woertlich im Skript steht, bleibt. Ein misslungener Lauf kostet
   damit nichts.

Die Woertlichkeitspruefung normalisiert beide Seiten gleich: Fussnotenziffern
und Trennreste raus, hier wie dort. Sonst faellt eine bereinigte Loesung durch,
weil der Skripttext den Satzrest noch enthaelt.

    python kuratieren.py --alle              alle Skripte, additiv
    python kuratieren.py zr-staat            eines
    python kuratieren.py --alle --pruefen    nur die Woertlichkeit, ohne API
    python kuratieren.py --alle --neu        Bestand verwerfen und neu aufbauen
"""
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
from karten import EXTRACTED, OUT, clean, ohne_fussnoten

PROMPT = """Du kuratierst Uebungskarten fuer die zweite juristische Staatspruefung.
Grundlage ist ein Abschnitt aus einem Ausbildungsskript und Rohkarten daraus.
Massstab ist die Klausur: klare Ansage, keine Erklaerung, keine Hoeflichkeit.

ABSCHNITT:
{abschnitt}

ROHKARTEN (JSON, ohne Loesung — die steht fest und wird nicht veraendert):
{rohkarten}

Fuer jede Rohkarte:
- verwerfen (einfach weglassen), wenn die Situation aus dem Abschnitt nicht
  eindeutig hervorgeht oder die Karte kein Formulierungsbaustein, Tenor,
  Schema oder Fall ist.
- sonst uebernehmen: schreibe die FRAGE neu, ein bis drei Saetze im
  Bearbeitervermerk-Stil ("Der Beklagte ist saeumig geblieben. Tenorieren Sie
  die Kostenentscheidung."). Die Frage darf die Loesung nicht vorwegnehmen.
  Vergib "gewicht" 1-3: 3 fuer Tenor, Aufbau, Urteilsstil und Faelle,
  2 fuer Tatbestand und Beweiswuerdigung, 1 fuer Rubrum-Formalien.

Nur JSON-Liste ohne Markdown:
[{{"id": "<id der Rohkarte>", "frage": "<neue Frage>", "gewicht": <1-3>}}]"""

RANDNUMMER = re.compile(r"\s\d{2,3}(?=\s§)")


def _normal(s: str) -> str:
    """Beide Seiten gleich behandeln — sonst scheitert eine bereinigte Loesung
    am unbereinigten Skripttext."""
    s = ohne_fussnoten(s)
    s = RANDNUMMER.sub(" ", s)
    s = re.sub(r"(\w)\s*-\s*(\w)", r"\1\2", s)          # Trennreste
    s = re.sub(r"[\u201e\u201c\"\u201d\u201a\u2018']", "", s)
    s = re.sub(r"[\s\u00a0]+", " ", s)
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
    treffer = [skript.find(k["loesung"][:40]) for k in karten if k.get("loesung")]
    treffer = [t for t in treffer if t >= 0]
    if not treffer:
        return skript[:6000]
    a, b = max(0, min(treffer) - 2500), min(len(skript), max(treffer) + 2500)
    return skript[a:b]


def _fuer_api(stapel: list[dict]) -> list[dict]:
    """Die API sieht nie eine Loesung — auch nicht bei Formulierungskarten."""
    return [{k: v for k, v in karte.items() if k != "loesung"} for karte in stapel]


def _bestand(sid: str) -> dict[str, dict]:
    pfad = OUT / f"{sid}.kuratiert.json"
    if not pfad.exists():
        return {}
    try:
        return {k["id"]: k for k in json.loads(pfad.read_text(encoding="utf-8"))["karten"]}
    except (json.JSONDecodeError, KeyError):
        return {}


def kuratiere(sid: str, nur_pruefen: bool = False, additiv: bool = True) -> dict:
    skript = clean((EXTRACTED / f"{sid}.txt").read_text(encoding="utf-8", errors="replace"))
    roh = json.loads((OUT / f"{sid}.json").read_text(encoding="utf-8"))["karten"]
    roh = [k for k in roh if woertlich_im_skript(k["loesung"], skript)]
    if nur_pruefen:
        return {"skript": sid, "woertlich": len(roh), "karten": roh}

    alt = _bestand(sid) if additiv else {}
    behalten = {i: k for i, k in alt.items() if woertlich_im_skript(k.get("loesung", ""), skript)}
    offen = [k for k in roh if k["id"] not in behalten]

    neu, verworfen = {}, 0
    for i in range(0, len(offen), 12):
        stapel = offen[i:i + 12]
        antwort = complete(PROMPT.format(abschnitt=abschnitt_text(skript, stapel),
                                         rohkarten=json.dumps(_fuer_api(stapel), ensure_ascii=False)),
                           max_tokens=3000)
        antwort = re.sub(r"^```(?:json)?|```$", "", antwort.strip(), flags=re.M).strip()
        try:
            auswahl = json.loads(antwort)
        except json.JSONDecodeError:
            print(f"{sid}: Stapel {i} unlesbar", file=sys.stderr)
            continue
        by_id = {k["id"]: k for k in stapel}
        for a in auswahl:
            r = by_id.get(a.get("id"))
            frage = (a.get("frage") or "").strip()
            if not r or len(frage) < 15:
                verworfen += 1
                continue
            gewicht = a.get("gewicht", 3 if r.get("typ") in ("fall", "aufbau") else 2)
            try:
                gewicht = max(1, min(3, int(gewicht)))
            except (TypeError, ValueError):
                gewicht = 2
            neu[r["id"]] = {**r, "frage": frage, "loesung": r["loesung"], "gewicht": gewicht}

    fertig = list({**behalten, **neu}.values())
    fertig.sort(key=lambda k: k["id"])
    print(f"{sid}: {len(roh)} woertlich | {len(behalten)} behalten | {len(neu)} neu "
          f"| {verworfen} verworfen -> {len(fertig)}", file=sys.stderr)
    return {"skript": sid, "karten": fertig}


def main() -> int:
    nur_pruefen = "--pruefen" in sys.argv
    additiv = "--neu" not in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    ids = (sorted(p.stem for p in OUT.glob("*.json") if ".kuratiert" not in p.name)
           if "--alle" in sys.argv else args)
    if not ids:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    for sid in ids:
        res = kuratiere(sid, nur_pruefen, additiv)
        if nur_pruefen:
            print(f"{sid}: {res['woertlich']} Karten bestehen die Woertlichkeitspruefung")
            continue
        (OUT / f"{sid}.kuratiert.json").write_text(
            json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
