#!/usr/bin/env python3
"""
Stellen-Monitor — Zusatzquellen (v2.1)

Ergänzt stellen_check.py um:
  - interamt.de   (Bund/Länder/Kommunen, ersetzt den Google-Umweg)
  - bpb-Infodienst Radikalisierungsprävention
  - Landesportale (Sachsen, Hessen, Niedersachsen)
  - jobs.giz.de

Dazu ein Altlasten-Filter (`ist_leiche`), der offensichtlich abgelaufene
Ausschreibungen aussortiert — das Problem, das Google und RapidJob erzeugen.

Einbinden: Datei neben stellen_check.py legen, dann in stellen_check.py
in main() die sources-Liste erweitern (siehe README-Kommentar am Dateiende).
"""

import re
import sys
import urllib.request
import urllib.error
from datetime import datetime
from html import unescape
from html.parser import HTMLParser
from urllib.parse import urljoin

USER_AGENT = "StellenMonitor/2.1 (+https://github.com/moschle/daily)"


# ─── HTTP ───
BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/127.0 Safari/537.36"
)


def _hole(url, ua, timeout):
    req = urllib.request.Request(url, headers={
        "User-Agent": ua,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "de-DE,de;q=0.9",
    })
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def _fetch(url, timeout=30):
    """Wie stellen_check.fetch_url: bei 401/403/429 einmal mit Browser-UA
    nachfassen. Runner-IPs werden von Cloudflare-Seiten geblockt."""
    try:
        raw = _hole(url, USER_AGENT, timeout)
    except urllib.error.HTTPError as e:
        if e.code not in (401, 403, 429):
            raise
        print(f"  {url} -> HTTP {e.code}, Retry mit Browser-UA", file=sys.stderr)
        raw = _hole(url, BROWSER_UA, timeout)
    for enc in ("utf-8", "iso-8859-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


# ─── Generischer Link-Ernter ───
class LinkHarvester(HTMLParser):
    """Sammelt <a href>-Elemente, deren href auf ein Muster passt,
    zusammen mit dem sichtbaren Linktext."""

    def __init__(self, href_pattern):
        super().__init__()
        self.pattern = re.compile(href_pattern, re.I)
        self.hits = []
        self._href = None
        self._buf = []
        self._depth = 0

    def handle_starttag(self, tag, attrs):
        if tag != "a":
            if self._href is not None:
                self._depth += 1
            return
        d = dict(attrs)
        href = d.get("href", "")
        if href and self.pattern.search(href):
            self._href = href
            self._buf = []
            if d.get("title"):
                self._buf.append(d["title"])
            self._depth = 0

    def handle_endtag(self, tag):
        if tag == "a" and self._href is not None:
            text = re.sub(r"\s+", " ", " ".join(self._buf)).strip()
            # title-Attribut und Linktext sind oft identisch -> Dopplung weg
            haelfte = len(text) // 2
            if len(text) > 20 and text[:haelfte].strip() == text[haelfte:].strip():
                text = text[:haelfte].strip()
            if text:
                self.hits.append((self._href, unescape(text)))
            self._href = None
            self._buf = []

    def handle_data(self, data):
        if self._href is not None:
            s = data.strip()
            if s:
                self._buf.append(s)


def _harvest(name, url, href_pattern, id_prefix, min_titel_len=12, timeout=30,
             strikt=True):
    """Holt eine HTML-Seite und erntet passende Stellenlinks.

    strikt=True (Normalbetrieb): Fehler werden GEWORFEN, damit ein 404 oder
    ein verschobenes href-Muster in der Mail als AUSFALL sichtbar wird statt
    als '0 geladen'. Genau daran sind Sachsen, Hessen, Niedersachsen und GIZ
    still gestorben.
    strikt=False: nur fuer bpb_diagnose(), die Muster reihum durchprobiert
    und dabei 0 Treffer als normales Ergebnis braucht.
    """
    try:
        html = _fetch(url, timeout=timeout)
    except Exception as e:
        if not strikt:
            print(f"{name} Fehler: {e}", file=sys.stderr)
            return []
        raise RuntimeError(f"Abruf fehlgeschlagen: {e}") from e

    p = LinkHarvester(href_pattern)
    try:
        p.feed(html)
    except Exception as e:
        if not strikt:
            print(f"{name} Parse-Fehler: {e}", file=sys.stderr)
            return []
        raise RuntimeError(f"Parse-Fehler ({len(html)} Zeichen): {e}") from e

    jobs, gesehen = [], set()
    for href, text in p.hits:
        if len(text) < min_titel_len:
            continue                      # "mehr", "Details", Navigation
        full = urljoin(url, href)
        jid = f"{id_prefix}-{re.sub(r'[^A-Za-z0-9]+', '', full)[-40:]}"
        if jid in gesehen:
            continue
        gesehen.add(jid)
        jobs.append({
            "source": name,
            "id": jid,
            "title": text[:250],
            "url": full,
            "summary": "",
            "updated": "",
        })
    if not jobs and strikt:
        raise RuntimeError(
            f"Seite geladen ({len(html)} Zeichen, {len(p.hits)} Links), aber 0 "
            f"Treffer fuer Muster {href_pattern!r} — Muster oder URL pruefen"
        )
    print(f"{name}: {len(jobs)} Stellen geladen", file=sys.stderr)
    return jobs


# ─── Altlasten-Filter ───
_MONATE = {
    "januar": 1, "februar": 2, "märz": 3, "maerz": 3, "april": 4, "mai": 5,
    "juni": 6, "juli": 7, "august": 8, "september": 9, "oktober": 10,
    "november": 11, "dezember": 12,
}


def ist_leiche(text, heute=None):
    """True, wenn die Ausschreibung erkennbar abgelaufen ist.

    Greift die vier Tells auf, die bei Google/RapidJob auffielen:
    Jahreszahl in der Kennziffer, Frist in der Vergangenheit,
    Befristungsende in der Vergangenheit, alte Gesetzesfassung.
    Konservativ: im Zweifel False, damit nichts Gutes wegfällt.
    """
    heute = heute or datetime.now()
    t = text.lower()

    # 1) Kennziffer mit Jahreszahl: "AWV-2019-048", "A 9 / 2019", "Kz 12/2021"
    for m in re.finditer(r"(?:kennziffer|kz\.?|az\.?|ausschreibung)\D{0,12}(20\d{2})", t):
        if int(m.group(1)) < heute.year - 1:
            return True
    for m in re.finditer(r"\b[a-z]{2,4}[-/\s](20\d{2})[-/]\d{2,4}\b", t):
        if int(m.group(1)) < heute.year - 1:
            return True

    # 2) Bewerbungsfrist explizit in der Vergangenheit
    for m in re.finditer(
        r"(?:frist|bewerbungsschluss|bewerben sie sich bis|bis zum)\D{0,20}"
        r"(\d{1,2})\.\s*(\d{1,2})\.\s*(20\d{2})", t):
        try:
            frist = datetime(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        except ValueError:
            continue
        if frist < heute:
            return True
    for m in re.finditer(
        r"(?:frist|bewerbungsschluss|bis zum)\D{0,20}"
        r"(\d{1,2})\.\s*([a-zä]+)\s*(20\d{2})", t):
        mon = _MONATE.get(m.group(2))
        if not mon:
            continue
        try:
            frist = datetime(int(m.group(3)), mon, int(m.group(1)))
        except ValueError:
            continue
        if frist < heute:
            return True

    # 3) Befristung endet in der Vergangenheit
    for m in re.finditer(r"befristet bis\D{0,15}(?:\d{1,2}\.\s*\d{1,2}\.\s*)?(20\d{2})", t):
        if int(m.group(1)) < heute.year:
            return True

    # 4) Gesetzesfassung mit altem Stand
    for m in re.finditer(
            r"i\.\s?d\.\s?f\.[^\d]{0,12}(?:\d{1,2}\.\s?\d{1,2}\.\s?)?(19|20)?(\d{2})\b", t):
        jahr = int(f"{m.group(1) or '20'}{m.group(2)}")
        if jahr < heute.year - 5:
            return True
    for m in re.finditer(r"in der fassung vom[^\d]{0,12}(?:\d{1,2}\.\s?\d{1,2}\.\s?)?(20\d{2})", t):
        if int(m.group(1)) < heute.year - 5:
            return True

    return False


# ─── Quelle: interamt.de — DEAKTIVIERT ───
# Befund 09.09.2026: interamt läuft auf Apache Wicket. /trefferliste
# schickt ohne Session einen 302 auf sich selbst (?0). Mit Cookie-Jar
# kommt zwar die Seite (95 KB), aber leer — die Ergebnistabelle
# (data-field="StellenangebotId", "Stellenbezeichnung", "Behoerde",
# "Bewerbungsfrist") wird erst nach einem Wicket-POST befüllt, dessen
# Komponentenpfade sich bei jedem UI-Release ändern.
# Nicht scrapebar mit vertretbarem Aufwand.
# Stattdessen: bei interamt registrieren und 2–3 Suchaufträge mit
# E-Mail-Benachrichtigung anlegen. Null Code, keine Wartung, und die
# Fristenfilterung ist dort echt.


# ─── Quelle: bpb-Infodienst Radikalisierungsprävention ───
BPB_URL = "https://www.bpb.de/themen/infodienst/304029/stellenangebote/"

# Das Muster /themen/infodienst/ war zu breit — es hat die Navigation
# eingesammelt. Welcher Pfad die Ausschreibungen trägt, lässt sich von
# außen nicht raten; der Diagnoselauf unten probiert drei Kandidaten
# durch und zeigt, welcher echte Stellen liefert.
BPB_KANDIDATEN = [
    ("intern, tiefer Pfad", r"/themen/infodienst/\d{6,}/[a-z0-9-]{15,}"),
    ("externe Links",       r"^https?://(?!www\.bpb\.de)"),
    ("PDF-Ausschreibungen", r"\.pdf$"),
]


# Solange kein Muster echte Ausschreibungen trifft: aus.
# bpb_diagnose() laeuft unabhaengig davon weiter.
BPB_AKTIV = False


def fetch_bpb_infodienst(pattern=None):
    if not BPB_AKTIV and pattern is None:
        print("bpb Infodienst: deaktiviert (Muster ungeklaert)", file=sys.stderr)
        return []
    return _harvest(
        "bpb Infodienst",
        BPB_URL,
        pattern or BPB_KANDIDATEN[0][1],
        "bpb",
        min_titel_len=25,
        strikt=pattern is None,   # Diagnoselauf darf 0 Treffer melden
    )


def bpb_diagnose():
    """Zeigt, welches href-Muster auf der bpb-Seite echte Stellen trifft."""
    print("\n=== bpb-Diagnose ===")
    for label, muster in BPB_KANDIDATEN:
        jobs = fetch_bpb_infodienst(muster)
        print(f"\n-- {label}: {len(jobs)} Treffer")
        for j in jobs[:6]:
            print(f"   {j['title'][:85]}")
            print(f"     {j['url'][:100]}")


# ─── Quelle: Deutscher Museumsbund ───
# Fundort der DHMD-Stelle. Deckt Volontariate, Kuratorisches und
# Wissenschaftskommunikation an Museen ab — kommt über keinen der
# bisherigen Feeds rein.
def fetch_museumsbund():
    return _harvest(
        "museumsbund",
        "https://www.museumsbund.de/stellenangebote/",
        r"/stellenangebote/[a-z0-9-]{12,}",
        "mbund",
        min_titel_len=15,
    )


# ─── Landesportale und GIZ — DEAKTIVIERT ───
# Befund 09.09.2026:
#   karriere.sachsen.de/stellenmarkt.html  → 404, Seite umgezogen
#   stellenmarkt.hessen.de                 → SAP UI5, Liste per JS
#   karriere.niedersachsen.de              → HTML ohne Stellen-hrefs
#   jobs.giz.de                            → SPA, im HTML stehen nur
#                                            ZZZZZ_JS_-Platzhalter
# Alle vier liefern still 0 Treffer — dieselbe Sackgasse wie die
# Schweizer Unis und die onapply-Portale von BfV und LfV Bayern.
# Für diese Häuser ist ein Suchauftrag per E-Mail der richtige Weg.


# ─── Selbsttest ───
def selbsttest():
    """python3 stellen_quellen_extra.py — prüft jede Quelle einzeln."""
    for label, fn in [
        ("museumsbund", fetch_museumsbund),
    ]:
        try:
            jobs = fn()
            print(f"\n### {label}: {len(jobs)} Treffer")
            for j in jobs[:5]:
                mark = "LEICHE" if ist_leiche(j["title"]) else "ok"
                print(f"  [{mark}] {j['title'][:90]}")
                print(f"         {j['url']}")
            if not jobs:
                print("  ⚠ 0 Treffer — URL oder href-Muster stimmt nicht mehr.")
        except Exception as e:
            print(f"\n### {label}: FEHLER {e}")


if __name__ == "__main__":
    selbsttest()
    bpb_diagnose()


# ─── Einbau in stellen_check.py ────────────────────────────────────────
#
# 1) Oben bei den Imports ergänzen:
#
#        from stellen_quellen_extra import (
#            fetch_museumsbund, fetch_bpb_infodienst, ist_leiche,
#        )
#
# 2) In main() die sources-Liste erweitern:
#
#        ("museumsbund", fetch_museumsbund),
#        ("bpb Infodienst", fetch_bpb_infodienst),
#
# 3) In der Scoring-Schleife von main(), direkt nach
#    `full_text = f"{job['title']} {job.get('summary','')}"`:
#
#        if ist_leiche(full_text):
#            continue
#
# ──────────────────────────────────────────────────────────────
