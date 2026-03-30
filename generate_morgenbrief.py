#!/usr/bin/env python3
"""
Morgenbrief: Täglicher Tagesplan via Claude → ePub → Kindle
"""

import os
import sys
import json
import smtplib
import urllib.request
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
from pathlib import Path

# ─── Kalender parsen (ics ohne externe Abhängigkeiten) ───

def fetch_calendar(ical_url):
    """Holt iCal-Daten und extrahiert Termine der nächsten 14 Tage."""
    try:
        req = urllib.request.Request(ical_url, headers={"User-Agent": "Morgenbrief/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        return f"[Kalender konnte nicht geladen werden: {e}]"

    import re
    events = []
    now = datetime.now(timezone.utc)
    horizon = now + timedelta(days=14)

    for block in re.findall(r"BEGIN:VEVENT(.*?)END:VEVENT", data, re.DOTALL):
        summary = ""
        dtstart_str = ""
        location = ""

        m = re.search(r"SUMMARY:(.*?)[\r\n]", block)
        if m:
            summary = m.group(1).strip()
        m = re.search(r"DTSTART[^:]*:(.*?)[\r\n]", block)
        if m:
            dtstart_str = m.group(1).strip()
        m = re.search(r"LOCATION:(.*?)[\r\n]", block)
        if m:
            location = m.group(1).strip().replace("\\n", ", ").replace("\\,", ",")

        # Datum parsen
        dt = None
        try:
            if "T" in dtstart_str:
                dt = datetime.strptime(dtstart_str[:15], "%Y%m%dT%H%M%S")
            elif len(dtstart_str) >= 8:
                dt = datetime.strptime(dtstart_str[:8], "%Y%m%d")
        except ValueError:
            continue

        if dt:
            dt_aware = dt.replace(tzinfo=timezone.utc)
            if now - timedelta(days=1) <= dt_aware <= horizon:
                date_str = dt.strftime("%a %d.%m. %H:%M") if "T" in dtstart_str else dt.strftime("%a %d.%m.")
                loc_str = f" ({location})" if location else ""
                events.append((dt, f"- {date_str}: {summary}{loc_str}"))

    events.sort(key=lambda x: x[0])
    if not events:
        return "[Keine Termine in den nächsten 14 Tagen gefunden]"
    return "\n".join(e[1] for e in events)


# ─── Wetter holen ───

def fetch_weather():
    """Holt Wetter für Leipzig via Open-Meteo (kein API Key nötig)."""
    url = (
        "https://api.open-meteo.com/v1/forecast?"
        "latitude=51.34&longitude=12.37"
        "&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,weathercode"
        "&timezone=Europe/Berlin&forecast_days=2"
    )
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read())
        daily = data["daily"]

        wmo_codes = {
            0: "Klar", 1: "Überwiegend klar", 2: "Teils bewölkt", 3: "Bewölkt",
            45: "Nebel", 48: "Reifnebel", 51: "Leichter Niesel", 53: "Niesel",
            55: "Starker Niesel", 61: "Leichter Regen", 63: "Regen", 65: "Starker Regen",
            71: "Leichter Schnee", 73: "Schnee", 75: "Starker Schnee",
            80: "Regenschauer", 81: "Starke Schauer", 95: "Gewitter"
        }

        lines = []
        for i in range(min(2, len(daily["time"]))):
            code = daily["weathercode"][i]
            desc = wmo_codes.get(code, f"Code {code}")
            tmin = daily["temperature_2m_min"][i]
            tmax = daily["temperature_2m_max"][i]
            rain = daily["precipitation_sum"][i]
            label = "Heute" if i == 0 else "Morgen"
            rain_str = f", {rain}mm Niederschlag" if rain > 0 else ""
            lines.append(f"- {label}: {desc}, {tmin}–{tmax}°C{rain_str}")

        return "\n".join(lines)
    except Exception as e:
        return f"[Wetter nicht verfügbar: {e}]"


# ─── Claude aufrufen ───

def call_claude(kontext, fahrplan, aufgaben, kalender, wetter):
    """Ruft die Anthropic API auf und lässt Claude den Morgenbrief schreiben."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        sys.exit("ANTHROPIC_API_KEY nicht gesetzt")

    today = datetime.now().strftime("%A, %d. %B %Y")
    weekday = datetime.now().strftime("%A")

    user_message = f"""Heute ist {today}.

## Kontext
{kontext}

## Fahrplan (Gesamtübersicht)
{fahrplan}

## Aktuelle Aufgaben
{aufgaben}

## Kalender (nächste 14 Tage)
{kalender}

## Wetter Leipzig
{wetter}

---

Schreibe jetzt den Morgenbrief für heute. Orientiere dich an den Anweisungen im Kontext-Dokument. Beachte besonders:
- Was steht heute konkret an? (Kalender + Wochentag-Routine)
- Welche Deadlines rücken näher?
- Was wurde seit dem letzten Update erledigt (abgehakte Aufgaben)?
- Was ist überfällig oder braucht Aufmerksamkeit?
- Ein kurzer, ehrlicher Schluss.

Kein Markdown verwenden. Schreibe in einfachem Fließtext mit Absätzen. Nutze Spiegelstriche (–) für Listen. Unter 500 Wörter."""

    payload = json.dumps({
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 1500,
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


# ─── ePub erzeugen ───

def create_epub(text, date_str):
    """Erzeugt eine minimale ePub-Datei aus dem Morgenbrief-Text."""
    import zipfile
    from io import BytesIO

    title = f"Morgenbrief {date_str}"

    # HTML aus Text
    paragraphs = text.strip().split("\n\n")
    html_body = ""
    for p in paragraphs:
        lines = p.strip().split("\n")
        formatted_lines = []
        for line in lines:
            if line.strip().startswith("–") or line.strip().startswith("-"):
                formatted_lines.append(f"<br/>{line.strip()}")
            else:
                formatted_lines.append(line.strip())
        html_body += f"<p>{'<br/>'.join(formatted_lines)}</p>\n"

    content_xhtml = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>{title}</title>
<style>
body {{ font-family: serif; font-size: 1em; line-height: 1.6; margin: 1em; }}
h1 {{ font-size: 1.3em; margin-bottom: 0.5em; }}
p {{ margin-bottom: 0.8em; }}
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
    <meta property="dcterms:modified">{datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")}</meta>
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
    """Versendet die ePub-Datei per Gmail SMTP an die Kindle-Adresse."""
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

    print(f"✓ Morgenbrief an {kindle_addr} gesendet")


# ─── Main ───

def main():
    repo_dir = Path(__file__).parent

    # Dateien lesen
    kontext = (repo_dir / "kontext.md").read_text(encoding="utf-8")
    fahrplan = (repo_dir / "fahrplan.md").read_text(encoding="utf-8")
    aufgaben = (repo_dir / "aufgaben.md").read_text(encoding="utf-8")

    # Kalender holen
    ical_url = os.environ.get("ICAL_URL", "")
    if ical_url:
        kalender = fetch_calendar(ical_url)
    else:
        kalender = "[Keine Kalender-URL konfiguriert]"

    # Wetter holen
    wetter = fetch_weather()

    # Claude fragen
    print("→ Claude schreibt den Morgenbrief...")
    text = call_claude(kontext, fahrplan, aufgaben, kalender, wetter)
    print(f"→ {len(text)} Zeichen generiert")

    # ePub erzeugen
    date_str = datetime.now().strftime("%Y-%m-%d")
    epub_path = create_epub(text, date_str)
    print(f"→ {epub_path} erstellt")

    # An Kindle senden
    send_to_kindle(epub_path)


if __name__ == "__main__":
    main()
