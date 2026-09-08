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
- [ ] deine Scans (Sachsen-Anhalt) einpflegen
- [ ] Anki-Daten (später)
- [ ] Open Legal Data API für verwandte Urteile (return_text=1)

## Nächste Schritte
1. `python jurabriefe/generate_jurabrief.py` lokal testen
2. Workflow manuell dispatchen
3. Mail prüfen
