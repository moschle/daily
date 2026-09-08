#!/usr/bin/env python3
"""Karten aus den Skript-Volltexten. Loesung immer aus dem Skript, nichts erfinden."""
from __future__ import annotations

import json
import random
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXTRACTED = HERE / "extracted"
OUT = HERE / "karten"

SEITE = re.compile(r"(?m)^=+ SEITE \d+ =+$")
FUSSNOTE = re.compile(r"(?m)^\d{1,3}\s{2}\S")
KOLUMNE = re.compile(r"(?m)^[A-ZÄÖÜIVX][^\n]{0,60}?\s+\d{1,3}\s*$")


def clean(text: str) -> str:
    seiten = []
    for s in SEITE.split(text):
        m = FUSSNOTE.search(s)
        if m:
            s = s[: m.start()]
        seiten.append(KOLUMNE.sub("", s))
    t = "\n".join(seiten)
    t = re.sub(r"(\w)-\n(\w)", r"\1\2", t)
    t = re.sub(r"(?<=[a-zäöüß])(\d{1,2})(?=[\s.,;:)“])", "", t)
    t = re.sub(r"[ \t\u00a0]{2,}", " ", t)
    t = re.sub(r"(?m)^ +| +$", "", t)
    return re.sub(r"\n{3,}", "\n\n", t).strip()


UEBERSCHRIFT = re.compile(r"(?m)^\s*((?:[A-Z]|[IVX]{1,4}|\d{1,2}|[a-z])\.\s+[^\n]{3,80})$")
RANDNUMMER = re.compile(r"(?m)^\s*(\d{1,3})\s*$")


def _abschnitt_bei(text: str, pos: int) -> str:
    kette: dict[str, str] = {}
    for m in UEBERSCHRIFT.finditer(text, 0, pos):
        t = " ".join(m.group(1).split())
        marke = t.split(".")[0]
        ebene = "A" if marke.isupper() and len(marke) == 1 else "I" if re.fullmatch(r"[IVX]+", marke) else "1" if marke.isdigit() else "a"
        kette[ebene] = t
        for tiefer in {"A": "I1a", "I": "1a", "1": "a"}.get(ebene, ""):
            kette.pop(tiefer, None)
    return " › ".join(kette[e] for e in "AI1a" if e in kette)


def _randnummer_bei(text: str, pos: int) -> str:
    rn = [m.group(1) for m in RANDNUMMER.finditer(text, max(0, pos - 2500), pos)]
    return rn[-1] if rn else ""


ZITAT = re.compile(r"„([^“]{20,1200})“", re.S)
JURA = re.compile(
    r"\b(Klage|Kläger|Beklagt|Urteil|Antrag|Kosten|vollstreckbar|verurteilt|"
    r"festgestellt|abgewiesen|Angeklagt|Beschuldigt|Revision|Bescheid|"
    r"Widerspruch|Verfügung|Beweis|Zeuge|Frist|Anspruch|Verfahren|"
    r"Anklage|Strafe|Mandant|Gericht|Verwaltungsakt|Vertrag|§)"
)
TENORSATZ = re.compile(
    r"(?m)^(?:\d+\.\s*)?(?:Die Klage wird[^\n]*|Der Antrag wird[^\n]*|"
    r"Die (?:Berufung|Revision|Beschwerde)[^\n]*wird[^\n]*|"
    r"Der Beklagte wird (?:verurteilt|verpflichtet)[^\n]*|"
    r"Es wird festgestellt[^\n]*|Das Urteil ist[^\n]*vollstreckbar[^\n]*|"
    r"Die Kosten des [^\n]*)$"
)
FALSCH = re.compile(r"(?i)(falsch sind|falsch wäre|fehlerhaft|nicht:|unzulässig ist|typische fehler|häufiger fehler)")
FALL = re.compile(r"(?m)^(?:Beispiels?fall|Fall|Übungsfall)(?:\s*\d+)?\s*:\s*(.+?)(?=\n\s*\n|\Z)", re.S)
AUFZAEHLUNG = re.compile(r"(?m)^\s*[•\-–]\s+(.+)$")


def _satz_davor(text: str, pos: int, n: int = 2) -> str:
    vorher = text[max(0, pos - 700): pos]
    vorher = re.sub(r"(?m)^\s*[•\-–]\s*", "", vorher)
    saetze = re.split(r"(?<=[.:!?])\s+", vorher.strip())
    saetze = [s.strip() for s in saetze if len(s.strip()) > 20 and not UEBERSCHRIFT.fullmatch(s.strip())]
    return " ".join(saetze[-n:]).strip()


def _karten_tenorsatz(text: str, sid: str) -> list[dict]:
    karten = []
    for absatz in re.finditer(r"(?s)(?:^|\n\n)(.+?)(?=\n\n|\Z)", text):
        zeilen = [z for z in absatz.group(1).split("\n") if z.strip()]
        treffer = [z for z in zeilen if TENORSATZ.match(z.strip())]
        if not treffer or len(treffer) < max(1, len(zeilen) // 2):
            continue
        block = " ".join(" ".join(z.split()) for z in zeilen)
        if len(block) < 30 or len(block) > 900:
            continue
        kontext = _satz_davor(text, absatz.start(), 2)
        if len(kontext) < 30:
            continue
        karten.append({"typ": "formulierung", "frage": f"Tenorieren Sie. Situation laut Skript: {kontext}",
                       "loesung": block, "pos": absatz.start()})
    return karten


def _karten_formulierung(text: str, sid: str) -> list[dict]:
    karten = []
    for m in ZITAT.finditer(text):
        zitat = " ".join(m.group(1).split())
        if not JURA.search(zitat) or zitat.count("...") > 3:
            continue
        kontext = _satz_davor(text, m.start())
        if len(kontext) < 30 or FALSCH.search(kontext[-160:]):
            continue
        karten.append({"typ": "formulierung", "frage": f"Formulieren Sie. Situation laut Skript: {kontext}",
                       "loesung": zitat, "pos": m.start()})
    return karten


def _karten_fehler(text: str, sid: str) -> list[dict]:
    karten = []
    for m in FALSCH.finditer(text):
        block = text[m.start(): m.start() + 1200]
        punkte = [" ".join(p.split()) for p in AUFZAEHLUNG.findall(block)]
        punkte = [p for p in punkte if 12 < len(p) < 400]
        if not punkte:
            continue
        regel = _satz_davor(text, m.start(), 1)
        einleitung = text[m.start(): block.find("\n", 0)].strip()
        for p in punkte[:6]:
            karten.append({"typ": "fehler",
                           "frage": f"Was ist hieran fehlerhaft, und wie lautet es richtig?\n{p}",
                           "loesung": f"{einleitung} {regel}".strip(), "pos": m.start()})
    return karten


def _karten_fall(text: str, sid: str) -> list[dict]:
    karten = []
    for m in FALL.finditer(text):
        fall = " ".join(m.group(1).split())
        rest = text[m.end():].lstrip("\n")
        loesung = " ".join(rest.split("\n\n", 1)[0].split())
        if loesung.startswith(("Fall", "Beispiel")) or UEBERSCHRIFT.match(loesung) or len(loesung) < 60:
            continue
        if len(fall) > 900:
            teile = re.split(r"(?<=[.?!])\s+(?=(?:Hier|Die Revision|Das Rechtsmittel|Der Antrag|Die Klage|Damit|Somit|Folglich)\b)", fall, maxsplit=1)
            if len(teile) == 2:
                fall, loesung = teile[0], teile[1] + " " + loesung
        if len(fall) < 60:
            continue
        karten.append({"typ": "fall", "frage": f"Lösen Sie im Klausurstil.\n{fall}",
                       "loesung": loesung[:1500], "pos": m.start()})
    return karten


def _karten_aufbau(text: str, sid: str) -> list[dict]:
    karten = []
    for m in re.finditer(r"(?i)(aufbau|reihenfolge|übersicht|gliederung|prüfungsreihenfolge)[^\n]{0,80}:\s*\n", text):
        block = text[m.end(): m.end() + 1500]
        punkte = [" ".join(p.split()) for p in AUFZAEHLUNG.findall(block.split("\n\n", 1)[0])]
        punkte = [p for p in punkte if 6 < len(p) < 250]
        if len(punkte) < 3:
            continue
        thema = " ".join(text[max(0, m.start() - 160): m.end()].split())
        gemischt = punkte[:]
        random.Random(m.start()).shuffle(gemischt)
        karten.append({
            "typ": "aufbau",
            "frage": f"Bringen Sie in die richtige Reihenfolge und ergänzen Sie Fehlendes.\n{thema}\n" + "\n".join(f"– {p}" for p in gemischt),
            "loesung": "\n".join(f"{i+1}. {p}" for i, p in enumerate(punkte)),
            "pos": m.start(),
        })
    return karten


def baue(sid: str) -> list[dict]:
    pfad = EXTRACTED / f"{sid}.txt"
    if not pfad.exists():
        return []
    text = clean(pfad.read_text(encoding="utf-8", errors="replace"))
    roh = (_karten_formulierung(text, sid) + _karten_tenorsatz(text, sid) + _karten_fall(text, sid)
           + _karten_fehler(text, sid) + _karten_aufbau(text, sid))
    roh.sort(key=lambda k: k["pos"])
    karten, gesehen = [], set()
    for i, k in enumerate(roh):
        schluessel = (k["typ"], k["loesung"][:80])
        if schluessel in gesehen:
            continue
        gesehen.add(schluessel)
        k["id"] = f"{sid}:{k['typ'][:4]}:{i+1:03d}"
        k["skript"] = sid
        k["abschnitt"] = _abschnitt_bei(text, k["pos"])
        k["rn"] = _randnummer_bei(text, k["pos"])
        k.pop("pos")
        karten.append(k)
    return karten


def main() -> int:
    ids = sorted(p.stem for p in EXTRACTED.glob("*.txt") if p.stat().st_size > 5000)
    if len(sys.argv) > 1 and sys.argv[1] in ids:
        karten = baue(sys.argv[1])
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 8
        for k in random.Random(1).sample(karten, min(n, len(karten))):
            print(f"[{k['id']}] {k['abschnitt']}  Rn {k['rn']}\n{k['frage']}\n→ {k['loesung']}\n")
        print(f"{len(karten)} Karten in {sys.argv[1]}")
        return 0
    OUT.mkdir(exist_ok=True)
    zeilen = ["# Karten aus den Skripten", "",
              "| Skript | formulierung | fall | fehler | aufbau | gesamt |",
              "|---|---|---|---|---|---|"]
    gesamt = 0
    for sid in ids:
        karten = baue(sid)
        (OUT / f"{sid}.json").write_text(json.dumps({"karten": karten}, ensure_ascii=False, indent=1), encoding="utf-8")
        z = {t: sum(1 for k in karten if k["typ"] == t) for t in ("formulierung", "fall", "fehler", "aufbau")}
        zeilen.append(f"| {sid} | {z['formulierung']} | {z['fall']} | {z['fehler']} | {z['aufbau']} | {len(karten)} |")
        gesamt += len(karten)
    zeilen.append(f"| **gesamt** | | | | | **{gesamt}** |")
    (OUT / "INDEX.md").write_text("\n".join(zeilen) + "\n", encoding="utf-8")
    print("\n".join(zeilen))
    return 0


if __name__ == "__main__":
    sys.exit(main())
