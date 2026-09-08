# Jurabrief — Entwurf

Täglicher (Mo/Mi/Fr) Fall-Brief für die 2. Staatsprüfung, Zivilrecht.

Baut auf der Morgenbrief-Infrastruktur auf:
- gleicher Gmail-Versand (Secrets: GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
- Empfänger: Freundin (nur TO ändern, FROM bleibt dein Account)
- gleicher Claude-Client (claude_client.py)

## Status (Entwurf)
- [x] Workflow-Datei (Mo/Mi/Fr 07:00)
- [x] Generator-Skript mit Fall-DB + Prompt
- [x] Beispiel-Fall-DB (3 Fälle, Berlin-Skript-Stil)
- [ ] echte Skripte einpflegen (Berlin PDF + deine Scans)
- [ ] Anki-Daten (später)
- [ ] Sachsen-Anhalt-Landesrecht (später)

## Nächste Schritte
1. `python jurabriefe/generate_jurabrief.py` lokal testen
2. Workflow manuell dispatchen
3. Mail prüfen
