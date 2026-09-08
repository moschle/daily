# Jurabrief — Entwurf

Täglicher (Mo/Mi/Fr) Fall-Brief für die 2. Staatsprüfung, Zivilrecht.

Baut auf der Morgenbrief-Infrastruktur auf:
- gleicher Gmail-Versand (Secrets: GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
- Empfänger: Freundin (nur TO ändern, FROM bleibt dein Account)
- gleicher Claude-Client (claude_client.py)

## Status (Entwurf)
- [x] Workflow-Datei (Mo/Mi/Fr 07:00)
- [x] Generator-Skript mit Fall-DB + Prompt
- [x] Fall-DB mit echten Themen aus Berlin-Skripten (12 Fälle)
- [x] Open Legal Data API: pro Fall wird ein verwandtes Urteil gesucht
  (cited_law book+section, Datum ab 2019, Volltext, nach Relevanz)
- [ ] deine Scans (Sachsen-Anhalt) einpflegen
- [ ] Anki-Daten (später)

## Wie die Urteils-Suche funktioniert
1. Generator pickt den nächsten Fall aus cases.json.
2. search_related_case() ruft Open Legal Data auf:
   `GET /api/cases/search/?text=...&cited_law_book=bgb&cited_law_section=433&start_date=2019-01-01&return_text=1&order_by=relevance`
3. Erstes Ergebnis (höchste Relevanz) wird als Lese-Hintergrund in den Prompt gepackt.
4. Claude formuliert daraus eine neue Aufgabe — nicht identisch zum Skript-Beispiel.
5. Mail geht raus.

Kein API-Key nötig für die Suche (Open Legal Data ist öffentlich lesbar).

## Nächste Schritte
1. `python jurabriefe/generate_jurabrief.py` lokal testen
2. Workflow manuell dispatchen
3. Mail prüfen
