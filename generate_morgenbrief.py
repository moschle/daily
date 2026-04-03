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
    """Holt Tageswetter für einen Ort."""
    url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat}&longitude={lon}"
        f"&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,weathercode"
        f"&hourly=temperature_2m,precipitation"
        f"&timezone=Europe/Berlin&forecast_days=1"
    )
    codes = {
        0: "Klar", 1: "Überwiegend klar", 2: "Teils bewölkt", 3: "Bewölkt",
        45: "Nebel", 48: "Reifnebel", 51: "Leichter Niesel", 53: "Niesel",
        55: "Starker Niesel", 61: "Leichter Regen", 63: "Regen", 65: "Starker Regen",
        71: "Leichter Schnee", 73: "Schnee", 75: "Starker Schnee",
        80: "Regenschauer", 81: "Starke Schauer", 95: "Gewitter"
    }
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read())
        d = data["daily"]
        desc = codes.get(d["weathercode"][0], f"Code {d['weathercode'][0]}")
        rain = d["precipitation_sum"][0]
        rain_str = f", {rain}mm Niederschlag" if rain and rain > 0 else ""

        # Aktuelle Temperatur aus hourly (nächste volle Stunde)
        current_hour = now_berlin().hour
        hourly_temps = data.get("hourly", {}).get("temperature_2m", [])
        current_temp = ""
        if hourly_temps and current_hour < len(hourly_temps):
            current_temp = f" (jetzt {hourly_temps[current_hour]:.0f}°C)"

        return f"{name}: {desc}, {d['temperature_2m_min'][0]:.0f}–{d['temperature_2m_max'][0]:.0f}°C{current_temp}{rain_str}"
    except Exception:
        return f"{name}: [nicht verfügbar]"


def fetch_weather():
    roitzsch = fetch_weather_for_location(51.62, 12.25, "Roitzsch")
    leipzig = fetch_weather_for_location(51.34, 12.37, "Leipzig")
    return f"{roitzsch}\n{leipzig}"


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

def call_claude(kontext, fahrplan, aufgaben, kalender, wetter, impulse):
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        sys.exit("ANTHROPIC_API_KEY nicht gesetzt")

    today = now_berlin().strftime("%A, %d. %B %Y")

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

AUFTRAG:
Schreibe den Morgenbrief exakt in der Struktur die im Kontext-Dokument definiert ist:
1. WETTER — die Wetterdaten oben einfach klar wiedergeben
2. HEUTE — nur Termine mit Label [HEUTE]. Daneben die 2–3 wichtigsten Aufgaben.
3. IMPULS — wähle EINEN Vorschlag aus dem Tagesimpuls, passend zu Wochentag und Wetter. Nicht die ganze Liste wiedergeben. Formuliere den Vorschlag als beiläufigen Satz, nicht als Befehl.
4. PROJEKTE — was heute ein guter Tag für wäre (kurz, nach Terminen einschätzen)
5. ERLEDIGTES — nur wenn es welches gibt
6. AUSBLICK — Termine mit Label [MORGEN] und [ÜBERMORGEN], nahende Deadlines. Max 2 Sätze.

Jede Sektion mit dem Namen als Überschrift (ohne Formatierung, einfach in Großbuchstaben).
Kein Markdown. Keine Vermutungen. Sachlich. Unter 350 Wörter."""

    payload = json.dumps({
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 1200,
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
    section_names = {"WETTER", "HEUTE", "IMPULS", "PROJEKTE", "ERLEDIGTES", "AUSBLICK"}

    def flush_block():
        if current_block:
            content = "<br/>".join(current_block)
            html_parts.append(f"<p>{content}</p>")
            current_block.clear()

    for line in lines:
        stripped = line.strip()
        if stripped in section_names or (stripped and stripped.rstrip(":") in section_names):
            flush_block()
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

    print(f"Morgenbrief wird geschrieben ({now_berlin().strftime('%d.%m.%Y %H:%M')} Berliner Zeit)...")
    text = call_claude(kontext, fahrplan, aufgaben, kalender, wetter, impulse)

    date_str = now_berlin().strftime("%Y-%m-%d")
    epub_path = create_epub(text, date_str)
    send_to_kindle(epub_path)


if __name__ == "__main__":
    main()
