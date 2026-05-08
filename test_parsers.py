"""Unit-Tests für die Parser anhand fester Beispiel-Inputs.
Aufruf: python test_parsers.py (im selben Verzeichnis wie stellen_check.py)"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from stellen_check import (
    matches_filters, KultweetParser, UniBwMParser,
    WHITELIST, BLACKLIST,
)
from xml.etree import ElementTree as ET

# ─── Test 1: H-Soz-Kult Atom-Parsing ───
HSK_SAMPLE = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>H-Soz-Kult Stellenangebote</title>
  <entry>
    <title>Job: 12x 0,65 Wiss. Mitarb. (Doktorand:in) "Inszenierung religiöser Atmosphäre in antiken Kulturen" (Philipps-Univ. Marburg)</title>
    <summary>Marburg, 01.11.2026-31.10.2029, Philipps-Universität Marburg, Bewerbungsschluss: 12.06.2026 Ausschreibung von 12 Teilzeitstellen am GRK 2844</summary>
    <updated>2026-05-07T19:32:18+00:00</updated>
    <link rel="alternate" href="https://www.hsozkult.de/job/id/job-162236"/>
    <id>https://www.hsozkult.de/job/id/job-162236</id>
  </entry>
  <entry>
    <title>Job: 1 Postdoc "EurAsian Transformations" (Central European Univ., Vienna)</title>
    <summary>Wien, , Central European University, Bewerbungsschluss: 30.05.2026</summary>
    <updated>2026-05-05T16:41:18+00:00</updated>
    <link rel="alternate" href="https://www.hsozkult.de/job/id/job-162202"/>
    <id>https://www.hsozkult.de/job/id/job-162202</id>
  </entry>
  <entry>
    <title>Job: 1 Wiss. Mitarb. (Postdoc) "Iranistik / Persische Lyrik" (LMU München)</title>
    <summary>München, Persische Klassiker und moderne Lyrik im Fokus.</summary>
    <updated>2026-05-08T10:00:00+00:00</updated>
    <link rel="alternate" href="https://www.hsozkult.de/job/id/job-fake-99999"/>
    <id>https://www.hsozkult.de/job/id/job-fake-99999</id>
  </entry>
</feed>
"""

ns = {"atom": "http://www.w3.org/2005/Atom"}
root = ET.fromstring(HSK_SAMPLE)
hsk_jobs = []
for entry in root.findall("atom:entry", ns):
    title = entry.find("atom:title", ns).text.strip()
    summary = entry.find("atom:summary", ns).text.strip()
    job_id = entry.find("atom:id", ns).text.strip()
    hsk_jobs.append({"title": title, "summary": summary, "id": job_id})

print("=== TEST 1: H-Soz-Kult Atom-Parsing ===")
assert len(hsk_jobs) == 3, f"Erwartet 3 Jobs, bekam {len(hsk_jobs)}"
print(f"  ✓ 3 Entries geparst")

results = []
for j in hsk_jobs:
    full = f"{j['title']} {j['summary']}"
    matched = matches_filters(full)
    results.append((j['title'][:60], matched))
    print(f"  [{ '✓' if matched else '✗'}] {j['title'][:80]}")

# ─── Test 2: kultweet HTML-Parser ───
KULTWEET_SAMPLE = """
<html><body>
<ul>
<li>
<a href="https://www.fu-berlin.de/path" title="Link zu #247733 - Wiss. Mitarbeiter*in (Praedoc) (m/w/d) mit 65%, Ostasien und Vorderer Orient, Institut für Iranistik, befristet | Berlin - Freie Universität Berlin">
Arbeitgeber: Freie Universität Berlin Wiss. Mitarbeiter*in (Praedoc) (m/w/d) mit 65%, Ostasien und Vorderer Orient, Institut für Iranistik, befristet | Berlin Abgeschlossenes wiss. Hochschulstudium (Master/Magister/Diplom) Ort: Berlin | Frist: 19.05.2026
</a>
</li>
<li>
<a href="https://example.com/path" title="Link zu #245277 - Projekt Manager/in (m/w/d) für EU-Förderprojekte Circular Migration | München - Münchner Forum für Dialog">
Arbeitgeber: Münchner Forum für Dialog gGmbH Projekt Manager/in für Circular Migration. Master in Migration. Ort: München | Frist: ohne Bewerbungsfrist
</a>
</li>
<li>
<a href="https://example.com/social" title="Link zu #999999 - Sozialarbeit Pflicht: Soziale Arbeit erforderlich | Berlin">
Sozialpädagoge gesucht, Studium der Sozialen Arbeit erforderlich. Ort: Berlin | Frist: 01.06.2026
</a>
</li>
</ul>
</body></html>
"""

print()
print("=== TEST 2: kultweet HTML-Parser ===")
parser = KultweetParser()
parser.feed(KULTWEET_SAMPLE)
print(f"  Anzahl gefundener Jobs: {len(parser.jobs)}")
for j in parser.jobs:
    full = f"{j['title']} {j['summary']}"
    matched = matches_filters(full)
    print(f"  [{ '✓' if matched else '✗'}] id={j['id']} title={j['title'][:80]}")

# ─── Test 3: UniBwM Parser ───
UNIBWM_SAMPLE = """
<html><body>
<a href="https://www.unibw.de/stellenausschreibungen/wm/bw-wm-e13-wirtschaft-und-recht.pdf">
<h2>Fakultät für Betriebswirtschaft - Institut für Ökonomie und Recht</h2>
Wissenschaftliche Mitarbeiter (m/w/d) E13 TVöD - Wirtschaft und Arbeitsrecht
</a>
<a href="https://www.unibw.de/stellenausschreibungen/wm/arabistik-fake.pdf">
<h2>Fakultät für Sprachen - Institut für Arabistik</h2>
Wissenschaftliche Mitarbeiter (m/w/d) E14 TVöD - Arabistik mit Schwerpunkt Persisch
</a>
</body></html>
"""
print()
print("=== TEST 3: UniBwM Parser ===")
parser = UniBwMParser()
parser.feed(UNIBWM_SAMPLE)
print(f"  Anzahl: {len(parser.jobs)}")
for j in parser.jobs:
    full = f"{j['title']} {j['summary']}"
    matched = matches_filters(full)
    print(f"  [{ '✓' if matched else '✗'}] {j['title'][:120]}")

# ─── Test 4: Filter-Logik ───
print()
print("=== TEST 4: Filter-Logik ===")
test_cases = [
    ("Praedoc Iranistik FU Berlin", True, "Whitelist 'iranistik'"),
    ("Postdoc Klassische Archäologie altgriechische Quellen", False, "Blacklist 'altgriech'"),
    ("Wissenschaftlicher Mitarbeiter Maschinenbau", False, "Kein Whitelist-Match"),
    ("Wiss. Mitarb. Verfassungsschutz Auswertung Islamismus", True, "Whitelist 'verfassungsschutz' + 'islamismus'"),
    ("Persische Lyrik Übersetzung Volontariat Verlag", True, "Mehrere Whitelist-Treffer"),
    ("Sozialpädagoge: Studium der Sozialen Arbeit erforderlich. Persisch von Vorteil.", False, "Blacklist sticht trotz Whitelist 'persisch'"),
    ("Studentische Hilfskraft Iranistik 8h/Woche", False, "Blacklist 'studentische hilfskraft'"),
    ("Postdoc Zentralasien Tadschikistan-Forschung", True, "Whitelist 'zentralasien' + 'tadschik'"),
    ("Projekt Manager Circular Migration Maghreb", True, "Whitelist 'circular migration' + 'maghreb'"),
]
fail_count = 0
for text, expected, note in test_cases:
    actual = matches_filters(text)
    mark = "✓" if actual == expected else "✗ FEHLER"
    if actual != expected:
        fail_count += 1
    print(f"  {mark} expected={expected} got={actual} | {text[:60]} | {note}")

print()
print("=== Zusammenfassung ===")
print(f"Whitelist: {len(WHITELIST)} Begriffe, Blacklist: {len(BLACKLIST)} Begriffe")
if fail_count == 0:
    print("Alle Tests grün ✓")
else:
    print(f"FEHLER: {fail_count} Tests fehlgeschlagen")
    sys.exit(1)
