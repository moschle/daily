#!/usr/bin/env python3
"""Vier Aenderungen am Morgenbrief:

1. Standort umschaltbar - Leipzig als Voreinstellung, ueber die Datei
   /automat/standort.txt oder die Variable STANDORT auf einen anderen Ort.
2. Kalender getrennt: eigene Termine (Moritz, SM) gegenueber fremden,
   die nur der Abstimmung dienen.
3. Tagesimpuls: statt einer Ideenliste genau ein konkreter, kurzer Vorschlag,
   gezogen aus seinem eigenen Bestand - Buch, Vokabelkarten, Album, Film.
4. Buchliste aus der Calibre-Bibliothek als Quelle fuer den Lesevorschlag.
"""
import ast
import json
import pathlib
import re
import sqlite3
import sys

REPO = pathlib.Path.home() / "Projects/daily"
p = REPO / "generate_morgenbrief.py"
s = p.read_text(encoding="utf-8")

# ── 1. Standort ───────────────────────────────────────────────────────────
alt_w = '''def fetch_weather():
    result = fetch_weather_for_location(51.34, 12.37, "Leipzig/Roitzsch")'''
neu_w = '''ORTE = {
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
    result = fetch_weather_for_location(lat, lon, name)'''
assert alt_w in s, "Wetterfunktion nicht gefunden"
s = s.replace(alt_w, neu_w)

alt_f = '''            req = urllib.request.Request("https://wttr.in/Leipzig?format=%t+%C+%p&lang=de", headers={"User-Agent": "curl/7.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                wttr = resp.read().decode("utf-8").strip()
            result = f"Leipzig: {wttr} (Quelle: wttr.in, Open-Meteo nicht erreichbar)"'''
neu_f = '''            req = urllib.request.Request(f"https://wttr.in/{name}?format=%t+%C+%p&lang=de", headers={"User-Agent": "curl/7.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                wttr = resp.read().decode("utf-8").strip()
            result = f"{name}: {wttr} (Quelle: wttr.in, Open-Meteo nicht erreichbar)"'''
assert alt_f in s
s = s.replace(alt_f, neu_f)

# ── 2. Kalender trennen ───────────────────────────────────────────────────
alt_k = '''CALDAV_ALLOWED_CALENDARS = {"SM", "Moritz", "Arbeit", "Familie", "Geburtstag", "Preply"}'''
neu_k = '''CALDAV_ALLOWED_CALENDARS = {"SM", "Moritz", "Arbeit", "Familie", "Geburtstag", "Preply"}
# Nur diese Kalender enthalten seine eigenen Verpflichtungen. Der Rest dient
# allein der Abstimmung und darf nicht als sein Termin dargestellt werden.
EIGENE_KALENDER = {"Moritz", "SM"}'''
assert alt_k in s
s = s.replace(alt_k, neu_k)

# Kalendername an die Events anhaengen
s = s.replace(
    "                print(f\"CalDAV: {cal_name} — {len(results)} Events\", file=sys.stderr)",
    "                print(f\"CalDAV: {cal_name} — {len(results)} Events\", file=sys.stderr)"
)
alt_e = '''                    ical_data = event.data
                    if ical_data:
                        events.extend(_parse_ical_events(ical_data, today_berlin, horizon))'''
neu_e = '''                    ical_data = event.data
                    if ical_data:
                        for zeile in _parse_ical_events(ical_data, today_berlin, horizon):
                            events.append(f"{zeile}\\t@{cal_name}")'''
assert alt_e in s
s = s.replace(alt_e, neu_e)

alt_r = '''    all_events = sorted(set(all_events))
    return "\\n".join(all_events) if all_events else "[Keine Termine in den nächsten 3 Tagen]"'''
neu_r = '''    all_events = sorted(set(all_events))
    eigene, fremde = [], []
    for zeile in all_events:
        if "\\t@" in zeile:
            text, kal = zeile.rsplit("\\t@", 1)
            (eigene if kal in EIGENE_KALENDER else fremde).append(f"{text}  [{kal}]")
        else:
            eigene.append(zeile)
    teile = []
    teile.append("DEINE TERMINE:\\n" + ("\\n".join(eigene) if eigene else "  [keine]"))
    if fremde:
        teile.append("NUR ZUR ABSTIMMUNG (nicht deine Termine):\\n" + "\\n".join(fremde))
    return "\\n\\n".join(teile) if (eigene or fremde) else "[Keine Termine in den nächsten 3 Tagen]"'''
assert alt_r in s
s = s.replace(alt_r, neu_r)

# ── 3. Tagesimpuls: genau ein konkreter Vorschlag ─────────────────────────
start = s.index("def generate_impulse():")
ende = s.index("# ─── Sprachübung (mit Vokabelgedächtnis) ───")
neu_i = '''VORSCHLAEGE_FILE = Path(__file__).parent / "vorschlaege.json"

def _lade_vorschlagsquellen():
    try:
        with open(VORSCHLAEGE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def generate_impulse():
    """Genau ein konkreter Vorschlag fuer heute - kurz, benannt, machbar.

    Die Vorschlaege stammen aus seinem eigenen Bestand: Buecher aus der
    Calibre-Bibliothek, Karten aus dem Anki-Deck, Alben aus der Mediathek.
    Nichts wird erfunden. Die Kategorie wechselt mit dem Wochentag, damit
    nicht jeden Tag dasselbe kommt.
    """
    today = now_berlin()
    day_de = {"Monday":"Montag","Tuesday":"Dienstag","Wednesday":"Mittwoch","Thursday":"Donnerstag",
              "Friday":"Freitag","Saturday":"Samstag","Sunday":"Sonntag"}.get(today.strftime("%A"), today.strftime("%A"))
    q = _lade_vorschlagsquellen()
    wd = today.weekday()   # 0 = Montag

    vorschlag = None

    if wd in (0, 3) and q.get("buecher"):
        b = random.choice(q["buecher"])
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

    return (f"Heute ist {day_de}.\\n"
            f"EINE SACHE für heute: {vorschlag}\\n"
            f"Nebenbei zu hören: {album_line}\\n"
            f"Gib genau diesen einen Vorschlag wieder, formuliere ihn kurz und ohne Alternativen. "
            f"Biete nichts zusätzlich an. Wenn der Tag voll ist, sag das in einem Halbsatz.")

'''
s = s[:start] + neu_i + s[ende:]

p.write_text(s, encoding="utf-8")
ast.parse(s)
print("generate_morgenbrief.py geaendert")

# ── 4. Vorschlagsquellen bauen ────────────────────────────────────────────
buecher = []
lib = pathlib.Path.home() / "Calibre Library/metadata.db"
if lib.exists():
    c = sqlite3.connect(f"file:{lib}?mode=ro", uri=True)
    for titel, autor in c.execute(
        "select b.title, coalesce(group_concat(a.name, ', '), '') "
        "from books b left join books_authors_link bal on bal.book=b.id "
        "left join authors a on a.id=bal.author group by b.id"):
        if titel:
            buecher.append({"titel": titel.strip(), "autor": (autor or "").strip()})
print("Buecher:", len(buecher))

vokabeln = []
bk = REPO / "bekannt_fa.json"
if bk.exists():
    vokabeln = [e for e in json.loads(bk.read_text(encoding="utf-8"))
                if e.get("word") and e.get("meaning")]
print("Vokabeln:", len(vokabeln))

# Filme: nur Regisseure, die in seinen eigenen Unterlagen vorkommen
filme = [
    "ein Film von Jafar Panahi",
    "ein Film von Abbas Kiarostami",
    "ein Film von Asghar Farhadi",
    "ein Film von Mohammad Rasoulof",
    "eine Dokumentation über Zentralasien",
    "ein Film, den du schon lange auf der Liste hast",
]

(REPO / "vorschlaege.json").write_text(
    json.dumps({"buecher": buecher, "vokabeln": vokabeln, "filme": filme},
               ensure_ascii=False, indent=1), encoding="utf-8")
print("vorschlaege.json geschrieben")
