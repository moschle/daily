#!/usr/bin/env python3
"""Klausur-Kontrolle: bewertet die gelöste Aufgabe über die Claude-API.

Eingabe: Antwortmail mit Lösungstext. Ausgabe: strukturierte Bewertung
(Punkte 0-18, Stärken, Lücken, konkrete Verbesserungen) plus FSRS-Update.

Der Prompt orientiert sich an offiziellen Korrekturleitfäden
(Gutachtenstil, Obersatz, Subsumtion, Problemerkenntnis, Schwerpunktsetzung).
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from claude_client import complete
from fsrs_scheduler import review

ROOT = Path(__file__).parent
CASES = ROOT / "cases.json"


def load_case(case_id: str) -> dict:
    data = json.loads(CASES.read_text(encoding="utf-8"))
    for c in data.get("cases", []):
        if c["id"] == case_id:
            return c
    return {}


GRADE_PROMPT = """Du bist erfahrene Korrektorin im 2. Juristischen Staatsexamen (Sachsen-Anhalt, LJPA Halle).
Bewerte die Klausurlösung einer Referendarin streng, aber fair — auf absolutem Examensniveau.
Orientiere dich an den offiziellen Bewertungskriterien:
- Gutachtenstil (Obersatz, Definition, Subsumtion, Ergebnis) bzw. Urteilsstil bei staatlicher Sicht
- Arbeit am Sachverhalt und am Gesetz, Auslegung (Wortlaut, Systematik, Telos)
- Problemerkenntnis und -bearbeitung, Schwerpunktsetzung, Klausurökonomie
- Vertretbare Lösungen akzeptieren, auch abweichend von der Musterlösung
- Häufige Fehler: Urteilsstil statt Gutachtenstil, ungenaue Obersätze, Evidenzbehauptungen, unwesentliches ausführlich

Fall: {gebiet}
Kernfrage: {kernfrage}
Erwartete Begriffe/Sprache: {begriffe}
Quelle: {quelle}

Ihre Lösung:
---
{loesung}
---

Antworte AUSSCHLIESSLICH als JSON (kein Markdown, kein Text davor/danach) mit genau diesen Keys:
  "punkte": Zahl 0-18 (18 = fehlerfrei, 0 = völlig unbrauchbar),
  "note": Zahl 1-5 (1 sehr unsicher, 5 sitzt),
  "staerken": [kurzer Text],
  "luecken": [konkrete Lücken, z. B. fehlende Obersatzbildung],
  "verbesserung": [was sie beim nächsten Mal tun soll],
  "muster_kurz": 2-3 Sätze Musterlösung zum Kern.
"""


def grade(case_id: str, loesung: str) -> dict:
    case = load_case(case_id)
    if not case:
        return {"fehler": f"Unbekannte Fall-ID: {case_id}"}
    prompt = GRADE_PROMPT.format(
        gebiet=case.get("gebiet", ""),
        kernfrage=case.get("kernfrage", ""),
        begriffe=", ".join(case.get("behoerdensprache", [])),
        quelle=case.get("quelle", ""),
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
    # Punkte auf 0-18 clampen
    try:
        punkte = int(result.get("punkte", 0))
    except (TypeError, ValueError):
        punkte = 0
    result["punkte"] = max(0, min(18, punkte))
    note = int(result.get("note", 3))
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
    cid = sys.argv[1]
    text = Path(sys.argv[2]).read_text(encoding="utf-8")
    print(json.dumps(grade(cid, text), ensure_ascii=False, indent=2))
