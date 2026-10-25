#!/usr/bin/env python3
"""
Morgenbrief: Täglicher Tagesplan via Claude → ePub → Kindle
Unterstützt mehrere Kalender (Semikolon-getrennte URLs) und BBC-Artikeltexte.
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

def _normalize_dashes(text):
    return text.replace("\u2014", "-").replace("\u2013", "-").replace("\u2012", "-")

<<<<<<< Updated upstream
# ─── Kalender: iCloud CalDAV + iCal-URLs (Semikolon-getrennt) ───
=======
# ─── Hilfs-Funktion: Dash-Normalisierung ───

def _normalize_dashes(text):
    """Ersetzt alle Dash-Varianten (em-dash, en-dash, minus) durch einfachen Bindestrich."""
    return text.replace("\u2014", "-").replace("\u2013", "-").replace("\u2012", "-")


# ─── Kalender parsen ───

def fetch_calendar(ical_url):
    try:
        req = urllib.request.Request(ical_url, headers={"User-Agent": "Morgenbrief/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        return f"[Kalender konnte nicht geladen werden: {e}]"
>>>>>>> Stashed changes

def _parse_ical_events(data, today_berlin, horizon):
    """Parst iCal-Daten und gibt Events als Liste von Strings zurück."""
    events = []
    data = data.replace('\r\n', '\n').replace('\r', '\n')
    for block in re.findall(r"BEGIN:VEVENT(.*?)END:VEVENT", data, re.DOTALL):
        summary, dtstart_str, location, is_utc = "", "", "", False
        m = re.search(r"SUMMARY:(.*?)[\n]", block, re.DOTALL)
        if m: summary = m.group(1).strip()
        m = re.search(r"DTSTART[^:]*:(.*?)[\n]", block, re.DOTALL)
        if m: dtstart_str = m.group(1).strip()
        if dtstart_str.endswith("Z"):
            is_utc = True
            dtstart_str = dtstart_str[:-1]
        m = re.search(r"LOCATION:(.*?)[\n]", block, re.DOTALL)
        if m: location = m.group(1).strip().replace("\\n", ", ").replace("\\,", ",")
        dt, is_allday = None, False
        try:
            if "T" in dtstart_str:
                dt = datetime.strptime(dtstart_str[:15], "%Y%m%dT%H%M%S")
            elif len(dtstart_str) >= 8:
                dt = datetime.strptime(dtstart_str[:8], "%Y%m%d")
                is_allday = True
        except ValueError:
            continue
        if dt is None: continue
        if is_allday: dt_berlin = dt.replace(tzinfo=BERLIN_TZ)
        elif is_utc: dt_berlin = dt.replace(tzinfo=timezone.utc).astimezone(BERLIN_TZ)
        else: dt_berlin = dt.replace(tzinfo=BERLIN_TZ)
        if today_berlin <= dt_berlin < horizon:
            date_str = dt_berlin.strftime("%a %d.%m.") if is_allday else dt_berlin.strftime("%a %d.%m. %H:%M")
            loc_str = f" ({location})" if location else ""
            day_diff = (dt_berlin.date() - today_berlin.date()).days
            tag_label = ["HEUTE", "MORGEN", "ÜBERMORGEN"][day_diff] if day_diff < 3 else ""
            events.append(f"  [{tag_label}] {date_str}: {summary}{loc_str}")
    return events

# Nur diese iCloud-Kalender einbeziehen (Shirin ausschließen)
CALDAV_ALLOWED_CALENDARS = {"SM", "Moritz", "Arbeit", "Familie", "Geburtstag", "Preply"}
# Nur diese Kalender enthalten seine eigenen Verpflichtungen. Der Rest dient
# allein der Abstimmung und darf nicht als sein Termin dargestellt werden.
EIGENE_KALENDER = {"Moritz", "SM"}

def _fetch_caldav_events(today_berlin, horizon):
    """Holt Events via CalDAV (iCloud mit app-spezifischem Passwort)."""
    apple_id = os.environ.get("APPLE_ID", "")
    app_password = os.environ.get("APPLE_APP_PASSWORD", "")
    if not apple_id or not app_password:
        return []
    try:
        import caldav
        client = caldav.DAVClient(url="https://caldav.icloud.com", username=apple_id, password=app_password)
        principal = client.principal()
        calendars = principal.calendars()
        events = []
        for cal in calendars:
            cal_name = getattr(cal, 'name', '') or ''
            if CALDAV_ALLOWED_CALENDARS and cal_name not in CALDAV_ALLOWED_CALENDARS:
                print(f"CalDAV: überspringe Kalender '{cal_name}'", file=sys.stderr)
                continue
            try:
                results = cal.date_search(start=today_berlin, end=horizon, expand=True)
                for event in results:
                    ical_data = event.data
                    if ical_data:
                        for zeile in _parse_ical_events(ical_data, today_berlin, horizon):
                            events.append(f"{zeile}\t@{cal_name}")
                print(f"CalDAV: {cal_name} — {len(results)} Events", file=sys.stderr)
            except Exception as e:
                print(f"CalDAV Kalender-Fehler ({cal_name}): {e}", file=sys.stderr)
        print(f"CalDAV gesamt: {len(events)} Events", file=sys.stderr)
        return events
    except ImportError:
        print("caldav nicht installiert, überspringe CalDAV", file=sys.stderr)
        return []
    except Exception as e:
        print(f"CalDAV Fehler: {e}", file=sys.stderr)
        return []

def _fetch_ical_urls(ical_urls, today_berlin, horizon):
    """Holt Events von iCal-URLs (Semikolon-getrennt)."""
    events = []
    urls = [u.strip() for u in ical_urls.split(';') if u.strip()]
    for url in urls:
        if url.startswith("webcal://"):
            url = url.replace("webcal://", "https://", 1)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Morgenbrief/1.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = resp.read().decode("utf-8", errors="replace")
            events.extend(_parse_ical_events(data, today_berlin, horizon))
        except Exception as e:
            print(f"iCal-Fehler bei {url[:60]}: {e}", file=sys.stderr)
    return events

def fetch_calendar(ical_urls):
    """Lädt Termine: erst CalDAV (iCloud), dann iCal-URLs als Fallback/Ergänzung."""
    today_berlin = now_berlin().replace(hour=0, minute=0, second=0, microsecond=0)
    horizon = today_berlin + timedelta(days=3)
    all_events = []
    # 1. CalDAV (iCloud mit App-Passwort)
    all_events.extend(_fetch_caldav_events(today_berlin, horizon))
    # 2. iCal-URLs (Google, etc.)
    if ical_urls:
        all_events.extend(_fetch_ical_urls(ical_urls, today_berlin, horizon))
    # Deduplizieren (gleicher Text = gleicher Termin)
    all_events = sorted(set(all_events))
    eigene, fremde = [], []
    for zeile in all_events:
        if "\t@" in zeile:
            text, kal = zeile.rsplit("\t@", 1)
            (eigene if kal in EIGENE_KALENDER else fremde).append(f"{text}  [{kal}]")
        else:
            eigene.append(zeile)
    teile = []
    teile.append("DEINE TERMINE:\n" + ("\n".join(eigene) if eigene else "  [keine]"))
    if fremde:
        teile.append("NUR ZUR ABSTIMMUNG (nicht deine Termine):\n" + "\n".join(fremde))
    return "\n\n".join(teile) if (eigene or fremde) else "[Keine Termine in den nächsten 3 Tagen]"

# ─── Wetter (unverändert) ───
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
        with urllib.request.urlopen(url, timeout=20) as resp:
            data = json.loads(resp.read())
        d, h = data["daily"], data.get("hourly", {})
        tmin, tmax = d["temperature_2m_min"][0], d["temperature_2m_max"][0]
        daily_desc = wmo.get(d["weathercode"][0], f"Code {d['weathercode'][0]}")
        hourly_precip = h.get("precipitation", [])
        hourly_prob = h.get("precipitation_probability", [])
        hourly_codes = h.get("weathercode", [])
<<<<<<< Updated upstream
        slots = [("Nacht",0,6),("Morgen",6,10),("Vormittag",10,13),("Nachmittag",13,18),("Abend",18,24)]
=======

        slots = [
            ("Nacht", 0, 6), ("Morgen", 6, 10), ("Vormittag", 10, 13),
            ("Nachmittag", 13, 18), ("Abend", 18, 24),
        ]

>>>>>>> Stashed changes
        precip_parts = []
        for sn, s, e in slots:
            if len(hourly_precip) < e or len(hourly_codes) < e:
                continue
<<<<<<< Updated upstream
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
        nt = hourly_temps[0:6]
        night_min = f"{min(nt):.0f}°C" if nt else f"{tmin:.0f}°C"
=======
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

>>>>>>> Stashed changes
        result = f"{name}: {daily_desc.capitalize()}, {tmin:.0f}–{tmax:.0f}°C (Nacht {night_min})"
        if precip_parts:
            result += "\n  " + "; ".join(precip_parts)
        elif d["precipitation_sum"][0] and d["precipitation_sum"][0] > 0:
            result += f" — {d['precipitation_sum'][0]:.1f}mm Niederschlag gesamt"
        return result
    except Exception as e:
        return f"{name}: [nicht verfügbar: {e}]"

ORTE = {
    "leipzig":  (51.34, 12.37, "Leipzig"),
    "roitzsch": (51.62, 12.30, "Roitzsch"),
    "zuerich":  (47.37,  8.54, "Zürich"),
    "zürich":   (47.37,  8.54, "Zürich"),
    "berlin":   (52.52, 13.40, "Berlin"),
    "halle":    (51.48, 11.97, "Halle (Saale)"),
    "dresden":  (51.05, 13.74, "Dresden"),
}

def aktueller_ort():
    """Wo er gerade ist. Voreinstellung Leipzig.

    Umschalten ueber die Datei /automat/standort.txt (eine Zeile, z. B. "zuerich")
    oder die Umgebungsvariable STANDORT. Unbekannte Orte fallen auf Leipzig zurueck.
    """
    wahl = os.environ.get("STANDORT", "").strip().lower()
    if not wahl:
        for kandidat in ("/automat/standort.txt", str(Path(__file__).parent / "standort.txt")):
            try:
                wahl = Path(kandidat).read_text(encoding="utf-8").strip().lower()
                if wahl:
                    break
            except Exception:
                continue
    return ORTE.get(wahl, ORTE["leipzig"])

def fetch_weather():
    lat, lon, name = aktueller_ort()
    result = fetch_weather_for_location(lat, lon, name)
    if "nicht verfügbar" in result:
        # Fallback: wttr.in
        try:
            req = urllib.request.Request(f"https://wttr.in/{name}?format=%t+%C+%p&lang=de", headers={"User-Agent": "curl/7.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                wttr = resp.read().decode("utf-8").strip()
            result = f"{name}: {wttr} (Quelle: wttr.in, Open-Meteo nicht erreichbar)"
        except Exception:
            pass
    return result

# ─── Nachrichten: Headline + Artikeltext aus BBC GitHub Markdown ───
def fetch_bbc_news_with_article(lang_code):
    """
    Ruft die BBC GitHub Markdown-Datei ab, extrahiert die erste Schlagzeile,
    den Link zum Artikel und lädt den ersten längeren Absatz des Artikels.
    Rückgabe: (headline, article_text) oder (None, None)
    """
    urls = {
        "ar": "https://raw.githubusercontent.com/bbc/world-service-rss/main/arabic.md",
        "fa": "https://raw.githubusercontent.com/bbc/world-service-rss/main/persian.md"
    }
    url = urls.get(lang_code)
    if not url:
        return None, None

<<<<<<< Updated upstream
=======
# ─── Nachrichten (BBC World Service, mit RSS-Fallback) ───

def _fetch_bbc_github(lang_code):
    """BBC World Service RSS-Links via GitHub Markdown."""
    if lang_code == "ar":
        url = "https://raw.githubusercontent.com/bbc/world-service-rss/main/arabic.md"
    elif lang_code == "fa":
        url = "https://raw.githubusercontent.com/bbc/world-service-rss/main/persian.md"
    else:
        return None
>>>>>>> Stashed changes
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Morgenbrief/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = resp.read().decode("utf-8", errors="replace")
<<<<<<< Updated upstream
    except Exception as e:
        print(f"BBC GitHub Fehler ({lang_code}): {e}", file=sys.stderr)
        return None, None
=======
        # Extrahiere erste RSS-URL aus dem Markdown
        rss_match = re.search(r'\((https?://feeds\.bbci\.co\.uk/[^)]+)\)', data)
        if rss_match:
            rss_url = rss_match.group(1)
            return _fetch_rss_headline(rss_url)
        # Fallback: Titel direkt aus Markdown
        match = re.search(r'## \[(.*?)\]\(.*?\)', data, re.DOTALL)
        if match:
            headline = match.group(1).strip()
            headline = headline.replace("&amp;", "&").replace("&quot;", '"')
            return headline[:300]
    except Exception as e:
        print(f"BBC GitHub Fehler ({lang_code}): {e}", file=sys.stderr)
    return None

def _fetch_rss_headline(rss_url):
    """Extrahiert erste Schlagzeile aus einem RSS-Feed."""
    try:
        req = urllib.request.Request(rss_url, headers={"User-Agent": "Morgenbrief/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = resp.read().decode("utf-8", errors="replace")
        titles = re.findall(r"<item>.*?<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>", data, re.DOTALL)
        if titles:
            headline = titles[0].strip()
            headline = headline.replace("&amp;", "&").replace("&quot;", '"').replace("&lt;", "<").replace("&gt;", ">")
            return headline[:300]
    except Exception:
        pass
    return None

# Direkte BBC RSS-Fallbacks (stabil, offiziell)
BBC_RSS_FALLBACKS = {
    "ar": "https://feeds.bbci.co.uk/arabic/rss.xml",
    "fa": "https://feeds.bbci.co.uk/persian/rss.xml",
}

def fetch_news_headline(lang_code):
    """Holt Schlagzeile: erst BBC GitHub, dann direkte BBC RSS als Fallback."""
    headline = _fetch_bbc_github(lang_code)
    if headline:
        return headline
    # Fallback: Direkte BBC RSS
    fallback_url = BBC_RSS_FALLBACKS.get(lang_code)
    if fallback_url:
        headline = _fetch_rss_headline(fallback_url)
        if headline:
            print(f"News via BBC RSS Fallback ({lang_code})", file=sys.stderr)
            return headline
    print(f"Keine News verfügbar ({lang_code})", file=sys.stderr)
    return None
>>>>>>> Stashed changes

    # Extrahiere die erste Zeile mit ## [Titel](Link)
    match = re.search(r'## \[(.*?)\]\((https?://[^)]+)\)', data, re.MULTILINE)
    if not match:
        # Fallback: nur den Titel aus der Zeile ohne Link (sollte nicht vorkommen)
        match = re.search(r'## \[(.*?)\]\(.*?\)', data, re.MULTILINE)
        if not match:
            print(f"Keine Schlagzeile in BBC {lang_code} gefunden", file=sys.stderr)
            return None, None
        headline = match.group(1).strip()
        article_url = None
    else:
        headline = match.group(1).strip()
        article_url = match.group(2).strip()

<<<<<<< Updated upstream
    article_text = ""
    if article_url:
        try:
            req = urllib.request.Request(article_url, headers={"User-Agent": "Morgenbrief/1.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                html = resp.read().decode("utf-8", errors="replace")
            # Suche nach dem ersten <p> mit ausreichend Text (ca. > 100 Zeichen)
            paragraphs = re.findall(r'<p[^>]*>(.*?)</p>', html, re.DOTALL)
            for para in paragraphs:
                clean = re.sub(r'<[^>]+>', ' ', para).strip()
                if len(clean) > 100:
                    article_text = clean[:800]  # Begrenzung
                    break
            if not article_text:
                # Fallback: Beschreibung aus der Markdown-Datei (die Zeile nach der Überschrift)
                lines = data.splitlines()
                for i, line in enumerate(lines):
                    if line.strip().startswith('## ['):
                        for j in range(i+1, min(i+10, len(lines))):
                            desc_line = lines[j].strip()
                            if desc_line and not desc_line.startswith('![') and not desc_line.startswith('_'):
                                article_text = desc_line[:500]
                                break
                        break
        except Exception as e:
            print(f"Artikel-Fetch Fehler ({lang_code}): {e}", file=sys.stderr)
=======
# ─── Musikbibliothek laden ───
>>>>>>> Stashed changes

    return headline, article_text

# ─── Musikbibliothek (aus Ihrer alten Version, unverändert) ───
MUSIC_LIBRARY_FILE = Path(__file__).parent / "all.txt"
_music_data = None

def _load_music_library():
    data = []
    if not MUSIC_LIBRARY_FILE.exists():
        return data
<<<<<<< Updated upstream
    for delim in ('\t', ','):
        try:
            with open(MUSIC_LIBRARY_FILE, "r", encoding="utf-8") as f:
                fl = f.readline()
                if not fl or "Album" not in fl:
                    continue
                f.seek(0)
                for row in csv.DictReader(f, delimiter=delim):
                    album, artist = row.get("Album","").strip(), row.get("Artist","").strip()
=======
    for delimiter in ('\t', ','):
        try:
            with open(MUSIC_LIBRARY_FILE, "r", encoding="utf-8") as f:
                first_line = f.readline()
                if not first_line or "Album" not in first_line:
                    continue
                f.seek(0)
                reader = csv.DictReader(f, delimiter=delimiter)
                for row in reader:
                    album = row.get("Album", "").strip()
                    artist = row.get("Artist", "").strip()
>>>>>>> Stashed changes
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
<<<<<<< Updated upstream
                    data.append({"artist":artist,"album":album,"plays":plays,"last_played":last_date,"rating":rating,"genre":row.get("Genre","").strip()})
            if data:
                print(f"Musikbibliothek: {len(data)} Einträge", file=sys.stderr)
=======
                    genre = row.get("Genre", "").strip()
                    data.append({
                        "artist": artist, "album": album, "plays": plays,
                        "last_played": last_date, "rating": rating, "genre": genre,
                    })
            if data:
                print(f"Musikbibliothek geladen: {len(data)} Einträge (Trennzeichen: {repr(delimiter)})", file=sys.stderr)
>>>>>>> Stashed changes
                break
        except Exception as e:
            print(f"Musikfehler ({repr(delim)}): {e}", file=sys.stderr)
    return data

_music_data = _load_music_library()

def _get_top_genres(limit=3):
    if not _music_data:
        return []
<<<<<<< Updated upstream
    gc = {}
    for e in _music_data:
        if e["genre"]:
            gc[e["genre"]] = gc.get(e["genre"],0) + e["plays"]
    return [g for g,_ in sorted(gc.items(), key=lambda x:x[1], reverse=True)[:limit]]
=======
    genre_playcount = {}
    for entry in _music_data:
        if entry["genre"]:
            genre_playcount[entry["genre"]] = genre_playcount.get(entry["genre"], 0) + entry["plays"]
    return [g for g, _ in sorted(genre_playcount.items(), key=lambda x: x[1], reverse=True)[:limit]]
>>>>>>> Stashed changes

def _get_high_rated_artists(threshold=80, limit=5):
    if not _music_data:
        return []
<<<<<<< Updated upstream
    sc = {}
    for e in _music_data:
        if e["rating"] >= threshold:
            sc[e["artist"]] = sc.get(e["artist"],0)+1
    return [a for a,_ in sorted(sc.items(), key=lambda x:x[1], reverse=True)[:limit]]
=======
    artist_scores = {}
    for entry in _music_data:
        if entry["rating"] >= threshold:
            artist_scores[entry["artist"]] = artist_scores.get(entry["artist"], 0) + 1
    return [a for a, _ in sorted(artist_scores.items(), key=lambda x: x[1], reverse=True)[:limit]]
>>>>>>> Stashed changes

def _get_similar_artists(artist_name, limit=3):
    if not _music_data:
        return []
<<<<<<< Updated upstream
    genres = {e["genre"] for e in _music_data if e["artist"]==artist_name and e["genre"]}
    if not genres:
        return []
    return list({e["artist"] for e in _music_data if e["artist"]!=artist_name and e["genre"] in genres})[:limit]
=======
    genres = {e["genre"] for e in _music_data if e["artist"] == artist_name and e["genre"]}
    if not genres:
        return []
    return list({e["artist"] for e in _music_data if e["artist"] != artist_name and e["genre"] in genres})[:limit]
>>>>>>> Stashed changes

def _select_album_of_the_day():
    """Wählt ein Album aus der Bibliothek (gewichtet nach Rating, Alter, Plays)."""
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

# ─── Entdeckungsvorschläge (minimal gehalten) ───
DISCOVERY_FILE = Path(__file__).parent / "discovery_albums.json"
_SEED_ALBUMS = [
    ("Kayhan Kalhor & Rembrandt Trio","Silence City"),("Tigran Hamasyan","A Fable"),
    ("Anouar Brahem","Thimar"),("Mohsen Namjoo","Toranj"),
    ("Mohammad Reza Shajarian","Ghame Eshgh"),("Grouper","Dragging a Dead Deer Up a Hill"),
    ("Midori Takada","Through the Looking Glass"),("Nils Frahm","Felt"),
    ("Arvo Pärt","Tabula Rasa"),("Vijay Iyer","Historicity"),
]

<<<<<<< Updated upstream
def _load_discovery_albums():
=======
# ─── Entdeckungsvorschläge (auto-generiert via Claude API) ───

DISCOVERY_FILE = Path(__file__).parent / "discovery_albums.json"

# Initiale Seed-Liste (wird beim ersten Lauf durch API-generierte ersetzt)
_SEED_ALBUMS = [
    ("Kayhan Kalhor & Rembrandt Trio", "Silence City"),
    ("Tigran Hamasyan", "A Fable"),
    ("Anouar Brahem", "Thimar"),
    ("Mohsen Namjoo", "Toranj"),
    ("Mohammad Reza Shajarian", "Ghame Eshgh"),
    ("Grouper", "Dragging a Dead Deer Up a Hill"),
    ("Midori Takada", "Through the Looking Glass"),
    ("Nils Frahm", "Felt"),
    ("Arvo Pärt", "Tabula Rasa"),
    ("Vijay Iyer", "Historicity"),
]

def _load_discovery_albums():
    """Lädt discovery_albums.json. Gibt (albums_list, needs_refresh) zurück."""
>>>>>>> Stashed changes
    if not DISCOVERY_FILE.exists():
        return [], True
    try:
        with open(DISCOVERY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        albums = data.get("albums", [])
        unseen = [a for a in albums if not a.get("suggested", False)]
<<<<<<< Updated upstream
        return albums, (not unseen)
    except Exception:
        return [], True
=======
        if not unseen:
            return albums, True  # Alle durch → refresh nötig
        return albums, False
    except Exception:
        return [], True

def _save_discovery_albums(albums, profile=None):
    """Speichert discovery_albums.json."""
    data = {
        "albums": albums,
        "generated_at": now_berlin().isoformat(),
    }
    if profile:
        data["generated_from"] = profile
    with open(DISCOVERY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def _generate_discovery_albums_via_api():
    """Generiert 20 neue Entdeckungsalben via Anthropic API basierend auf dem Musikprofil."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None

    top_genres = _get_top_genres(5)
    top_artists = _get_high_rated_artists(threshold=60, limit=10)
    library_artists = {e["artist"] for e in _music_data} if _music_data else set()

    prompt = f"""Ich suche 20 Alben-Empfehlungen die ich noch NICHT kenne.

Meine Top-Genres: {', '.join(top_genres)}
Meine Lieblingskünstler: {', '.join(top_artists)}

Regeln:
- KEINE Alben von Künstlern die ich schon höre (siehe Lieblingskünstler oben)
- Mischung aus: bekannten Klassikern die ich verpasst haben könnte, Geheimtipps, und Musik aus dem Iran/Zentralasien/arabischer Welt
- Vielfalt: nicht alles ein Genre
- Format: Antworte NUR mit einer JSON-Liste, kein anderer Text:
[{{"artist": "Name", "album": "Albumtitel"}}, ...]
"""

    payload = json.dumps({
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 1000,
        "messages": [{"role": "user", "content": prompt}]
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
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
        text = result["content"][0]["text"].strip()
        # JSON extrahieren (auch wenn in ```json ... ``` gewrappt)
        text = re.sub(r'^```json\s*', '', text)
        text = re.sub(r'\s*```


# ─── Tagesimpuls ───
>>>>>>> Stashed changes

def _save_discovery_albums(albums, profile=None):
    data = {"albums": albums, "generated_at": now_berlin().isoformat()}
    if profile:
        data["generated_from"] = profile
    with open(DISCOVERY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

<<<<<<< Updated upstream
def _generate_discovery_albums_via_api():
=======
    creative_pool = [
        "Entwickle einen Film oder scanne Negative.",
        "Schau einen persischen Film (z. B. von Panahi, Kiarostami, Farhadi oder Rasoulof).",
        "Nimm eine Mixtape-Seite auf.",
        "Schreibe handschriftlich einen Brief.",
        "Mache Skizzen oder zeichne.",
        "Übersetze ein Gedicht, das nicht für hochroth ist.",
        "Mach einen langen Spaziergang mit der Kamera.",
        "Improvisiere am Klavier – ganz ohne Übungsziel.",
        "Lies einen alten Text von dir und mache dir Notizen dazu.",
        "Koche etwas Neues – ein Rezept aus einer anderen Küche.",
        "Schicke eine Postkarte an jemanden.",
        "Mache Field Recordings (im Garten oder in der Umgebung).",
    ]
    creative_suggestion = random.choice(creative_pool)

    # 25% Chance: Entdeckungsalbum (nicht in Bibliothek), sonst aus Bibliothek
    if random.random() < 0.25:
        artist, album = _select_discovery_album()
        album_line = f"Album des Tages: {artist} — {album} (Entdeckung – noch nicht in deiner Bibliothek)"
    else:
        album_entry = _select_album_of_the_day()
        if album_entry:
            album_line = f"Album des Tages: {album_entry['artist']} — {album_entry['album']}"
            if album_entry["plays"] == 0:
                album_line += " (Noch nie gehört – vielleicht eine schöne Entdeckung?)"
            elif album_entry["rating"] >= 80:
                album_line += " (Du magst diesen Künstler – hör mal wieder rein!)"
            elif album_entry["last_played"] and (today.date() - album_entry["last_played"]).days > 90:
                album_line += " (Lange nicht gehört – Zeit für ein Revival.)"
        else:
            artist, album = _select_discovery_album()
            album_line = f"Album des Tages: {artist} — {album}"

    return f"""Heute ist {day_de}. Kleine Ideen für den Tag (wähle höchstens eine, wenn Zeit ist):
– Kreativ: {creative_suggestion}
– {album_line}
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
            pass
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
        word, meaning = word.strip(), meaning.strip()
        if not word or not meaning:
            continue
        if not any(w["word"] == word for w in memory.get(lang_code, [])):
            memory.setdefault(lang_code, []).append({
                "word": word, "meaning": meaning, "first_seen": today,
                "last_review": today, "interval": 1, "times_reviewed": 0,
            })
    save_vocab_memory(memory)

def update_reviewed_vocab(lang_code, reviewed_words, memory):
    today = now_berlin().isoformat()
    for word in reviewed_words:
        for entry in memory.get(lang_code, []):
            if entry["word"] == word:
                entry["last_review"] = today
                entry["times_reviewed"] += 1
                entry["interval"] = min(entry.get("interval", 1) * 2, 30)
                break
    save_vocab_memory(memory)

def generate_language_exercise():
    today = now_berlin()
    day_of_year = today.timetuple().tm_yday
    days_since_start = max(0, (today - LANG_START).days)
    week = days_since_start // 7

    if day_of_year % 2 == 0:
        language, lang_code = "Arabisch", "ar"
    else:
        language, lang_code = "Persisch", "fa"

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
Die folgenden Wörter sollen heute wiederholt werden. Baue sie in den Übungstext ein:
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
Wenn du im Übungstext ein Wort einführst, das über den Grundwortschatz hinausgeht:
1. Glossiere es sofort inline auf Deutsch in Klammern.
2. Füge am Ende des Textes eine Zeile ein: "NEUE VOKABELN: Wort (Bedeutung), Wort (Bedeutung)"
"""

    return {
        "language": language, "lang_code": lang_code, "level": level,
        "instructions": instructions, "topic": topic, "headline": headline,
        "news_source": news_source, "week": week,
        "repetition_prompt": repetition_prompt,
        "new_vocab_instruction": new_vocab_instruction,
        "memory": memory, "due_vocab": due_vocab,
    }


# ─── Claude aufrufen ───

def call_claude(kontext, fahrplan, aufgaben, kalender, wetter, impulse, lang_exercise):
>>>>>>> Stashed changes
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    top_genres = _get_top_genres(5)
    top_artists = _get_high_rated_artists(threshold=60, limit=10)
    library_artists = {e["artist"] for e in _music_data} if _music_data else set()

<<<<<<< Updated upstream
    prompt = (f"Ich suche 20 Alben-Empfehlungen die ich noch NICHT kenne.\n\n"
              f"Meine Top-Genres: {', '.join(top_genres)}\n"
              f"Meine Lieblingskünstler: {', '.join(top_artists)}\n\n"
              f"Regeln:\n"
              f"- KEINE Alben von Künstlern die ich schon höre\n"
              f"- Mischung aus: bekannten Klassikern, Geheimtipps, Musik aus Iran/Zentralasien/arabischer Welt\n"
              f"- Vielfalt: nicht alles ein Genre\n"
              f'- Antworte NUR mit JSON-Liste, kein anderer Text:\n'
              f'[{{"artist": "Name", "album": "Albumtitel"}}, ...]')
=======
    today = now_berlin().strftime("%A, %d. %B %Y")
    lang = lang_exercise
    script = 'arabischer' if lang['lang_code'] == 'ar' else 'persischer'
    dialect_rule = 'Fusha (MSA), kein Dialekt.' if lang['lang_code'] == 'ar' else 'Farsi-ye meyar, kein Slang.'

    if lang.get('headline'):
        news_prompt = f"""NACHRICHTEN (RTL, in Originalschrift):
Die folgende Schlagzeile von {lang['news_source']} in {script} Originalschrift wiedergeben.
Glossiere schwierige Wörter inline auf Deutsch in Klammern.
Danach in 2-3 einfachen Sätzen auf {lang['language']} zusammenfassen (Level {lang['level']}).
Schlagzeile: {lang['headline']}"""
    else:
        news_prompt = """NACHRICHTEN:
Keine aktuellen Nachrichten verfügbar. Schreibe einen kurzen Satz auf Deutsch."""

    lang_prompt = f"""SPRACHÜBUNG - TEXT (RTL, in Originalschrift):
Schreibe einen kurzen Übungstext auf {lang['language']} zum Thema "{lang['topic']}".
Regeln:
- 5-8 Sätze in {script} Schrift.
- {lang['instructions']}
- {dialect_rule}
- {lang['new_vocab_instruction']}
{lang['repetition_prompt']}

SPRACHÜBUNG - FRAGEN (LTR, auf Deutsch):
2-3 Verständnisfragen auf Deutsch zum obigen Text. Jede Frage in einer neuen Zeile.
Keine Originalschrift in diesem Abschnitt."""

    user_message = f"""Heute ist {today}.

WETTER:
{wetter}

TAGESIMPULS:
{impulse}

KONTEXT (enthält Format und Regeln - befolge sie exakt):
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
Schreibe den Morgenbrief exakt in dieser Struktur:
1. WETTER
2. HEUTE
3. IMPULS
4. PROJEKTE
5. ERLEDIGTES
6. AUSBLICK
7. SPRACHÜBUNG - TEXT (Übungstext in Originalschrift, RTL)
8. SPRACHÜBUNG - FRAGEN (Verständnisfragen auf Deutsch, LTR)
9. NACHRICHTEN (Schlagzeile + Zusammenfassung in Originalschrift, RTL)

WICHTIG: Verwende als Trennzeichen zwischen Wörtern in Sektionstiteln immer einen einfachen Bindestrich (-), NIEMALS einen Gedankenstrich.
Jede Sektion mit dem Namen als Überschrift in Großbuchstaben. Kein Markdown. Sachlich."""
>>>>>>> Stashed changes

    payload = json.dumps({
        "model": "claude-sonnet-4-20250514", "max_tokens": 1000,
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
<<<<<<< Updated upstream
        print(f"Discovery-Generierung fehlgeschlagen: {e}", file=sys.stderr)
    return None

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

# ─── Tagesimpuls ───
VORSCHLAEGE_FILE = Path(__file__).parent / "vorschlaege.json"

def _lade_vorschlagsquellen():
    try:
        with open(VORSCHLAEGE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}
=======
        sys.exit(f"Claude API Fehler: {e}")


def strip_markdown(text):
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'`(.+?)`', r'\1', text)
    text = re.sub(r'^\*\s+', '– ', text, flags=re.MULTILINE)
    return text


# ─── ePub erzeugen (mit robuster RTL/LTR Erkennung) ───

def create_epub(text, date_str):
    import zipfile
    from io import BytesIO

    title = f"Morgenbrief {date_str}"
    text = strip_markdown(text)
    # Normalisiere alle Dash-Varianten für zuverlässige Sektionserkennung
    text_normalized = _normalize_dashes(text)

    lines = text_normalized.strip().split("\n")
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

        if "SPRACHÜBUNG - TEXT" in upper or "SPRACHUEBUNG - TEXT" in upper:
            flush_block()
            current_rtl = True
            html_parts.append(f"<h2>{stripped}</h2>")
        elif "SPRACHÜBUNG - FRAGEN" in upper or "SPRACHUEBUNG - FRAGEN" in upper or stripped.startswith("FRAGEN:"):
            flush_block()
            current_rtl = False  # Fragen sind auf Deutsch → LTR
            html_parts.append(f"<h2>{stripped}</h2>")
        elif upper.strip().rstrip(":") == "NACHRICHTEN":
            flush_block()
            current_rtl = True  # Nachrichten enthalten arabische/persische Schrift → RTL
            html_parts.append(f"<h2>{stripped}</h2>")
        elif upper.strip().rstrip(":") in {"WETTER", "HEUTE", "IMPULS", "PROJEKTE", "ERLEDIGTES", "AUSBLICK"}:
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
        print("Keine News verfügbar.")

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
, '', text)
        raw = json.loads(text)
        # Gegen Bibliothek filtern
        albums = []
        for item in raw:
            artist = item.get("artist", "").strip()
            album = item.get("album", "").strip()
            if artist and album and artist not in library_artists:
                albums.append({"artist": artist, "album": album, "suggested": False})
        if albums:
            profile = {"top_genres": top_genres, "top_artists": top_artists}
            _save_discovery_albums(albums, profile)
            print(f"Discovery: {len(albums)} neue Alben generiert", file=sys.stderr)
            return albums
    except Exception as e:
        print(f"Discovery-Generierung fehlgeschlagen: {e}", file=sys.stderr)
    return None

def _select_discovery_album():
    """Wählt ein Entdeckungsalbum. Generiert neue wenn nötig."""
    albums, needs_refresh = _load_discovery_albums()

    if needs_refresh:
        new_albums = _generate_discovery_albums_via_api()
        if new_albums:
            albums = new_albums
        elif not albums:
            # Fallback auf Seed-Liste wenn API nicht verfügbar
            albums = [{"artist": a, "album": b, "suggested": False} for a, b in _SEED_ALBUMS]
            _save_discovery_albums(albums)

    unseen = [a for a in albums if not a.get("suggested", False)]
    if not unseen:
        unseen = albums  # Safety fallback

    pick = random.choice(unseen)
    # Als vorgeschlagen markieren
    for a in albums:
        if a["artist"] == pick["artist"] and a["album"] == pick["album"]:
            a["suggested"] = True
            break
    _save_discovery_albums(albums)
    return (pick["artist"], pick["album"])


# ─── Tagesimpuls ───
>>>>>>> Stashed changes

def generate_impulse():
    """Genau ein konkreter Vorschlag fuer heute - kurz, benannt, machbar.

    Die Vorschlaege stammen aus seinem eigenen Bestand: Buecher aus der
    Calibre-Bibliothek, Karten aus dem Anki-Deck, Alben aus der Mediathek.
    Nichts wird erfunden. Die Kategorie wechselt mit dem Wochentag, damit
    nicht jeden Tag dasselbe kommt.
    """
    today = now_berlin()
<<<<<<< Updated upstream
    day_de = {"Monday":"Montag","Tuesday":"Dienstag","Wednesday":"Mittwoch","Thursday":"Donnerstag",
              "Friday":"Freitag","Saturday":"Samstag","Sunday":"Sonntag"}.get(today.strftime("%A"), today.strftime("%A"))
    q = _lade_vorschlagsquellen()
    wd = today.weekday()   # 0 = Montag

    vorschlag = None

    # Nachschlagewerke, Zeitschriftenhefte und Harry Potter taugen nicht fuer
    # "eine Seite lesen" (08.10.2026: Persian-English Wiktionary dictionary).
    nicht_lesen = re.compile(r"dictionary|wiktionary|wörterbuch|lexikon|rowling|harry potter|"
                             r"arabic today|newsnet|review \d", re.I)
    buecher = [b for b in q.get("buecher", []) if not nicht_lesen.search(
        f"{b.get('titel', '')} {b.get('autor', '')}")]
    if wd in (0, 3) and buecher:
        b = random.choice(buecher)
        titel = b.get("titel", "").strip()
        autor = b.get("autor", "").strip()
        wie = autor and f"{titel} von {autor}" or titel
        vorschlag = f"Lies eine einzige Seite: {wie}. Eine Seite, nicht mehr."

    elif wd in (1, 4) and q.get("vokabeln"):
        drei = random.sample(q["vokabeln"], min(3, len(q["vokabeln"])))
        liste = ", ".join(f"{v['word']} ({v['meaning'][:40]})" for v in drei)
        vorschlag = f"Fünf Minuten Persisch: {liste}. Nur diese drei, laut lesen."

    elif wd == 2 and q.get("filme"):
        f = random.choice(q["filme"])
        vorschlag = f"Sieh heute Abend etwas: {f}."

    elif wd == 5:
        vorschlag = "Nimm dir dreißig Minuten und geh mit der Kamera raus. Zehn Bilder, dann Schluss."

    else:
        vorschlag = "Schreib heute zehn Zeilen, egal worüber. Handschriftlich, kein Bildschirm."

    # Album kommt zusaetzlich, das laeuft nebenbei
    if random.random() < 0.25:
        artist, album = _select_discovery_album()
        album_line = f"{artist} — {album} (Entdeckung, nicht in deiner Bibliothek)"
    else:
        entry = _select_album_of_the_day()
        if entry:
            album_line = f"{entry['artist']} — {entry['album']}"
            if entry["plays"] == 0:
                album_line += " (noch nie gehört)"
            elif entry["last_played"] and (today.date() - entry["last_played"]).days > 90:
                album_line += " (lange nicht gehört)"
        else:
            a, b = _select_discovery_album()
            album_line = f"{a} — {b}"
=======
    weekday = today.strftime("%A")
    day_de = {
        "Monday": "Montag", "Tuesday": "Dienstag", "Wednesday": "Mittwoch",
        "Thursday": "Donnerstag", "Friday": "Freitag", "Saturday": "Samstag",
        "Sunday": "Sonntag"
    }.get(weekday, weekday)

    creative_pool = [
        "Entwickle einen Film oder scanne Negative.",
        "Schau einen persischen Film (z. B. von Panahi, Kiarostami, Farhadi oder Rasoulof).",
        "Nimm eine Mixtape-Seite auf.",
        "Schreibe handschriftlich einen Brief.",
        "Mache Skizzen oder zeichne.",
        "Übersetze ein Gedicht, das nicht für hochroth ist.",
        "Mach einen langen Spaziergang mit der Kamera.",
        "Improvisiere am Klavier – ganz ohne Übungsziel.",
        "Lies einen alten Text von dir und mache dir Notizen dazu.",
        "Koche etwas Neues – ein Rezept aus einer anderen Küche.",
        "Schicke eine Postkarte an jemanden.",
        "Mache Field Recordings (im Garten oder in der Umgebung).",
    ]
    creative_suggestion = random.choice(creative_pool)

    # 25% Chance: Entdeckungsalbum (nicht in Bibliothek), sonst aus Bibliothek
    if random.random() < 0.25:
        artist, album = _select_discovery_album()
        album_line = f"Album des Tages: {artist} — {album} (Entdeckung – noch nicht in deiner Bibliothek)"
    else:
        album_entry = _select_album_of_the_day()
        if album_entry:
            album_line = f"Album des Tages: {album_entry['artist']} — {album_entry['album']}"
            if album_entry["plays"] == 0:
                album_line += " (Noch nie gehört – vielleicht eine schöne Entdeckung?)"
            elif album_entry["rating"] >= 80:
                album_line += " (Du magst diesen Künstler – hör mal wieder rein!)"
            elif album_entry["last_played"] and (today.date() - album_entry["last_played"]).days > 90:
                album_line += " (Lange nicht gehört – Zeit für ein Revival.)"
        else:
            artist, album = _select_discovery_album()
            album_line = f"Album des Tages: {artist} — {album}"

    return f"""Heute ist {day_de}. Kleine Ideen für den Tag (wähle höchstens eine, wenn Zeit ist):
– Kreativ: {creative_suggestion}
– {album_line}
Passe die Auswahl an deine Termine und das Wetter an. Wenn der Tag voll ist, lass die Vorschläge einfach weg."""
>>>>>>> Stashed changes

    return (f"Heute ist {day_de}.\n"
            f"EINE SACHE für heute: {vorschlag}\n"
            f"Nebenbei zu hören: {album_line}\n"
            f"Gib genau diesen einen Vorschlag wieder, formuliere ihn kurz und ohne Alternativen. "
            f"Biete nichts zusätzlich an. Wenn der Tag voll ist, sag das in einem Halbsatz.")

# ─── Sprachübung (mit Vokabelgedächtnis) ───
LANG_START = datetime(2026, 4, 5, tzinfo=BERLIN_TZ)
VOCAB_FILE = Path(__file__).parent / "vocab_memory.json"

def load_vocab_memory():
    if VOCAB_FILE.exists():
        try:
            with open(VOCAB_FILE,"r",encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
<<<<<<< Updated upstream
    return {"ar":[],"fa":[]}
=======
    return {"ar": [], "fa": []}
>>>>>>> Stashed changes

def save_vocab_memory(m):
    with open(VOCAB_FILE,"w",encoding="utf-8") as f:
        json.dump(m, f, ensure_ascii=False, indent=2)

BEKANNT_FILE = Path(__file__).parent / "bekannt_fa.json"

def load_bekannt(lc):
    """Woerter, die er aus Anki schon kann. Die sollen nicht als neu eingefuehrt werden."""
    if lc != "fa" or not BEKANNT_FILE.exists():
        return []
    try:
        with open(BEKANNT_FILE, "r", encoding="utf-8") as f:
            return [e["word"] for e in json.load(f) if e.get("word")]
    except Exception:
        return []

def get_due_vocab(lc, m):
    today = now_berlin().date()
    return [e for e in m.get(lc,[]) if (today - datetime.fromisoformat(e["last_review"]).date()).days >= e.get("interval",1)]

def add_new_vocab(lc, words, m):
    today = now_berlin().isoformat()
<<<<<<< Updated upstream
    for w, meaning in words:
        w, meaning = w.strip(), meaning.strip()
        if w and meaning and not any(x["word"]==w for x in m.get(lc,[])):
            m.setdefault(lc,[]).append({"word":w,"meaning":meaning,"first_seen":today,"last_review":today,"interval":1,"times_reviewed":0})
    save_vocab_memory(m)
=======
    for word, meaning in words:
        word, meaning = word.strip(), meaning.strip()
        if not word or not meaning:
            continue
        if not any(w["word"] == word for w in memory.get(lang_code, [])):
            memory.setdefault(lang_code, []).append({
                "word": word, "meaning": meaning, "first_seen": today,
                "last_review": today, "interval": 1, "times_reviewed": 0,
            })
    save_vocab_memory(memory)
>>>>>>> Stashed changes

def update_reviewed_vocab(lc, reviewed, m):
    today = now_berlin().isoformat()
<<<<<<< Updated upstream
    for w in reviewed:
        for e in m.get(lc,[]):
            if e["word"]==w:
                e["last_review"]=today
                e["times_reviewed"]+=1
                e["interval"]=min(e.get("interval",1)*2,30)
=======
    for word in reviewed_words:
        for entry in memory.get(lang_code, []):
            if entry["word"] == word:
                entry["last_review"] = today
                entry["times_reviewed"] += 1
                entry["interval"] = min(entry.get("interval", 1) * 2, 30)
>>>>>>> Stashed changes
                break
    save_vocab_memory(m)

def generate_language_exercise():
    today = now_berlin()
<<<<<<< Updated upstream
    doy = today.timetuple().tm_yday
    dss = max(0, (today - LANG_START).days)
    week = dss // 7
    language, lc = ("Persisch", "fa")   # nur noch Persisch, Arabisch entfaellt
    if week<2:
        level, instr = "A2 (einfach)", "Sehr einfache Sätze. Grundvokabular: Familie, Essen, Wetter, Tagesablauf. Präsens und einfache Vergangenheit."
    elif week<6:
        level, instr = "B1 (mittel)", "Längere Sätze möglich. Themen: Reisen, Arbeit, Meinungen, Nachrichten. Konjunktiv, Relativsätze erlaubt."
    elif week<12:
        level, instr = "B1+ (gehoben)", "Komplexere Strukturen. Themen: Kultur, Politik, Literatur. Passiv, indirekte Rede."
    else:
        level, instr = "B2 (fortgeschritten)", "Anspruchsvoller Text. Zeitungssprache, abstrakte Themen, idiomatische Wendungen."
=======
    day_of_year = today.timetuple().tm_yday
    days_since_start = max(0, (today - LANG_START).days)
    week = days_since_start // 7

    if day_of_year % 2 == 0:
        language, lang_code = "Arabisch", "ar"
    else:
        language, lang_code = "Persisch", "fa"
>>>>>>> Stashed changes

    mem = load_vocab_memory()
    due = get_due_vocab(lc, mem)
    bekannt = load_bekannt(lc)
    rep = ""
    if due:
        vl = "\n".join([f"  - {v['word']} ({v['meaning']})" for v in due])
        rep = f"\nVOKABELWIEDERHOLUNG:\nDiese Wörter sollen heute wiederholt werden. Baue sie in den Übungstext ein:\n{vl}\n"

    headline, article = fetch_bbc_news_with_article(lc)
    if headline:
        news_content = f"Schlagzeile: {headline}\n\nArtikeltext:\n{article[:800]}" if article else f"Schlagzeile: {headline}"
    else:
        news_content = None

    topics = ["Tagesablauf und Routine","Essen und Kochen","Eine Reise beschreiben","Familie und Freunde",
              "Das Wetter","Einkaufen auf dem Markt","Ein Buch oder Film beschreiben","Die eigene Stadt vorstellen",
              "Arbeit und Beruf","Kindheitserinnerungen","Natur und Umwelt","Musik und Kunst","Gesundheit und Sport","Politik und Gesellschaft"]

<<<<<<< Updated upstream
    return {"language":language,"lang_code":lc,"level":level,"instructions":instr,
            "topic":topics[dss%len(topics)],"headline":headline,"news_text":news_content,
            "week":week,"repetition_prompt":rep,
            "new_vocab_instruction":"\nWICHTIG: Neue Vokabeln inline glossieren. Am Ende eine Zeile: \"NEUE VOKABELN: Wort (Bedeutung), Wort (Bedeutung)\"\n",
            "memory":mem,"due_vocab":due,"bekannt":bekannt}
=======
    repetition_prompt = ""
    if due_vocab:
        vocab_list = "\n".join([f"  - {v['word']} ({v['meaning']})" for v in due_vocab])
        repetition_prompt = f"""
VOKABELWIEDERHOLUNG (Spaced Repetition):
Die folgenden Wörter sollen heute wiederholt werden. Baue sie in den Übungstext ein:
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
Wenn du im Übungstext ein Wort einführst, das über den Grundwortschatz hinausgeht:
1. Glossiere es sofort inline auf Deutsch in Klammern.
2. Füge am Ende des Textes eine Zeile ein: "NEUE VOKABELN: Wort (Bedeutung), Wort (Bedeutung)"
"""

    return {
        "language": language, "lang_code": lang_code, "level": level,
        "instructions": instructions, "topic": topic, "headline": headline,
        "news_source": news_source, "week": week,
        "repetition_prompt": repetition_prompt,
        "new_vocab_instruction": new_vocab_instruction,
        "memory": memory, "due_vocab": due_vocab,
    }


# ─── Claude aufrufen ───
>>>>>>> Stashed changes

# ─── Claude aufrufen ───
def call_claude(kontext, fahrplan, aufgaben, kalender, wetter, impulse, lang_exercise):
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        sys.exit("ANTHROPIC_API_KEY nicht gesetzt")
    today = now_berlin().strftime("%A, %d. %B %Y")
    lang = lang_exercise
    script = 'arabischer' if lang['lang_code']=='ar' else 'persischer'
    dialect = 'Fusha (MSA), kein Dialekt.' if lang['lang_code']=='ar' else 'Farsi-ye meyar, kein Slang.'
    vok = 'WICHTIG: Arabischen Text MIT VOLLSTÄNDIGER VOKALISIERUNG (tashkīl/harakat auf jedem Wort) schreiben. ' if lang['lang_code']=='ar' else ''

    if lang.get('headline'):
<<<<<<< Updated upstream
        news_p = (f"NACHRICHTEN (RTL, in Originalschrift):\n"
                  f"Die folgende Nachricht von BBC in {script} Originalschrift wiedergeben. {vok}\n"
                  f"Zunächst die Schlagzeile, dann den Artikeltext sinngemäß in 3-4 Sätzen zusammenfassen. {vok}\n"
                  f"Glossiere schwierige Wörter inline auf Deutsch in Klammern (passend zu Level {lang['level']}).\n\n"
                  f"Schlagzeile: {lang['headline']}\n\n"
                  f"Artikeltext (zur Zusammenfassung):\n{lang['news_text']}\n")
    else:
        news_p = "NACHRICHTEN:\nKeine aktuellen Nachrichten verfügbar. Schreibe einen kurzen Satz auf Deutsch."

    bek = lang.get("bekannt") or []
    if bek:
        probe = ", ".join(bek[:400])
        bekannt_p = ("BEKANNTER WORTSCHATZ: Diese Woerter kennt er bereits aus seinem Anki-Deck. "
                     "Verwende sie gern im Text, fuehre sie aber NICHT als neue Vokabel auf. "
                     "Neue Vokabeln muessen ausserhalb dieser Liste liegen:\n" + probe + "\n")
    else:
        bekannt_p = ""
    lang_p = (f"SPRACHÜBUNG - TEXT (RTL, in Originalschrift):\n"
              f"Schreibe einen kurzen Übungstext auf {lang['language']} zum Thema \"{lang['topic']}\".\n"
              f"Regeln:\n- 5-8 Sätze in {script} Schrift. {vok}\n- {lang['instructions']}\n- {dialect}\n"
              f"- {lang['new_vocab_instruction']}\n{lang['repetition_prompt']}\n"
              f"{bekannt_p}\n"
              f"SPRACHÜBUNG - FRAGEN (LTR, auf Deutsch):\n"
              f"2-3 Verständnisfragen auf Deutsch zum obigen Text. Jede Frage in einer neuen Zeile.\n"
              f"Keine Originalschrift in diesem Abschnitt.")

    msg = (f"Heute ist {today}.\n\nWETTER:\n{wetter}\n\nTAGESIMPULS:\n{impulse}\n\n"
           f"KONTEXT (enthält Format und Regeln - befolge sie exakt):\n{kontext}\n\n"
           f"OFFENE AUFGABEN:\n{aufgaben}\n\nKALENDER (nächste 3 Tage):\n{kalender}\n\n"
           f"FAHRPLAN (nur als Hintergrund):\n{fahrplan}\n\n{lang_p}\n\n{news_p}\n\n"
           f"AUFTRAG:\nSchreibe den Morgenbrief exakt in dieser Struktur:\n"
           f"1. WETTER\n2. HEUTE\n3. IMPULS\n4. PROJEKTE\n5. ERLEDIGTES\n6. AUSBLICK\n"
           f"7. SPRACHÜBUNG - TEXT (Übungstext in Originalschrift, RTL)\n"
           f"8. SPRACHÜBUNG - FRAGEN (Verständnisfragen auf Deutsch, LTR)\n"
           f"9. NACHRICHTEN (Schlagzeile + Zusammenfassung in Originalschrift, RTL)\n\n"
           f"WICHTIG: Verwende in Sektionstiteln immer einfache Bindestriche (-), NIEMALS Gedankenstriche.\n"
           f"Jede Sektion als Überschrift in Großbuchstaben. Kein Markdown. Sachlich.")
=======
        news_prompt = f"""NACHRICHTEN (RTL, in Originalschrift):
Die folgende Schlagzeile von {lang['news_source']} in {script} Originalschrift wiedergeben.
Glossiere schwierige Wörter inline auf Deutsch in Klammern.
Danach in 2-3 einfachen Sätzen auf {lang['language']} zusammenfassen (Level {lang['level']}).
Schlagzeile: {lang['headline']}"""
    else:
        news_prompt = """NACHRICHTEN:
Keine aktuellen Nachrichten verfügbar. Schreibe einen kurzen Satz auf Deutsch."""

    lang_prompt = f"""SPRACHÜBUNG - TEXT (RTL, in Originalschrift):
Schreibe einen kurzen Übungstext auf {lang['language']} zum Thema "{lang['topic']}".
Regeln:
- 5-8 Sätze in {script} Schrift.
- {lang['instructions']}
- {dialect_rule}
- {lang['new_vocab_instruction']}
{lang['repetition_prompt']}

SPRACHÜBUNG - FRAGEN (LTR, auf Deutsch):
2-3 Verständnisfragen auf Deutsch zum obigen Text. Jede Frage in einer neuen Zeile.
Keine Originalschrift in diesem Abschnitt."""

    user_message = f"""Heute ist {today}.

WETTER:
{wetter}

TAGESIMPULS:
{impulse}

KONTEXT (enthält Format und Regeln - befolge sie exakt):
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
Schreibe den Morgenbrief exakt in dieser Struktur:
1. WETTER
2. HEUTE
3. IMPULS
4. PROJEKTE
5. ERLEDIGTES
6. AUSBLICK
7. SPRACHÜBUNG - TEXT (Übungstext in Originalschrift, RTL)
8. SPRACHÜBUNG - FRAGEN (Verständnisfragen auf Deutsch, LTR)
9. NACHRICHTEN (Schlagzeile + Zusammenfassung in Originalschrift, RTL)

WICHTIG: Verwende als Trennzeichen zwischen Wörtern in Sektionstiteln immer einen einfachen Bindestrich (-), NIEMALS einen Gedankenstrich.
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
>>>>>>> Stashed changes

    payload = json.dumps({"model":"claude-sonnet-4-20250514","max_tokens":3000,
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

<<<<<<< Updated upstream
# ─── ePub erzeugen (robuste RTL/LTR Erkennung, wie in alter Version) ───
=======

# ─── ePub erzeugen (mit robuster RTL/LTR Erkennung) ───

>>>>>>> Stashed changes
def create_epub(text, date_str):
    import zipfile
    from io import BytesIO
    title = f"Morgenbrief {date_str}"
    text = strip_markdown(text)
<<<<<<< Updated upstream
    text = _normalize_dashes(text)

    lines = text.strip().split("\n")
    html_parts, current_block, current_rtl = [], [], False
=======
    # Normalisiere alle Dash-Varianten für zuverlässige Sektionserkennung
    text_normalized = _normalize_dashes(text)

    lines = text_normalized.strip().split("\n")
    html_parts = []
    current_block = []
    current_rtl = False
>>>>>>> Stashed changes

    def flush():
        nonlocal current_rtl
        if current_block:
            c = "<br/>".join(current_block)
            if current_rtl:
                html_parts.append(f'<p dir="rtl" style="text-align:right;font-size:1.1em;line-height:1.8;">{c}</p>')
            else:
                html_parts.append(f"<p>{c}</p>")
            current_block.clear()

    for line in lines:
<<<<<<< Updated upstream
        s = line.strip()
        u = s.upper()
        if "SPRACHÜBUNG - TEXT" in u or "SPRACHUEBUNG - TEXT" in u:
            flush()
            current_rtl = True
            html_parts.append(f"<h2>{s}</h2>")
        elif "SPRACHÜBUNG - FRAGEN" in u or "SPRACHUEBUNG - FRAGEN" in u or s.startswith("FRAGEN:"):
            flush()
            current_rtl = False
            html_parts.append(f"<h2>{s}</h2>")
        elif u.strip().rstrip(":") == "NACHRICHTEN":
            flush()
            current_rtl = True
            html_parts.append(f"<h2>{s}</h2>")
        elif u.strip().rstrip(":") in {"WETTER","HEUTE","IMPULS","PROJEKTE","ERLEDIGTES","AUSBLICK"}:
            flush()
=======
        stripped = line.strip()
        upper = stripped.upper()

        if "SPRACHÜBUNG - TEXT" in upper or "SPRACHUEBUNG - TEXT" in upper:
            flush_block()
            current_rtl = True
            html_parts.append(f"<h2>{stripped}</h2>")
        elif "SPRACHÜBUNG - FRAGEN" in upper or "SPRACHUEBUNG - FRAGEN" in upper or stripped.startswith("FRAGEN:"):
            flush_block()
            current_rtl = False  # Fragen sind auf Deutsch → LTR
            html_parts.append(f"<h2>{stripped}</h2>")
        elif upper.strip().rstrip(":") == "NACHRICHTEN":
            flush_block()
            current_rtl = True  # Nachrichten enthalten arabische/persische Schrift → RTL
            html_parts.append(f"<h2>{stripped}</h2>")
        elif upper.strip().rstrip(":") in {"WETTER", "HEUTE", "IMPULS", "PROJEKTE", "ERLEDIGTES", "AUSBLICK"}:
            flush_block()
>>>>>>> Stashed changes
            current_rtl = False
            html_parts.append(f"<h2>{s}</h2>")
        elif s == "":
            flush()
        else:
            current_block.append(s)
    flush()

    xhtml = (f'<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE html>\n'
             f'<html xmlns="http://www.w3.org/1999/xhtml"><head><title>{title}</title>\n'
             f'<style>body{{font-family:serif;font-size:1em;line-height:1.5;margin:1em;}}'
             f'h1{{font-size:1.4em;margin-bottom:0.3em;}}h2{{font-size:1.1em;margin-top:1em;margin-bottom:0.3em;text-transform:uppercase;letter-spacing:0.05em;}}'
             f'p{{margin-bottom:0.6em;}}</style></head><body>\n<h1>{title}</h1>\n'
             + "\n".join(html_parts) + '\n</body></html>')

    container = ('<?xml version="1.0" encoding="UTF-8"?>\n<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">'
                 '\n<rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles></container>')
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    opf = (f'<?xml version="1.0" encoding="UTF-8"?>\n<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="uid">'
           f'\n<metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:identifier id="uid">morgenbrief-{date_str}</dc:identifier>'
           f'<dc:title>{title}</dc:title><dc:language>de</dc:language><dc:creator>Claude</dc:creator>'
           f'<meta property="dcterms:modified">{ts}</meta></metadata>'
           f'\n<manifest><item id="content" href="content.xhtml" media-type="application/xhtml+xml"/>'
           f'<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/></manifest>'
           f'\n<spine><itemref idref="content"/></spine></package>')
    nav = (f'<?xml version="1.0" encoding="UTF-8"?>\n<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">'
           f'<head><title>Navigation</title></head><body>\n<nav epub:type="toc"><h1>Inhalt</h1><ol><li><a href="content.xhtml">{title}</a></li></ol></nav>'
           f'\n</body></html>')

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

# ─── Versand: per Mail an MORGENBRIEF_TO, ohne diese Variable an den Kindle ───
def _brief_html(text):
    import html as _h
    teile = []
    for block in re.split(r"\n\s*\n", text.strip()):
        zeilen = [_h.escape(z) for z in block.splitlines()]
        teile.append('<p dir="auto">' + '<br>'.join(zeilen) + '</p>')
    return ('<html><body style="font-family:Georgia,serif;font-size:17px;line-height:1.5;'
            'max-width:40em;margin:auto">' + ''.join(teile) + '</body></html>')


def send_to_kindle(epub_path, text=None, anhaenge=None):
    ga, gp = os.environ.get("GMAIL_ADDRESS"), os.environ.get("GMAIL_APP_PASSWORD")
    als_mail = bool(os.environ.get("MORGENBRIEF_TO"))
    ka = os.environ.get("MORGENBRIEF_TO") or os.environ.get("KINDLE_EMAIL")
    if not all([ga,gp,ka]):
        sys.exit("Gmail-Zugang oder Empfänger fehlt")
    msg = MIMEMultipart("mixed")
    msg["From"] = ga
    msg["To"] = ka
    msg["Subject"] = f"Morgenbrief {now_berlin().strftime('%d.%m.%Y')}" if als_mail else "Morgenbrief"
    if als_mail and text:
        alt = MIMEMultipart("alternative")
        alt.attach(MIMEText(text, "plain", "utf-8"))
        alt.attach(MIMEText(_brief_html(text), "html", "utf-8"))
        msg.attach(alt)
    else:
        msg.attach(MIMEText("","plain"))
    with open(epub_path,"rb") as f:
        part = MIMEBase("application","epub+zip")
        part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition",f"attachment; filename={os.path.basename(epub_path)}")
        msg.attach(part)
    for pfad in (anhaenge or []):
        with open(pfad, "rb") as f:
            teil = MIMEBase("application", "octet-stream")
            teil.set_payload(f.read())
        encoders.encode_base64(teil)
        teil.add_header("Content-Disposition", f"attachment; filename={os.path.basename(str(pfad))}")
        msg.attach(teil)
    with smtplib.SMTP_SSL("smtp.gmail.com",465) as smtp:
        smtp.login(ga,gp)
        smtp.sendmail(ga,ka,msg.as_string())
    print(f"Morgenbrief an {ka} gesendet")

# ─── Main ───
def main():
    repo = Path(__file__).parent
    kontext = (repo/"kontext.md").read_text(encoding="utf-8")
    fahrplan = (repo/"fahrplan.md").read_text(encoding="utf-8")
    aufgaben = (repo/"aufgaben.md").read_text(encoding="utf-8")

    # ICAL_URL kann mehrere, durch Semikolon getrennte URLs enthalten
    ical_urls = os.environ.get("ICAL_URL", "")
    kalender = fetch_calendar(ical_urls) if ical_urls else "[Keine Kalender-URL]"
    wetter = fetch_weather()
    impulse = generate_impulse()
    lang_ex = generate_language_exercise()

    print(f"Morgenbrief wird geschrieben ({now_berlin().strftime('%d.%m.%Y %H:%M')} Berliner Zeit)...")
    print(f"Sprachübung: {lang_ex['language']} (Level {lang_ex['level']}, Thema: {lang_ex['topic']})")
    if lang_ex.get('headline'):
        print(f"News: {lang_ex['headline'][:60]}...")
    else:
        print("Keine News verfügbar.")

    text = call_claude(kontext, fahrplan, aufgaben, kalender, wetter, impulse, lang_ex)

    # Vokabelgedächtnis
    vm = re.search(r"NEUE VOKABELN:\s*(.*?)(?:\n|$)", text, re.IGNORECASE)
    if vm:
        pairs = re.findall(r"([^\s,]+)\s*\(([^)]+)\)", vm.group(1))
        if pairs:
            add_new_vocab(lang_ex["lang_code"], pairs, lang_ex["memory"])
        text = re.sub(r"NEUE VOKABELN:.*\n?", "", text, flags=re.IGNORECASE)
    due_w = [v["word"] for v in lang_ex.get("due_vocab",[])]
    reviewed = [w for w in due_w if w in text]
    if reviewed:
        update_reviewed_vocab(lang_ex["lang_code"], reviewed, lang_ex["memory"])

    epub = create_epub(text, now_berlin().strftime("%Y-%m-%d"))
    send_to_kindle(epub, text)

if __name__ == "__main__":
    main()
