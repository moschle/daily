"""Wöchentliche Prüfungssimulation Persisch (seit 25.11.2026, nach dem Vortest Polizei Berlin).

Freitag: ein echter, harter Text aus staatsnahen Telegram-Kanälen, OHNE Glossen. Aufgabe:
30 Minuten schriftlich übersetzen, ohne Wörterbuch, Lücken markieren, nicht abbrechen.
Textsorte wechselt wöchentlich: Erklärung (Sepah/Ministerien) · Rede · Freitagspredigt · Agitation.
Samstag: vollständige Übersetzung und die schweren Wörter (diese gehen ins Anki-Paket).
Nichts wird vom Sprachmodell erfunden: der Text ist immer ein echter Post mit Link.
Zustand außerhalb des Repos (/automat/wochentest.json), damit ein Deploy ihn nicht löscht."""
from __future__ import annotations

import json
import os
from datetime import date, timedelta
from pathlib import Path

STATE = Path(os.environ.get("WOCHENTEST_STATE") or (
    "/automat/wochentest.json" if Path("/automat").exists() else Path(__file__).with_name("wochentest_state.json")))
KANAELE = ["farsna", "Mehrnews", "irna_1313"]
MIN_WOERTER = 60      # Telegram-Posts sind kurz: zwei Posts = zwei Absätze wie im Test
MAX_WOERTER = 160     # je Absatz
SEITEN = 12           # je Kanal ca. 20 Posts pro Seite, also etwa die letzten 1-3 Tage

# Merkmale je Textsorte; dazu immer das allgemeine Kampfvokabular
GATTUNGEN = [
    ("Erklärung (بیانیه/اطلاعیه)", ["بیانیه", "اطلاعیه", "سپاه", "قرارگاه", "روابط عمومی", "عملیات", "به اطلاع"]),
    ("Rede (بیانات)", ["بیانات", "سخنرانی", "رهبر انقلاب", "رهبر معظم", "در دیدار", "در جمع", "تأکید کرد"]),
    ("Freitagspredigt (خطبه)", ["خطبه", "نماز جمعه", "امام جمعه", "خطیب"]),
    ("Agitation (شهادت، مقاومت)", ["شهید", "شهادت", "مقاومت", "انتقام", "خون", "جبهه", "حماسه"]),
]
KAMPF = ["استکبار", "دشمن", "صهیونیست", "آمریکا", "مقاومت", "شهید", "انتقام", "بسم الله", "جبهه",
         "ولایت", "انقلاب اسلامی", "مستکبر", "پاسخ", "قاطع", "امت"]
AUFGABE = ("PRÜFUNGSSIMULATION (Freitag): 30 Minuten, ohne Wörterbuch, schriftlich ins Deutsche übersetzen. "
           "Unbekanntes markieren und weiterschreiben, nicht abbrechen. Lösung kommt morgen.")


def _laden() -> dict:
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _kuerzen(text: str) -> str:
    w = text.split()
    if len(w) <= MAX_WOERTER:
        return text
    kurz = " ".join(w[:MAX_WOERTER])
    ende = max(kurz.rfind("."), kurz.rfind("؛"), kurz.rfind("!"))
    return kurz[: ende + 1] if ende > len(kurz) // 2 else kurz + " …"


def _text_suchen() -> dict | None:
    import re
    import auswertung
    name, merkmale = GATTUNGEN[date.today().isocalendar()[1] % len(GATTUNGEN)]
    kandidaten, alle = [], []
    for k in KANAELE:
        posts, vor = [], ""
        for _ in range(SEITEN):
            try:
                seite = auswertung._posts(k + (f"?before={vor}" if vor else ""))
            except Exception as e:
                print(f"Wochentest: {k} nicht erreichbar ({e})")
                break
            if not seite:
                break
            posts += seite
            vor = seite[0]["id"].split("/")[-1]
        for p in posts:
            t = re.sub(r"@\w+|\S+\.(?:com|ir)\b|[\U0001F300-\U0001FAFF☀-➿⬀-⯿️]", "", p["text"]).strip()
            if len(t.split()) < MIN_WOERTER:
                continue
            punkte = 60 * sum(m in t for m in merkmale) + 15 * sum(m in t for m in KAMPF) + min(len(t.split()), 250) // 5
            alle.append((punkte, p["id"], t, p["zeit"]))
            if sum(m in t for m in merkmale):
                kandidaten.append(alle[-1])
    if not kandidaten:   # Textsorte diese Woche nicht dabei: die kampfbetontesten Posts
        kandidaten, name = alle, "Agitation/Meldung (gewünschte Textsorte nicht gefunden)"
    # zwei verschiedene Meldungen (nicht dieselbe Nachricht bei Mehr und IRNA)
    gewaehlt = []
    for c in sorted(kandidaten, reverse=True):
        if not any(c[2][:25] == g[2][:25] or c[1] == g[1] for g in gewaehlt):
            gewaehlt.append(c)
        if len(gewaehlt) == 2:
            break
    kandidaten = gewaehlt
    if not kandidaten:
        return None
    return {"text": "\n\n".join(_kuerzen(c[2]) for c in kandidaten),
            "quelle": ", ".join(f"t.me/{c[1]}" for c in kandidaten),
            "zeit": kandidaten[0][3], "gattung": name}


def erzeuge(complete) -> tuple[str, list[tuple[str, str]]]:
    import sprachuebung as su
    heute = date.today()
    st = _laden()
    if st.get("lauf") == heute.isoformat():               # zweiter Lauf am selben Tag
        return st.get("abschnitt", ""), []

    abschnitt, neue = "", []
    if heute.weekday() == 4:                               # Freitag: Aufgabe
        t = _text_suchen()
        if t:
            abschnitt = (f"{AUFGABE}\nTextsorte: {t['gattung']} · Quelle: {t['quelle']} · {t['zeit'][:10]}\n\n"
                         f"{t['text']}\n")
            st = {"aufgabe": t, "aufgabe_datum": heute.isoformat()}
    elif heute.weekday() == 5 and st.get("aufgabe_datum") == (heute - timedelta(days=1)).isoformat():
        t = st["aufgabe"]
        d = su._json(complete(
            "Übersetze den folgenden echten persischen Text (staatsnahe iranische Quelle) vollständig, genau und "
            "satzweise ins Deutsche; religiöse Formeln und Kampfbegriffe wörtlich mit gängiger deutscher Entsprechung. "
            "Erfinde nichts, lass nichts aus. Nenne dazu bis zu 15 schwere Wörter oder feste Wendungen aus dem Text "
            "(Persisch in Grundform mit Kurzvokalzeichen, knappe deutsche Bedeutung im Sinn dieses Textes), "
            "keine Eigennamen.\n"
            'Antworte nur als JSON: {"uebersetzung": "...", "woerter": [{"fa": "...", "de": "..."}]}\n\n'
            + t["text"], max_tokens=3000))
        woerter = [(w["fa"].strip(), w["de"].strip()) for w in d.get("woerter", []) if w.get("fa") and w.get("de")]
        liste = "\n".join(f"{fa} – {de}" for fa, de in woerter)
        abschnitt = (f"LÖSUNG PRÜFUNGSSIMULATION (Text von gestern, {t['quelle']})\n\n"
                     f"{d.get('uebersetzung', '')}\n\nSCHWERE WÖRTER (im Anki-Paket)\n{liste}\n")
        bekannt = set()
        if su.BEKANNT_FILE.exists():
            for e in json.loads(su.BEKANNT_FILE.read_text(encoding="utf-8")):
                bekannt |= su._formen(e.get("word", ""))
        neue = [(fa, de) for fa, de in woerter if not (su._formen(fa) <= bekannt)]
    st["lauf"], st["abschnitt"] = heute.isoformat(), abschnitt
    STATE.write_text(json.dumps(st, ensure_ascii=False), encoding="utf-8")
    return abschnitt, neue
