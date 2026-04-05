#!/usr/bin/env python3
"""
Morgenbrief: Täglicher Tagesplan via Claude → ePub → Kindle
"""

import os
import sys
import json
import re
import smtplib
import urllib.request
import csv
import random
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
from pathlib import Path
from zoneinfo import ZoneInfo

# ─── Zeitzone ───
BERLIN_TZ = ZoneInfo("Europe/Berlin")

def now_berlin():
    return datetime.now(BERLIN_TZ)


# ─── Kalender parsen ───

def fetch_calendar(ical_url):
    """Holt iCal-Daten und extrahiert Termine von heute + nächste 2 Tage (Berliner Zeit)."""
    try:
        req = urllib.request.Request(ical_url, headers={"User-Agent": "Morgenbrief/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        return f"[Kalender konnte nicht geladen werden: {e}]"

    events = []
    today_berlin = now_berlin().replace(hour=0, minute=0, second=0, microsecond=0)
    horizon = today_berlin + timedelta(days=3)

    for block in re.findall(r"BEGIN:VEVENT(.*?)END:VEVENT", data, re.DOTALL):
        summary = ""
        dtstart_str = ""
        location = ""
        is_utc = False
        has_tzid_berlin = False

        m = re.search(r"SUMMARY:(.*?)[\r\n]", block)
        if m:
            summary = m.group(1).strip()
        m = re.search(r"DTSTART[^:]*:(.*?)[\r\n]", block)
        if m:
            dtstart_str = m.group(1).strip()
        dtstart_line = re.search(r"DTSTART([^:]*):", block)
        if dtstart_line and "Europe/Berlin" in dtstart_line.group(1):
            has_tzid_berlin = True
        if dtstart_str.endswith("Z"):
            is_utc = True
            dtstart_str = dtstart_str[:-1]

        m = re.search(r"LOCATION:(.*?)[\r\n]", block)
        if m:
            location = m.group(1).strip().replace("\\n", ", ").replace("\\,", ",")

        dt = None
        is_allday = False
        try:
            if "T" in dtstart_str:
                dt = datetime.strptime(dtstart_str[:15], "%Y%m%dT%H%M%S")
            elif len(dtstart_str) >= 8:
                dt = datetime.strptime(dtstart_str[:8], "%Y%m%d")
                is_allday = True
        except ValueError:
            continue

        if dt is None:
            continue

        if is_allday:
            dt_berlin = dt.replace(tzinfo=BERLIN_TZ)
        elif is_utc:
            dt_berlin = dt.replace(tzinfo=timezone.utc).astimezone(BERLIN_TZ)
        elif has_tzid_berlin:
            dt_berlin = dt.replace(tzinfo=BERLIN_TZ)
        else:
            dt_berlin = dt.replace(tzinfo=BERLIN_TZ)

        if today_berlin <= dt_berlin < horizon:
            if is_allday:
                date_str = dt_berlin.strftime("%a %d.%m.")
            else:
                date_str = dt_berlin.strftime("%a %d.%m. %H:%M")
            loc_str = f" ({location})" if location else ""

            day_diff = (dt_berlin.date() - today_berlin.date()).days
            tag_label = ["HEUTE", "MORGEN", "ÜBERMORGEN"][day_diff] if day_diff < 3 else ""

            events.append((dt_berlin, tag_label, f"  [{tag_label}] {date_str}: {summary}{loc_str}"))

    events.sort(key=lambda x: x[0])
    if not events:
        return "[Keine Termine in den nächsten 3 Tagen]"
    return "\n".join(e[2] for e in events)


# ─── Wetter ───

def fetch_weather_for_location(lat, lon, name):
    url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat}&longitude={lon}"
        f"&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,weathercode"
        f"&hourly=temperature_2m,precipitation,precipitation_probability,weathercode"
        f"&timezone=Europe/Berlin&forecast_days=1"
    )
    wmo_codes = {
        0: "klar", 1: "überwiegend klar", 2: "teils bewölkt", 3: "bewölkt",
        45: "Nebel", 48: "Reifnebel",
        51: "leichter Niesel", 53: "Niesel", 55: "starker Niesel",
        56: "gefrierender Niesel", 57: "starker gefrierender Niesel",
        61: "leichter Regen", 63: "Regen", 65: "starker Regen",
        66: "gefrierender Regen", 67: "starker gefrierender Regen",
        71: "leichter Schneefall", 73: "Schneefall", 75: "starker Schneefall",
        77: "Schneegriesel",
        80: "leichte Regenschauer", 81: "Regenschauer", 82: "heftige Regenschauer",
        85: "leichte Schneeschauer", 86: "heftige Schneeschauer",
        95: "Gewitter", 96: "Gewitter mit leichtem Hagel", 99: "Gewitter mit Hagel"
    }
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read())
        d = data["daily"]
        h = data.get("hourly", {})

        tmin = d["temperature_2m_min"][0]
        tmax = d["temperature_2m_max"][0]
        daily_code = d["weathercode"][0]
        daily_desc = wmo_codes.get(daily_code, f"Code {daily_code}")

        hourly_temps = h.get("temperature_2m", [])
        hourly_precip = h.get("precipitation", [])
        hourly_prob = h.get("precipitation_probability", [])
        hourly_codes = h.get("weathercode", [])

        slots = [
            ("Nacht", 0, 6),
            ("Morgen", 6, 10),
            ("Vormittag", 10, 13),
            ("Nachmittag", 13, 18),
            ("Abend", 18, 24),
        ]

        precip_parts = []
        for slot_name, start, end in slots:
            if len(hourly_precip) < end or len(hourly_codes) < end:
                continue
            slot_precip = sum(hourly_precip[start:end])
            slot_probs = hourly_prob[start:end] if len(hourly_prob) >= end else []
            slot_codes_list = hourly_codes[start:end]

            if slot_precip > 0.1 or (slot_probs and max(slot_probs) > 30):
                max_code = max(slot_codes_list) if slot_codes_list else 0
                precip_desc = wmo_codes.get(max_code, "Niederschlag")
                avg_prob = int(sum(slot_probs) / len(slot_probs)) if slot_probs else 0
                if slot_precip > 0.1:
                    precip_parts.append(f"{slot_name}: {precip_desc} ({slot_precip:.1f}mm, {avg_prob}%)")
                elif avg_prob > 30:
                    precip_parts.append(f"{slot_name}: mögl. {precip_desc} ({avg_prob}%)")

        night_temps = hourly_temps[0:6] if len(hourly_temps) >= 6 else []
        night_min = f"{min(night_temps):.0f}°C" if night_temps else f"{tmin:.0f}°C"

        result = f"{name}: {daily_desc.capitalize()}, {tmin:.0f}–{tmax:.0f}°C (Nacht {night_min})"
        if precip_parts:
            result += "\n  " + "; ".join(precip_parts)
        elif d["precipitation_sum"][0] and d["precipitation_sum"][0] > 0:
            result += f" — {d['precipitation_sum'][0]:.1f}mm Niederschlag gesamt"
        return result
    except Exception as e:
        return f"{name}: [nicht verfügbar: {e}]"

def fetch_weather():
    return fetch_weather_for_location(51.34, 12.37, "Leipzig/Roitzsch")


# ─── Nachrichten (BBC World Service RSS – stabil) ───

def fetch_news_headline(lang_code):
    """
    Holt eine aktuelle Schlagzeile aus den offiziellen BBC World Service Feeds (Markdown).
    Quellen: https://github.com/bbc/world-service-rss
    """
    if lang_code == "ar":
        url = "https://raw.githubusercontent.com/bbc/world-service-rss/main/arabic.md"
    elif lang_code == "fa":
        url = "https://raw.githubusercontent.com/bbc/world-service-rss/main/persian.md"
    else:
        return None

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Morgenbrief/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = resp.read().decode("utf-8", errors="replace")
        # Format: ## [TITLE](URL) ...
        match = re.search(r'## \[(.*?)\]\(.*?\)', data, re.DOTALL)
        if match:
            headline = match.group(1).strip()
            # Entferne HTML-Entities
            headline = headline.replace("&amp;", "&").replace("&quot;", '"').replace("&lt;", "<").replace("&gt;", ">")
            print(f"News via BBC gefunden: {headline[:60]}...", file=sys.stderr)
            return headline[:300]
    except Exception as e:
        print(f"BBC News Fehler ({lang_code}): {e}", file=sys.stderr)
    return None


# ─── Musikbibliothek laden (aus all.txt) ───

MUSIC_LIBRARY_FILE = Path(__file__).parent / "all.txt"
_music_data = None

def _load_music_library():
    """Liest die iTunes-Exportdatei (TSV oder CSV) und gibt eine Liste von Alben zurück."""
    data = []
    if not MUSIC_LIBRARY_FILE.exists():
        print("Hinweis: all.txt nicht gefunden. Keine personalisierten Albumvorschläge.", file=sys.stderr)
        return data

    # Versuche zuerst Tabulator, dann Komma als Trennzeichen
    for delimiter in ('\t', ','):
        try:
            with open(MUSIC_LIBRARY_FILE, "r", encoding="utf-8") as f:
                # Erste Zeile: Header
                first_line = f.readline()
                if not first_line:
                    continue
                f.seek(0)
                # Prüfe, ob die erste Zeile das erwartete Format hat (Spalte "Album")
                if "Album" not in first_line:
                    continue
                reader = csv.DictReader(f, delimiter=delimiter)
                for row in reader:
                    album = row.get("Album", "").strip()
                    artist = row.get("Artist", "").strip()
                    if not album or not artist:
                        continue
                    # Plays
                    plays_str = row.get("Plays", "0")
                    try:
                        plays = int(plays_str) if plays_str else 0
                    except:
                        plays = 0
                    # Last Played
                    last_str = row.get("Last Played", "").strip()
                    last_date = None
                    if last_str and "," in last_str:
                        try:
                            date_part = last_str.split(",")[0].strip()
                            last_date = datetime.strptime(date_part, "%d.%m.%Y").date()
                        except:
                            pass
                    # Bewertung (My Rating: 0-100)
                    rating_str = row.get("My Rating", "0")
                    try:
                        rating = int(rating_str) if rating_str else 0
                    except:
                        rating = 0
                    # Genre
                    genre = row.get("Genre", "").strip()
                    data.append({
                        "artist": artist,
                        "album": album,
                        "plays": plays,
                        "last_played": last_date,
                        "rating": rating,
                        "genre": genre,
                    })
            # Wenn erfolgreich gelesen, Schleife abbrechen
            if data:
                print(f"Musikbibliothek geladen: {len(data)} Alben (Trennzeichen: {repr(delimiter)})", file=sys.stderr)
                break
        except Exception as e:
            print(f"Fehler beim Lesen mit Trennzeichen {repr(delimiter)}: {e}", file=sys.stderr)
            continue
    return data

# Beim Modulstart laden
_music_data = _load_music_library()

def _get_top_genres(limit=3):
    if not _music_data:
        return []
    genre_playcount = {}
    for entry in _music_data:
        genre = entry["genre"]
        if not genre:
            continue
        genre_playcount[genre] = genre_playcount.get(genre, 0) + entry["plays"]
    sorted_genres = sorted(genre_playcount.items(), key=lambda x: x[1], reverse=True)
    return [g for g, _ in sorted_genres[:limit]]

def _get_high_rated_artists(threshold=80, limit=5):
    if not _music_data:
        return []
    artist_scores = {}
    for entry in _music_data:
        if entry["rating"] >= threshold:
            artist_scores[entry["artist"]] = artist_scores.get(entry["artist"], 0) + 1
    sorted_artists = sorted(artist_scores.items(), key=lambda x: x[1], reverse=True)
    return [a for a, _ in sorted_artists[:limit]]

def _get_similar_artists(artist_name, limit=3):
    if not _music_data:
        return []
    # Finde Genres des Künstlers
    genres = set()
    for entry in _music_data:
        if entry["artist"] == artist_name and entry["genre"]:
            genres.add(entry["genre"])
    if not genres:
        return []
    similar = set()
    for entry in _music_data:
        if entry["artist"] != artist_name and entry["genre"] in genres:
            similar.add(entry["artist"])
    return list(similar)[:limit]

def _select_album_of_the_day():
    if not _music_data:
        return None
    today = now_berlin().date()
    is_exploration = random.random() < 0.2  # 20% Entdeckungsmodus

    top_genres = _get_top_genres(3)
    high_rated_artists = _get_high_rated_artists(threshold=80)

    similar_artists = set()
    zero_play_albums = []
    if is_exploration:
        for artist in high_rated_artists:
            similar_artists.update(_get_similar_artists(artist))
        zero_play_albums = [e for e in _music_data if e["plays"] == 0]

    weighted = []
    for entry in _music_data:
        weight = 1.0
        if is_exploration:
            if entry["plays"] == 0:
                weight *= 2.0
            if entry["artist"] in similar_artists:
                weight *= 2.0
        else:
            if entry["rating"] >= 80:
                weight *= 1.5 * (entry["rating"] / 50)
            if entry["genre"] in top_genres:
                weight *= 1.2
        days_since = (today - entry["last_played"]).days if entry["last_played"] else 365
        weight *= (days_since + 1)
        weight *= (1.0 / (entry["plays"] + 1))
        weight *= random.uniform(0.8, 1.2)
        weighted.append((weight, entry))

    if not weighted:
        return None
    total = sum(w for w, _ in weighted)
    r = random.random() * total
    cum = 0
    for w, entry in weighted:
        cum += w
        if r <= cum:
            return entry
    return weighted[-1][1]


# ─── Tagesimpuls (personalisiert) ───

def generate_impulse():
    today = now_berlin()
    weekday = today.strftime("%A")
    day_de = {
        "Monday": "Montag", "Tuesday": "Dienstag", "Wednesday": "Mittwoch",
        "Thursday": "Donnerstag", "Friday": "Freitag", "Saturday": "Samstag",
        "Sunday": "Sonntag"
    }.get(weekday, weekday)

    album_entry = _select_album_of_the_day()
    if album_entry:
        album_suggestion = f"Album des Tages: {album_entry['artist']} — {album_entry['album']}"
        if album_entry["plays"] == 0:
            album_suggestion += " (Noch nie gehört – vielleicht eine schöne Entdeckung?)"
        elif album_entry["rating"] >= 80:
            album_suggestion += " (Du magst diesen Künstler – hör mal wieder rein!)"
        elif album_entry["last_played"] and (today.date() - album_entry["last_played"]).days > 90:
            album_suggestion += " (Lange nicht gehört – Zeit für ein Revival.)"
    else:
        # Fallback
        fallback = ["Ahmad Jamal — The Awakening", "Nils Frahm — Felt", "Avishai Cohen — From Darkness"]
        album_suggestion = f"Album des Tages: {random.choice(fallback)}"

    creative_pool = [
        "Entwickle einen Film oder scanne Negative.",
        "Schau einen persischen Film (z. B. von Panahi, Kiarostami, Farhadi oder Rasoulof).",
        "Nimm eine Mixtape-Seite auf.",
        "Schreibe handschriftlich einen Brief.",
        "Mache Skizzen oder zeichne.",
        "Übersetze ein Gedicht, das nicht für hochroth ist.",
        "Mach einen langen Spaziergang mit der Kamera.",
        "Improvisiere am Klavier – ganz ohne Übungsziel.",
        "Lies einen alten Text von dir und mache dir Notizen dazu.",
        "Koche etwas Neues – ein Rezept aus einer anderen Küche.",
        "Schicke eine Postkarte an jemanden.",
        "Mache Field Recordings (im Garten oder in der Umgebung)."
    ]
    creative_today = random.choice(creative_pool)

    return f"""Heute ist {day_de}. Kleine Ideen für den Tag (wähle höchstens eine, wenn Zeit ist):
– Kreativ: {creative_today}
– {album_suggestion}
Passe die Auswahl an deine Termine und das Wetter an. Wenn der Tag voll ist, lass die Vorschläge einfach weg."""


# ─── Sprachübung (mit Vokabelgedächtnis) ───

LANG_START = datetime(2026, 4, 5, tzinfo=BERLIN_TZ)
VOCAB_FILE = Path(__file__).parent / "vocab_memory.json"

def load_vocab_memory():
    if VOCAB_FILE.exists():
        try:
            with open(VOCAB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {"ar": [], "fa": []}
    return {"ar": [], "fa": []}

def save_vocab_memory(memory):
    with open(VOCAB_FILE, "w", encoding="utf-8") as f:
        json.dump(memory, f, ensure_ascii=False, indent=2)

def get_due_vocab(lang_code, memory):
    today = now_berlin().date()
    due = []
    for entry in memory.get(lang_code, []):
        last_review = datetime.fromisoformat(entry["last_review"]).date()
        interval = entry.get("interval", 1)
        if (today - last_review).days >= interval:
            due.append(entry)
    return due

def add_new_vocab(lang_code, words, memory):
    today = now_berlin().isoformat()
    for word, meaning in words:
        word = word.strip()
        meaning = meaning.strip()
        if not word or not meaning:
            continue
        exists = any(w["word"] == word for w in memory.get(lang_code, []))
        if not exists:
            memory.setdefault(lang_code, []).append({
                "word": word,
                "meaning": meaning,
                "first_seen": today,
                "last_review": today,
                "interval": 1,
                "times_reviewed": 0
            })
    save_vocab_memory(memory)

def update_reviewed_vocab(lang_code, reviewed_words, memory):
    today = now_berlin().isoformat()
    for word in reviewed_words:
        for entry in memory.get(lang_code, []):
            if entry["word"] == word:
                entry["last_review"] = today
                entry["times_reviewed"] += 1
                new_interval = entry.get("interval", 1) * 2
                entry["interval"] = min(new_interval, 30)
                break
    save_vocab_memory(memory)

def generate_language_exercise():
    today = now_berlin()
    day_of_year = today.timetuple().tm_yday
    days_since_start = max(0, (today - LANG_START).days)
    week = days_since_start // 7

    if day_of_year % 2 == 0:
        language = "Arabisch"
        lang_code = "ar"
    else:
        language = "Persisch"
        lang_code = "fa"

    if week < 2:
        level = "A2 (einfach)"
        instructions = "Sehr einfache Sätze. Grundvokabular: Familie, Essen, Wetter, Tagesablauf. Präsens und einfache Vergangenheit."
    elif week < 6:
        level = "B1 (mittel)"
        instructions = "Längere Sätze möglich. Themen: Reisen, Arbeit, Meinungen, Nachrichten. Konjunktiv, Relativsätze erlaubt."
    elif week < 12:
        level = "B1+ (gehoben)"
        instructions = "Komplexere Strukturen. Themen: Kultur, Politik, Literatur. Passiv, indirekte Rede."
    else:
        level = "B2 (fortgeschritten)"
        instructions = "Anspruchsvoller Text. Zeitungssprache, abstrakte Themen, idiomatische Wendungen."

    memory = load_vocab_memory()
    due_vocab = get_due_vocab(lang_code, memory)

    repetition_prompt = ""
    if due_vocab:
        vocab_list = "\n".join([f"  - {v['word']} ({v['meaning']})" for v in due_vocab])
        repetition_prompt = f"""
VOKABELWIEDERHOLUNG (Spaced Repetition):
Die folgenden Wörter wurden früher eingeführt und sollen heute wiederholt werden. Baue sie in den Übungstext ein (oder erstelle einen separaten Wiederholungssatz am Ende des Textes):
{vocab_list}
"""

    headline = fetch_news_headline(lang_code)
    news_source = "BBC" if headline else None

    fallback_topics = [
        "Tagesablauf und Routine", "Essen und Kochen", "Eine Reise beschreiben",
        "Familie und Freunde", "Das Wetter", "Einkaufen auf dem Markt",
        "Ein Buch oder Film beschreiben", "Die eigene Stadt vorstellen",
        "Arbeit und Beruf", "Kindheitserinnerungen", "Natur und Umwelt",
        "Musik und Kunst", "Gesundheit und Sport", "Politik und Gesellschaft",
    ]
    topic = fallback_topics[days_since_start % len(fallback_topics)]

    new_vocab_instruction = """
WICHTIG FÜR NEUE VOKABELN:
Wenn du im Übungstext ein Wort einführst, das über den absoluten Grundwortschatz hinausgeht (also nicht alltäglich wie "ich, du, essen, gehen, groß, klein"), dann:
1. Glossiere es sofort inline auf Deutsch in Klammern hinter dem Wort.
2. Füge am Ende des TEXT-Abschnitts (vor den Verständnisfragen) eine Zeile ein: "NEUE VOKABELN: Wort (Bedeutung), weiteres Wort (Bedeutung)"
   Beispiel: "NEUE VOKABELN: مكتبة (Bibliothek), سريع (schnell)"
"""

    return {
        "language": language,
        "lang_code": lang_code,
        "level": level,
        "instructions": instructions,
        "topic": topic,
        "headline": headline,
        "news_source": news_source,
        "week": week,
        "repetition_prompt": repetition_prompt,
        "new_vocab_instruction": new_vocab_instruction,
        "memory": memory,
        "due_vocab": due_vocab,
    }


# ─── Claude aufrufen (mit getrennten Sprachübungs-Sektionen) ───

def call_claude(kontext, fahrplan, aufgaben, kalender, wetter, impulse, lang_exercise):
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        sys.exit("ANTHROPIC_API_KEY nicht gesetzt")

    today = now_berlin().strftime("%A, %d. %B %Y")
    lang = lang_exercise
    script = 'arabischer' if lang['lang_code'] == 'ar' else 'persischer'
    dialect_rule = 'Fusha (MSA), kein Dialekt.' if lang['lang_code'] == 'ar' else 'Farsi-ye meyar, kein Slang.'

    # News-Block
    if lang.get('headline'):
        news_prompt = f"""NACHRICHTEN:
Die folgende Schlagzeile von {lang['news_source']} in {script} Originalschrift wiedergeben. Glossiere schwierige Wörter inline auf Deutsch in Klammern. Danach in 2–3 einfachen Sätzen auf {lang['language']} zusammenfassen (Level {lang['level']}).
Schlagzeile: {lang['headline']}"""
    else:
        news_prompt = """NACHRICHTEN:
Keine aktuellen Nachrichten verfügbar. Schreibe stattdessen einen kurzen Satz auf Deutsch, dass heute keine neue Schlagzeile vorliegt."""

    # Sprachübung – explizit getrennt
    lang_prompt = f"""SPRACHÜBUNG – TEXT (RTL, in Originalschrift):
Schreibe einen kurzen Übungstext auf {lang['language']} zum Thema "{lang['topic']}".
Regeln:
- 5–8 Sätze in {script} Schrift.
- {lang['instructions']}
- {dialect_rule}
- {lang['new_vocab_instruction']}
{lang['repetition_prompt']}

SPRACHÜBUNG – FRAGEN (LTR, auf Deutsch):
Schreibe 2–3 Verständnisfragen auf Deutsch zum obigen Text. Jede Frage in einer neuen Zeile. Keine Originalschrift mehr. Beginne diese Sektion mit der Zeile "FRAGEN:" direkt nach dem Text, damit die Formatierung klar ist."""

    user_message = f"""Heute ist {today}.

WETTER:
{wetter}

TAGESIMPULS:
{impulse}

KONTEXT (enthält Format und Regeln — befolge sie exakt):
{kontext}

OFFENE AUFGABEN:
{aufgaben}

KALENDER (nächste 3 Tage, Tag-Labels beachten):
{kalender}

FAHRPLAN (nur als Hintergrund für Deadlines):
{fahrplan}

{lang_prompt}

{news_prompt}

AUFTRAG:
Schreibe den Morgenbrief exakt in der Struktur die im Kontext-Dokument definiert ist:
1. WETTER
2. HEUTE
3. IMPULS
4. PROJEKTE
5. ERLEDIGTES
6. AUSBLICK
7. SPRACHÜBUNG – TEXT
8. SPRACHÜBUNG – FRAGEN (mit vorangestellter Zeile "FRAGEN:")
9. NACHRICHTEN

Jede Sektion mit dem Namen als Überschrift in Großbuchstaben. Kein Markdown. Sachlich."""

    payload = json.dumps({
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 2000,
        "messages": [{"role": "user", "content": user_message}]
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01"
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read())
        return result["content"][0]["text"]
    except Exception as e:
        sys.exit(f"Claude API Fehler: {e}")


def strip_markdown(text):
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'`(.+?)`', r'\1', text)
    text = re.sub(r'^\*\s+', '– ', text, flags=re.MULTILINE)
    return text


# ─── ePub erzeugen (mit korrekter RTL/LTR Erkennung) ───

def create_epub(text, date_str):
    import zipfile
    from io import BytesIO

    title = f"Morgenbrief {date_str}"
    text = strip_markdown(text)

    lines = text.strip().split("\n")
    html_parts = []
    current_block = []
    current_rtl = False

    def flush_block():
        nonlocal current_rtl
        if current_block:
            content = "<br/>".join(current_block)
            if current_rtl:
                html_parts.append(f'<p dir="rtl" style="text-align: right; font-size: 1.1em; line-height: 1.8;">{content}</p>')
            else:
                html_parts.append(f"<p>{content}</p>")
            current_block.clear()

    for line in lines:
        stripped = line.strip()
        upper = stripped.upper()
        # Erkennung der Sektionen
        if "SPRACHÜBUNG – TEXT" in upper or "SPRACHÜBUNG - TEXT" in upper:
            flush_block()
            current_rtl = True
            html_parts.append(f"<h2>{stripped}</h2>")
        elif "SPRACHÜBUNG – FRAGEN" in upper or "SPRACHÜBUNG - FRAGEN" in upper or stripped.startswith("FRAGEN:"):
            flush_block()
            current_rtl = False
            html_parts.append(f"<h2>{stripped}</h2>")
        elif upper in {"WETTER", "HEUTE", "IMPULS", "PROJEKTE", "ERLEDIGTES", "AUSBLICK", "NACHRICHTEN"}:
            flush_block()
            current_rtl = False
            html_parts.append(f"<h2>{stripped}</h2>")
        elif stripped == "":
            flush_block()
        else:
            current_block.append(stripped)
    flush_block()

    html_body = "\n".join(html_parts)

    content_xhtml = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>{title}</title>
<style>
body {{ font-family: serif; font-size: 1em; line-height: 1.5; margin: 1em; }}
h1 {{ font-size: 1.4em; margin-bottom: 0.3em; }}
h2 {{ font-size: 1.1em; margin-top: 1em; margin-bottom: 0.3em; text-transform: uppercase; letter-spacing: 0.05em; }}
p {{ margin-bottom: 0.6em; }}
</style>
</head>
<body>
<h1>{title}</h1>
{html_body}
</body>
</html>"""

    container_xml = """<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>"""

    content_opf = f"""<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="uid">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="uid">morgenbrief-{date_str}</dc:identifier>
    <dc:title>{title}</dc:title>
    <dc:language>de</dc:language>
    <dc:creator>Claude</dc:creator>
    <meta property="dcterms:modified">{datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}</meta>
  </metadata>
  <manifest>
    <item id="content" href="content.xhtml" media-type="application/xhtml+xml"/>
    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>
  </manifest>
  <spine>
    <itemref idref="content"/>
  </spine>
</package>"""

    nav_xhtml = f"""<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head><title>Navigation</title></head>
<body>
<nav epub:type="toc"><h1>Inhalt</h1><ol><li><a href="content.xhtml">{title}</a></li></ol></nav>
</body>
</html>"""

    buf = BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        zf.writestr("META-INF/container.xml", container_xml)
        zf.writestr("OEBPS/content.opf", content_opf)
        zf.writestr("OEBPS/content.xhtml", content_xhtml)
        zf.writestr("OEBPS/nav.xhtml", nav_xhtml)

    filename = f"morgenbrief_{date_str}.epub"
    with open(filename, "wb") as f:
        f.write(buf.getvalue())
    return filename


# ─── Mail an Kindle ───

def send_to_kindle(epub_path):
    gmail_addr = os.environ.get("GMAIL_ADDRESS")
    gmail_pw = os.environ.get("GMAIL_APP_PASSWORD")
    kindle_addr = os.environ.get("KINDLE_EMAIL")

    if not all([gmail_addr, gmail_pw, kindle_addr]):
        sys.exit("Gmail/Kindle Secrets nicht vollständig gesetzt")

    msg = MIMEMultipart()
    msg["From"] = gmail_addr
    msg["To"] = kindle_addr
    msg["Subject"] = "Morgenbrief"
    msg.attach(MIMEText("", "plain"))

    with open(epub_path, "rb") as f:
        part = MIMEBase("application", "epub+zip")
        part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f"attachment; filename={os.path.basename(epub_path)}")
        msg.attach(part)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(gmail_addr, gmail_pw)
        smtp.sendmail(gmail_addr, kindle_addr, msg.as_string())
    print(f"Morgenbrief an {kindle_addr} gesendet")


# ─── Main ───

def main():
    repo_dir = Path(__file__).parent
    kontext = (repo_dir / "kontext.md").read_text(encoding="utf-8")
    fahrplan = (repo_dir / "fahrplan.md").read_text(encoding="utf-8")
    aufgaben = (repo_dir / "aufgaben.md").read_text(encoding="utf-8")

    ical_url = os.environ.get("ICAL_URL", "")
    kalender = fetch_calendar(ical_url) if ical_url else "[Keine Kalender-URL]"
    wetter = fetch_weather()
    impulse = generate_impulse()
    lang_exercise = generate_language_exercise()

    print(f"Morgenbrief wird geschrieben ({now_berlin().strftime('%d.%m.%Y %H:%M')} Berliner Zeit)...")
    print(f"Sprachübung: {lang_exercise['language']} (Level {lang_exercise['level']}, Thema: {lang_exercise['topic']})")
    if lang_exercise.get('headline'):
        print(f"News vorhanden: {lang_exercise['headline'][:60]}...")
    else:
        print("Keine News – verwende Platzhalter.")

    text = call_claude(kontext, fahrplan, aufgaben, kalender, wetter, impulse, lang_exercise)

    # Vokabelgedächtnis aktualisieren
    new_vocab_match = re.search(r"NEUE VOKABELN:\s*(.*?)(?:\n|$)", text, re.IGNORECASE)
    if new_vocab_match:
        vocab_line = new_vocab_match.group(1)
        pairs = re.findall(r"([^\s,]+)\s*\(([^)]+)\)", vocab_line)
        if pairs:
            add_new_vocab(lang_exercise["lang_code"], pairs, lang_exercise["memory"])
            text = re.sub(r"NEUE VOKABELN:.*\n?", "", text, flags=re.IGNORECASE)

    due_words = [v["word"] for v in lang_exercise.get("due_vocab", [])]
    reviewed = [w for w in due_words if w in text]
    if reviewed:
        update_reviewed_vocab(lang_exercise["lang_code"], reviewed, lang_exercise["memory"])

    date_str = now_berlin().strftime("%Y-%m-%d")
    epub_path = create_epub(text, date_str)
    send_to_kindle(epub_path)


if __name__ == "__main__":
    main()
