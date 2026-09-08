# Jurabrief

Mo/Mi/Fr-Brief für die 2. Staatsprüfung (Sachsen-Anhalt), Ziel April 2027.

## Ablauf

**Montag / Mittwoch / Freitag, 07:00** — `jurabrief.yml`
1. Adaptiver Plan wählt den Fall (Phase + FSRS-Fälligkeit + Gewicht).
2. Open Legal Data sucht ein verwandtes Urteil (ab 2019, nicht identisch).
3. Mail: **Teil 1 Lesen** (Urteil + Lesehinweis) → **Teil 2 Aufgabe** (Skript-Fall lösen).
4. Versand von deinem Gmail-Account an `JURABRIEF_TO`.

**Dienstag / Donnerstag, 19:00** — `jurabrief-antwort.yml`
1. IMAP liest die Antwortmail (`SCORE: 1-5` + Lösungstext).
2. `grade_solution.py` bewertet die Klausur über Claude (Punkte, Lücken, Muster).
3. FSRS-Scheduler (`fsrs_scheduler.py`) plant die nächste Wiederholung.
4. Auswertung-Mail mit Stärken, Lücken, Verbesserung, nächstem Termin.

## Daten

| Datei | Rolle |
|---|---|
| `cases.json` | 12 Themen aus Berliner Skript-Inhaltsverzeichnissen |
| `extracted/*.txt` | Volltexte der 11 Berlin-PDFs (via Action) |
| `lernplan.json` | 3 Phasen bis 30.04.2027 |
| `progress.json` | Gewichte + Feedback-Historie |
| `fsrs_cards.json` | FSRS-Karten pro Fall (Stabilität, Due-Datum) |
| `last_grade.json` | letzte Klausur-Bewertung |

## Secrets

- `ANTHROPIC_API_KEY` — Claude für Lesehinweis, Bewertung, Musterlösung
- `GMAIL_ADDRESS` + `GMAIL_APP_PASSWORD` — Versand + IMAP-Empfang
- `JURABRIEF_TO` — Empfängerin (deine Freundin)

## Lokal testen

```
pip install -r requirements.txt
python jurabriefe/generate_jurabrief.py          # Brief bauen (ohne Mail, wenn keine Secrets)
python jurabriefe/fsrs_scheduler.py due           # fällige Fälle
python jurabriefe/adaptive_plan.py               # nächster Fall + Grund
```

Landesrecht Sachsen-Anhalt (VerwR) kommt später aus deinen Scans rein — einfach
in `cases.json` ergänzen, der Rest bleibt unverändert.
