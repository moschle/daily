#!/usr/bin/env python3
"""Karten aus den Ausbildungsskripten lesen statt sie mit Regeln zu ernten.

Der alte Weg (karten.py) erntet, was zufaellig in Anfuehrungszeichen steht.
Das ergibt aus 719 Seiten 217 Karten, davon 94 Prozent Formulierungen, und
laesst Aufbau, Voraussetzungen, Abgrenzungen und Fristen vollstaendig liegen.

Hier liest ein Modell jeden Abschnitt einmal und schlaegt Karten vor. Damit
daraus keine Nacharbeit wird, gilt:

* Jede Karte fuehrt einen BELEG mit — die woertliche Skriptstelle. Kommt der
  Beleg nicht als Zeichenkette in genau diesem Abschnitt vor, fliegt die Karte
  raus. Eine erfundene Fundstelle uebersteht keine Teilstring-Pruefung.
* Die ID ist sha1 ueber den Beleg. Derselbe Abschnitt ergibt dieselben IDs,
  ein zweiter Lauf ist idempotent, nichts verrutscht. (Das Umnummerieren war
  die Ursache der kaputt gepaarten Karten form:017 und form:021.)
* Ein Manifest haelt fest, welcher Abschnitt erledigt ist. Ein Abbruch bei
  Abschnitt 150 kostet die ersten 149 nicht noch einmal.
* Geschnitten wird an Ueberschriften, nie mitten in einer Einheit.
* Kein stiller Rueckfall: jeder Abschnitt wird protokolliert, am Ende eine
  Bilanz nach Typ und eine Durchfallquote.

Aufruf:
    python jurabriefe/karten_llm.py sr-anwalt --limit 3      # Probe
    python jurabriefe/karten_llm.py sr-anwalt                # ganzes Skript
    python jurabriefe/karten_llm.py --alle
    python jurabriefe/karten_llm.py sr-anwalt --trocken      # ohne API
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from pathlib import Path

HIER = Path(__file__).resolve().parent
EXTRACT = HIER / "extracted"
KARTEN = HIER / "karten"
MANIFEST = KARTEN / "llm_manifest.json"

ZIEL = 6000
MAXIMUM = 9500
MIN_ABSCHNITT = 500
MAX_KARTEN = 5

TYPEN = {"formulierung", "aufbau", "voraussetzungen", "abgrenzung", "frist", "fehler"}

SEITE = re.compile(r"(?m)^=+ SEITE \d+ =+$")
FUSSNOTE = re.compile(r"(?m)^\d{1,3}\s{2}\S")
UEBERSCHRIFT = re.compile(
    r"(?m)^\s*((?:[A-Z]\)|[IVXL]{1,5}\.|\d{1,2}\.|[a-z]\))\s+[A-ZÄÖÜ][^\n]{2,58})$")
# Kein "[A-Z]." als Zaehler: "M. jedoch nicht belehrt" ist eine Namensabkuerzung
# im Fliesstext, keine Ueberschrift. Und kein Satz: was einen Satzpunkt oder ein
# Komma am Ende traegt, ist Text.
SATZ = re.compile(r"\.\s+[a-zäöüß]|,\s*$|\.$")


def ist_ueberschrift(t: str) -> bool:
    return not SATZ.search(t.strip())
INHALT = re.compile(r"\d{1,3}\s*[-–]\s*\d{1,3}")


# ---------------------------------------------------------------- Saeubern

def saeubere(roh: str) -> str:
    """Derselbe Saeuberer, den pruefe_karten.py fuer die Belegpruefung benutzt.

    Ein eigener waere bequemer, aber dann passt kein Beleg mehr: geprueft wird
    gegen clean() aus karten.py. Zusaetzlich faellt hier nur noch das
    Inhaltsverzeichnis weg, das clean() nicht kennt.
    """
    from karten import clean
    text = clean(roh)
    seiten = [s for s in text.split("\n\n") if len(INHALT.findall(s)) < 5]
    return "\n\n".join(seiten)


# ------------------------------------------------------------- Abschnitte

def schneide(text: str) -> list[dict]:
    """An Ueberschriften trennen, dann bis zur Zielgroesse sammeln.

    Nie innerhalb einer Einheit schneiden — genau der Fehler, der den
    Lesetext bei 'Tatbestandsvoraussetzungen' anfangen liess.
    """
    marken = [(m.start(), m.group(1).strip()) for m in UEBERSCHRIFT.finditer(text)
               if ist_ueberschrift(m.group(1))]
    if not marken:
        marken = [(0, "")]
    if marken[0][0] > 0:
        marken.insert(0, (0, ""))

    bloecke = []
    for i, (pos, titel) in enumerate(marken):
        ende = marken[i + 1][0] if i + 1 < len(marken) else len(text)
        koerper = text[pos:ende].strip()
        if koerper:
            bloecke.append({"titel": titel, "text": koerper})

    abschnitte, puffer, titel_kette = [], [], []
    for b in bloecke:
        if b["titel"]:
            titel_kette = (titel_kette + [b["titel"]])[-2:]
        puffer.append(b["text"])
        laenge = sum(len(x) for x in puffer)
        if laenge >= ZIEL:
            abschnitte.append({"ort": " › ".join(titel_kette), "text": "\n\n".join(puffer)})
            puffer = []
    if puffer:
        rest = "\n\n".join(puffer)
        if len(rest) < MIN_ABSCHNITT and abschnitte:
            abschnitte[-1]["text"] += "\n\n" + rest
        else:
            abschnitte.append({"ort": " › ".join(titel_kette), "text": rest})

    # Uebergrosse Abschnitte an Absatzgrenzen halbieren
    fertig = []
    for a in abschnitte:
        while len(a["text"]) > MAXIMUM:
            schnitt = a["text"].rfind("\n\n", 0, MAXIMUM)
            if schnitt < MIN_ABSCHNITT:
                break
            fertig.append({"ort": a["ort"], "text": a["text"][:schnitt].strip()})
            a = {"ort": a["ort"], "text": a["text"][schnitt:].strip()}
        fertig.append(a)
    return [a for a in fertig if len(a["text"]) >= MIN_ABSCHNITT]


# ------------------------------------------------------------------ Modell

PROMPT = """Du baust Lernkarten aus einem Ausbildungsskript fuer das zweite juristische Staatsexamen.

Abschnitt aus dem Skript "{sid}", Fundstelle: {ort}

---
{text}
---

Erzeuge Karten zu dem, was dieser Abschnitt tatsaechlich lehrt. Antworte NUR mit JSON, ohne Vorrede und ohne Codefence:

{{"karten": [{{"typ": "...", "frage": "...", "loesung": "...", "beleg": "..."}}]}}

Erlaubte Typen: formulierung (ein Mustersatz ist zu formulieren), aufbau (Reihenfolge oder Gliederung einer Pruefung), voraussetzungen (Tatbestandsmerkmale oder Zulaessigkeitsvoraussetzungen), abgrenzung (zwei Rechtsbehelfe, Klagearten oder Begriffe unterscheiden), frist (Dauer, Beginn, Berechnung, Folgen der Versaeumung), fehler (ein typischer Fehler und was stattdessen richtig ist).

Regeln:
- Hoechstens {max_karten} Karten. WENIGER IST RICHTIG. Eine leere Liste ist eine gueltige und oft die richtige Antwort — ein Abschnitt mit Vorwort, Literaturhinweisen oder allgemeinen Ermahnungen gibt keine Karte her. Erfinde nichts, um die Liste zu fuellen.
- Die Frage muss ohne das Skript beantwortbar sein. Sie bringt ihren Sachverhalt selbst mit, in ganzen Saetzen. Ein Klammerzusatz aus acht Woertern ersetzt keinen Sachverhalt. Falsch: "Formulieren Sie die Parteivorstellung (Mietrueckstaende, Pallasstrasse 57)." Richtig: "Ihre Mandantin vermietet eine Wohnung in der Pallasstrasse 57 in Berlin-Schoeneberg. Der Mieter hat die Miete fuer August bis November 2023 nicht gezahlt. Formulieren Sie die einleitende Parteivorstellung im Schriftsatz."
- Die Loesung steht fuer sich und nennt die tragenden Punkte, nicht nur ein Stichwort.
- beleg: eine woertliche, zusammenhaengende Passage AUS DEM OBIGEN ABSCHNITT, mindestens 40 Zeichen, die die Loesung traegt. Zeichengenau abschreiben, nichts umformulieren, keine Auslassungszeichen. Der Beleg wird maschinell gegen den Abschnitt geprueft; stimmt er nicht, wird die Karte verworfen.
- Keine zwei Karten zur selben Aussage.
"""


def frage_modell(sid: str, abschnitt: dict) -> tuple[list[dict], int]:
    from claude_client import complete
    p = PROMPT.format(sid=sid, ort=abschnitt["ort"] or "(ohne Ueberschrift)",
                      text=abschnitt["text"], max_karten=MAX_KARTEN)
    roh = complete(p, max_tokens=8000).strip()
    roh = re.sub(r"^```(?:json)?|```$", "", roh, flags=re.M).strip()
    return json.loads(roh).get("karten", []), len(p)


def frage_trocken(sid: str, abschnitt: dict) -> tuple[list[dict], int]:
    """Ohne API: eine gueltige und eine erfundene Karte, um beide Wege zu pruefen."""
    absatz = next((a for a in abschnitt["text"].split("\n\n") if len(a) > 120), None)
    karten = []
    if absatz:
        karten.append({"typ": "voraussetzungen", "frage": "Testfrage mit Sachverhalt?",
                       "loesung": "Testloesung mit tragenden Punkten.",
                       "beleg": " ".join(absatz.split())[:120]})
    karten.append({"typ": "frist", "frage": "Erfundene Karte?", "loesung": "Sollte verworfen werden.",
                   "beleg": "Diese Passage steht so nirgends im Skript, sie ist frei erfunden."})
    return karten, len(abschnitt["text"])


# --------------------------------------------------------------- Annahme

def norm(s: str) -> str:
    return " ".join((s or "").split())


def annehmen(karten, abschnitt, sid, bekannt: set[str]) -> tuple[list[dict], list[str]]:
    heu = norm(abschnitt["text"])
    gut, verworfen = [], []
    for k in karten:
        typ = (k.get("typ") or "").strip().lower()
        frage, loesung, beleg = (norm(k.get(f)) for f in ("frage", "loesung", "beleg"))
        if typ not in TYPEN:
            verworfen.append(f"Typ {typ!r}"); continue
        if not (15 <= len(frage) <= 600):
            verworfen.append("Fragenlaenge"); continue
        if not (10 <= len(loesung) <= 1500):
            verworfen.append("Loesungslaenge"); continue
        if len(beleg) < 40:
            verworfen.append("Beleg zu kurz"); continue
        if beleg not in heu:
            verworfen.append("Beleg nicht im Abschnitt"); continue
        kid = f"{sid}:{typ[:4]}:{hashlib.sha1(beleg.encode()).hexdigest()[:10]}"
        if kid in bekannt:
            verworfen.append("Dublette"); continue
        bekannt.add(kid)
        gut.append({"id": kid, "typ": typ, "gewicht": 2, "skript": sid,
                    "rn": "", "abschnitt": abschnitt["ort"],
                    "frage": frage, "loesung": loesung, "beleg": beleg})
    return gut, verworfen


# ------------------------------------------------------------------ Ablauf

def lies_json(p: Path, vorgabe):
    if not p.exists():
        return vorgabe
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return vorgabe


def bekannte_ids(sid: str) -> set[str]:
    ids = set()
    for name in (f"{sid}.kuratiert.json", f"{sid}.json", f"{sid}.gen.json"):
        for k in lies_json(KARTEN / name, {}).get("karten", []):
            if k.get("id"):
                ids.add(k["id"])
    return ids


def lauf(sid: str, limit: int | None, trocken: bool, neu: bool) -> dict:
    quelle = EXTRACT / f"{sid}.txt"
    if not quelle.exists():
        sys.exit(f"{quelle} fehlt")
    text = saeubere(quelle.read_text(encoding="utf-8", errors="replace"))
    abschnitte = schneide(text)
    print(f"{sid}: {len(text)} Zeichen bereinigt, {len(abschnitte)} Abschnitte", file=sys.stderr)

    manifest = lies_json(MANIFEST, {})
    erledigt = {} if neu else (manifest.get(sid) or {})
    ziel = KARTEN / f"{sid}.gen.json"
    bestand = lies_json(ziel, {"karten": []})
    bekannt = bekannte_ids(sid)

    stat = {"abschnitte": 0, "vorgeschlagen": 0, "angenommen": 0,
            "verworfen": {}, "typen": {}, "prompt_zeichen": 0}

    for i, a in enumerate(abschnitte, 1):
        if limit and stat["abschnitte"] >= limit:
            break
        schluessel = hashlib.sha1(norm(a["text"]).encode()).hexdigest()[:12]
        if schluessel in erledigt:
            continue
        stat["abschnitte"] += 1
        try:
            vorschlaege, zeichen = (frage_trocken if trocken else frage_modell)(sid, a)
        except Exception as e:
            print(f"  [{i}] FEHLER: {e}", file=sys.stderr)
            continue
        stat["prompt_zeichen"] += zeichen
        stat["vorgeschlagen"] += len(vorschlaege)
        gut, weg = annehmen(vorschlaege, a, sid, bekannt)
        for grund in weg:
            stat["verworfen"][grund] = stat["verworfen"].get(grund, 0) + 1
        for k in gut:
            stat["typen"][k["typ"]] = stat["typen"].get(k["typ"], 0) + 1
        bestand["karten"].extend(gut)
        stat["angenommen"] += len(gut)
        erledigt[schluessel] = {"karten": len(gut), "stand": time.strftime("%Y-%m-%d")}
        print(f"  [{i}/{len(abschnitte)}] {a['ort'][:52]:52} "
              f"{len(vorschlaege)} vorgeschlagen, {len(gut)} genommen", file=sys.stderr)
        # Nach jedem Abschnitt sichern: ein Abbruch kostet nichts Bezahltes.
        ziel.write_text(json.dumps(bestand, ensure_ascii=False, indent=1), encoding="utf-8")
        manifest[sid] = erledigt
        MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")

    return stat


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("skripte", nargs="*")
    ap.add_argument("--alle", action="store_true")
    ap.add_argument("--limit", type=int, default=None, help="nur die ersten N Abschnitte")
    ap.add_argument("--trocken", action="store_true", help="ohne API, prueft nur die Mechanik")
    ap.add_argument("--neu", action="store_true", help="Manifest fuer dieses Skript ignorieren")
    args = ap.parse_args()

    sids = args.skripte
    if args.alle:
        sids = sorted(p.stem for p in EXTRACT.glob("*.txt"))
    if not sids:
        sys.exit("Skript angeben oder --alle")

    gesamt = {"angenommen": 0, "vorgeschlagen": 0, "typen": {}, "verworfen": {}, "prompt_zeichen": 0}
    for sid in sids:
        s = lauf(sid, args.limit, args.trocken, args.neu)
        for feld in ("angenommen", "vorgeschlagen", "prompt_zeichen"):
            gesamt[feld] += s[feld]
        for feld in ("typen", "verworfen"):
            for k, v in s[feld].items():
                gesamt[feld][k] = gesamt[feld].get(k, 0) + v

    quote = (1 - gesamt["angenommen"] / gesamt["vorgeschlagen"]) * 100 if gesamt["vorgeschlagen"] else 0
    print("\n=== Bilanz ===")
    print(f"vorgeschlagen {gesamt['vorgeschlagen']}, angenommen {gesamt['angenommen']}, "
          f"Durchfallquote {quote:.0f} %")
    print("Typen:", dict(sorted(gesamt["typen"].items(), key=lambda x: -x[1])))
    if gesamt["verworfen"]:
        print("Verworfen:", dict(sorted(gesamt["verworfen"].items(), key=lambda x: -x[1])))
    print(f"Eingabe geschaetzt {gesamt['prompt_zeichen'] // 4} Token")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
