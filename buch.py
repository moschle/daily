"""Persisches Buch im Morgenbrief: jeden Tag der nächste Abschnitt im Originalwortlaut.

Daten liegen nur auf dem Server (BUCH_DIR, Standard /automat/buch_fa), nicht im Repo:
  reihenfolge.json   Text-Namen in Lesereihenfolge
  texte/<name>.json  {"titel", "absaetze": [...]}
  stand.json         {"text", "absatz", "fertig": [...], "datum", "heute"}
Der Abschnitt endet immer an einem Absatzende; ein kurzer Rest der Geschichte kommt
gleich mit, damit kein Tag nur aus ein paar Zeilen besteht.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from datetime import date
from pathlib import Path

MIN_W, MAX_W, REST_W = 500, 750, 300
WORT = re.compile(r"[؀-ۿ‌]+")


def _laden(pfad: Path, leer):
    try:
        return json.loads(pfad.read_text(encoding="utf-8"))
    except Exception:
        return leer


def _w(t: str) -> int:
    return len(t.split())


def haeufigkeit(ordner: Path) -> Counter:
    """Wortformen über alle Texte gezählt; entscheidet, welche Wörter ins Anki-Paket kommen."""
    c = Counter()
    for name in _laden(ordner / "reihenfolge.json", []):
        for a in _laden(ordner / "texte" / f"{name}.json", {}).get("absaetze", []):
            c.update(WORT.findall(a))
    return c


def abschnitt(ordner: Path) -> tuple[str, str] | None:
    """(Kopfzeile, Text) für heute oder None, wenn alles gelesen ist."""
    stand = _laden(ordner / "stand.json", {})
    heute = date.today().isoformat()
    if stand.get("datum") == heute and stand.get("heute"):
        return tuple(stand["heute"])           # Nachversand: dasselbe Stück
    reihe = _laden(ordner / "reihenfolge.json", [])
    fertig = stand.get("fertig", [])
    name, start = stand.get("text"), stand.get("absatz", 0)
    if not name or name in fertig:
        name, start = next((n for n in reihe if n not in fertig), None), 0
    if not name:
        return None
    text = _laden(ordner / "texte" / f"{name}.json", None)
    if not text:
        return None
    abs_ = text["absaetze"]
    ende, n = len(abs_) - 1, 0
    for i in range(start, len(abs_)):
        n += _w(abs_[i])
        naechster = _w(abs_[i + 1]) if i + 1 < len(abs_) else 0
        if n >= MAX_W or (n >= MIN_W and (n + naechster > MAX_W or abs_[i + 1:i + 2] == ["* * *"])):
            ende = i
            break
    if sum(_w(a) for a in abs_[ende + 1:]) < REST_W:
        ende = len(abs_) - 1
    stueck = "\n\n".join(abs_[start:ende + 1])
    gesamt = sum(_w(a) for a in abs_) or 1
    bis = sum(_w(a) for a in abs_[:ende + 1])
    kopf = text["titel"] + (f" ({round(100 * bis / gesamt)} %)" if ende < len(abs_) - 1 else " (Schluss)")
    if ende >= len(abs_) - 1:
        fertig.append(name)
        name, ende = None, -1
    (ordner / "stand.json").write_text(json.dumps(
        {"text": name, "absatz": ende + 1, "fertig": fertig, "datum": heute, "heute": [kopf, stueck]},
        ensure_ascii=False), encoding="utf-8")
    return kopf, stueck
