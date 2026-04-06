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
from icalendar import Calendar
import requests

# ─── Zeitzone ───
BERLIN_TZ = ZoneInfo("Europe/Berlin")

def now_berlin():
    return datetime.now(BERLIN_TZ)

def _normalize_dashes(text):
    return text.replace("\u2014", "-").replace("\u2013", "-").replace("\u2012", "-")


# ─── Kalender parsen (mit icalendar) ───

def fetch_calendar(ical_url):
    if ical_url.startswith("webcal://"):
        ical_url = ical_url.replace("webcal://", "https://", 1)
    try:
        resp = requests.get(ical_url, timeout=15, headers={"User-Agent": "Morgenbrief/1.0"})
        resp.raise_for_status()
        cal = Calendar.from_ical(resp.text)
    except Exception as e:
        return f"[Kalender konnte nicht geladen werden: {e}]"

    events = []
    today_berlin = now_berlin().replace(hour=0, minute=0, second=0, microsecond=0)
    horizon = today_berlin + timedelta(days=3)

    for component in cal.walk('VEVENT'):
        dtstart = component.get('DTSTART')
        if dtstart is None:
            continue
        dt = dtstart.dt
        summary = str(component.get('SUMMARY', ''))
        location = str(component.get('LOCATION', ''))

        if isinstance(dt, datetime):
            if dt.tzinfo is None:
                dt_berlin = dt.replace(tzinfo=BERLIN_TZ)
            else:
                dt_berlin = dt.astimezone(BERLIN_TZ)
            is_allday = False
        else:
            dt_berlin = datetime.combine(dt, datetime.min.time()).replace(tzinfo=BERLIN_TZ)
            is_allday = True

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
    return "\n".join(e[2] for e in events) if events else "[Keine Termine in den nächsten 3 Tagen]"


# ─── Wetter ───

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


# ─── Nachrichten (BBC World Service, mit RSS-Fallback) ───

def _fetch_rss_headline(rss_url):
    try:
        resp = requests.get(rss_url, timeout=10, headers={"User-Agent": "Morgenbrief/1.0"})
        resp.raise_for_status()
        data = resp.text
        titles = re.findall(r"<item>.*?<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>", data, re.DOTALL)
        if titles:
            h = titles[0].strip().replace("&amp;","&").replace("&quot;",'"').replace("&lt;","<").replace("&gt;",">")
            return h[:300]
    except Exception:
        pass
    return None

def _fetch_bbc_github(lang_code):
    urls = {"ar": "https://raw.githubusercontent.com/bbc/world-service-rss/main/arabic.md",
            "fa": "https://raw.githubusercontent.com/bbc/world-service-rss/main/persian.md"}
    url = urls.get(lang_code)
    if not url: return None
    try:
        resp = requests.get(url, timeout=10, headers={"User-Agent": "Morgenbrief/1.0"})
        resp.raise_for_status()
        data = resp.text
        rss_match = re.search(r'\((https?://feeds\.bbci\.co\.uk/[^)]+)\)', data)
        if rss_match:
            return _fetch_rss_headline(rss_match.group(1))
        match = re.search(r'## \[(.*?)\]\(.*?\)', data, re.DOTALL)
        if match:
            h = match.group(1).strip().replace("&amp;","&").replace("&quot;",'"')
            return h[:300]
    except Exception as e:
        print(f"BBC GitHub Fehler ({lang_code}): {e}", file=sys.stderr)
    return None

BBC_RSS_FALLBACKS = {"ar": "https://feeds.bbci.co.uk/arabic/rss.xml", "fa": "https://feeds.bbci.co.uk/persian/rss.xml"}

def fetch_news_headline(lang_code):
    headline = _fetch_bbc_github(lang_code)
    if headline: return headline
    fb = BBC_RSS_FALLBACKS.get(lang_code)
    if fb:
        headline = _fetch_rss_headline(fb)
        if headline:
            print(f"News via BBC RSS Fallback ({lang_code})", file=sys.stderr)
            return headline
    print(f"Keine News verfügbar ({lang_code})", file=sys.stderr)
    return None

def _clean_html(text):
    text = re.sub(r'<[^>]+>', ' ', text)
    text = text.replace("&amp;","&").replace("&quot;",'"').replace("&lt;","<").replace("&gt;",">").replace("&#039;","'")
    return re.sub(r'\s+', ' ', text).strip()

def _fetch_article_text(lang_code):
    """Holt den Artikeltext der ersten BBC-Nachricht (unabhängig von fetch_news_headline)."""
    gh_urls = {"ar": "https://raw.githubusercontent.com/bbc/world-service-rss/main/arabic.md",
               "fa": "https://raw.githubusercontent.com/bbc/world-service-rss/main/persian.md"}
    rss_url = BBC_RSS_FALLBACKS.get(lang_code)
    gh = gh_urls.get(lang_code)
    if gh:
        try:
            resp = requests.get(gh, timeout=10, headers={"User-Agent": "Morgenbrief/1.0"})
            resp.raise_for_status()
            data = resp.text
            m = re.search(r'\((https?://feeds\.bbci\.co\.uk/[^)]+)\)', data)
            if m:
                rss_url = m.group(1)
        except Exception: pass
    if not rss_url: return ""
    try:
        resp = requests.get(rss_url, timeout=10, headers={"User-Agent": "Morgenbrief/1.0"})
        resp.raise_for_status()
        rss = resp.text
        items = re.findall(r"<item>(.*?)</item>", rss, re.DOTALL)
        if not items: return ""
        link_m = re.search(r"<link>(.*?)</link>", items[0])
        desc_m = re.search(r"<description>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</description>", items[0], re.DOTALL)
        desc = _clean_html(desc_m.group(1))[:500] if desc_m else ""
        link = link_m.group(1).strip() if link_m else ""
    except Exception:
        return ""
    if not link: return desc
    try:
        resp = requests.get(link, timeout=15, headers={"User-Agent": "Morgenbrief/1.0"})
        resp.raise_for_status()
        html_page = resp.text
        paragraphs = re.findall(r'<p[^>]*>([^<]+(?:<[^/p][^>]*>[^<]*</[^p][^>]*>)*[^<]*)</p>', html_page)
        text_parts = [_clean_html(p) for p in paragraphs if len(_clean_html(p)) > 40]
        if text_parts:
            article = "\n".join(text_parts[:8])
            print(f"Artikel geladen ({lang_code}): {len(article)} Zeichen", file=sys.stderr)
            return article
    except Exception as e:
        print(f"Artikel-Fetch Fehler: {e}", file=sys.stderr)
    return desc


# ─── Musikbibliothek ───

MUSIC_LIBRARY_FILE = Path(__file__).parent / "all.txt"
_music_data = None

def _load_music_library():
    data = []
    if not MUSIC_LIBRARY_FILE.exists(): return data
    for delim in ('\t', ','):
        try:
            with open(MUSIC_LIBRARY_FILE, "r", encoding="utf-8") as f:
                fl = f.readline()
                if not fl or "Album" not in fl: continue
                f.seek(0)
                for row in csv.DictReader(f, delimiter=delim):
                    album, artist = row.get("Album","").strip(), row.get("Artist","").strip()
                    if not album or not artist: continue
                    try: plays = int(row.get("Plays","0") or "0")
                    except: plays = 0
                    last_date = None
                    ls = row.get("Last Played","").strip()
                    if ls and "," in ls:
                        try: last_date = datetime.strptime(ls.split(",")[0].strip(), "%d.%m.%Y").date()
                        except: pass
                    try: rating = int(row.get("My Rating","0") or "0")
                    except: rating = 0
                    data.append({"artist":artist,"album":album,"plays":plays,"last_played":last_date,"rating":rating,"genre":row.get("Genre","").strip()})
            if data:
                print(f"Musikbibliothek: {len(data)} Einträge", file=sys.stderr)
                break
        except Exception as e:
            print(f"Musikfehler ({repr(delim)}): {e}", file=sys.stderr)
    return data

_music_data = _load_music_library()

def _get_top_genres(limit=3):
    if not _music_data: return []
    gc = {}
    for e in _music_data:
        if e["genre"]: gc[e["genre"]] = gc.get(e["genre"],0) + e["plays"]
    return [g for g,_ in sorted(gc.items(), key=lambda x:x[1], reverse=True)[:limit]]

def _get_high_rated_artists(threshold=80, limit=5):
    if not _music_data: return []
    sc = {}
    for e in _music_data:
        if e["rating"] >= threshold: sc[e["artist"]] = sc.get(e["artist"],0)+1
    return [a for a,_ in sorted(sc.items(), key=lambda x:x[1], reverse=True)[:limit]]

def _get_similar_artists(artist_name, limit=3):
    if not _music_data: return []
    genres = {e["genre"] for e in _music_data if e["artist"]==artist_name and e["genre"]}
    if not genres: return []
    return list({e["artist"] for e in _music_data if e["artist"]!=artist_name and e["genre"] in genres})[:limit]

def _select_album_of_the_day():
    if not _music_data: return None
    today = now_berlin().date()
    is_exploration = random.random() < 0.2
    top_genres = _get_top_genres(3)
    ha = _get_high_rated_artists(threshold=80)
    similar = set()
    if is_exploration:
        for a in ha: similar.update(_get_similar_artists(a))
    weighted = []
    for e in _music_data:
        w = 1.0
        if is_exploration:
            if e["plays"]==0: w *= 2.0
            if e["artist"] in similar: w *= 2.0
        else:
            if e["rating"]>=80: w *= 1.5*(e["rating"]/50)
            if e["genre"] in top_genres: w *= 1.2
        ds = (today - e["last_played"]).days if e["last_played"] else 365
        w *= (ds+1) * (1.0/(e["plays"]+1)) * random.uniform(0.8,1.2)
        weighted.append((w,e))
    if not weighted: return None
    total = sum(w for w,_ in weighted)
    r = random.random()*total
    cum = 0
    for w,e in weighted:
        cum += w
        if r <= cum: return e
    return weighted[-1][1]


# ─── Entdeckungsvorschläge (auto-generiert via Claude API) ───

DISCOVERY_FILE = Path(__file__).parent / "discovery_albums.json"

_SEED_ALBUMS = [
    ("Kayhan Kalhor & Rembrandt Trio","Silence City"),("Tigran Hamasyan","A Fable"),
    ("Anouar Brahem","Thimar"),("Mohsen Namjoo","Toranj"),
    ("Mohammad Reza Shajarian","Ghame Eshgh"),("Grouper","Dragging a Dead Deer Up a Hill"),
    ("Midori Takada","Through the Looking Glass"),("Nils Frahm","Felt"),
    ("Arvo Pärt","Tabula Rasa"),("Vijay Iyer","Historicity"),
]

def _load_discovery_albums():
    if not DISCOVERY_FILE.exists(): return [], True
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
    if profile: data["generated_from"] = profile
    with open(DISCOVERY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def _generate_discovery_albums_via_api():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key: return None
    top_genres = _get_top_genres(5)
    top_artists = _get_high_rated_artists(threshold=60, limit=10)
    library_artists = {e["artist"] for e in _music_data} if _music_data else set()

    prompt = (f"Ich suche 20 Alben-Empfehlungen die ich noch NICHT kenne.\n\n"
              f"Meine Top-Genres: {', '.join(top_genres)}\n"
              f"Meine Lieblingskünstler: {', '.join(top_artists)}\n\n"
              f"Regeln:\n"
              f"- KEINE Alben von Künstlern die ich schon höre\n"
              f"- Mischung aus: bekannten Klassikern, Geheimtipps, Musik aus Iran/Zentralasien/arabischer Welt\n"
              f"- Vielfalt: nicht alles ein Genre\n"
              f'- Antworte NUR mit JSON-Liste, kein anderer Text:\n'
              f'[{{"artist": "Name", "album": "Albumtitel"}}, ...]')

    payload = json.dumps({
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 2000,
        "messages": [{"role": "user", "content": prompt}]
    }).encode("utf-8")
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=payload,
        headers={"Content-Type":"application/json","x-api-key":api_key,"anthropic-version":"2023-06-01"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
        text = result["content"][0]["text"].strip()
        text = re.sub(r'^[`]{3}json\s*', '', text)
        text = re.sub(r'\s*[`]{3}$', '', text)
        raw = json.loads(text)
        albums = []
        for item in raw:
            a, b = item.get("artist","").strip(), item.get("album","").strip()
            if a and b and a not in library_artists:
                albums.append({"artist": a, "album": b, "suggested": False})
        if albums:
            _save_discovery_albums(albums, {"top_genres": top_genres, "top_artists": top_artists})
            print(f"Discovery: {len(albums)} neue Alben generiert", file=sys.stderr)
            return albums
    except Exception as e:
        print(f"Discovery-Generierung fehlgeschlagen: {e}", file=sys.stderr)
    return None

def _select_discovery_album():
    albums, needs_refresh = _load_discovery_albums()
    if needs_refresh:
        new = _generate_discovery_albums_via_api()
        if new: albums = new
        elif not albums:
            albums = [{"artist":a,"album":b,"suggested":False} for a,b in _SEED_ALBUMS]
            _save_discovery_albums(albums)
    unseen = [a for a in albums if not a.get("suggested", False)]
    if not unseen: unseen = albums
    pick = random.choice(unseen)
    for a in albums:
        if a["artist"]==pick["artist"] and a["album"]==pick["album"]:
            a["suggested"] = True; break
    _save_discovery_albums(albums)
    return (pick["artist"], pick["album"])


# ─── Tagesimpuls ───

def generate_impulse():
    today = now_berlin()
    day_de = {"Monday":"Montag","Tuesday":"Dienstag","Wednesday":"Mittwoch","Thursday":"Donnerstag",
              "Friday":"Freitag","Saturday":"Samstag","Sunday":"Sonntag"}.get(today.strftime("%A"), today.strftime("%A"))

    creative_pool = [
        "Entwickle einen Film oder scanne Negative.",
        "Schau einen persischen Film (z. B. von Panahi, Kiarostami, Farhadi oder Rasoulof).",
        "Nimm eine Mixtape-Seite auf.", "Schreibe handschriftlich einen Brief.",
        "Mache Skizzen oder zeichne.", "Übersetze ein Gedicht, das nicht für hochroth ist.",
        "Mach einen langen Spaziergang mit der Kamera.",
        "Improvisiere am Klavier – ganz ohne Übungsziel.",
        "Lies einen alten Text von dir und mache dir Notizen dazu.",
        "Koche etwas Neues – ein Rezept aus einer anderen Küche.",
        "Schicke eine Postkarte an jemanden.",
        "Mache Field Recordings (im Garten oder in der Umgebung).",
    ]

    if random.random() < 0.25:
        artist, album = _select_discovery_album()
        album_line = f"Album des Tages: {artist} — {album} (Entdeckung – nicht in deiner Bibliothek)"
    else:
        entry = _select_album_of_the_day()
        if entry:
            album_line = f"Album des Tages: {entry['artist']} — {entry['album']}"
            if entry["plays"]==0: album_line += " (Noch nie gehört!)"
            elif entry["rating"]>=80: album_line += " (Du magst diesen Künstler – hör mal wieder rein!)"
            elif entry["last_played"] and (today.date()-entry["last_played"]).days > 90: album_line += " (Lange nicht gehört.)"
        else:
            a, b = _select_discovery_album()
            album_line = f"Album des Tages: {a} — {b}"

    return (f"Heute ist {day_de}. Kleine Ideen für den Tag (wähle höchstens eine, wenn Zeit ist):\n"
            f"– Kreativ: {random.choice(creative_pool)}\n"
            f"– {album_line}\n"
            f"Passe die Auswahl an deine Termine und das Wetter an. Wenn der Tag voll ist, lass die Vorschläge einfach weg.")


# ─── Sprachübung (mit Vokabelgedächtnis) ───

LANG_START = datetime(2026, 4, 5, tzinfo=BERLIN_TZ)
VOCAB_FILE = Path(__file__).parent / "vocab_memory.json"

def load_vocab_memory():
    if VOCAB_FILE.exists():
        try:
            with open(VOCAB_FILE,"r",encoding="utf-8") as f: return json.load(f)
        except: pass
    return {"ar":[],"fa":[]}

def save_vocab_memory(m):
    with open(VOCAB_FILE,"w",encoding="utf-8") as f: json.dump(m,f,ensure_ascii=False,indent=2)

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
                e["last_review"]=today; e["times_reviewed"]+=1; e["interval"]=min(e.get("interval",1)*2,30); break
    save_vocab_memory(m)

def generate_language_exercise():
    today = now_berlin()
    doy = today.timetuple().tm_yday
    dss = max(0, (today - LANG_START).days)
    week = dss // 7
    language, lc = ("Arabisch","ar") if doy%2==0 else ("Persisch","fa")
    if week<2: level, instr = "A2 (einfach)", "Sehr einfache Sätze. Grundvokabular: Familie, Essen, Wetter, Tagesablauf. Präsens und einfache Vergangenheit."
    elif week<6: level, instr = "B1 (mittel)", "Längere Sätze möglich. Themen: Reisen, Arbeit, Meinungen, Nachrichten. Konjunktiv, Relativsätze erlaubt."
    elif week<12: level, instr = "B1+ (gehoben)", "Komplexere Strukturen. Themen: Kultur, Politik, Literatur. Passiv, indirekte Rede."
    else: level, instr = "B2 (fortgeschritten)", "Anspruchsvoller Text. Zeitungssprache, abstrakte Themen, idiomatische Wendungen."

    mem = load_vocab_memory()
    due = get_due_vocab(lc, mem)
    rep = ""
    if due:
        vl = "\n".join([f"  - {v['word']} ({v['meaning']})" for v in due])
        rep = f"\nVOKABELWIEDERHOLUNG:\nDiese Wörter sollen heute wiederholt werden. Baue sie in den Übungstext ein:\n{vl}\n"

    hl = fetch_news_headline(lc)
    article_text = _fetch_article_text(lc) if hl else ""
    topics = ["Tagesablauf und Routine","Essen und Kochen","Eine Reise beschreiben","Familie und Freunde",
              "Das Wetter","Einkaufen auf dem Markt","Ein Buch oder Film beschreiben","Die eigene Stadt vorstellen",
              "Arbeit und Beruf","Kindheitserinnerungen","Natur und Umwelt","Musik und Kunst","Gesundheit und Sport","Politik und Gesellschaft"]

    return {"language":language,"lang_code":lc,"level":level,"instructions":instr,
            "topic":topics[dss%len(topics)],"headline":hl,"article_text":article_text,"news_source":"BBC" if hl else None,
            "week":week,"repetition_prompt":rep,
            "new_vocab_instruction":"\nWICHTIG: Neue Vokabeln inline glossieren. Am Ende eine Zeile: \"NEUE VOKABELN: Wort (Bedeutung), Wort (Bedeutung)\"\n",
            "memory":mem,"due_vocab":due}


# ─── Claude aufrufen ───

def call_claude(kontext, fahrplan, aufgaben, kalender, wetter, impulse, lang_exercise):
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key: sys.exit("ANTHROPIC_API_KEY nicht gesetzt")
    today = now_berlin().strftime("%A, %d. %B %Y")
    lang = lang_exercise
    script = 'arabischer' if lang['lang_code']=='ar' else 'persischer'
    dialect = 'Fusha (MSA), kein Dialekt.' if lang['lang_code']=='ar' else 'Farsi-ye meyar, kein Slang.'
    
    vocalization_instruction = ""
    if lang['lang_code'] == 'ar':
        vocalization_instruction = ("DU MUSST ALLE ARABISCHEN WÖRTER VOLLSTÄNDIG VOKALISIEREN (Tashkīl/Harakat). "
                                    "Beispiel: كِتابٌ, مَدْرَسَةٌ, ذَهَبَ. Jeder Buchstabe erhält sein kurzes Vokalzeichen. "
                                    "Unvokalisierter Text ist nicht akzeptabel.\n")
    else:
        vocalization_instruction = ""

    if lang.get('headline'):
        article_block = ""
        if lang.get('article_text'):
            article_block = f"\nArtikeltext (als Grundlage):\n{lang['article_text'][:1500]}\n"
        news_p = (f"NACHRICHTEN (RTL, in Originalschrift):\n"
                  f"Schlagzeile: {lang['headline'][:200]}\n"
                  f"{article_block}"
                  f"Gib die Schlagzeile in {script} Originalschrift wieder. {vocalization_instruction}\n"
                  f"Fasse den Artikel in 4-6 Sätzen auf {lang['language']} zusammen (Level {lang['level']}). {vocalization_instruction}\n"
                  f"Glossiere schwierige Wörter inline auf Deutsch (passend zu Level {lang['level']}).")
    else:
        news_p = ("NACHRICHTEN (RTL, in Originalschrift):\n"
                  "Keine aktuellen Nachrichten verfügbar. Schreibe einen kurzen Satz auf Deutsch, dass heute keine Nachrichten abgerufen werden konnten.")

    lang_p = (f"SPRACHÜBUNG - TEXT (RTL, in Originalschrift):\n"
              f"Schreibe einen kurzen Übungstext auf {lang['language']} zum Thema \"{lang['topic']}\".\n"
              f"Regeln:\n- 5-8 Sätze in {script} Schrift. {vocalization_instruction}\n- {lang['instructions']}\n- {dialect}\n"
              f"- {lang['new_vocab_instruction']}\n{lang['repetition_prompt']}\n"
              f"SPRACHÜBUNG - FRAGEN (LTR, auf Deutsch):\n"
              f"2-3 Verständnisfragen auf Deutsch zum obigen Text. Jede Frage in einer neuen Zeile.\n"
              f"Keine Originalschrift in diesem Abschnitt. Schreibe die Fragen in normaler lateinischer Schrift (LTR).")

    msg = (f"Heute ist {today}.\n\nWETTER:\n{wetter}\n\nTAGESIMPULS:\n{impulse}\n\n"
           f"KONTEXT (enthält Format und Regeln - befolge sie exakt):\n{kontext}\n\n"   # <-- FIXED: {kontext} not \kontext}
           f"OFFENE AUFGABEN:\n{aufgaben}\n\nKALENDER (nächste 3 Tage):\n{kalender}\n\n"
           f"FAHRPLAN (nur als Hintergrund):\n{fahrplan}\n\n{lang_p}\n\n{news_p}\n\n"
           f"AUFTRAG:\nSchreibe den Morgenbrief exakt in dieser Struktur:\n"
           f"1. WETTER\n2. HEUTE\n3. IMPULS\n4. PROJEKTE\n5. ERLEDIGTES\n6. AUSBLICK\n"
           f"7. SPRACHÜBUNG - TEXT (Übungstext in Originalschrift, RTL)\n"
           f"8. SPRACHÜBUNG - FRAGEN (Verständnisfragen auf Deutsch, LTR)\n"
           f"9. NACHRICHTEN (Schlagzeile + Zusammenfassung in Originalschrift, RTL)\n\n"
           f"WICHTIG: Verwende in Sektionstiteln immer einfache Bindestriche (-), NIEMALS Gedankenstriche.\n"
           f"Jede Sektion als Überschrift in Großbuchstaben. Kein Markdown. Sachlich.")

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


# ─── ePub erzeugen (robuste RTL/LTR Erkennung) ───

def create_epub(text, date_str):
    import zipfile
    from io import BytesIO
    title = f"Morgenbrief {date_str}"
    text = strip_markdown(text)
    text = _normalize_dashes(text)

    lines = text.strip().split("\n")
    html_parts, current_block, current_rtl = [], [], False

    def flush():
        nonlocal current_rtl
        if current_block:
            c = "<br/>".join(html.escape(line) for line in current_block)
            if current_rtl:
                html_parts.append(f'<p dir="rtl" style="text-align:right;font-size:1.1em;line-height:1.8;">{c}</p>')
            else:
                html_parts.append(f'<p dir="ltr">{c}</p>')
            current_block.clear()

    for line in lines:
        s = line.strip()
        u = s.upper()
        # Erkennung der Sektionen (robust)
        # Text-Übung (RTL)
        if re.search(r'SPRACH[ÜU]BUNG\s*[-–]\s*TEXT', u):
            flush()
            current_rtl = True
            html_parts.append(f'<h2 dir="ltr">{html.escape(s)}</h2>')
        # Fragen (LTR) – erkenne verschiedene Varianten
        elif re.search(r'SPRACH[ÜU]BUNG\s*[-–]\s*FRAGEN', u) or re.search(r'VERST[ÄA]NDNISFRAGEN', u) or u.startswith('FRAGEN:'):
            flush()
            current_rtl = False
            html_parts.append(f'<h2 dir="ltr">{html.escape(s)}</h2>')
        # Nachrichten (RTL)
        elif re.search(r'^NACHRICHTEN', u):
            flush()
            current_rtl = True
            html_parts.append(f'<h2 dir="ltr">{html.escape(s)}</h2>')
        # Andere Standard-Sektionen (LTR)
        elif u.rstrip(':').lstrip() in {"WETTER", "HEUTE", "IMPULS", "PROJEKTE", "ERLEDIGTES", "AUSBLICK"}:
            flush()
            current_rtl = False
            html_parts.append(f'<h2 dir="ltr">{html.escape(s)}</h2>')
        elif s == "":
            flush()
        else:
            current_block.append(s)
    flush()

    # Debug: Ausgabe der erkannten Sektionen (in GitHub Actions Log sichtbar)
    print(f"ePub generiert mit {len(html_parts)} Blöcken", file=sys.stderr)

    xhtml = (f'<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE html>\n'
             f'<html xmlns="http://www.w3.org/1999/xhtml"><head><title>{html.escape(title)}</title>\n'
             f'<style>body{{font-family:serif;font-size:1em;line-height:1.5;margin:1em;}}'
             f'h1{{font-size:1.4em;margin-bottom:0.3em;}}h2{{font-size:1.1em;margin-top:1em;margin-bottom:0.3em;text-transform:uppercase;letter-spacing:0.05em;}}'
             f'p{{margin-bottom:0.6em;}}</style></head><body>\n<h1>{html.escape(title)}</h1>\n'
             + "\n".join(html_parts) + '\n</body></html>')

    container = ('<?xml version="1.0" encoding="UTF-8"?>\n<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">'
                 '\n<rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles></container>')
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    opf = (f'<?xml version="1.0" encoding="UTF-8"?>\n<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="uid">'
           f'\n<metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:identifier id="uid">morgenbrief-{date_str}</dc:identifier>'
           f'<dc:title>{html.escape(title)}</dc:title><dc:language>de</dc:language><dc:creator>Claude</dc:creator>'
           f'<meta property="dcterms:modified">{ts}</meta></metadata>'
           f'\n<manifest><item id="content" href="content.xhtml" media-type="application/xhtml+xml"/>'
           f'<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/></manifest>'
           f'\n<spine><itemref idref="content"/></spine></package>')
    nav = (f'<?xml version="1.0" encoding="UTF-8"?>\n<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">'
           f'<head><title>Navigation</title></head><body>\n<nav epub:type="toc"><h1>Inhalt</h1><ol><li><a href="content.xhtml">{html.escape(title)}</a></li></ol></nav>'
           f'\n</body></html>')

    buf = BytesIO()
    with zipfile.ZipFile(buf,"w",zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("mimetype","application/epub+zip",compress_type=zipfile.ZIP_STORED)
        zf.writestr("META-INF/container.xml",container)
        zf.writestr("OEBPS/content.opf",opf)
        zf.writestr("OEBPS/content.xhtml",xhtml)
        zf.writestr("OEBPS/nav.xhtml",nav)
    fn = f"morgenbrief_{date_str}.epub"
    with open(fn,"wb") as f: f.write(buf.getvalue())
    return fn


# ─── Mail an Kindle ───

def send_to_kindle(epub_path):
    ga, gp, ka = os.environ.get("GMAIL_ADDRESS"), os.environ.get("GMAIL_APP_PASSWORD"), os.environ.get("KINDLE_EMAIL")
    if not all([ga,gp,ka]): sys.exit("Gmail/Kindle Secrets nicht vollständig")
    msg = MIMEMultipart(); msg["From"]=ga; msg["To"]=ka; msg["Subject"]="Morgenbrief"
    msg.attach(MIMEText("","plain"))
    with open(epub_path,"rb") as f:
        part = MIMEBase("application","epub+zip"); part.set_payload(f.read())
        encoders.encode_base64(part); part.add_header("Content-Disposition",f"attachment; filename={os.path.basename(epub_path)}")
        msg.attach(part)
    with smtplib.SMTP_SSL("smtp.gmail.com",465) as smtp:
        smtp.login(ga,gp); smtp.sendmail(ga,ka,msg.as_string())
    print(f"Morgenbrief an {ka} gesendet")


# ─── Main ───

def main():
    repo = Path(__file__).parent
    try:
        kontext = (repo/"kontext.md").read_text(encoding="utf-8")
    except FileNotFoundError:
        kontext = "Du bist ein Schriftsteller, Übersetzer und Musiker. Sei direkt und sachlich."
        print("Warnung: kontext.md nicht gefunden, verwende Standard.", file=sys.stderr)
    try:
        fahrplan = (repo/"fahrplan.md").read_text(encoding="utf-8")
    except FileNotFoundError:
        fahrplan = "Kein Fahrplan vorhanden."
    try:
        aufgaben = (repo/"aufgaben.md").read_text(encoding="utf-8")
    except FileNotFoundError:
        aufgaben = "Keine Aufgaben."

    ical_url = os.environ.get("ICAL_URL","")
    kalender = fetch_calendar(ical_url) if ical_url else "[Keine Kalender-URL]"
    wetter = fetch_weather()
    impulse = generate_impulse()
    lang_ex = generate_language_exercise()

    print(f"Morgenbrief wird geschrieben ({now_berlin().strftime('%d.%m.%Y %H:%M')} Berliner Zeit)...")
    print(f"Sprachübung: {lang_ex['language']} (Level {lang_ex['level']}, Thema: {lang_ex['topic']})")
    if lang_ex.get('headline'): print(f"News: {lang_ex['headline'][:60]}...")
    else: print("Keine News verfügbar.")

    text = call_claude(kontext, fahrplan, aufgaben, kalender, wetter, impulse, lang_ex)

    # Vokabelgedächtnis
    vm = re.search(r"NEUE VOKABELN:\s*(.*?)(?:\n|$)", text, re.IGNORECASE | re.MULTILINE)
    if vm:
        pairs = re.findall(r"([^\s,]+)\s*\(([^)]+)\)", vm.group(1))
        if pairs: add_new_vocab(lang_ex["lang_code"], pairs, lang_ex["memory"])
        text = re.sub(r"NEUE VOKABELN:.*\n?", "", text, flags=re.IGNORECASE | re.MULTILINE)
    due_w = [v["word"] for v in lang_ex.get("due_vocab",[])]
    reviewed = [w for w in due_w if w in text]
    if reviewed: update_reviewed_vocab(lang_ex["lang_code"], reviewed, lang_ex["memory"])

    epub = create_epub(text, now_berlin().strftime("%Y-%m-%d"))
    send_to_kindle(epub)


if __name__ == "__main__":
    main()
