"""Auswertungstraining für den Vortest Polizei Berlin (bis sprachuebung.PRUEFUNG_BIS).

Jeden Tag zwei echte, aktuelle Telegram-Posts im Original (ein staatsnaher Kanal, im Wechsel
ein kritischer/neutraler), dazu die Aufgabe nach dem Auswertungsschema. Die Musterlösung
kommt am nächsten Tag. Wichtige unbekannte Wörter gehen ins Anki-Paket des Tages.
Zustand liegt außerhalb des Repos (/automat/auswertung.json), damit ein Deploy ihn nicht löscht.
"""
from __future__ import annotations

import html
import json
import os
import re
import urllib.request
from datetime import date
from pathlib import Path

STATE = Path(os.environ.get("AUSWERTUNG_STATE") or (
    "/automat/auswertung.json" if Path("/automat").exists() else Path(__file__).with_name("auswertung_state.json")))
KANAELE_KRITISCH = ["bbcpersian", "iranintltv"]   # geprüft 18.11.2026 über t.me/s/
KANAL_STAATSNAH = "farsna"                        # Tasnimnews hat keine Web-Vorschau
MIN_WOERTER = 30

SCHEMA = ("Schema: Kernaussage · Quelle · Feststellungen (Wer/Was/Wann/Wo/Wie) · "
          "Bewertung (Quelle A–F / Information 1–6, Perspektive mit Belegwörtern) · "
          "Einschätzung · Relevanz und Empfehlung · offene Punkte")


def _posts(kanal: str) -> list[dict]:
    req = urllib.request.Request(f"https://t.me/s/{kanal}", headers={"User-Agent": "Mozilla/5.0"})
    roh = urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "replace")
    out = []
    for stueck in roh.split('data-post="')[1:]:
        pid = stueck.split('"', 1)[0]
        m = re.search(r'<div class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>', stueck, re.S)
        if not m:
            continue
        text = re.sub(r"<br\s*/?>", "\n", m.group(1))
        text = html.unescape(re.sub(r"<[^>]+>", "", text)).strip()
        t = re.search(r'<time datetime="([^"]+)"', stueck)
        out.append({"id": pid, "text": text, "zeit": t.group(1) if t else ""})
    return out


def _neuester(kanal: str) -> dict | None:
    for p in reversed(_posts(kanal)):
        if len(p["text"].split()) >= MIN_WOERTER:
            return {**p, "kanal": kanal}
    return None


def _laden() -> dict:
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def erzeuge(complete) -> tuple[str, list[tuple[str, str]]]:
    import sprachuebung as su
    heute = date.today().isoformat()
    st = _laden()
    if st.get("datum") == heute:                      # zweiter Lauf am selben Tag
        return st.get("abschnitt", ""), []

    texte = []
    for k in (KANAL_STAATSNAH, KANAELE_KRITISCH[date.today().toordinal() % 2]):
        try:
            p = _neuester(k)
            if p:
                texte.append(p)
        except Exception as e:
            print(f"Auswertung: {k} nicht erreichbar ({e})")
    if not texte:
        return "", []

    auftrag = "\n\n".join(f"TEXT {i} (Telegram @{t['kanal']}, {t['zeit']}):\n{t['text']}"
                          for i, t in enumerate(texte, 1))
    antwort = su._json(complete(
        "Du bist Ausbilder für OSINT-Analysten der Polizei. Werte jeden der folgenden echten persischen "
        "Telegram-Posts als Musterlösung aus, auf Deutsch, knapp (max. 8 Zeilen pro Text), nach diesem "
        f"Schema: {SCHEMA}. Trenne Feststellungen (nur was im Text steht) streng von Einschätzungen. "
        "Nenne bei der Perspektive die persischen Belegwörter. Erfinde nichts.\n"
        "Gib zusätzlich pro Text bis zu 6 wichtige, nachrichtentypische Wörter oder Wendungen "
        "(Persisch mit Vokalzeichen, Deutsch) an, die ein B1-Lerner wahrscheinlich nicht kennt.\n"
        'Antworte nur als JSON: {"loesungen": ["...", "..."], "woerter": [{"fa": "...", "de": "..."}]}\n\n'
        + auftrag, max_tokens=2500))

    kopf = "AUSWERTUNG (Vortest-Training: 15 Min. pro Text, schriftlich auf Deutsch)\n" + SCHEMA
    teile = [f"Text {i} – Telegram @{t['kanal']} · {t['zeit']} · t.me/{t['id']}\n{t['text']}"
             for i, t in enumerate(texte, 1)]
    abschnitt = kopf + "\n\n" + "\n\n".join(teile)
    if st.get("loesung"):
        abschnitt += "\n\nMUSTERLÖSUNG VON GESTERN\n" + st["loesung"]

    loesung = "\n\n".join(f"Text {i}: {l}" for i, l in enumerate(antwort.get("loesungen", []), 1))
    STATE.write_text(json.dumps({"datum": heute, "abschnitt": abschnitt, "loesung": loesung},
                                ensure_ascii=False), encoding="utf-8")

    bekannt = set()
    if su.BEKANNT_FILE.exists():
        for e in json.loads(su.BEKANNT_FILE.read_text(encoding="utf-8")):
            bekannt |= su._formen(e.get("word", ""))
    neue = [(w["fa"], w["de"]) for w in antwort.get("woerter", [])
            if w.get("fa") and w.get("de") and not (su._formen(w["fa"]) <= bekannt)]
    return abschnitt, neue
