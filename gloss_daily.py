#!/usr/bin/env python3
"""
GLOSS Tagesplaner — legt beim Login einen Lernzettel auf den GLOSS_DIR
und öffnet GLOSS mit der richtigen Sprache.
"""

import json
import webbrowser
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

BERLIN_TZ = ZoneInfo("Europe/Berlin")
STATE_FILE = Path(__file__).parent / "gloss_state.json"
GLOSS_DIR = Path.home() / "Desktop"

# Alte Zettel aufräumen
def _cleanup_old():
    for f in GLOSS_DIR.glob("GLOSS_*.md"):
        try: f.unlink()
        except: pass

def load_state():
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r") as f: return json.load(f)
        except: pass
    return {"ar_lesson": 0, "fa_lesson": 0, "ar_level": "1", "fa_level": "1",
            "ar_competence_idx": 0, "fa_competence_idx": 0, "last_date": ""}

def save_state(state):
    with open(STATE_FILE, "w") as f: json.dump(state, f, indent=2)

COMPETENCES = ["Lexical", "Structural", "Discourse", "Socio-Cultural"]
MODALITIES = ["Listening", "Reading"]

def main():
    now = datetime.now(BERLIN_TZ)
    date_str = now.strftime("%Y-%m-%d")
    day_de = {"Monday":"Montag","Tuesday":"Dienstag","Wednesday":"Mittwoch",
              "Thursday":"Donnerstag","Friday":"Freitag","Saturday":"Samstag",
              "Sunday":"Sonntag"}.get(now.strftime("%A"), "")
    doy = now.timetuple().tm_yday

    state = load_state()
    if state.get("last_date") == date_str:
        return  # Heute schon gelaufen

    _cleanup_old()

    # Sprache bestimmen (gleiche Logik wie Morgenbrief)
    if doy % 2 == 0:
        lang, lang_name, gloss_lang = "ar", "Arabisch", "Arabic-Levantine"
        lesson_key, comp_key, level_key = "ar_lesson", "ar_competence_idx", "ar_level"
    else:
        lang, lang_name, gloss_lang = "fa", "Persisch", "Farsi"
        lesson_key, comp_key, level_key = "fa_lesson", "fa_competence_idx", "fa_level"

    lesson_nr = state.get(lesson_key, 0) + 1
    state[lesson_key] = lesson_nr
    comp_idx = state.get(comp_key, 0)
    comp = COMPETENCES[comp_idx % len(COMPETENCES)]
    state[comp_key] = comp_idx + 1
    level = state.get(level_key, "1")
    modality = MODALITIES[(lesson_nr // 5) % 2]  # Alle 5 Lektionen wechseln

    # Pimsleur-Lektion berechnen
    if lang == "ar":
        pimsleur = f"Pimsleur Eastern Arabic — Lektion {lesson_nr}"
        lesen = "Arabic Today oder Easy Arabic Reader"
        preply = "Mi + Fr: Preply Arabisch (Libanesin)"
    else:
        pimsleur = f"Pimsleur Farsi — Lektion {lesson_nr}"
        lesen = "Harry Potter auf Persisch (10–15 Seiten)"
        preply = "Do: Preply Persisch (Afghanin)"

    zettel = GLOSS_DIR / f"GLOSS_{date_str}.md"
    zettel.write_text(f"""# {day_de}, {now.strftime('%d.%m.%Y')} — {lang_name}-Tag

## GLOSS #{lesson_nr}
Öffne gloss.dliflc.edu und wähle:
  Sprache: {gloss_lang}
  Level: {level}
  Modality: {modality}
  Competence: {comp}

## Ablauf (20–30 Min.)
1. Hören ohne Text (5 Min.)
2. Transkript lesen + Glossar (5 Min.)
3. Hören mit Text (5 Min.) — Alternate Audio
4. Aufgaben (5–10 Min.)
5. Optional: Anki-Deck laden

## Heute außerdem
– {pimsleur}
– Lesen: {lesen}
– {preply}
– Morgenbrief-Sprachübung
""", encoding="utf-8")

    webbrowser.open("https://gloss.dliflc.edu/")

    state["last_date"] = date_str
    save_state(state)
    print(f"{lang_name}-Tag #{lesson_nr} — {comp} — Level {level} — {modality}")

if __name__ == "__main__":
    main()
