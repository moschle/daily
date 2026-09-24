# Jurabrief

Mo/Mi/Fr-Brief zur Vorbereitung auf die zweite juristische Staatsprüfung
(Sachsen-Anhalt), Ziel April 2027. Grundlage sind die Berliner
Ausbildungsskripte des Kammergerichts als Volltext.

## Ablauf

**Montag / Mittwoch / Freitag** — `jurabrief.yml`, Cron 01:23, 03:23 und 06:23 UTC
(03:23 / 05:23 / 08:23 MESZ). Der erste erfolgreiche Lauf versendet; die beiden
anderen sind No-Ops (Tagessperre `letzter_brief`). Scheitert der Versand, wird
die Sperre zurückgesetzt.

1. Offene Karten älterer Briefe ohne Antwort verbucht `auto_wertung` als
   `unbeantwortet` (nur Fälligkeit verschoben, kein Grade).
2. `adaptive_plan.current_phase()` liefert die Phase des Lernplans,
   `kartenbrief.waehle_fall()` den Fall: das Skript mit den meisten fälligen
   und schwächsten Karten, die letzten zwei Fälle gesperrt. FSRS liegt auf den
   Karten, nicht auf den Fällen.
3. `kartenbrief.waehle(anzahl=2)` zieht zwei Skriptkarten.
4. Open Legal Data liefert ein Urteil als Lesetext (bis 60 000 Zeichen); Claude
   stellt dazu Fragen, die ohne das Urteil lesbar sind.
5. Mail: **I. Lesetext** → **II. Aufgaben**. Lösungen bleiben in
   `state.json` unter `offene_packs` (Schlüssel `fall@TT.MM.`), höchstens sechs,
   älter als 14 Tage werden verworfen.

**Täglich 17:00 UTC (19:00 MESZ)** — `jurabrief-antwort.yml`

1. `korrektur.py` sucht per IMAP `SUBJECT "Jurabrief"` der letzten 14 Tage und
   merkt sich verarbeitete Message-IDs.
2. `pack_nach_inhalt()` ordnet eine Antwort dem richtigen Paket zu, auch wenn
   sie im falschen Reply-Thread steht.
3. Erste Zeile `gut`/`wieder`/`schwer`/`leicht` → Selbsteinschätzung;
   `7 Punkte` → Punkte direkt; `streichen 2` → Karte dauerhaft raus;
   eigener Text ab 400 Zeichen (`MIN_KLAUSUR`) → Klausur.
4. Claude bewertet 0–18 Punkte je Karte, der Schnitt wird lokal gerechnet.
   Punkte gehen in FSRS (`progress.json`).
5. Verarbeitete Mails werden aus der INBOX geräumt (`JURABRIEF_AUFRAEUMEN=0`
   schaltet das ab).

## Dateien

| Datei | Rolle |
|---|---|
| `generate_jurabrief.py` | Brief bauen und senden |
| `kartenbrief.py` | Fall- und Kartenwahl, Pakete, Brieftext |
| `korrektur.py` | Antworten lesen, bewerten, FSRS fortschreiben |
| `fsrs_scheduler.py` | Karten-FSRS, `auto_wertung` |
| `adaptive_plan.py` | nur noch `current_phase()` |
| `cases.json` | Fälle mit Skriptanker und Suchbegriffen (`zr-009`–`zr-012` sind Verwaltungsrecht) |
| `lernplan.json` | Phasen bis 30.04.2027 |
| `progress.json` | FSRS-Karten, Punkteverlauf, Feedback |
| `state.json` | zuletzt gezeigte Fälle und Urteile, offene Pakete |
| `karten/*.kuratiert.json` | kuratierte Karten, im Brief verdrahtet |
| `karten.py`, `kuratieren.py`, `karten_llm.py`, `pruefe_karten.py` | Kartenbau aus den Skripten |
| `extracted/*.txt` | Volltexte der elf Berliner Skripte |
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
