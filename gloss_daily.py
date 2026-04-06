#!/usr/bin/env python3
"""
GLOSS Tagesplaner — öffnet die richtige GLOSS-Seite und legt einen Lernzettel auf den Desktop.
Aufruf: python3 gloss_daily.py
Oder via launchd/cron jeden Morgen automatisch.
"""

import json
import subprocess
import webbrowser
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

BERLIN_TZ = ZoneInfo("Europe/Berlin")
STATE_FILE = Path(__file__).parent / "gloss_state.json"

def today():
    return datetime.now(BERLIN_TZ)

def load_state():
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return {"ar_lesson": 0, "fa_lesson": 0, "ar_level": "1", "fa_level": "1", "last_date": ""}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

def main():
    now = today()
    doy = now.timetuple().tm_yday
    date_str = now.strftime("%Y-%m-%d")
    day_de = {"Monday":"Montag","Tuesday":"Dienstag","Wednesday":"Mittwoch",
              "Thursday":"Donnerstag","Friday":"Freitag","Saturday":"Samstag",
              "Sunday":"Sonntag"}.get(now.strftime("%A"), "")

    state = load_state()

    # Schon heute gelaufen?
    if state.get("last_date") == date_str:
        print(f"Heute ({date_str}) schon gelaufen.")
        return

    # Sprache bestimmen (gleiche Logik wie Morgenbrief)
    if doy % 2 == 0:
        lang = "Arabisch"
        lang_code = "ar"
        gloss_lang = "Arabic-Levantine"
        level = state.get("ar_level", "1")
        lesson_count = state.get("ar_lesson", 0) + 1
        state["ar_lesson"] = lesson_count
        pimsleur = f"Pimsleur Eastern Arabic — Lektion {lesson_count}"
        lesen = "Arabic Today oder Easy Arabic Reader"
        extras = "Mi: Preply Arabisch (Libanesin) | Fr: Preply Arabisch"
    else:
        lang = "Persisch"
        lang_code = "fa"
        gloss_lang = "Farsi"
        level = state.get("fa_level", "1")
        lesson_count = state.get("fa_lesson", 0) + 1
        state["fa_lesson"] = lesson_count
        pimsleur = f"Pimsleur Farsi — Lektion {lesson_count}"
        lesen = "Harry Potter auf Persisch (10–15 Seiten)"
        extras = "Do: Preply Persisch (Afghanin) | Abends: Once Upon a Time in Iran"

    # Competence rotieren (Lexical → Structural → Discourse → Socio-Cultural)
    competences = ["Lexical", "Structural", "Discourse", "Socio-Cultural"]
    comp = competences[lesson_count % 4]

    # GLOSS-URL mit Filtern
    gloss_url = f"https://gloss.dliflc.edu/"

    # Tageszettel auf Desktop
    desktop = Path.home() / "Desktop"
    zettel = desktop / f"GLOSS_{date_str}.md"

    inhalt = f"""# {day_de}, {now.strftime('%d.%m.%Y')} — {lang}-Tag

## GLOSS-Lektion #{lesson_count}
Sprache: {gloss_lang}
Level: {level}
Competence: {comp}
Modality: Listening (oder Reading, wenn schon gehört)

→ {gloss_url}

## Ablauf (20–30 Min.)
1. Hören ohne Text (5 Min.) — große Audiodatei
2. Transkript lesen + Glossar (5 Min.)
3. Hören mit Text (5 Min.) — kleine Audiodatei (langsam)
4. Aufgaben machen (5–10 Min.) — Competence: {comp}
5. Optional: Anki-Deck der Lektion laden

## Außerdem heute
– {pimsleur}
– Lesen: {lesen}
– {extras}
– Morgenbrief-Sprachübung durcharbeiten
"""

    zettel.write_text(inhalt, encoding="utf-8")
    print(f"Tageszettel: {zettel}")

    # GLOSS im Browser öffnen
    webbrowser.open(gloss_url)

    state["last_date"] = date_str
    save_state(state)
    print(f"{lang}-Tag #{lesson_count} — {comp} — Level {level}")

if __name__ == "__main__":
    main()
