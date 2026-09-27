#!/usr/bin/env python3
"""Startet den Morgenbrief mit aktuellem Claude-Modell.

generate_morgenbrief.py bleibt die Quelle für Kalender, Wetter, ePub.
Dieser Wrapper ersetzt den API-Aufruf, der auf claude-sonnet-4-20250514
mit HTTP 400 stirbt, und schickt bei Totalausfall trotzdem einen Brief.
"""

from __future__ import annotations

import sys
from pathlib import Path

_APKG = None

import generate_morgenbrief as g
from claude_client import complete


def call_claude(kontext, fahrplan, aufgaben, kalender, wetter, impulse, lang_exercise):
    today = g.now_berlin().strftime("%A, %d. %B %Y")
    lang = lang_exercise
    script = "arabischer" if lang["lang_code"] == "ar" else "persischer"
    dialect = (
        "Fusha (MSA), kein Dialekt."
        if lang["lang_code"] == "ar"
        else "Farsi-ye meyar, kein Slang."
    )
    vok = (
        "WICHTIG: Arabischen Text MIT VOLLSTÄNDIGER VOKALISIERUNG "
        "(tashkīl/harakat auf jedem Wort) schreiben. "
        if lang["lang_code"] == "ar"
        else ""
    )
    if lang.get("headline"):
        news_p = (
            f"NACHRICHTEN (RTL, in Originalschrift):\n"
            f"Die folgende Nachricht von BBC in {script} Originalschrift wiedergeben. {vok}\n"
            f"Zunächst die Schlagzeile, dann den Artikeltext sinngemäß in 3-4 Sätzen zusammenfassen. {vok}\n"
            f"Glossiere schwierige Wörter inline auf Deutsch in Klammern (passend zu Level {lang['level']}).\n\n"
            f"Schlagzeile: {lang['headline']}\n\n"
            f"Artikeltext (zur Zusammenfassung):\n{lang['news_text']}\n"
        )
    else:
        news_p = (
            "NACHRICHTEN:\nKeine aktuellen Nachrichten verfügbar. "
            "Schreibe einen kurzen Satz auf Deutsch."
        )
    import sprachuebung
    global _APKG
    try:
        ue = sprachuebung.erzeuge(lang, complete)
        if ue["neue"]:
            g.add_new_vocab("fa", ue["neue"], lang["memory"])
            _APKG = sprachuebung.anki_paket(ue["neue"], Path("/tmp"))
        sprachteil = ue["abschnitt"]
        print(f"Leseübung: {round((1 - ue['quote']) * 100)} % bekannt, {len(ue['neue'])} neue Wörter")
    except Exception as e:
        print(f"Leseübung gescheitert: {e}", file=sys.stderr)
        sprachteil = "SPRACHÜBUNG - TEXT\n[entfällt heute]\n"
    msg = (
        f"Heute ist {today}.\n\nWETTER:\n{wetter}\n\nTAGESIMPULS:\n{impulse}\n\n"
        f"KONTEXT (enthält Format und Regeln - befolge sie exakt):\n{kontext}\n\n"
        f"OFFENE AUFGABEN:\n{aufgaben}\n\nKALENDER (nächste 3 Tage):\n{kalender}\n\n"
        f"FAHRPLAN (nur als Hintergrund):\n{fahrplan}\n\n"
        f"AUFTRAG:\nSchreibe den Morgenbrief exakt in dieser Struktur:\n"
        f"1. WETTER\n2. HEUTE\n3. IMPULS\n4. PROJEKTE\n5. ERLEDIGTES\n6. AUSBLICK\n\n"
        f"Schreibe KEINE Sprachübung und KEINE Nachrichten; diese Teile werden separat angehängt.\n"
        f"WICHTIG: Verwende in Sektionstiteln immer einfache Bindestriche (-), NIEMALS Gedankenstriche.\n"
        f"Jede Sektion als Überschrift in Großbuchstaben. Kein Markdown. Sachlich."
    )
    return complete(msg, max_tokens=2500).rstrip() + "\n\n" + sprachteil


def fallback_brief(wetter, kalender, impulse, lang_ex):
    news = lang_ex.get("headline") or "Keine Nachricht geladen."
    return (
        f"WETTER\n{wetter}\n\n"
        f"HEUTE\nClaude war nicht erreichbar. Kalender und Wetter ungekürzt.\n\n"
        f"IMPULS\n{impulse}\n\n"
        f"PROJEKTE\n-\n\n"
        f"ERLEDIGTES\n-\n\n"
        f"AUSBLICK\n{kalender}\n\n"
        f"SPRACHÜBUNG - TEXT\n[entfällt, API-Fehler]\n\n"
        f"SPRACHÜBUNG - FRAGEN\n-\n\n"
        f"NACHRICHTEN\n{news}\n"
    )


def main():
    g.call_claude = call_claude
    _senden = g.send_to_kindle
    g.send_to_kindle = lambda epub, text=None: _senden(
        epub, text, anhaenge=[_APKG] if _APKG else None)
    try:
        g.main()
        return
    except Exception as e:
        print(f"Claude-Lauf gescheitert, Fallback-Brief: {e}", file=sys.stderr)

    ical_urls = g.os.environ.get("ICAL_URL", "")
    kalender = g.fetch_calendar(ical_urls) if ical_urls else "[Kein Kalender]"
    wetter = g.fetch_weather()
    impulse = g.generate_impulse()
    lang_ex = g.generate_language_exercise()
    text = fallback_brief(wetter, kalender, impulse, lang_ex)
    epub = g.create_epub(text, g.now_berlin().strftime("%Y-%m-%d"))
    g.send_to_kindle(epub, text)


if __name__ == "__main__":
    main()
