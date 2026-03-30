# Morgenbrief

Ein täglicher Tagesplan, geschrieben von Claude, geliefert auf deinen Kindle um 6:00 Uhr.

## Wie es funktioniert

1. Du pflegst `aufgaben.md` und `fahrplan.md` in diesem Repo
2. Jeden Morgen um 6:00 läuft ein GitHub Action
3. Der Workflow holt deinen Google Calendar (via iCal-URL), liest Aufgaben und Fahrplan
4. Claude (Anthropic API) analysiert den Sachstand und schreibt einen persönlichen Tagesbrief
5. Das Ergebnis wird als ePub an deinen Kindle geschickt (Send-to-Kindle via Gmail SMTP)

## Setup

### 1. GitHub Secrets einrichten

In deinem Repo → Settings → Secrets and variables → Actions:

| Secret | Beschreibung |
|--------|-------------|
| `ANTHROPIC_API_KEY` | Dein Anthropic API Key |
| `ICAL_URL` | iCal-URL deines Kalenders (Google Calendar: Einstellungen → Kalender → Geheime Adresse im iCal-Format) |
| `KINDLE_EMAIL` | Deine Send-to-Kindle-Adresse (z.B. `moritz_abc@kindle.com`) |
| `GMAIL_ADDRESS` | Gmail-Adresse für den Versand |
| `GMAIL_APP_PASSWORD` | Gmail App-Passwort (nicht dein normales Passwort!) |

### 2. Gmail App-Passwort erstellen

Google-Konto → Sicherheit → 2-Faktor-Authentifizierung → App-Passwörter → Neues Passwort generieren.
Die Gmail-Adresse muss in den Amazon Kindle-Einstellungen als zugelassene Absenderadresse eingetragen sein.

### 3. Aufgaben pflegen

Bearbeite `aufgaben.md` direkt auf GitHub (oder per Working Copy / GitHub Mobile App).
Hake erledigte Aufgaben ab mit `[x]`. Claude sieht, was sich verändert hat.

### 4. Optional: Manuell auslösen

Actions → Morgenbrief → Run workflow → Klick.

## Dateien

- `fahrplan.md` — Dein Gesamtfahrplan (Deadlines, Szenarien, Lift-Termine)
- `aufgaben.md` — Laufende Aufgaben mit Checkboxen
- `kontext.md` — Persönlicher Kontext für Claude (wer du bist, was du machst, wie Claude mit dir reden soll)
- `generate_morgenbrief.py` — Hauptskript
- `.github/workflows/morgenbrief.yml` — Täglicher Cron-Job
