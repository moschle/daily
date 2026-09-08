# Jurabrief

Mo/Mi/Fr-Brief für die 2. Staatsprüfung (Sachsen-Anhalt), Ziel April.

## Was wiederhergestellt ist — und was nicht

Der unterbrochene Chat hat **keinen** geparsten Volltext und **kein** Feedback-System ins Repo geschrieben.
Wiederhergestellt aus dem, was wirklich da war:
- 12 Themen aus den Berliner Inhaltsverzeichnissen (`cases.json`)
- Generator + Open-Legal-Data-Suche
- Mail: erst Urteil lesen, dann Skript-Aufgabe

Neu aufgesetzt (diese Commit):
- PDF-Volltext-Extractor für die öffentlichen Berlin-Skripte
- Lernplan-Phasen bis 30.04.2027
- Adaptives Feedback: Antwortmail mit `SCORE: 1-5` verschiebt die Gewichte

## PDFs komplett auslesen

Lokal oder in Actions:

```
pip install pypdf
python jurabriefe/extract_skripte.py
```

Schreibt `jurabriefe/extracted/<id>.txt` plus `index.json`.
Die Berlin-PDFs sind echte Text-PDFs, kein Scan — pypdf reicht.
Deine Sachsen-Anhalt-Scans kommen als Datei dazu (OCR, falls nötig).

## Feedback-Loop

Sie antwortet auf die Mail:

```
SCORE: 3

<ihre Lösung>
```

`ingest_feedback.py` liest per IMAP die Inbox, speichert die Antwort,
hebt das Gewicht bei SCORE 1–2 (nochmal üben) und senkt es bei 4–5.

Workflow: nach dem Versand optional denselben Job mit Ingest laufen lassen,
oder einen zweiten Cron (z. B. abends).
