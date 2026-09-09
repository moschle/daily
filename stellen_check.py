#!/usr/bin/env python3
"""
Stellen-Monitor: tägliche Suche nach passenden Wissenschafts-/Behörden-Stellen.
Quellen:
  DE: H-Soz-Kult (Atom), kultweet.de (HTML), UniBwM (HTML), service.bund.de (RSS)
  Internationale Erweiterung: arthist.net (RSS), jobs.ac.uk × 3 Fachbereiche (RSS)
Filter: Score-basiert mit Wortgrenzen-Matching + Hard-Blacklist.
Output: HTML-Mail an GMAIL_ADDRESS, wenn neue Treffer da sind.
State: stellen_seen.json mit gesehenen IDs (Aufräumen nach 90 Tagen).
"""
