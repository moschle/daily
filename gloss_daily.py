#!/usr/bin/env python3
"""
GLOSS Tagesplaner.
Läuft bei Login (LaunchAgent mit RunAtLoad).
- Räumt gestrige GLOSS-Dateien vom Desktop
- Löscht die gestrige Lektion aus dem Quellordner (= Fortschritt)
- Kopiert die nächste Lektion auf den Desktop
- Erstellt einen Lernzettel mit allen Tagesaufgaben
"""

import shutil
import glob
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

BERLIN_TZ = ZoneInfo("Europe/Berlin")
GLOSS_DIR = Path("/Users/moritzschlenstedt/Projects/gloss")
DESKTOP = Path.home() / "Desktop"

TOPIC_NAMES = {
    "cul": "Kultur", "soc": "Gesellschaft", "ecn": "Wirtschaft",
    "env": "Umwelt", "geo": "Geographie", "sci": "Wissenschaft",
    "sec": "Sicherheit", "mil": "Militär", "pol": "Politik", "tec": "Technologie",
}

def get_today():
    return datetime.now(BERLIN_TZ)

def get_language(doy):
    """Gerade Tage = Arabisch, ungerade = Persisch (wie Morgenbrief)."""
    if doy % 2 == 0:
        return "ar", "Arabisch", "ar_1"
    else:
        return "fa", "Persisch", "fa_1"

def get_lesson_dirs(lang_folder):
    """Gibt sortierte Liste der verbleibenden Lektions-Ordner zurück."""
    folder = GLOSS_DIR / lang_folder
    if not folder.exists():
        return []
    return sorted([d for d in folder.iterdir() if d.is_dir() and not d.name.startswith(".")])

def decode_lesson_name(name):
    """Dekodiert z.B. 'ars_soc426' → ('Gesellschaft', 'ars_soc426')."""
    parts = name.split("_")
    if len(parts) >= 2:
        topic_code = parts[1][:3]
        return TOPIC_NAMES.get(topic_code, topic_code), name
    return name, name

def cleanup_desktop():
    """Entfernt alle GLOSS-Dateien und -Ordner vom Desktop."""
    removed = []
    for f in DESKTOP.glob("GLOSS_*"):
        if f.is_dir():
            shutil.rmtree(f)
        else:
            f.unlink()
        removed.append(f.name)
    return removed

def delete_previous_lesson(lang_folder, lesson_name):
    """Löscht eine abgeschlossene Lektion aus dem Quellordner."""
    lesson_dir = GLOSS_DIR / lang_folder / lesson_name
    if lesson_dir.exists():
        shutil.rmtree(lesson_dir)
    # Auch das .apkg daneben
    apkg = GLOSS_DIR / lang_folder / f"{lesson_name}.apkg"
    if apkg.exists():
        apkg.unlink()

def copy_lesson_to_desktop(lang_folder, lesson_dir):
    """Kopiert alle Dateien einer Lektion in einen Ordner auf dem Desktop."""
    dest_dir = DESKTOP / f"GLOSS_{lesson_dir.name}"
    dest_dir.mkdir(exist_ok=True)
    copied = []
    for f in lesson_dir.iterdir():
        if f.is_file():
            dest = dest_dir / f.name
            shutil.copy2(f, dest)
            copied.append(f.name)
    apkg = GLOSS_DIR / lang_folder / f"{lesson_dir.name}.apkg"
    if apkg.exists():
        dest = dest_dir / apkg.name
        shutil.copy2(apkg, dest)
        copied.append(apkg.name)
    return copied, dest_dir

def create_daily_note(dest_dir, date_str, day_de, lang_name, lang_code, lesson_name, topic, remaining, files, warning):
    """Erstellt den Lernzettel auf dem Desktop."""
    gloss_url = f"https://gloss.dliflc.edu/products/gloss/{lesson_name}/{lesson_name}_act1.html"

    if lang_code == "ar":
        pimsleur = "Pimsleur Eastern Arabic"
        lesen = "Arabic Today oder Easy Arabic Reader"
        preply = "Mi + Fr: Preply Arabisch (Libanesin)"
    else:
        pimsleur = "Pimsleur Farsi"
        lesen = "Harry Potter auf Persisch (10–15 Seiten)"
        preply = "Do: Preply Persisch (Afghanin)"

    warning_text = ""
    if warning:
        warning_text = f"\n⚠️  NUR NOCH {remaining} LEKTION(EN) ÜBRIG — neues Level herunterladen!\n"

    note = f"""# {day_de}, {date_str} — {lang_name}-Tag
{warning_text}
## GLOSS: {lesson_name}
Thema: {topic}
Verbleibend: {remaining} Lektionen

Online: {gloss_url}

Dateien auf dem Desktop:
{chr(10).join(f'  – {f}' for f in files)}

## Ablauf (20–30 Min.)
1. Hören ohne Text (5 Min.) — source_original.mp3 / source.mp3
2. Transkript lesen (5 Min.) — source.pdf (falls vorhanden)
3. Hören mit Text (5 Min.) — act5_source.mp3 (falls vorhanden, sonst nochmal original)
4. Aufgaben online (5–10 Min.) — Link oben
5. Optional: Anki-Deck importieren (.apkg)

## Heute außerdem
– {pimsleur}
– Lesen: {lesen}
– {preply}
– Morgenbrief-Sprachübung durcharbeiten
– Sonnengrüße (6x) + Liegestütze (30) + Plank (60s)
"""
    zettel = dest_dir / f"LERNPLAN.md"
    zettel.write_text(note, encoding="utf-8")
    return zettel

# --- State: welche Lektion lag gestern auf dem Desktop? ---
STATE_FILE = GLOSS_DIR / ".last_lesson"

def read_last_lesson():
    if STATE_FILE.exists():
        parts = STATE_FILE.read_text().strip().split("|")
        if len(parts) == 3:
            return parts[0], parts[1], parts[2]  # lang_folder, lesson_name, date
    return None, None, None

def write_last_lesson(lang_folder, lesson_name, date_str):
    STATE_FILE.write_text(f"{lang_folder}|{lesson_name}|{date_str}")

def clear_last_lesson():
    if STATE_FILE.exists():
        STATE_FILE.unlink()

def main():
    now = get_today()
    date_str = now.strftime("%Y-%m-%d")
    day_de = {"Monday":"Montag","Tuesday":"Dienstag","Wednesday":"Mittwoch",
              "Thursday":"Donnerstag","Friday":"Freitag","Saturday":"Samstag",
              "Sunday":"Sonntag"}.get(now.strftime("%A"), "")
    doy = now.timetuple().tm_yday

    # 1. Schon heute gelaufen?
    prev_folder, prev_lesson, prev_date = read_last_lesson()
    if prev_date == date_str:
        print(f"Heute schon gelaufen ({prev_lesson})")
        return

    # 2. Gestrige GLOSS-Dateien vom Desktop räumen
    cleanup_desktop()

    # 3. Gestrige Lektion aus Quellordner löschen (= abgeschlossen)
    if prev_folder and prev_lesson:
        delete_previous_lesson(prev_folder, prev_lesson)
        print(f"Gelöscht: {prev_folder}/{prev_lesson}")

    # 4. Heutige Sprache bestimmen
    lang_code, lang_name, lang_folder = get_language(doy)

    # 5. Nächste Lektion finden
    lessons = get_lesson_dirs(lang_folder)
    remaining = len(lessons)

    if remaining == 0:
        # Keine Lektionen mehr — Zettel mit Warnung
        note = DESKTOP / f"GLOSS_{date_str}.md"
        note.write_text(f"# {day_de}, {date_str} — {lang_name}-Tag\n\n"
                        f"⚠️  KEINE LEKTIONEN MEHR in {lang_folder}!\n"
                        f"Lade das nächste Level von gloss.dliflc.edu herunter.\n",
                        encoding="utf-8")
        clear_last_lesson()
        print(f"Keine Lektionen mehr in {lang_folder}")
        return

    lesson = lessons[0]
    lesson_name = lesson.name
    topic, _ = decode_lesson_name(lesson_name)
    warning = remaining <= 2

    # 6. Lektion auf Desktop kopieren
    files, dest_dir = copy_lesson_to_desktop(lang_folder, lesson)

    # 7. Lernzettel erstellen
    zettel = create_daily_note(dest_dir, date_str, day_de, lang_name, lang_code,
                                lesson_name, topic, remaining, files, warning)

    # 8. Merken welche Lektion heute dran war
    write_last_lesson(lang_folder, lesson_name, date_str)

    print(f"{lang_name}-Tag: {lesson_name} ({topic}), {remaining} verbleibend")
    print(f"Zettel: {zettel}")
    if warning:
        print(f"⚠️  Nur noch {remaining} Lektion(en)!")

if __name__ == "__main__":
    main()
