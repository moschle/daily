"""Abschnitt LESEN im Morgenbrief: ein Stück Forschungsliteratur pro Tag.

Die Stücke schneidet der Mac (~/Projects/foerderungen/leseliste/lesen_export.py)
aus Bookends und Calibre und legt sie hier ab. Die PDFs bleiben auf dem Mac,
nichts davon gehört ins Repo.

  LESEN_DIR/reihenfolge.json   Liste der Stück-Namen in Lesereihenfolge
  LESEN_DIR/stuecke/<name>.json  {"titel", "teil", "von", "text"}
  LESEN_DIR/stand.json         {"geliefert": [<name>, ...]}  (schreibt nur dieser Server)
"""

from __future__ import annotations

import json
import os
from datetime import date
from pathlib import Path

LESEN_DIR = Path(os.environ.get("LESEN_DIR", "/automat/lesen"))


def _laden(pfad: Path, leer):
    try:
        return json.loads(pfad.read_text(encoding="utf-8"))
    except Exception:
        return leer


def abschnitt() -> str:
    reihe = _laden(LESEN_DIR / "reihenfolge.json", [])
    stand = _laden(LESEN_DIR / "stand.json", {"geliefert": []})
    geliefert = stand.get("geliefert", [])
    heute = date.today().isoformat()
    # Lief der Brief heute schon (Nachversand), dasselbe Stück noch einmal
    if stand.get("datum") == heute and stand.get("heute"):
        name = stand["heute"]
    else:
        name = next((n for n in reihe if n not in geliefert), None)
    if not name:
        return ""
    stueck = _laden(LESEN_DIR / "stuecke" / f"{name}.json", None)
    if not stueck:
        return ""
    if name not in geliefert:
        geliefert.append(name)
    (LESEN_DIR / "stand.json").write_text(
        json.dumps({"geliefert": geliefert, "datum": heute, "heute": name}, ensure_ascii=False),
        encoding="utf-8")
    kopf = stueck["titel"]
    if stueck.get("von", 1) > 1:
        kopf += f" ({stueck['teil']}/{stueck['von']})"
    return f"LESEN\n{kopf}\n\n{stueck['text'].strip()}\n\n"
