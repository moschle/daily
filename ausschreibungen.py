#!/usr/bin/env python3
"""Literarische Ausschreibungen (Stipendien, Residenzen, Preise) fuer den Stellen-Monitor.

Quelle: wortmagier.de/ausschreibungen-wettbewerbe.html (Karten mit Titel, Deadline,
Kurztext, Link). Eigene Bewertung nach Moritz' Feldern: Prosa/Roman, Uebersetzung,
Lyrik, Residenzen. Raus: Krimi, Kinder-/Jugendbuch, Liebesroman, Anthologien,
reine Verlagseinreichungen, regional beschraenkte Angebote (NRW, Hamburg u. a.).

Wird von stellen_boot.py aufgerufen; Fehler duerfen den Monitor nie stoppen.
"""
from __future__ import annotations

import json
import re
import sys
import urllib.request
from datetime import date, datetime
from html import escape, unescape
from pathlib import Path

WM_URL = "https://www.wortmagier.de/ausschreibungen-wettbewerbe.html"
SEEN_FILE = Path(__file__).parent / "ausschreibungen_seen.json"
MIN_SCORE = 2
ERINNERUNG_TAGE = 7   # schon gemeldete, passende Ausschreibungen kurz vor Fristende nochmal zeigen

PLUS = [
    (3, r"aufenthalt|residenz|stipendiatenhaus|k(ue|ü)nstlerhaus|writer.?in.?residence"),
    (2, r"arbeitsstipendium|projektstipendium|stipendi"),
    (2, r"\bprosa\b|\broman\b|erz(ae|ä)hl"),
    (2, r"(ue|ü)bersetz"),
    (1, r"\blyrik\b|gedicht"),
    (1, r"sachsen|leipzig|dresden|halle|mitteldeutsch"),
    (1, r"debüt|debut|nachwuchs"),
    (1, r"preis\b|literaturpreis"),
]
VETO = [
    r"krimi|kriminal",
    r"kinder|jugendbuch|jugendliteratur|\bkjl\b",
    r"liebesroman|new adult|romance",
    r"anthol",
    r"nur (von )?verlage|nur von verlagen",
    r"\bnrw\b|nordrhein|hamburg|hvv|bayern|baden-w(ue|ü)rttemberg|(oe|ö)sterreich|tirol|wien",
    r"nur f(ue|ü)r frauen|ausschlie(ss|ß)lich f(ue|ü)r frauen",
    r"sch(ue|ü)ler",
]
# Ausnahme: Baden-Baden (Baldreit) ist offen fuer alle, obwohl es in BW liegt
VETO_AUSNAHMEN = [r"baden-baden"]


def _get(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def _datum(text: str):
    m = re.search(r"(\d{1,2})\.(\d{1,2})\.(\d{4})", text)
    if not m:
        return None
    try:
        return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    except ValueError:
        return None


def fetch_wortmagier() -> list:
    html = _get(WM_URL)
    eintraege = []
    for block in re.split(r'<article class="card"', html)[1:]:
        m_t = re.search(r"<h2>(.*?)</h2>", block, re.S)
        if not m_t:
            continue
        titel = unescape(re.sub(r"<[^>]+>", "", m_t.group(1))).strip()
        m_d = re.search(r'<time class="deadline">(.*?)</time>', block, re.S)
        frist_text = unescape(m_d.group(1)).strip() if m_d else ""
        m_x = re.search(r'<p class="card-text">(.*?)</p>', block, re.S)
        text = unescape(re.sub(r"<[^>]+>", " ", m_x.group(1))).strip() if m_x else ""
        m_l = re.search(r'<p class="card-link"><a href="([^"]+)"', block)
        url = unescape(m_l.group(1)) if m_l else WM_URL
        eintraege.append({
            "id": "wm-" + re.sub(r"[^a-z0-9]+", "-", (url if m_l else titel).lower())[-80:],
            "titel": titel,
            "frist": _datum(frist_text),
            "frist_text": frist_text.replace("Deadline:", "").strip(),
            "text": re.sub(r"\s+", " ", text),
            "url": url,
        })
    print(f"wortmagier: {len(eintraege)} Ausschreibungen geladen", file=sys.stderr)
    return eintraege


def bewerte(e: dict):
    t = f"{e['titel']} {e['text']}".lower()
    ausnahme = any(re.search(p, t) for p in VETO_AUSNAHMEN)
    for p in VETO:
        if re.search(p, t) and not ausnahme:
            return 0, [f"veto:{p.split('|')[0]}"]
    punkte, gruende = 0, []
    for gewicht, p in PLUS:
        if re.search(p, t):
            punkte += gewicht
            gruende.append(p.split("|")[0].strip("\\b"))
    return punkte, gruende


def _lade_seen() -> dict:
    try:
        return json.loads(SEEN_FILE.read_text())
    except Exception:
        return {}


def pruefe() -> tuple:
    """Gibt (neue_treffer, erinnerungen, status) zurueck und speichert den Seen-Stand."""
    heute = date.today()
    seen = _lade_seen()
    neu, erinnern = [], []
    eintraege = fetch_wortmagier()
    for e in eintraege:
        if e["frist"] and e["frist"] < heute:
            continue
        punkte, gruende = bewerte(e)
        if punkte < MIN_SCORE:
            continue
        e["punkte"], e["gruende"] = punkte, gruende
        if e["id"] not in seen:
            neu.append(e)
            seen[e["id"]] = {"titel": e["titel"], "frist": e["frist_text"],
                             "gemeldet": heute.isoformat(), "erinnert": ""}
        elif e["frist"] and (e["frist"] - heute).days <= ERINNERUNG_TAGE \
                and not seen[e["id"]].get("erinnert"):
            erinnern.append(e)
            seen[e["id"]]["erinnert"] = heute.isoformat()
    # alte Eintraege nach 400 Tagen vergessen
    grenze = heute.toordinal() - 400
    seen = {k: v for k, v in seen.items()
            if date.fromisoformat(v.get("gemeldet", heute.isoformat())).toordinal() >= grenze}
    SEEN_FILE.write_text(json.dumps(seen, ensure_ascii=False, indent=1))
    neu.sort(key=lambda x: (x["frist"] or date.max, -x["punkte"]))
    erinnern.sort(key=lambda x: x["frist"] or date.max)
    status = f"Ausschreibungen: {len(eintraege)} gelesen, {len(neu)} neu passend, {len(erinnern)} Erinnerungen"
    return neu, erinnern, status


def html_abschnitt(neu: list, erinnern: list, status: str) -> str:
    if not neu and not erinnern:
        return ""
    def zeile(e):
        frist = escape(e["frist_text"] or "ohne Frist")
        return (f"<li><b><a href='{escape(e['url'])}'>{escape(e['titel'])}</a></b> "
                f"— Frist {frist} <span style='color:#888'>({e['punkte']} P.)</span><br>"
                f"<span style='color:#444'>{escape(e['text'][:300])}</span></li>")
    teile = ["<h2>Literarische Ausschreibungen</h2>"]
    if erinnern:
        teile.append("<p><b>Frist läuft bald ab:</b></p><ul>" + "".join(zeile(e) for e in erinnern) + "</ul>")
    if neu:
        teile.append("<p><b>Neu passend:</b></p><ul>" + "".join(zeile(e) for e in neu) + "</ul>")
    teile.append(f"<p style='color:#888;font-size:smaller'>{escape(status)} · Quelle: wortmagier.de</p>")
    return "".join(teile)


if __name__ == "__main__":
    # Testlauf ohne Speichern
    for e in fetch_wortmagier():
        p, g = bewerte(e)
        print(f"{p:>2}  {e['frist_text']:>11}  {e['titel'][:70]}  {g}")
