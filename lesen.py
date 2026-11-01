"""Abschnitt LESEN im Morgenbrief: ein zusammenhängender Ausschnitt Forschungsliteratur pro Tag.

Der Mac (~/Projects/foerderungen/leseliste/lesen_export.py) liest die Texte aus Bookends und
Calibre als Absatzlisten aus und legt sie hier ab; die PDFs bleiben auf dem Mac, nichts davon
gehört ins Repo.

  LESEN_DIR/reihenfolge.json     Text-Namen in Lesereihenfolge
  LESEN_DIR/texte/<name>.json    {"titel", "absaetze": [...]}  ("## " = Überschrift)
  LESEN_DIR/stand.json           {"text", "absatz", "fertig": [...], "datum", "heute"}  (nur hier geschrieben)

Claude wählt aus dem Fenster ab der aktuellen Stelle ein Ende an einer sinnvollen Grenze und
gibt den Abschnitt bereinigt zurück (Absätze, Fußnotenreste, Halbleerzeichen). Eine Prüfung
stellt sicher, dass der Wortlaut nicht verändert wurde; sonst geht der Rohtext raus. Am
nächsten Tag geht es am gewählten Ende weiter.
"""

from __future__ import annotations

import json
from collections import Counter
import os
import re
import sys
import unicodedata
import urllib.request
from datetime import date
from pathlib import Path

LESEN_DIR = Path(os.environ.get("LESEN_DIR", "/automat/lesen"))
MIN_W, MAX_W, FENSTER_W = 2500, 4000, 5500


def _laden(pfad: Path, leer):
    try:
        return json.loads(pfad.read_text(encoding="utf-8"))
    except Exception:
        return leer


def _w(t: str) -> int:
    return len(t.split())


def _buchstaben(t: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKC", t) if c.isalpha())


def _claude(prompt: str, max_tokens: int) -> str:
    try:
        from claude_client import MODELS
    except Exception:
        MODELS = ["claude-sonnet-4-6"]
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    fehler = None
    for model in MODELS:
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=json.dumps({"model": model, "max_tokens": max_tokens,
                             "messages": [{"role": "user", "content": prompt}]}).encode(),
            headers={"Content-Type": "application/json", "x-api-key": key,
                     "anthropic-version": "2023-06-01"})
        try:
            with urllib.request.urlopen(req, timeout=420) as r:
                return json.loads(r.read())["content"][0]["text"]
        except Exception as e:
            fehler = e
            print(f"Lesen: {model} gescheitert: {e}", file=sys.stderr)
    raise RuntimeError(fehler)


AUFTRAG = """Du bekommst den Anfang eines Abschnitts aus einem wissenschaftlichen Text. Die Absätze sind nummeriert, "## " markiert eine Überschrift. Der Text stammt aus einer PDF-Extraktion und kann Fehler enthalten.

1. Wähle das Ende des heutigen Leseabschnitts. Er beginnt bei Absatz {start} und soll zwischen {min_w} und {max_w} Wörter lang sein. Lege das Ende an eine sinnvolle Grenze: Ende eines Kapitels oder Unterabschnitts (vor einer Überschrift) oder Ende eines Gedankengangs. Nie mitten in einer Argumentation.
2. Gib den Text von Absatz {start} bis zum gewählten Absatz bereinigt aus:
   - Absätze richtig trennen; über Zeilen-, Spalten- oder Seitengrenzen zerrissene Sätze und Wörter zusammenfügen
   - Reste von Kopf- und Fußzeilen, Seitenzahlen, Fußnotenziffern, Fußnotentext, Bildunterschriften, Verlags- und Download-Hinweisen entfernen
   - persischen/tadschikischen Text in persischer Schrift korrekt setzen: Halbleerzeichen (U+200C) bei می-/نمی-, -ها, -های, -ای, -تر, -ترین usw.; durch die Extraktion zerlegte Ligaturen korrigieren (z. B. تحوالت → تحولات, انقالب → انقلاب)
   - Überschriften als eigene Zeile ohne "##"
   - KEIN Wort umformulieren, nichts kürzen außer den genannten Resten, nichts zusammenfassen, nichts ergänzen, nicht übersetzen

Antwortformat, sonst nichts:
ENDE: <Nummer des letzten Absatzes>

<bereinigter Text>

TEXT:
{absaetze}"""


def _waehle_und_bereinige(abs_: list[str], start: int) -> tuple[int, str]:
    fenster, n = [], 0
    for i in range(start, len(abs_)):
        fenster.append(i)
        n += _w(abs_[i])
        if n >= FENSTER_W:
            break
    roh = lambda bis: "\n\n".join(abs_[i][3:] if abs_[i].startswith("## ") else abs_[i]
                                  for i in range(start, bis + 1))
    rest = sum(_w(a) for a in abs_[start:])
    # Fallback: Ende nach Wortzahl, möglichst vor einer Überschrift
    ende, n = fenster[-1], 0
    for i in fenster:
        n += _w(abs_[i])
        if n >= MIN_W and (i + 1 < len(abs_) and abs_[i + 1].startswith("## ") or n >= MAX_W):
            ende = i
            break
    if rest <= MAX_W:
        ende = len(abs_) - 1
    try:
        prompt = AUFTRAG.format(start=start, min_w=MIN_W if rest > MAX_W else 0,
                                max_w=MAX_W if rest > MAX_W else rest,
                                absaetze="\n\n".join(f"[{i}] {abs_[i]}" for i in fenster))
        antwort = _claude(prompt, 16000)
        m = re.match(r"\s*ENDE:\s*(\d+)\s*\n(.*)", antwort, re.S)
        if not m:
            raise ValueError("Antwortformat")
        k_ende = int(m.group(1))
        if not (start <= k_ende <= fenster[-1]):
            raise ValueError(f"Ende {k_ende} außerhalb")
        text = m.group(2).strip()
        a, b = _buchstaben(roh(k_ende)), _buchstaben(text)
        ta = Counter(a[i:i + 3] for i in range(len(a) - 2))
        tb = Counter(b[i:i + 3] for i in range(len(b) - 2))
        quote = sum((ta & tb).values()) / max(1, sum(tb.values()))
        if not (0.8 * len(a) <= len(b) <= 1.02 * len(a)) or quote < 0.95:
            raise ValueError(f"Prüfung: Länge {len(b)}/{len(a)}, Übereinstimmung {quote:.2f}")
        return k_ende, text
    except Exception as e:
        print(f"Lesen: Bereinigung verworfen ({e}), Rohtext bis {ende}", file=sys.stderr)
        return ende, roh(ende)


def abschnitt() -> str:
    stand = _laden(LESEN_DIR / "stand.json", {})
    heute = date.today().isoformat()
    if stand.get("datum") == heute and stand.get("heute"):
        return stand["heute"]  # Nachversand am selben Tag: dasselbe Stück
    reihe = _laden(LESEN_DIR / "reihenfolge.json", [])
    fertig = stand.get("fertig", [])
    name, start = stand.get("text"), stand.get("absatz", 0)
    if not name or name in fertig or not (LESEN_DIR / "texte" / f"{name}.json").exists():
        name = next((n for n in reihe if n not in fertig), None)
        start = 0
    if not name:
        return ""
    text = _laden(LESEN_DIR / "texte" / f"{name}.json", None)
    if not text:
        return ""
    abs_ = text["absaetze"]
    ende, stueck = _waehle_und_bereinige(abs_, start)
    gesamt = sum(_w(a) for a in abs_) or 1
    bis = sum(_w(a) for a in abs_[:ende + 1])
    kopf = text["titel"]
    if start > 0 or ende < len(abs_) - 1:
        kopf += f" ({round(100 * bis / gesamt)} %)"
    out = f"LESEN\n{kopf}\n\n{stueck}\n\n"
    if ende >= len(abs_) - 1:
        fertig.append(name)
        name, ende = None, -1
    (LESEN_DIR / "stand.json").write_text(json.dumps(
        {"text": name, "absatz": ende + 1, "fertig": fertig, "datum": heute, "heute": out},
        ensure_ascii=False), encoding="utf-8")
    return out
