"""Lernkarten zur Forschungslektüre im Morgenbrief (seit 05.11.2026).

Zu jedem Leseabschnitt entstehen Karten im Notiztyp "IW-Sicherheit (Kontext)" für den
Unterstapel "23 Lektüre Morgenbrief" im Deck "Islamwissenschaft & Sicherheitspolitik".
Die Karten verankern das Gelesene historisch (Personen, Werke, Epochen mit Daten und Orten)
und verbinden es mit früher Gelesenem; dafür führt LESEN_DIR/karten.json ein Protokoll
mit einer kurzen Zusammenfassung jedes Abschnitts.
"""
from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

MODELL_ID = 1790500000001
DECK_ID = 1793600000023
DECK_NAME = "Islamwissenschaft & Sicherheitspolitik::23 Lektüre Morgenbrief"
CSS = (".card{font-family:-apple-system,\"Segoe UI\",Helvetica,Arial,sans-serif;font-size:21px;line-height:1.45;"
       "text-align:center;color:#1d1d1f;background:#fff;padding:12px}\n.q{font-weight:600}\n.a{font-size:22px}\n"
       ".k{margin:18px auto 0;max-width:34em;font-size:16px;line-height:1.5;text-align:left;color:#555;"
       "border-top:1px solid #ddd;padding-top:10px}\n.night_mode .card,.nightMode .card{background:#1e1e1e;color:#eee}\n"
       ".night_mode .k,.nightMode .k{color:#aaa;border-color:#444}\n")

AUFTRAG = """Du erstellst Anki-Lernkarten zu einem wissenschaftlichen Text, den ein Islamwissenschaftler und Literaturwissenschaftler (Schwerpunkt persische und tadschikische Literatur) heute gelesen hat. Ziel: Das Wissen soll sich dauerhaft und historisch festigen, und Zusammenhänge mit früher Gelesenem sollen sichtbar werden.

Erstelle {n} Karten, auf Deutsch, verteilt auf:
- historische Verankerung: Personen, Werke, Gattungen, Ereignisse mit Lebensdaten, Jahrhundert, Ort, Dynastie oder Epoche
- Begriffe und Fachtermini mit knapper Definition (persische/arabische Begriffe in der Umschrift des Textes)
- zentrale Thesen: Wer vertritt im Text was, und worauf stützt es sich?
- Zusammenhänge: Verbindung zu den früher gelesenen Texten unten, wenn eine echte inhaltliche Verbindung besteht (gleiche Person, Epoche, Gattung, Theorie, Gegenposition). Keine erzwungenen Verbindungen.

Regeln:
- Nur, was im Text steht oder zum unstrittigen Grundwissen gehört; nichts erfinden. Daten nur, wenn sie im Text stehen oder sicher sind.
- "frage" eindeutig, "antwort" kurz (höchstens 15 Wörter).
- "kontext": 1–2 Sätze Einordnung (wann, wo, warum wichtig, Bezug zum Text). Die Antwort darf darin nicht wörtlich stehen.
- "umkehren": true nur, wenn die Antwort eindeutig zur Frage zurückführt (Begriff ↔ Definition, Werk ↔ Autor).
- Keine Karten zu Fußnoten, Seitenzahlen oder Formalien.

Außerdem "zusammenfassung": 2–3 Sätze, worum es im Abschnitt geht (für spätere Querverweise).

Antworte NUR mit JSON: {{"zusammenfassung": "", "karten": [{{"frage": "", "antwort": "", "kontext": "", "umkehren": false}}]}}

FRÜHER GELESEN:
{verlauf}

HEUTIGER TEXT: {titel}
{text}"""


def _json(roh: str) -> dict:
    m = re.search(r"\{.*\}", roh, re.S)
    return json.loads(m.group(0)) if m else {}


def erzeugen(ordner: Path, name: str, titel: str, text: str, claude, n: int = 8, datum: str | None = None) -> list:
    """Karten erzeugen und im Protokoll ablegen; gibt die Karten zurück."""
    pfad = ordner / "karten.json"
    try:
        protokoll = json.loads(pfad.read_text(encoding="utf-8"))
    except Exception:
        protokoll = []
    verlauf = "\n".join(f"- {p['titel']}: {p['zusammenfassung']}" for p in protokoll[-40:]) or "-"
    d = _json(claude(AUFTRAG.format(n=n, verlauf=verlauf, titel=titel, text=text[:30000]), 8000))
    karten = [k for k in d.get("karten", []) if k.get("frage") and k.get("antwort")]
    protokoll.append({"datum": datum or date.today().isoformat(), "text": name, "titel": titel,
                      "zusammenfassung": d.get("zusammenfassung", ""), "karten": karten})
    pfad.write_text(json.dumps(protokoll, ensure_ascii=False, indent=1), encoding="utf-8")
    return karten


def paket(karten: list, ziel: Path, tag: str) -> Path | None:
    if not karten:
        return None
    import genanki
    modell = genanki.Model(
        MODELL_ID, "IW-Sicherheit (Kontext)",
        fields=[{"name": f} for f in ("ID", "Frage", "Antwort", "Kontext", "Umkehren")],
        templates=[
            {"name": "Vorwärts", "qfmt": '<div class="q" dir="auto">{{Frage}}</div>',
             "afmt": '{{FrontSide}}<hr id="answer"><div class="a" dir="auto">{{Antwort}}</div>'
                     '{{#Kontext}}<div class="k">{{Kontext}}</div>{{/Kontext}}'},
            {"name": "Rückwärts", "qfmt": '{{#Umkehren}}<div class="q" dir="auto">{{Antwort}}</div>{{/Umkehren}}',
             "afmt": '{{FrontSide}}<hr id="answer"><div class="a" dir="auto">{{Frage}}</div>'
                     '{{#Kontext}}<div class="k">{{Kontext}}</div>{{/Kontext}}'}],
        css=CSS)
    deck = genanki.Deck(DECK_ID, DECK_NAME)
    for i, k in enumerate(karten, 1):
        deck.add_note(genanki.Note(
            model=modell, guid=genanki.guid_for("lektuere", k["frage"]),
            fields=[f"L{tag}-{i:02d}", k["frage"], k["antwort"], k.get("kontext", ""),
                    "1" if k.get("umkehren") else ""],
            tags=["lektuere", f"lek_{tag}"]))
    pfad = ziel / f"lektuere_{tag}.apkg"
    genanki.Package(deck).write_to_file(str(pfad))
    return pfad
