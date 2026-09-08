# Jurabrief

Mo/Mi/Fr-Brief zur Vorbereitung auf die zweite juristische Staatsprüfung
(Sachsen-Anhalt), Ziel April 2027. Grundlage sind die Berliner
Ausbildungsskripte des Kammergerichts als Volltext.

## Ablauf

**Montag / Mittwoch / Freitag, 07:00** — `jurabrief.yml`
1. `adaptive_plan.py` wählt den Fall: Phase des Lernplans, FSRS-Fälligkeit, Ergebnisgewicht.
   Offene Karten vom letzten Brief werden vorher neutral verbucht (`auto_wertung`).
2. Open Legal Data liefert ein thematisch passendes Urteil (Suchbegriffe je Fall) — nur zum Lesen.
3. Mail: **I. Lesetext** (Urteil) → **II. Bearbeitung** (Bearbeitervermerk) → **Skript (Regeln)**.
4. Betreff trägt die Fall-ID: `[zr-002]`.

**Dienstag / Donnerstag / Samstag, 19:00** — `jurabrief-antwort.yml`
1. `korrektur.py` liest ungelesene Antworten per IMAP.
2. Erste Zeile `gut`/`wieder`/`schwer`/`leicht` → Selbsteinschätzung.
   `7 Punkte` → Punkte direkt. Text ab 1200 Zeichen → Klausur.
3. Klausuren werden über Claude gegen Bearbeitervermerk und Skriptabschnitt
   korrigiert: 0-18 Punkte, Fehlerstellen mit Zitat, Regel, richtiger Fassung.
4. Punkte gehen in FSRS (`progress.json`): 0-3 wieder, 4-5 schwer, 6-8 gut, ab 9 leicht.
5. Auswertungsmail mit Punkten, Fehlern, nächstem Schritt, Gebietsschnitt.

## Dateien

| Datei | Rolle |
|---|---|
| `cases.json` | 12 Fälle: Gebiet, Skriptanker, Suchbegriffe |
| `lernplan.json` | Phasen bis 30.04.2027 |
| `progress.json` | FSRS-Karten, Punkteverlauf, Feedback |
| `state.json` | zuletzt gezeigte Fälle und Urteile |
| `extracted/*.txt` | Volltexte der elf Berliner Skripte |
| `karten.py`, `kuratieren.py` | Kartenschicht (Rohkarten → kuratierte Karten); noch nicht im Brief verdrahtet |
| `skripte.json`, `extract_skripte.py` | Quellen und Extraktion (`--lokal` für eigene PDFs) |

## Secrets

`GMAIL_ADDRESS`, `GMAIL_APP_PASSWORD`, `JURABRIEF_TO`, `ANTHROPIC_API_KEY`

## Lokal

```
pip install -r requirements.txt
python jurabriefe/generate_jurabrief.py   # Brief bauen; ohne Secrets nur Ausgabe
python jurabriefe/fsrs_scheduler.py       # Karten und Fälligkeiten
python jurabriefe/karten.py               # Rohkarten aus den Skripten
```

Verlagsmaterial (z. B. Landesrechtsskripte) gehört nicht in dieses öffentliche
Repo. `private/` ist per `.gitignore` ausgeschlossen; `karten.py` liest den Pfad
aus `JURABRIEF_EXTRACTED` / `JURABRIEF_KARTEN`.
