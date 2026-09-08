# Jurabrief — Entwurf

Täglicher (Mo/Mi/Fr) Brief für die 2. Staatsprüfung.

## Mail-Aufbau
1. **Teil 1 — Lesen:** verwandtes Urteil (Open Legal Data, ab 2019).
   Nur Sprache und Aufbau. Keine Aufgabe.
2. **Teil 2 — Aufgabe:** der Fall aus dem Berliner Skript
   (Gebiet + Kernfrage). Nicht neu generiert.

Claude schreibt nur den kurzen Lesehinweis (zwei bis drei Sätze).
Die Aufgabe kommt unverändert aus `cases.json`.

## Status
- [x] Workflow Mo/Mi/Fr 07:00
- [x] Fall-DB aus Berlin-Skripten (12 Themen)
- [x] Open Legal Data (cited_law, Datum ab 2019, Volltext)
- [x] Lesen zuerst, dann Skript-Aufgabe
- [ ] volle Sachverhalte aus den PDFs / Scans
- [ ] Musterlösung im Folgeberief
- [ ] Sachsen-Anhalt Landesrecht

## Nächste Schritte
1. `python jurabriefe/generate_jurabrief.py` lokal testen
2. Workflow dispatchen und Mail prüfen
3. Sobald Scans da sind: echte Sachverhalte in cases.json
