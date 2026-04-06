#!/usr/bin/env python3
import os, sys, json, re, smtplib, urllib.request, csv, random, html
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
from pathlib import Path
from zoneinfo import ZoneInfo
import requests

BERLIN_TZ = ZoneInfo("Europe/Berlin")
def now_berlin(): return datetime.now(BERLIN_TZ)

# ------------------------------------------------------------
# KALENDER PARSEN (NUR REGEX, mit Debug)
# ------------------------------------------------------------
def fetch_calendar(ical_url):
    if not ical_url:
        print("DEBUG: ICAL_URL ist leer", file=sys.stderr)
        return "[Keine Kalender-URL]"
    
    print(f"DEBUG: Lade Kalender von {ical_url[:80]}...", file=sys.stderr)
    try:
        resp = requests.get(ical_url, timeout=15, headers={"User-Agent": "Morgenbrief/1.0"})
        resp.raise_for_status()
        data = resp.text
    except Exception as e:
        print(f"DEBUG: Kalender-Fehler: {e}", file=sys.stderr)
        return f"[Kalender konnte nicht geladen werden: {e}]"
    
    # Ersten 1000 Zeichen zur Kontrolle ausgeben
    print(f"DEBUG: iCal Anfang:\n{data[:1000]}", file=sys.stderr)
    
    # Normalisiere Zeilenumbrüche
    data = data.replace('\r\n', '\n').replace('\r', '\n')
    
    events = []
    today_berlin = now_berlin().replace(hour=0, minute=0, second=0, microsecond=0)
    horizon = today_berlin + timedelta(days=3)
    
    # Finde alle VEVENT-Blöcke
    blocks = re.findall(r"BEGIN:VEVENT(.*?)END:VEVENT", data, re.DOTALL)
    print(f"DEBUG: {len(blocks)} VEVENT-Blöcke gefunden", file=sys.stderr)
    
    for idx, block in enumerate(blocks):
        # Extrahiere SUMMARY
        m = re.search(r"SUMMARY:(.*?)[\n]", block, re.DOTALL)
        summary = m.group(1).strip() if m else ""
        # Extrahiere DTSTART (egal ob mit TZID oder VALUE=DATE)
        m = re.search(r"DTSTART[^:]*:(.*?)[\n]", block, re.DOTALL)
        dtstart_str = m.group(1).strip() if m else ""
        # Extrahiere LOCATION
        m = re.search(r"LOCATION:(.*?)[\n]", block, re.DOTALL)
        location = m.group(1).strip().replace("\\n", ", ").replace("\\,", ",") if m else ""
        
        if not dtstart_str:
            print(f"DEBUG: Block {idx} hat kein DTSTART, überspringe", file=sys.stderr)
            continue
        
        is_utc = dtstart_str.endswith('Z')
        if is_utc:
            dtstart_str = dtstart_str[:-1]
        
        dt = None
        is_allday = False
        try:
            if 'T' in dtstart_str:
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
            print(f"DEBUG: Event hinzugefügt: {summary[:50]}", file=sys.stderr)
    
    result = "\n".join(events) if events else "[Keine Termine in den nächsten 3 Tagen]"
    print(f"DEBUG: Kalender-Events: {len(events)}", file=sys.stderr)
    return result

# ------------------------------------------------------------
# NACHRICHTEN (BBC GitHub Markdown mit Debug)
# ------------------------------------------------------------
def fetch_bbc_news(lang_code):
    urls = {
        "ar": "https://raw.githubusercontent.com/bbc/world-service-rss/main/arabic.md",
        "fa": "https://raw.githubusercontent.com/bbc/world-service-rss/main/persian.md"
    }
    url = urls.get(lang_code)
    if not url:
        print(f"DEBUG: Keine URL für {lang_code}", file=sys.stderr)
        return None, None
    
    print(f"DEBUG: Lade BBC News von {url}", file=sys.stderr)
    try:
        resp = requests.get(url, timeout=10, headers={"User-Agent": "Morgenbrief/1.0"})
        resp.raise_for_status()
        content = resp.text
        print(f"DEBUG: BBC Datei geladen, Länge {len(content)}", file=sys.stderr)
        
        # Suche nach der ersten Zeile, die '## [' enthält (auch nach Leerzeichen)
        lines = content.splitlines()
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith('## ['):
                # Titel extrahieren
                match = re.search(r'## \[(.*?)\]\(.*?\)', stripped)
                if match:
                    headline = match.group(1).strip()
                    print(f"DEBUG: Headline gefunden: {headline[:60]}", file=sys.stderr)
                    # Beschreibung: nächste nicht-leere Zeile, die nicht mit '![' oder '_' beginnt
                    description = ""
                    for j in range(i+1, min(i+10, len(lines))):
                        desc_line = lines[j].strip()
                        if desc_line and not desc_line.startswith('![') and not desc_line.startswith('_'):
                            description = desc_line[:500]
                            break
                    return headline, description
        print("DEBUG: Keine Überschrift im BBC Markdown gefunden", file=sys.stderr)
        return None, None
    except Exception as e:
        print(f"DEBUG: BBC Fehler: {e}", file=sys.stderr)
        return None, None

# ------------------------------------------------------------
# FORCIERT LTR FÜR FRAGEN (erkennt "Verständnisfragen:" und ähnliches)
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
        r'^Verständnisfragen',   # wichtig: exakt das, was Claude schreibt
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

# ------------------------------------------------------------
# VEREINFACHTE HAUPTFUNKTION (nur das Nötigste für den Test)
# ------------------------------------------------------------
def main():
    print("DEBUG: Starte Morgenbrief", file=sys.stderr)
    
    # Lies die Secrets aus der Umgebung (für GitHub Action)
    ical_url = os.environ.get("ICAL_URL", "")
    print(f"DEBUG: ICAL_URL vorhanden: {bool(ical_url)}", file=sys.stderr)
    
    kalender = fetch_calendar(ical_url)
    print(f"DEBUG: Kalenderausgabe:\n{kalender}", file=sys.stderr)
    
    # Test der News-Funktion für beide Sprachen
    for lang in ['ar', 'fa']:
        h, d = fetch_bbc_news(lang)
        print(f"DEBUG: News {lang}: {h[:50] if h else 'keine'}", file=sys.stderr)
    
    # Simuliere einen Text mit Verständnisfragen (wie Claude schreibt)
    test_text = """SPRACHÜBUNG - TEXT
... arabischer Text ...
SPRACHÜBUNG - FRAGEN
Verständnisfragen:
1. Was bedeutet das?
2. Wie geht es weiter?
NACHRICHTEN
..."""
    
    forced = force_ltr_on_questions(test_text)
    print("DEBUG: Ergebnis force_ltr_on_questions:", file=sys.stderr)
    print(forced, file=sys.stderr)
    
    # Hier würde der eigentliche Claude-Aufruf folgen, aber für den Debug reicht's

if __name__ == "__main__":
    main()
