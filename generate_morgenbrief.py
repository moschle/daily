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
import html
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
from pathlib import Path
from zoneinfo import ZoneInfo
import requests

BERLIN_TZ = ZoneInfo("Europe/Berlin")

def now_berlin():
    return datetime.now(BERLIN_TZ)

def _normalize_dashes(text):
    return text.replace("\u2014", "-").replace("\u2013", "-").replace("\u2012", "-")


# ------------------------------------------------------------
# KALENDER PARSEN (Robust mit Regex, funktionierte früher)
# ------------------------------------------------------------
def fetch_calendar(ical_url):
    if not ical_url:
        print("DEBUG: ICAL_URL ist leer", file=sys.stderr)
        return "[Keine Kalender-URL]"

    if ical_url.startswith("webcal://"):
        ical_url = ical_url.replace("webcal://", "https://", 1)

    try:
        resp = requests.get(ical_url, timeout=15, headers={"User-Agent": "Morgenbrief/1.0"})
        resp.raise_for_status()
        data = resp.text
    except Exception as e:
        print(f"DEBUG: Kalender-Fehler: {e}", file=sys.stderr)
        return f"[Kalender konnte nicht geladen werden: {e}]"

    # Zeilenumbrüche normalisieren (wichtig für Windows/iCal-Exporte)
    data = data.replace('\r\n', '\n').replace('\r', '\n')
    print(f"DEBUG: iCal-Inhalt (erste 500 Zeichen):\n{data[:500]}", file=sys.stderr)

    events = []
    today_berlin = now_berlin().replace(hour=0, minute=0, second=0, microsecond=0)
    horizon = today_berlin + timedelta(days=3)

    # Alle VEVENT-Blöcke finden
    blocks = re.findall(r"BEGIN:VEVENT(.*?)END:VEVENT", data, re.DOTALL)
    print(f"DEBUG: {len(blocks)} VEVENT-Blöcke gefunden", file=sys.stderr)

    for block in blocks:
        summary = ""
        dtstart_str = ""
        location = ""
        is_utc = False

        m = re.search(r"SUMMARY:(.*?)[\n]", block, re.DOTALL)
        if m:
            summary = m.group(1).strip()
        m = re.search(r"DTSTART[^:]*:(.*?)[\n]", block, re.DOTALL)
        if m:
            dtstart_str = m.group(1).strip()
        m = re.search(r"LOCATION:(.*?)[\n]", block, re.DOTALL)
        if m:
            location = m.group(1).strip().replace("\\n", ", ").replace("\\,", ",")

        if not dtstart_str:
            continue

        if dtstart_str.endswith("Z"):
            is_utc = True
            dtstart_str = dtstart_str[:-1]

        dt = None
        is_allday = False
        try:
            if "T" in dtstart_str:
                dt = datetime.strptime(dtstart_str[:15], "%Y%m%dT%H%M%S")
            elif len(dtstart_str) >= 8:
                dt = datetime.strptime(dtstart_str[:8], "%Y%m%d")
                is_allday = True
        except ValueError as e:
            print(f"DEBUG: DTSTART Parse-Fehler '{dtstart_str}': {e}", file=sys.stderr)
            continue

        if dt is None:
            continue

        if is_allday:
            dt_berlin = dt.replace(tzinfo=BERLIN_TZ)
        elif is_utc:
            dt_berlin = dt.replace(tzinfo=timezone.utc).astimezone(BERLIN_TZ)
        else:
            dt_berlin = dt.replace(tzinfo=BERLIN_TZ)

        if today_berlin <= dt_berlin < horizon:
            date_str = dt_berlin.strftime("%a %d.%m.") if is_allday else dt_berlin.strftime("%a %d.%m. %H:%M")
            loc_str = f" ({location})" if location else ""
            day_diff = (dt_berlin.date() - today_berlin.date()).days
            tag_label = ["HEUTE", "MORGEN", "ÜBERMORGEN"][day_diff] if day_diff < 3 else ""
            events.append(f"  [{tag_label}] {date_str}: {summary}{loc_str}")

    result = "\n".join(events) if events else "[Keine Termine in den nächsten 3 Tagen]"
    print(f"DEBUG: {len(events)} Kalender-Events gefunden", file=sys.stderr)
    return result


# ------------------------------------------------------------
# WETTER (unverändert, funktioniert)
# ------------------------------------------------------------
def fetch_weather_for_location(lat, lon, name):
    url = (f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
           f"&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,weathercode"
           f"&hourly=temperature_2m,precipitation,precipitation_probability,weathercode"
           f"&timezone=Europe/Berlin&forecast_days=1")
    wmo = {0:"klar",1:"überwiegend klar",2:"teils bewölkt",3:"bewölkt",45:"Nebel",48:"Reifnebel",
           51:"leichter Niesel",53:"Niesel",55:"starker Niesel",61:"leichter Regen",63:"Regen",
           65:"starker Regen",71:"leichter Schneefall",73:"Schneefall",75:"starker Schneefall",
           80:"leichte Regenschauer",81:"Regenschauer",82:"heftige Regenschauer",
           95:"Gewitter",96:"Gewitter mit leichtem Hagel",99:"Gewitter mit Hagel"}
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        d, h = data["daily"], data.get("hourly", {})
        tmin, tmax = d["temperature_2m_min"][0], d["temperature_2m_max"][0]
        daily_desc = wmo.get(d["weathercode"][0], f"Code {d['weathercode'][0]}")
        hourly_precip = h.get("precipitation", [])
        hourly_prob = h.get("precipitation_probability", [])
        hourly_codes = h.get("weathercode", [])
        slots = [("Nacht",0,6),("Morgen",6,10),("Vormittag",10,13),("Nachmittag",13,18),("Abend",18,24)]
        precip_parts = []
        for sn, s, e in slots:
            if len(hourly_precip) < e or len(hourly_codes) < e:
                continue
            sp = sum(hourly_precip[s:e])
            sprobs = hourly_prob[s:e] if len(hourly_prob) >= e else []
            if sp > 0.1 or (sprobs and max(sprobs) > 30):
                mc = max(hourly_codes[s:e]) if hourly_codes[s:e] else 0
                avg_p = int(sum(sprobs)/len(sprobs)) if sprobs else 0
                if sp > 0.1:
                    precip_parts.append(f"{sn}: {wmo.get(mc,'Niederschlag')} ({sp:.1f}mm, {avg_p}%)")
                elif avg_p > 30:
                    precip_parts.append(f"{sn}: mögl. {wmo.get(mc,'Niederschlag')} ({avg_p}%)")
        hourly_temps = h.get("temperature_2m", [])
        if len(hourly_temps) >= 6:
            nt = hourly_temps[0:6]
            night_min = f"{min(nt):.0f}°C"
        else:
            night_min = f"{tmin:.0f}°C"
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


# ------------------------------------------------------------
# NACHRICHTEN (BBC GitHub Markdown)
# ------------------------------------------------------------
def fetch_bbc_news(lang_code):
    urls = {
        "ar": "https://raw.githubusercontent.com/bbc/world-service-rss/main/arabic.md",
        "fa": "https://raw.githubusercontent.com/bbc/world-service-rss/main/persian.md"
    }
    url = urls.get(lang_code)
    if not url:
        print(f"DEBUG: Keine BBC-URL für {lang_code}", file=sys.stderr)
        return None, None

    try:
        resp = requests.get(url, timeout=10, headers={"User-Agent": "Morgenbrief/1.0"})
        resp.raise_for_status()
        content = resp.text
        lines = content.splitlines()
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith('## ['):
                match = re.search(r'## \[(.*?)\]\(.*?\)', stripped)
                if match:
                    headline = match.group(1).strip()
                    description = ""
                    for j in range(i+1, min(i+10, len(lines))):
                        desc_line = lines[j].strip()
                        if desc_line and not desc_line.startswith('![') and not desc_line.startswith('_'):
                            description = desc_line[:500]
                            break
                    print(f"DEBUG: BBC News ({lang_code}) geladen: {headline[:60]}", file=sys.stderr)
                    return headline, description
        print(f"DEBUG: Keine BBC News für {lang_code} gefunden", file=sys.stderr)
        return None, None
    except Exception as e:
        print(f"DEBUG: BBC Fehler ({lang_code}): {e}", file=sys.stderr)
        return None, None


# ------------------------------------------------------------
# MUSIKBIBLIOTHEK (gekürzt, da unverändert)
# ------------------------------------------------------------
MUSIC_LIBRARY_FILE = Path(__file__).parent / "all.txt"
_music_data = None

def _load_music_library():
    data = []
    if not MUSIC_LIBRARY_FILE.exists():
        return data
    for delim in ('\t', ','):
        try:
            with open(MUSIC_LIBRARY_FILE, "r", encoding="utf-8") as f:
                fl = f.readline()
                if not fl or "Album" not in fl:
                    continue
                f.seek(0)
                for row in csv.DictReader(f, delimiter=delim):
                    album, artist = row.get("Album","").strip(), row.get("Artist","").strip()
                    if not album or not artist:
                        continue
                    try:
                        plays = int(row.get("Plays","0") or "0")
                    except:
                        plays = 0
                    last_date = None
                    ls = row.get("Last Played","").strip()
                    if ls and "," in ls:
                        try:
                            last_date = datetime.strptime(ls.split(",")[0].strip(), "%d.%m.%Y").date()
                        except:
                            pass
                    try:
                        rating = int(row.get("My Rating","0") or "0")
                    except:
                        rating = 0
                    data.append({"artist":artist,"album":album,"plays":plays,"last_played":last_date,"rating":rating,"genre":row.get("Genre","").strip()})
            if data:
                print(f"Musikbibliothek: {len(data)} Einträge", file=sys.stderr)
                break
        except Exception as e:
            print(f"Musikfehler ({repr(delim)}): {e}", file=sys.stderr)
    return data

_music_data = _load_music_library()

def _get_top_genres(limit=3):
    if not _music_data:
        return []
    gc = {}
    for e in _music_data:
        if e["genre"]:
            gc[e["genre"]] = gc.get(e["genre"],0) + e["plays"]
    return [g for g,_ in sorted(gc.items(), key=lambda x:x[1], reverse=True)[:limit]]

def _get_high_rated_artists(threshold=80, limit=5):
    if not _music_data:
        return []
    sc = {}
    for e in _music_data:
        if e["rating"] >= threshold:
            sc[e["artist"]] = sc.get(e["artist"],0)+1
    return [a for a,_ in sorted(sc.items(), key=lambda x:x[1], reverse=True)[:limit]]

def _get_similar_artists(artist_name, limit=3):
    if not _music_data:
        return []
    genres = {e["genre"] for e in _music_data if e["artist"]==artist_name and e["genre"]}
    if not genres:
        return []
    return list({e["artist"] for e in _music_data if e["artist"]!=artist_name and e["genre"] in genres})[:limit]

def _select_album_of_the_day():
    if not _music_data:
        return None
    today = now_berlin().date()
    is_exploration = random.random() < 0.2
    top_genres = _get_top_genres(3)
    ha = _get_high_rated_artists(threshold=80)
    similar = set()
    if is_exploration:
        for a in ha:
            similar.update(_get_similar_artists(a))
    weighted = []
    for e in _music_data:
        w = 1.0
        if is_exploration:
            if e["plays"]==0:
                w *= 2.0
            if e["artist"] in similar:
                w *= 2.0
        else:
            if e["rating"]>=80:
                w *= 1.5*(e["rating"]/50)
            if e["genre"] in top_genres:
                w *= 1.2
        ds = (today - e["last_played"]).days if e["last_played"] else 365
        w *= (ds+1) * (1.0/(e["plays"]+1)) * random.uniform(0.8,1.2)
        weighted.append((w,e))
    if not weighted:
        return None
    total = sum(w for w,_ in weighted)
    r = random.random()*total
    cum = 0
    for w,e in weighted:
        cum += w
        if r <= cum:
            return e
    return weighted[-1][1]

# Discovery-Alben (minimal)
DISCOVERY_FILE = Path(__file__).parent / "discovery_albums.json"
_SEED_ALBUMS = [("Kayhan Kalhor & Rembrandt Trio","Silence City")]

def _load_discovery_albums():
    if not DISCOVERY_FILE.exists():
        return [], True
    try:
        with open(DISCOVERY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        albums = data.get("albums", [])
        unseen = [a for a in albums if not a.get("suggested", False)]
        return albums, (not unseen)
    except Exception:
        return [], True

def _save_discovery_albums(albums, profile=None):
    data = {"albums": albums, "generated_at": now_berlin().isoformat()}
    if profile:
        data["generated_from"] = profile
    with open(DISCOVERY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def _generate_discovery_albums_via_api():
    return None  # Vereinfacht

def _select_discovery_album():
    albums, needs_refresh = _load_discovery_albums()
    if needs_refresh:
        new = _generate_discovery_albums_via_api()
        if new:
            albums = new
        elif not albums:
            albums = [{"artist":a,"album":b,"suggested":False} for a,b in _SEED_ALBUMS]
            _save_discovery_albums(albums)
    unseen = [a for a in albums if not a.get("suggested", False)]
    if not unseen:
        unseen = albums
    pick = random.choice(unseen)
    for a in albums:
        if a["artist"]==pick["artist"] and a["album"]==pick["album"]:
            a["suggested"] = True
            break
    _save_discovery_albums(albums)
    return (pick["artist"], pick["album"])


# ------------------------------------------------------------
# TAGESIMPULS
# ------------------------------------------------------------
def generate_impulse():
    today = now_berlin()
    day_de = {"Monday":"Montag","Tuesday":"Dienstag","Wednesday":"Mittwoch","Thursday":"Donnerstag",
              "Friday":"Freitag","Saturday":"Samstag","Sunday":"Sonntag"}.get(today.strftime("%A"), today.strftime("%A"))
    creative_pool = ["Entwickle einen Film oder scanne Negative.", "Schau einen persischen Film."]
    if random.random() < 0.25:
        artist, album = _select_discovery_album()
        album_line = f"Album des Tages: {artist} — {album} (Entdeckung)"
    else:
        entry = _select_album_of_the_day()
        if entry:
            album_line = f"Album des Tages: {entry['artist']} — {entry['album']}"
        else:
            a, b = _select_discovery_album()
            album_line = f"Album des Tages: {a} — {b}"
    return (f"Heute ist {day_de}. Kleine Ideen für den Tag:\n"
            f"– Kreativ: {random.choice(creative_pool)}\n"
            f"– {album_line}")


# ------------------------------------------------------------
# SPRACHÜBUNG (mit Vokabelgedächtnis)
# ------------------------------------------------------------
LANG_START = datetime(2026, 4, 5, tzinfo=BERLIN_TZ)
VOCAB_FILE = Path(__file__).parent / "vocab_memory.json"

def load_vocab_memory():
    if VOCAB_FILE.exists():
        try:
            with open(VOCAB_FILE,"r",encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {"ar":[],"fa":[]}

def save_vocab_memory(m):
    with open(VOCAB_FILE,"w",encoding="utf-8") as f:
        json.dump(m, f, ensure_ascii=False, indent=2)

def get_due_vocab(lc, m):
    today = now_berlin().date()
    return [e for e in m.get(lc,[]) if (today - datetime.fromisoformat(e["last_review"]).date()).days >= e.get("interval",1)]

def add_new_vocab(lc, words, m):
    today = now_berlin().isoformat()
    for w, meaning in words:
        w, meaning = w.strip(), meaning.strip()
        if w and meaning and not any(x["word"]==w for x in m.get(lc,[])):
            m.setdefault(lc,[]).append({"word":w,"meaning":meaning,"first_seen":today,"last_review":today,"interval":1,"times_reviewed":0})
    save_vocab_memory(m)

def update_reviewed_vocab(lc, reviewed, m):
    today = now_berlin().isoformat()
    for w in reviewed:
        for e in m.get(lc,[]):
            if e["word"]==w:
                e["last_review"]=today
                e["times_reviewed"]+=1
                e["interval"]=min(e.get("interval",1)*2,30)
                break
    save_vocab_memory(m)

def generate_language_exercise():
    today = now_berlin()
    doy = today.timetuple().tm_yday
    dss = max(0, (today - LANG_START).days)
    week = dss // 7
    language, lc = ("Arabisch","ar") if doy%2==0 else ("Persisch","fa")
    if week<2:
        level, instr = "A2", "Einfache Sätze."
    elif week<6:
        level, instr = "B1", "Längere Sätze."
    else:
        level, instr = "B2", "Komplexe Strukturen."

    mem = load_vocab_memory()
    due = get_due_vocab(lc, mem)
    rep = ""
    if due:
        vl = "\n".join([f"  - {v['word']} ({v['meaning']})" for v in due])
        rep = f"\nVOKABELWIEDERHOLUNG:\n{vl}\n"

    news_headline, news_desc = fetch_bbc_news(lc)
    if news_headline:
        news_text = f"Schlagzeile: {news_headline}\nZusammenfassung: {news_desc[:300]}" if news_desc else f"Schlagzeile: {news_headline}"
    else:
        news_text = None

    topics = ["Tagesablauf", "Essen", "Reise", "Familie"]
    return {"language":language,"lang_code":lc,"level":level,"instructions":instr,
            "topic":topics[dss%len(topics)],"headline":news_headline,"news_text":news_text,
            "week":week,"repetition_prompt":rep,
            "new_vocab_instruction":"\nGlossar am Ende: Wort = Bedeutung\n",
            "memory":mem,"due_vocab":due}


# ------------------------------------------------------------
# CLAUDE AUFRUF (mit verstärkter LTR-Instruktion)
# ------------------------------------------------------------
def call_claude(kontext, fahrplan, aufgaben, kalender, wetter, impulse, lang_exercise):
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        sys.exit("ANTHROPIC_API_KEY nicht gesetzt")
    today = now_berlin().strftime("%A, %d. %B %Y")
    lang = lang_exercise
    script = 'arabischer' if lang['lang_code']=='ar' else 'persischer'
    dialect = 'Fusha' if lang['lang_code']=='ar' else 'Farsi-ye meyar'

    vocal = ""
    if lang['lang_code'] == 'ar':
        vocal = "ALLE ARABISCHEN WÖRTER MÜSSEN VOKALISIERT SEIN. Beispiel: كِتابٌ, مَدْرَسَةٌ.\n"

    if lang.get('headline'):
        news_p = (f"NACHRICHTEN (RTL, in Originalschrift):\n"
                  f"Schlagzeile: {lang['headline']}\n"
                  f"Zusammenfassung: {lang['news_text'] if lang['news_text'] else ''}\n"
                  f"Gib beides in {script} Schrift. {vocal}\n"
                  f"Glossar mit 3-5 Wörtern: Wort = Bedeutung")
    else:
        news_p = "NACHRICHTEN\nKeine aktuellen Nachrichten (auf Deutsch)."

    lang_p = (f"SPRACHÜBUNG - TEXT (RTL, in Originalschrift):\n"
              f"Thema: {lang['topic']}. {lang['instructions']} {vocal}\n"
              f"{lang['repetition_prompt']}\n"
              f"SPRACHÜBUNG - FRAGEN (LTR, auf Deutsch):\n"
              f"2-3 Fragen. Jede in neuer Zeile. NUR lateinische Buchstaben.\n"
              f"Füge nach den Fragen eine Zeile '---' ein.\n")

    msg = (f"Heute {today}.\n\nWETTER:\n{wetter}\n\nIMPULS:\n{impulse}\n\n"
           f"KONTEXT:\n{kontext}\n\nAUFGABEN:\n{aufgaben}\n\nKALENDER:\n{kalender}\n\n"
           f"FAHRPLAN:\n{fahrplan}\n\n{lang_p}\n\n{news_p}\n\n"
           f"STRUKTUR:\n1. WETTER\n2. HEUTE\n3. IMPULS\n4. PROJEKTE\n5. ERLEDIGTES\n6. AUSBLICK\n"
           f"7. SPRACHÜBUNG - TEXT\n8. SPRACHÜBUNG - FRAGEN\n9. NACHRICHTEN\n"
           f"Überschriften in Großbuchstaben, Bindestriche, kein Markdown.")

    payload = json.dumps({"model":"claude-sonnet-4-20250514","max_tokens":8000,
                          "messages":[{"role":"user","content":msg}]}).encode("utf-8")
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=payload,
        headers={"Content-Type":"application/json","x-api-key":api_key,"anthropic-version":"2023-06-01"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read())["content"][0]["text"]
    except Exception as e:
        sys.exit(f"Claude API Fehler: {e}")

def strip_markdown(text):
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'`(.+?)`', r'\1', text)
    text = re.sub(r'^\*\s+', '– ', text, flags=re.MULTILINE)
    return text


# ------------------------------------------------------------
# FORCIERT LTR FÜR FRAGEN (erkennt "Verständnisfragen:")
# ------------------------------------------------------------
def force_ltr_on_questions(text):
    lines = text.splitlines()
    new_lines = []
    in_fragen = False

    start_patterns = [
        r'SPRACH[ÜU]BUNG\s*[-–]\s*FRAGEN',
        r'VERST[ÄA]NDNISFRAGEN',
        r'^FRAGEN:',
        r'^FRAGEN\s*$',
        r'^Verständnisfragen',      # exakt was Claude schreibt
        r'^Verständnisfragen:',     # mit Doppelpunkt
        r'^Verständnisfragen\s*:',  # mit Leerzeichen vor Doppelpunkt
    ]
    end_patterns = [
        r'^NACHRICHTEN',
        r'^AUSBLICK',
        r'^ERLEDIGTES',
        r'^PROJEKTE',
        r'^WETTER',
        r'^HEUTE'
    ]

    for line in lines:
        u = line.strip().upper()
        # Start erkannt?
        is_start = any(re.search(p, u, re.IGNORECASE) for p in start_patterns)
        if is_start and not in_fragen:
            in_fragen = True
            new_lines.append(line)
            new_lines.append('<div dir="ltr">')
            print("DEBUG: LTR-Container für Fragen geöffnet", file=sys.stderr)
            continue

        if in_fragen:
            is_end = any(u.startswith(p) or u == p for p in end_patterns)
            if is_end:
                new_lines.append('</div>')
                in_fragen = False
                print("DEBUG: LTR-Container geschlossen", file=sys.stderr)
                new_lines.append(line)
                continue
        new_lines.append(line)

    if in_fragen:
        new_lines.append('</div>')
        print("DEBUG: LTR-Container am Ende geschlossen", file=sys.stderr)
    return "\n".join(new_lines)


def ensure_news_section(text):
    if not re.search(r'^NACHRICHTEN\s*$', text, re.MULTILINE):
        text += "\n\nNACHRICHTEN\nKeine aktuellen Nachrichten verfügbar."
    return text


# ------------------------------------------------------------
# EPUB ERZEUGEN
# ------------------------------------------------------------
def create_epub(text, date_str):
    import zipfile
    from io import BytesIO
    title = f"Morgenbrief {date_str}"
    text = strip_markdown(text)
    text = _normalize_dashes(text)
    text = force_ltr_on_questions(text)   # <-- Hier wird LTR erzwungen
    text = ensure_news_section(text)

    lines = text.strip().split("\n")
    html_parts, current_block, current_rtl = [], [], False

    def flush():
        nonlocal current_rtl
        if current_block:
            c = "<br/>".join(html.escape(line) for line in current_block)
            if current_rtl:
                html_parts.append(f'<p dir="rtl" style="text-align:right;">{c}</p>')
            else:
                html_parts.append(f'<p dir="ltr">{c}</p>')
            current_block.clear()

    for line in lines:
        s = line.strip()
        u = s.upper()
        if s == '<div dir="ltr">' or s == '</div>':
            flush()
            html_parts.append(s)
            continue
        if re.search(r'SPRACH[ÜU]BUNG\s*[-–]\s*TEXT', u):
            flush(); current_rtl = True; html_parts.append(f'<h2>{html.escape(s)}</h2>')
        elif re.search(r'SPRACH[ÜU]BUNG\s*[-–]\s*FRAGEN', u) or re.search(r'VERST[ÄA]NDNISFRAGEN', u):
            flush(); current_rtl = False; html_parts.append(f'<h2>{html.escape(s)}</h2>')
        elif u.startswith('NACHRICHTEN'):
            flush(); current_rtl = True; html_parts.append(f'<h2>{html.escape(s)}</h2>')
        elif u.rstrip(':').lstrip() in {"WETTER","HEUTE","IMPULS","PROJEKTE","ERLEDIGTES","AUSBLICK"}:
            flush(); current_rtl = False; html_parts.append(f'<h2>{html.escape(s)}</h2>')
        elif s == "":
            flush()
        else:
            current_block.append(s)
    flush()

    xhtml = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>{html.escape(title)}</title>
<style>body{{font-family:serif;margin:1em;}} h2{{text-transform:uppercase;}}</style>
</head><body><h1>{html.escape(title)}</h1>
{"".join(html_parts)}
</body></html>'''

    container = '<?xml version="1.0"?><container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles></container>'
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    opf = f'''<?xml version="1.0"?><package xmlns="http://www.idpf.org/2007/opf" version="3.0"><metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:identifier id="uid">morgenbrief-{date_str}</dc:identifier><dc:title>{html.escape(title)}</dc:title><dc:language>de</dc:language><meta property="dcterms:modified">{ts}</meta></metadata><manifest><item id="content" href="content.xhtml" media-type="application/xhtml+xml"/><item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/></manifest><spine><itemref idref="content"/></spine></package>'''
    nav = f'''<?xml version="1.0"?><html xmlns="http://www.w3.org/1999/xhtml"><head><title>Navigation</title></head><body><nav><h1>Inhalt</h1><ol><li><a href="content.xhtml">{html.escape(title)}</a></li></ol></nav></body></html>'''

    buf = BytesIO()
    with zipfile.ZipFile(buf,"w",zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("mimetype","application/epub+zip",compress_type=zipfile.ZIP_STORED)
        zf.writestr("META-INF/container.xml",container)
        zf.writestr("OEBPS/content.opf",opf)
        zf.writestr("OEBPS/content.xhtml",xhtml)
        zf.writestr("OEBPS/nav.xhtml",nav)
    fn = f"morgenbrief_{date_str}.epub"
    with open(fn,"wb") as f:
        f.write(buf.getvalue())
    return fn


# ------------------------------------------------------------
# MAIL VERSAND
# ------------------------------------------------------------
def send_to_kindle(epub_path):
    ga = os.environ.get("GMAIL_ADDRESS")
    gp = os.environ.get("GMAIL_APP_PASSWORD")
    ka = os.environ.get("KINDLE_EMAIL")
    if not all([ga,gp,ka]):
        sys.exit("Fehlende Secrets")
    msg = MIMEMultipart()
    msg["From"] = ga
    msg["To"] = ka
    msg["Subject"] = "Morgenbrief"
    msg.attach(MIMEText("", "plain"))
    with open(epub_path, "rb") as f:
        part = MIMEBase("application", "epub+zip")
        part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f"attachment; filename={os.path.basename(epub_path)}")
        msg.attach(part)
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(ga, gp)
        smtp.sendmail(ga, ka, msg.as_string())
    print(f"Gesendet an {ka}")


# ------------------------------------------------------------
# MAIN
# ------------------------------------------------------------
def main():
    repo = Path(__file__).parent
    kontext = (repo/"kontext.md").read_text(encoding="utf-8") if (repo/"kontext.md").exists() else "Du bist ein Schriftsteller."
    fahrplan = (repo/"fahrplan.md").read_text(encoding="utf-8") if (repo/"fahrplan.md").exists() else ""
    aufgaben = (repo/"aufgaben.md").read_text(encoding="utf-8") if (repo/"aufgaben.md").exists() else ""

    ical_url = os.environ.get("ICAL_URL", "")
    print(f"DEBUG: ICAL_URL {'gesetzt' if ical_url else 'LEER'}", file=sys.stderr)
    kalender = fetch_calendar(ical_url) if ical_url else "[Keine URL]"
    print(f"DEBUG: Kalenderausgabe:\n{kalender}", file=sys.stderr)

    wetter = fetch_weather()
    impulse = generate_impulse()
    lang_ex = generate_language_exercise()

    print(f"DEBUG: Sprache {lang_ex['language']}, News vorhanden: {bool(lang_ex['headline'])}", file=sys.stderr)

    text = call_claude(kontext, fahrplan, aufgaben, kalender, wetter, impulse, lang_ex)

    # Vokabeln extrahieren
    gloss_match = re.search(r'(?:Glossar|NEUE VOKABELN):\s*(.*?)(?:\n\n|\n$)', text, re.IGNORECASE | re.DOTALL)
    if gloss_match:
        pairs = re.findall(r'([^\s=]+)\s*[=:]\s*([^,\n]+)', gloss_match.group(1))
        if pairs:
            add_new_vocab(lang_ex["lang_code"], pairs, lang_ex["memory"])
        text = re.sub(r'(?:Glossar|NEUE VOKABELN):.*?(?=\n\n|\n$)', '', text, flags=re.IGNORECASE | re.DOTALL)

    epub = create_epub(text, now_berlin().strftime("%Y-%m-%d"))
    send_to_kindle(epub)

if __name__ == "__main__":
    main()
