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
from datetime import datetime
from html import unescape
from html.parser import HTMLParser
from urllib.parse import urljoin

USER_AGENT = "StellenMonitor/2.1 (+https://github.com/moschle/daily)"


# ─── HTTP ───
def _fetch(url, timeout=30):
    req = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "de-DE,de;q=0.9",
    })
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
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
            if text:
                self.hits.append((self._href, unescape(text)))
            self._href = None
            self._buf = []

    def handle_data(self, data):
        if self._href is not None:
            s = data.strip()
            if s:
                self._buf.append(s)


def _harvest(name, url, href_pattern, id_prefix, min_titel_len=12, timeout=30):
    """Holt eine HTML-Seite und erntet passende Stellenlinks."""
    try:
        html = _fetch(url, timeout=timeout)
    except Exception as e:
        print(f"{name} Fehler: {e}", file=sys.stderr)
        return []

    p = LinkHarvester(href_pattern)
    try:
        p.feed(html)
    except Exception as e:
        print(f"{name} Parse-Fehler: {e}", file=sys.stderr)
        return []

    jobs, gesehen = [], set()
    for href, text in p.hits:
        if len(text) < min_titel_len:
            continue
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
    print(f"{name}: {len(jobs)} Stellen geladen", file=sys.stderr)
    return jobs


# ─── Altlasten-Filter ───
_MONATE = {
    "januar": 1, "februar": 2, "märz": 3, "maerz": 3, "april": 4, "mai": 5,
    "juni": 6, "juli": 7, "august": 8, "september": 9, "oktober": 10,
    "november": 11, "dezember": 12,
}


def ist_leiche(text, heute=None):
    """True, wenn die Ausschreibung erkennbar abgelaufen ist."""
    heute = heute or datetime.now()
    t = text.lower()

    for m in re.finditer(r"(?:kennziffer|kz\.?|az\.?|ausschreibung)\D{0,12}(20\d{2})", t):
        if int(m.group(1)) < heute.year - 1:
            return True
    for m in re.finditer(r"\b[a-z]{2,4}[-/\s](20\d{2})[-/]\d{2,4}\b", t):
        if int(m.group(1)) < heute.year - 1:
            return True

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

    for m in re.finditer(r"befristet bis\D{0,15}(?:\d{1,2}\.\s*\d{1,2}\.\s*)?(20\d{2})", t):
        if int(m.group(1)) < heute.year:
            return True

    for m in re.finditer(
            r"i\.\s?d\.\s?f\.[^\d]{0,12}(?:\d{1,2}\.\s?\d{1,2}\.\s?)?(19|20)?(\d{2})\b", t):
        jahr = int(f"{m.group(1) or '20'}{m.group(2)}")
        if jahr < heute.year - 5:
            return True
    for m in re.finditer(r"in der fassung vom[^\d]{0,12}(?:\d{1,2}\.\s?\d{1,2}\.\s?)?(20\d{2})", t):
        if int(m.group(1)) < heute.year - 5:
            return True

    return False


INTERAMT_SUCHEN = [
    ("interamt Islamwiss/Orient",
     "https://interamt.de/koop/app/trefferliste?"
     "suchbegriff=Islamwissenschaft&umkreis=bundesweit"),
    ("interamt Verfassungsschutz",
     "https://interamt.de/koop/app/trefferliste?"
     "suchbegriff=Verfassungsschutz+Auswertung&umkreis=bundesweit"),
    ("interamt Wissenschaft/Kultur",
     "https://interamt.de/koop/app/trefferliste?"
     "suchbegriff=wissenschaftlicher+Mitarbeiter+Kultur&umkreis=bundesweit"),
]


def fetch_interamt():
    jobs = []
    for name, url in INTERAMT_SUCHEN:
        jobs.extend(_harvest(name, url, r"stellenangebot\?id=|/stellenangebot/", "interamt"))
    return jobs


def fetch_bpb_infodienst():
    return _harvest(
        "bpb Infodienst",
        "https://www.bpb.de/themen/infodienst/304029/stellenangebote/",
        r"/themen/infodienst/",
        "bpb",
        min_titel_len=20,
    )


LANDESPORTALE = [
    ("karriere.sachsen", "https://www.karriere.sachsen.de/stellenmarkt.html",
     r"stellenangebot|/stelle/|stellenausschreibung"),
    ("Stellenmarkt Hessen", "https://stellenmarkt.hessen.de/",
     r"/stellenangebot|/jobs?/"),
    ("Karriere Niedersachsen", "https://www.karriere.niedersachsen.de/stellenangebote/",
     r"/stellenangebote/"),
]


def fetch_landesportale():
    jobs = []
    for name, url, pattern in LANDESPORTALE:
        jobs.extend(_harvest(name, url, pattern, name.split(".")[0].lower()))
    return jobs


def fetch_giz():
    return _harvest(
        "jobs.giz.de",
        "https://jobs.giz.de/index.php?ac=search_result",
        r"ac=jobad|jobad&|/jobad/",
        "giz",
    )


def selbsttest():
    for label, fn in [
        ("interamt", fetch_interamt),
        ("bpb", fetch_bpb_infodienst),
        ("Landesportale", fetch_landesportale),
        ("GIZ", fetch_giz),
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
