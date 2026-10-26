"""Zweite Bewertungsstufe des Stellen-Monitors: Claude liest die Ausschreibung.

Stufe 1 (stellen_boot.py) holt alle Stellen und filtert Leichen. Hier werden
noch nicht bewertete Stellen mit dem Text ihrer Detailseite an Claude geschickt
und gegen Moritz' Profil bewertet (0-10, Muss-Luecken, Ort, Umfang, Frist).

Ergebnisse landen in stellen_llm_cache.json, damit jede Stelle nur einmal
bewertet wird. Faellt die API aus, laeuft der Monitor mit dem Schlagwort-Score
weiter (aufgerufen in try/except).

Parallelbetrieb seit 26.10.2026: Die Mail zeigt beide Bewertungen.
"""
from __future__ import annotations

import html as _html
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

import stellen_check as sc

CACHE = Path(__file__).with_name("stellen_llm_cache.json")
MODELLE = [m.strip() for m in os.environ.get("STELLEN_MODELL", "").split(",") if m.strip()] or [
    "claude-haiku-5-5",
    "claude-haiku-4-5",
]
API = "https://api.anthropic.com/v1/messages"
MAX_PRO_LAUF = int(os.environ.get("STELLEN_LLM_MAX", "150"))   # Stellen pro Lauf
BATCH = 6                                                       # Stellen pro API-Aufruf
DETAIL_ZEICHEN = 5000
MIN_LLM = 6                                                     # ab hier in der Mail

# Grobe Vorfilter: das bekommt Claude gar nicht erst zu sehen
VETO = re.compile(
    r"werkstudent|praktik|azubi|ausbildung zu|duales studium|\bfsj\b|bufdi|"
    r"pflegefach|pflegekraft|erzieher|kita|sozialpädagog|sozialarbeit|therapeut|"
    r"software|entwickler|developer|devops|informatiker|administrator|"
    r"elektro|ingenieur|techniker|hausmeister|reinigung|buchhalt|steuerfach|"
    r"professur|\bw ?[23]\b|lehrkraft für|minijob|aushilfe",
    re.I,
)

PROFIL = """Du bewertest Stellenausschreibungen für Moritz Schlenstedt (30, wohnt in Leipzig).

PROFIL
- M.A. Arabistik/Islamwissenschaft & Deutsche Literatur und Kultur, MLU Halle (1,2; Masterarbeit 1,0, erscheint 2027 als Monografie bei De Gruyter Brill). B.A. Literarisches Schreiben, DLL Leipzig (1,4). Davor Arabistik in Leipzig. Ausbildung zum Winzer (VDP-Weingut).
- Promotion in Islamwissenschaft an der MLU Halle in Vorbereitung (tadschikische Lyrik, freier Vers). Keine Promotion abgeschlossen.
- Wiss. Hilfskraft Germanistik MLU 2024–2026: Recherche zum KZ Langenstein-Zwieberge (2 eigene Beiträge, Mitteldeutscher Verlag 2026; MfS-Akten), skriptgestützte Datenauswertung, Redigieren.
- Gründer/Vorsitz Kulturverein Warte für Kultur e.V. seit 2018: >30 Lesungen/Veranstaltungen kuratiert und moderiert, Förderanträge kommunal bis Bund, Buchhaltung.
- Ressortleiter Kultur, Radio mephisto 97.6 (2021–2022). DaF-Lehrkraft 2025. Pflege-/Assistenzjobs. Rettungssanitäter.
- Feldforschung Tadschikistan/Pamir/Xinjiang 2025 (3 Monate), Aufenthalte in sahrauischen Flüchtlingslagern (Algerien). IJFD Frankreich.
- Sprachen: Deutsch (Mutterspr.), Englisch und Französisch fließend, Persisch/Tadschikisch und Arabisch fortgeschritten. Kein Polnisch, Russisch, Türkisch.
- Technik: Python, Web-Scraping, Datenpipelines, SQL, Speech-to-Text, maschinelle Übersetzung.
- Literarisch: Lyriker (3x Bundespreis lyrix), Übersetzer tadschikischer/persischer Lyrik. Sänger (Chor, Band), Bildhauer (freiberuflich).
- Böll-Alumnus. Interesse auch an Sicherheitsbehörden (BfV-Talentpool Farsi/Dari), Bundeswehr-Reserve.
- Kaum klassische Berufserfahrung in Vollzeit; keine Leitungserfahrung im Angestelltenverhältnis.

PASSENDE FELDER (Beispiele, nicht abschließend)
Literatur- und Kulturvermittlung, Literaturhäuser, Lektorat/Redaktion, Verlage, Übersetzung, Gedenkstätten/Erinnerungskultur/Provenienz/Archive mit Inhaltsbezug,
Islamwissenschaft/Iran/Afghanistan/Zentralasien/MENA, Analyse (auch Sicherheitsbehörden), politische Bildung, Förderwesen/Stiftungen, Promotionsstellen in Islamwiss./Literaturwiss.,
Wissenschaftskommunikation, Musikvermittlung, Kultur-Digitalisierung, DaF.

ORT UND UMFANG
- Gern: Schweiz (alle Orte), München, Berlin, Köln. Zur Not Frankfurt oder Stadtnähe. Leipzig, Dresden, zur Not Halle in Ordnung.
- Alle anderen Orte nur, wenn nicht Vollzeit vor Ort (Teilzeit, viel mobiles Arbeiten, Remote).
- Teilzeit ist ihm willkommen (Promotion läuft nebenher).

BEWERTUNG 0–10
10 = passt genau, Muss-Kriterien erfüllt, Ort ok. 6 = realistische Bewerbung lohnt sich. 3 = nur thematisch nah oder deutliche Lücken. 0 = passt nicht.
Ziehe kräftig ab, wenn ein MUSS-Kriterium sicher nicht erfüllt ist (z. B. abgeschlossene Promotion, mehrjährige einschlägige Berufserfahrung, bestimmtes Fachstudium wie Kunstgeschichte/Jura/BWL, Staatsexamen, fehlende Pflichtsprache, Leitungserfahrung) oder der Ort nach den Regeln oben nicht geht. Frist abgelaufen (heute: {heute}) → 0.

AUSGABE
Nur ein JSON-Array, ein Objekt je Stelle, in derselben Reihenfolge, ohne weiteren Text:
[{{"id": "...", "score": 0-10, "grund": "ein Satz, warum", "luecken": "fehlende Muss-Kriterien oder leer",
  "ort": "...", "umfang": "z. B. 50 %, 20 h, Vollzeit", "remote": "ja/teilweise/nein/unklar",
  "verguetung": "z. B. E13 TV-L oder leer", "frist": "TT.MM.JJJJ oder leer"}}]
"""


def _lade_cache() -> dict:
    try:
        return json.loads(CACHE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _speichere_cache(cache: dict) -> None:
    CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=0), encoding="utf-8")


_ZW = dict.fromkeys(list(range(0x200B, 0x2010)) + [0xAD], None)


def _detailtext(job: dict) -> str:
    try:
        roh = sc.fetch_url(job["url"], timeout=25)
    except Exception as e:
        return f"(Detailseite nicht ladbar: {type(e).__name__})"
    roh = re.sub(r"(?is)<(script|style|nav|footer|header)[^>]*>.*?</\1>", " ", roh)
    txt = _html.unescape(re.sub(r"<[^>]+>", " ", roh)).translate(_ZW)
    txt = re.sub(r"\s+", " ", txt)
    # Den Teil ab der ersten typischen Ausschreibungsformulierung nehmen
    m = re.search(r"(Ihre Aufgaben|Aufgaben|Wir suchen|sucht zum|Your tasks|Das bieten wir|Ihr Profil)", txt)
    start = max(0, m.start() - 800) if m else 0
    return txt[start:start + DETAIL_ZEICHEN]


def _frage(prompt: str) -> str:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY fehlt")
    letzter = None
    for modell in MODELLE:
        body = json.dumps({"model": modell, "max_tokens": 4000,
                           "messages": [{"role": "user", "content": prompt}]}).encode()
        req = urllib.request.Request(API, data=body, headers={
            "Content-Type": "application/json", "x-api-key": key,
            "anthropic-version": "2023-06-01"})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                data = json.loads(r.read())
            return next(b["text"] for b in data["content"] if b.get("type") == "text")
        except urllib.error.HTTPError as e:
            letzter = f"HTTP {e.code} {modell}: {e.read()[:300]!r}"
        except Exception as e:
            letzter = f"{type(e).__name__} {modell}: {e}"
    raise RuntimeError(letzter)


def _parse(antwort: str) -> list:
    m = re.search(r"\[.*\]", antwort, re.S)
    return json.loads(m.group(0)) if m else []


def bewerte(jobs: list, vorrang: dict | None = None) -> tuple[list, str]:
    """Bewertet neue Stellen. Gibt (neu_bewertete Treffer >= MIN_LLM, Statuszeile) zurück.

    vorrang: id -> Schlagwort-Score, damit bei Kappung die vielversprechenden zuerst drankommen.
    """
    cache = _lade_cache()
    offen = [j for j in jobs if j["id"] not in cache
             and not VETO.search(j["title"].translate(_ZW))]
    vorrang = vorrang or {}
    offen.sort(key=lambda j: -vorrang.get(j["id"], 0))
    rest = max(0, len(offen) - MAX_PRO_LAUF)
    offen = offen[:MAX_PRO_LAUF]
    heute = datetime.now(sc.BERLIN_TZ).strftime("%d.%m.%Y")
    kopf = PROFIL.format(heute=heute)
    treffer, fehler = [], 0
    for i in range(0, len(offen), BATCH):
        teil = offen[i:i + BATCH]
        bloecke = []
        for j in teil:
            bloecke.append(f"### id: {j['id']}\nTitel: {j['title'].translate(_ZW)}\n"
                           f"Quelle: {j['source']}\nText: {_detailtext(j)}")
        try:
            res = _parse(_frage(kopf + "\n\nSTELLEN\n\n" + "\n\n".join(bloecke)))
        except Exception as e:
            fehler += 1
            print(f"LLM-Bewertung gescheitert: {e}", file=sys.stderr)
            if fehler >= 3:
                break
            continue
        nach_id = {str(r.get("id")): r for r in res if isinstance(r, dict)}
        for j in teil:
            r = nach_id.get(j["id"])
            if not r:
                continue
            r["titel"], r["url"], r["quelle"] = j["title"].translate(_ZW), j["url"], j["source"]
            r["datum"] = heute
            cache[j["id"]] = r
            try:
                if float(r.get("score", 0)) >= MIN_LLM:
                    treffer.append(r)
            except (TypeError, ValueError):
                pass
        _speichere_cache(cache)
    status = (f"KI-Bewertung: {len(offen)} Stellen bewertet, {len(treffer)} ab {MIN_LLM}/10"
              + (f", {rest} auf später verschoben" if rest else "")
              + (f", {fehler} Fehlaufrufe" if fehler else ""))
    return sorted(treffer, key=lambda r: -float(r.get("score", 0))), status


def html_abschnitt(treffer: list, status: str) -> str:
    def e(s):
        return _html.escape(str(s or ""))
    teile = [f"<h2>KI-Bewertung (Testbetrieb)</h2><p style='color:#666;font-size:0.85em;'>{e(status)}</p>"]
    if not treffer:
        teile.append("<p><em>Keine neuen Stellen ab 6/10.</em></p>")
    for r in treffer:
        farbe = "#1a7a1a" if float(r.get("score", 0)) >= 8 else "#2a5a9a"
        zeile = " · ".join(x for x in [e(r.get("ort")), e(r.get("umfang")), e(r.get("verguetung")),
                                        ("Remote: " + e(r.get("remote"))) if r.get("remote") else "",
                                        ("Frist " + e(r.get("frist"))) if r.get("frist") else ""] if x)
        teile.append(
            f"<div style='margin-bottom:1.1em;padding:0.4em;border-left:3px solid {farbe};'>"
            f"<div style='font-size:0.8em;color:{farbe};'><strong>{e(r.get('score'))}/10</strong> · {e(r.get('quelle'))}</div>"
            f"<a href='{e(r.get('url'))}'><strong>{e(r.get('titel'))}</strong></a>"
            f"<br><span style='font-size:0.9em;'>{zeile}</span>"
            f"<br><span style='color:#333;font-size:0.9em;'>{e(r.get('grund'))}</span>"
            + (f"<br><span style='color:#a33;font-size:0.85em;'>Lücken: {e(r.get('luecken'))}</span>" if r.get("luecken") else "")
            + "</div>")
    return "".join(teile)
