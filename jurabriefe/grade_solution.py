#!/usr/bin/env python3
"""Klausurkontrolle auf Examensniveau."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from claude_client import complete
from fsrs_scheduler import review

ROOT = Path(__file__).parent
CASES = ROOT / "cases.json"
EXTRACTED = ROOT / "extracted"

GRADE_PROMPT = """Du korrigierst eine Assessorklausur, staatliche Sicht, 2. Examen.
Massstab: Berliner ZR-Skript und die Praxis des LJPA. Keine Anrede.

Gebiet: {gebiet}
Quelle: {quelle}
Skriptregeln:
{regeln}

Musterrubrum (nicht als einzige richtige Loesung, aber als Massstab der Formalien):
{muster}

Loesung der Bearbeiterin:
---
{loesung}
---

Pruefe insbesondere:
- Im Namen des Volkes
- Eingangsformel
- Parteibezeichnung (Genitiv/Akkusativ oder durchgehender Nominativ), Anschrift, gesetzliche Vertreter
- Parteistellung rechtsbuendig, Widerklagezusatz
- Prozessbevollmaechtigte in Parenthese, ausgeschrieben
- Streithelfer unter der Partei, der sie beigetreten sind
- Gericht, Spruchkoerper, Richter mit Amtsbezeichnung, letzter Verhandlungstag, nicht Verkuendungstag
- Kaufmann unter der Firma, Minderjaehrige mit Geburtsdatum und beiden Eltern

Antwort nur JSON:
  "punkte": 0-18,
  "note": 1-5,
  "staerken": [str],
  "luecken": [str],
  "verbesserung": [str],
  "muster_kurz": kurzer Hinweis ohne den ganzen Kopf zu wiederholen.
"""


def load_case(case_id: str) -> dict:
    data = json.loads(CASES.read_text(encoding="utf-8"))
    for c in data.get("cases", []):
        if c["id"] == case_id:
            return c
    return {}


def load_skript(case: dict) -> tuple[str, str]:
    sid = case.get("skript_id")
    path = EXTRACTED / f"{sid}.txt" if sid else None
    if not path or not path.exists():
        return "", ""
    text = path.read_text(encoding="utf-8")
    start = case.get("skript_start") or ""
    end = case.get("skript_end") or ""
    i = text.find(start) if start else 0
    # skip TOC
    while i >= 0 and "...." in text[i: text.find("\n", i)]:
        nxt = text.find(start, i + 1)
        if nxt < 0:
            break
        i = nxt
    j = text.find(end, i + 1) if end else -1
    chunk = text[i: j if j > i else i + 20000]
    k = chunk.find("12 C 310/24")
    if k >= 0:
        line = chunk.rfind("Amtsgericht", 0, k + 1)
        if line >= 0:
            return chunk[:line][:3500], chunk[line:line + 2500]
    return chunk[:3500], ""


def grade(case_id: str, loesung: str) -> dict:
    case = load_case(case_id)
    if not case:
        return {"fehler": f"Unbekannte Fall-ID: {case_id}"}
    regeln, muster = load_skript(case)
    prompt = GRADE_PROMPT.format(
        gebiet=case.get("gebiet", ""),
        quelle=case.get("quelle", ""),
        regeln=regeln[:3000],
        muster=muster[:2500] or "(kein Musterrubrum im Abschnitt)",
        loesung=loesung[:6000],
    )
    try:
        raw = complete(prompt, max_tokens=900)
    except Exception as e:
        return {"fehler": f"API: {e}"}
    m = re.search(r"\{.*\}", raw, re.S)
    if not m:
        return {"fehler": "Kein JSON", "roh": raw[:500]}
    try:
        result = json.loads(m.group(0))
    except json.JSONDecodeError:
        return {"fehler": "JSON kaputt", "roh": raw[:500]}
    try:
        punkte = int(result.get("punkte", 0))
    except (TypeError, ValueError):
        punkte = 0
    result["punkte"] = max(0, min(18, punkte))
    try:
        note = int(result.get("note", 3))
    except (TypeError, ValueError):
        note = 3
    result["note"] = max(1, min(5, note))
    result["case_id"] = case_id
    result["fsrs"] = review(case_id, result["note"], json.dumps(result.get("luecken", []), ensure_ascii=False))
    (ROOT / "last_grade.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return result


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Nutzung: grade_solution.py <case_id> <loesungstext-Datei>")
        sys.exit(1)
    print(json.dumps(grade(sys.argv[1], Path(sys.argv[2]).read_text(encoding="utf-8")), ensure_ascii=False, indent=2))
