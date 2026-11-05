"""GOLESTAN im Morgenbrief: jeden Tag eine Geschichte aus Saadis Golestan (seit 05.11.2026).

Daten nur auf dem Server: GOLESTAN_DIR/teile.json (golestan_holen.py), stand.json.
Sehr kurze Stücke (Merksprüche in Bab 8) werden zusammengefasst, damit jeder Tag
etwa 80–250 Wörter hat. Glossen und Anki-Wörter setzt sprachuebung.golestan_glossieren.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

MIN_W, MAX_W = 80, 250


def _laden(pfad: Path, leer):
    try:
        return json.loads(pfad.read_text(encoding="utf-8"))
    except Exception:
        return leer


def _text(teil: dict) -> str:
    """Prosa als Absatz, Halbverse paarweise eingerückt."""
    out, vers = [], []
    for pos, z in teil["zeilen"]:
        z = z.strip()
        if pos in (0, 1, 2, 3) or (isinstance(pos, int) and pos >= 0):
            vers.append("    " + z)
            continue
        if vers:
            out.append("\n".join(vers))
            vers = []
        out.append(z)
    if vers:
        out.append("\n".join(vers))
    return "\n\n".join(out)


def abschnitt(ordner: Path) -> tuple[str, str] | None:
    stand = _laden(ordner / "stand.json", {})
    heute = date.today().isoformat()
    if stand.get("datum") == heute and stand.get("heute"):
        return tuple(stand["heute"])
    teile = _laden(ordner / "teile.json", [])
    i = stand.get("naechster", 0)
    if i >= len(teile):
        return None
    titel, stuecke, n = teile[i]["titel"], [], 0
    while i < len(teile):
        t = _text(teile[i])
        w = len(t.split())
        if stuecke and n + w > MAX_W:
            break
        stuecke.append(t if not stuecke else f"{teile[i]['titel']}\n\n{t}")
        n += w
        i += 1
        if n >= MIN_W:
            break
    kopf = f"{titel} ({i}/{len(teile)})"
    out = (kopf, "\n\n".join(stuecke))
    woche = (stand.get("woche") or [])[-6:] + [list(out)]
    (ordner / "stand.json").write_text(json.dumps({"naechster": i, "datum": heute, "heute": list(out),
                                                   "woche": woche}, ensure_ascii=False), encoding="utf-8")
    return out


APKG = None   # sonntags eine Merkvers-Karte (lesen_karten-Format), hängt run_morgenbrief an

WOCHENKARTE = """Unten stehen die Golestan-Geschichten (Saadi), die ein Deutscher (Persisch B1, Islamwissenschaftler) diese Woche gelesen hat.
Wähle den bekanntesten oder einprägsamsten Merkvers bzw. Spruch daraus und erstelle EINE Anki-Karte:
"frage": der erste Halbvers bzw. Satzanfang auf Persisch mit Kurzvokalen, gefolgt von „…“;
"antwort": die Fortsetzung auf Persisch und darunter eine deutsche Übersetzung des ganzen Verses;
"kontext": 1–2 Sätze, in welcher Geschichte (Bab, Nummer) der Vers steht und worum es dort geht.
Antworte NUR mit JSON: {{"frage": "", "antwort": "", "kontext": ""}}

{texte}"""


def wochenkarte(ordner: Path, claude) -> None:
    """Sonntags: eine Karte mit dem Merkvers der Woche ins Lektüre-Deck."""
    global APKG
    if date.today().weekday() != 6:
        return
    import re
    import lesen_karten
    woche = _laden(ordner / "stand.json", {}).get("woche") or []
    if not woche:
        return
    roh = claude(WOCHENKARTE.format(texte="\n\n".join(f"{k}\n{t}" for k, t in woche)), 1500)
    m = re.search(r"\{.*\}", roh, re.S)
    karte = json.loads(m.group(0)) if m else {}
    if karte.get("frage") and karte.get("antwort"):
        APKG = lesen_karten.paket([karte], Path("/tmp"), f"golestan_{date.today().isoformat()}")
