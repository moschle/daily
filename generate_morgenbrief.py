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
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
from pathlib import Path

# Berlin timezone offset (MESZ = +2, MEZ = +1)
# Simple DST detection: last Sunday March → last Sunday October
def _berlin_offset():
    """Returns Berlin UTC offset as timedelta."""
    now_utc = datetime.now(timezone.utc)
    year = now_utc.year
    # Last Sunday in March
    mar31 = datetime(year, 3, 31)
    dst_start = mar31 - timedelta(days=(mar31.weekday() + 1) % 7)
    dst_start = dst_start.replace(hour=1, tzinfo=timezone.utc)
    # Last Sunday in October
    oct31 = datetime(year, 10, 31)
    dst_end = oct31 - timedelta(days=(oct31.weekday() + 1) % 7)
    dst_end = dst_end.replace(hour=1, tzinfo=timezone.utc)
    if dst_start <= now_utc < dst_end:
        return timedelta(hours=2)  # MESZ
    return timedelta(hours=1)  # MEZ

BERLIN_OFFSET = _berlin_offset()
BERLIN_TZ = timezone(BERLIN_OFFSET)


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
    horizon = today_berlin + timedelta(days=3)  # heute + 2 weitere Tage

    for block in re.findall(r"BEGIN:VEVENT(.*?)END:VEVENT", data, re.DOTALL):
        summary = ""
        dtstart_str = ""
        location = ""
        is_utc = False

        m = re.search(r"SUMMARY:(.*?)[\r\n]", block)
        if m:
            summary = m.group(1).strip()
        m = re.search(r"DTSTART[^:]*:(.*?)[\r\n]", block)
        if m:
            dtstart_str = m.group(1).strip()
        # Check if DTSTART has TZID or ends with Z
        dtstart_line_m = re.search(r"DTSTART([^:]*):.*?[\r\n]", block)
        dtstart_params = dtstart_line_m.group(1) if dtstart_line_m else ""
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

        # Convert to Berlin time
        if is_allday:
            dt_berlin = dt.replace(tzinfo=BERLIN_TZ)
        elif is_utc:
            dt_berlin = dt.replace(tzinfo=timezone.utc).astimezone(BERLIN_TZ)
        elif "Europe/Berlin" in dtstart_params or "Europe%2FBerlin" in dtstart_params:
            dt_berlin = dt.replace(tzinfo=BERLIN_TZ)
        else:
            # Assume Berlin time for events without explicit timezone (Google Cal default)
            dt_berlin = dt.replace(tzinfo=BERLIN_TZ)

        if today_berlin <= dt_berlin < horizon:
            if is_allday:
                date_str = dt_berlin.strftime("%a %d.%m.")
            else:
                date_str = dt_berlin.strftime("%a %d.%m. %H:%M")
            loc_str = f" ({location})" if location else ""

            # Tag-Label für Sortierung
            day_diff = (dt_berlin.date() - today_berlin.date()).days
            tag_label = ["HEUTE", "MORGEN", "ÜBERMORGEN"][day_diff] if day_diff < 3 else ""

            events.append((dt_berlin, tag_label, f"  [{tag_label}] {date_str}: {summary}{loc_str}"))

    events.sort(key=lambda x: x[0])
    if not events:
        return "[Keine Termine in den nächsten 3 Tagen]"
    return "\n".join(e[2] for e in events)


# ─── Wetter holen ───

def fetch_weather_for_location(lat, lon, name):
    """Holt detailliertes Tageswetter für einen Ort mit Niederschlag nach Tageszeit."""
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

        # Temperatur und Niederschlag nach Tageszeit
        hourly_temps = h.get("temperature_2m", [])
        hourly_precip = h.get("precipitation", [])
        hourly_prob = h.get("precipitation_probability", [])
        hourly_codes = h.get("weathercode", [])

        # Zeitfenster: Nacht 0-5, Morgen 6-9, Vormittag 10-12, Nachmittag 13-17, Abend 18-23
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
                # Find the most severe weather code in this slot
                max_code = max(slot_codes_list) if slot_codes_list else 0
                precip_desc = wmo_codes.get(max_code, "Niederschlag")
                avg_prob = int(sum(slot_probs) / len(slot_probs)) if slot_probs else 0
                if slot_precip > 0.1:
                    precip_parts.append(f"{slot_name}: {precip_desc} ({slot_precip:.1f}mm, {avg_prob}%)")
                elif avg_prob > 30:
                    precip_parts.append(f"{slot_name}: mögl. {precip_desc} ({avg_prob}%)")

        # Nachttemperatur (Minimum der Stunden 0-5)
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
    # Nur Leipzig — Roitzsch ist 30km entfernt, Wetter praktisch identisch
    leipzig = fetch_weather_for_location(51.34, 12.37, "Leipzig/Roitzsch")
    return leipzig


# ─── Nachrichten für Sprachübung holen ───

def fetch_news_headline(lang_code):
    """Holt eine aktuelle Schlagzeile für die Sprachübung."""
    if lang_code == "ar":
        # Al Jazeera Arabic RSS
        url = "https://www.aljazeera.net/aljazeerarss/a7c186be-1baa-4bd4-9d80-a84db769f779/73d0e1b4-532f-45ef-b135-bfdff8b8cab9"
    else:
        # Tehran Times / IRNA English (for topic extraction)
        url = "https://www.tehrantimes.com/rss"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Morgenbrief/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = resp.read().decode("utf-8", errors="replace")
        # Extract first <title> from RSS items (skip channel title)
        titles = re.findall(r"<item>.*?<title>(?:<\!\[CDATA\[)?(.*?)(?:\]\]>)?</title>", data, re.DOTALL)
        if titles:
            # Clean HTML entities
            headline = titles[0].strip()
            headline = headline.replace("&amp;", "&").replace("&quot;", '"').replace("&lt;", "<").replace("&gt;", ">")
            return headline[:300]
    except Exception:
        pass
    return None


# ─── Sprachübung generieren ───

LANG_START = datetime(2026, 4, 5, tzinfo=BERLIN_TZ)

def generate_language_exercise():
    """Bestimmt Sprache (Arabisch/Persisch) und Schwierigkeitsgrad für den Tag."""
    today = now_berlin()
    day_of_year = today.timetuple().tm_yday
    days_since_start = max(0, (today - LANG_START).days)
    week = days_since_start // 7

    # Gerader Tag = Arabisch, ungerader Tag = Persisch
    if day_of_year % 2 == 0:
        language = "Arabisch"
        lang_code = "ar"
    else:
        language = "Persisch"
        lang_code = "fa"

    # Schwierigkeitsstufe steigt über Wochen
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

    # Aktuelle Nachricht holen (zusätzlich zum Übungsthema)
    headline = fetch_news_headline(lang_code)
    news_source = ("Al Jazeera" if lang_code == "ar" else "Tehran Times") if headline else None

    # Thema rotiert (für strukturierte Übung)
    fallback_topics = [
        "Tagesablauf und Routine", "Essen und Kochen", "Eine Reise beschreiben",
        "Familie und Freunde", "Das Wetter", "Einkaufen auf dem Markt",
        "Ein Buch oder Film beschreiben", "Die eigene Stadt vorstellen",
        "Arbeit und Beruf", "Kindheitserinnerungen", "Natur und Umwelt",
        "Musik und Kunst", "Gesundheit und Sport", "Politik und Gesellschaft",
    ]
    topic = fallback_topics[days_since_start % len(fallback_topics)]

    return {
        "language": language,
        "lang_code": lang_code,
        "level": level,
        "instructions": instructions,
        "topic": topic,
        "headline": headline,
        "news_source": news_source,
        "week": week,
    }


# ─── Tagesimpuls generieren ───

def generate_impulse():
    """Gibt dem Prompt kontextsensitive Vorschläge statt einer festen Liste."""
    today = now_berlin()
    weekday = today.strftime("%A")  # Monday, Tuesday, etc.
    day_de = {
        "Monday": "Montag", "Tuesday": "Dienstag", "Wednesday": "Mittwoch",
        "Thursday": "Donnerstag", "Friday": "Freitag", "Saturday": "Samstag",
        "Sunday": "Sonntag"
    }.get(weekday, weekday)
    month = today.month
    day_of_year = today.timetuple().tm_yday

    # Rotate through different creative suggestions using day of year
    creative_pools = [
        "Einen Film entwickeln oder Negative scannen",
        "Einen persischen Film schauen (z.B. Panahi, Kiarostami, Farhadi, Rasoulof)",
        "Eine Mixtape-Seite aufnehmen",
        "Einen Brief schreiben (handschriftlich)",
        "Skizzen machen oder zeichnen",
        "Ein Gedicht übersetzen, das nicht für hochroth ist",
        "Einen langen Spaziergang mit Kamera machen",
        "Etwas am Klavier improvisieren, ohne Übungsziel",
        "Einen alten Text von dir lesen und dazu Notizen machen",
        "Etwas Neues kochen — ein Rezept aus einer anderen Küche",
        "Eine Postkarte an jemanden schicken",
        "Feldaufnahmen machen (Garten, Umgebung)",
    ]

    album_pools = [
        "Ahmad Jamal — The Awakening",
        "Kayhan Kalhor & Rembrandt Trio — Silence City",
        "Tigran Hamasyan — A Fable",
        "Sadegh Nojouki — Safar",
        "Avishai Cohen — From Darkness",
        "Anouar Brahem — Thimar",
        "Nils Frahm — Felt",
        "Vijay Iyer — Historicity",
        "Shabaka Hutchings — Afrikan Culture",
        "Aziza Mustafa Zadeh — Shamans",
        "Arvo Pärt — Tabula Rasa",
        "Alva Noto & Ryuichi Sakamoto — Vrioon",
        "Nusrat Fateh Ali Khan — Mustt Mustt",
        "Sussan Deyhim — Madman of God",
        "Bill Evans — Waltz for Debby",
    ]

    creative_today = creative_pools[day_of_year % len(creative_pools)]
    album_today = album_pools[day_of_year % len(album_pools)]

    return f"""Heute ist {day_de}. Tagesvorschläge (nimm EINEN, nicht alle):
– Kreativ: {creative_today}
– Album des Tages: {album_today}
Wähle passend zum Wochentag, Wetter und Terminen aus. Wenn der Tag voll ist, lass die Vorschläge weg."""


# ─── Claude aufrufen ───

def call_claude(kontext, fahrplan, aufgaben, kalender, wetter, impulse, lang_exercise):
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        sys.exit("ANTHROPIC_API_KEY nicht gesetzt")

    today = now_berlin().strftime("%A, %d. %B %Y")

    lang = lang_exercise
    script = 'arabischer' if lang['lang_code'] == 'ar' else 'persischer'
    dialect_rule = 'Fusha (MSA), kein Dialekt.' if lang['lang_code'] == 'ar' else 'Farsi-ye meyar, kein Slang.'

    lang_prompt = f"""SPRACHÜBUNG ({lang['language']}, Level {lang['level']}, Woche {lang['week']+1}):
Schreibe einen kurzen Übungstext auf {lang['language']} zum Thema "{lang['topic']}".
Regeln:
- 5–8 Sätze in {script} Schrift.
- {lang['instructions']}
- {dialect_rule}
- Wenn ein Wort über Grundwortschatz hinausgeht: sofort in Klammern auf Deutsch erklären.
- KEIN Transliteration. Nur Originalschrift + deutsche Glossen in Klammern.
- Am Ende: 2–3 Verständnisfragen auf Deutsch zum Text."""

    # Nachrichtenblock (zusätzlich zur Übung)
    news_prompt = ""
    if lang.get('headline'):
        news_prompt = f"""\nNACHRICHTEN (von {lang['news_source']}):
Schreibe unter der Überschrift NACHRICHTEN die folgende Schlagzeile in {script} Originalschrift.
Glossiere schwierige Wörter inline auf Deutsch in Klammern.
Fasse dann in 2–3 einfachen Sätzen auf {lang['language']} zusammen, worum es geht (Level {lang['level']}).
Schlagzeile: {lang['headline']}"""

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
1. WETTER — die Wetterdaten oben einfach klar wiedergeben
2. HEUTE — nur Termine mit Label [HEUTE]. Daneben die 2–3 wichtigsten Aufgaben.
3. IMPULS — wähle EINEN Vorschlag aus dem Tagesimpuls, passend zu Wochentag und Wetter. Nicht die ganze Liste wiedergeben. Formuliere den Vorschlag als beiläufigen Satz, nicht als Befehl.
4. PROJEKTE — was heute ein guter Tag für wäre (kurz, nach Terminen einschätzen)
5. ERLEDIGTES — nur wenn es welches gibt
6. AUSBLICK — Termine mit Label [MORGEN] und [ÜBERMORGEN], nahende Deadlines. Max 2 Sätze.
7. SPRACHÜBUNG — den Übungstext gemäß den Anweisungen oben generieren. In Originalschrift. Neue Vokabeln inline in Klammern auf Deutsch glossieren. Am Ende 2–3 Verständnisfragen auf Deutsch.
8. NACHRICHTEN — falls Nachrichtenanweisungen oben vorhanden: Schlagzeile in Originalschrift + Zusammenfassung. Sonst weglassen.

Jede Sektion mit dem Namen als Überschrift (ohne Formatierung, einfach in Großbuchstaben).
Kein Markdown. Keine Vermutungen. Sachlich. Morgenbrief-Teil unter 350 Wörter, Sprachübung zusätzlich."""

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
    """Entfernt Markdown-Formatierung als Fallback."""
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'`(.+?)`', r'\1', text)
    text = re.sub(r'^\*\s+', '– ', text, flags=re.MULTILINE)
    return text


# ─── ePub erzeugen ───

def create_epub(text, date_str):
    import zipfile
    from io import BytesIO

    title = f"Morgenbrief {date_str}"
    text = strip_markdown(text)

    # Sektionen erkennen und als HTML-Überschriften formatieren
    lines = text.strip().split("\n")
    html_parts = []
    current_block = []
    section_names = {"WETTER", "HEUTE", "IMPULS", "PROJEKTE", "ERLEDIGTES", "AUSBLICK", "SPRACHÜBUNG", "NACHRICHTEN"}
    rtl_section = False  # Track if we're in the SPRACHÜBUNG section

    def flush_block():
        if current_block:
            content = "<br/>".join(current_block)
            if rtl_section:
                html_parts.append(f'<p dir="rtl" style="text-align: right; font-size: 1.1em; line-height: 1.8;">{content}</p>')
            else:
                html_parts.append(f"<p>{content}</p>")
            current_block.clear()

    for line in lines:
        stripped = line.strip()
        if stripped in section_names or (stripped and stripped.rstrip(":") in section_names):
            flush_block()
            section_key = stripped.rstrip(":")
            rtl_section = (section_key in ("SPRACHÜBUNG", "NACHRICHTEN"))
            html_parts.append(f"<h2>{stripped}</h2>")
        elif stripped == "":
            flush_block()
        elif stripped.startswith("–") or stripped.startswith("-"):
            current_block.append(stripped)
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


# ─── Per Mail an Kindle schicken ───

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
    text = call_claude(kontext, fahrplan, aufgaben, kalender, wetter, impulse, lang_exercise)

    date_str = now_berlin().strftime("%Y-%m-%d")
    epub_path = create_epub(text, date_str)
    send_to_kindle(epub_path)


if __name__ == "__main__":
    main()
