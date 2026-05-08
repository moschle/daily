#!/usr/bin/env python3
"""
Stellen-Monitor: tägliche Suche nach passenden Wissenschafts-/Behörden-Stellen.
Quellen: H-Soz-Kult (Atom), kultweet.de (HTML), UniBwM (HTML), service.bund.de (RSS).
Filter: Whitelist/Blacklist nach Stichwörtern.
Output: HTML-Mail an GMAIL_ADDRESS, wenn neue Treffer da sind.
State: stellen_seen.json mit gesehenen IDs (Aufräumen nach 90 Tagen).
"""

import os
import sys
import json
import re
import smtplib
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from xml.etree import ElementTree as ET
from zoneinfo import ZoneInfo

BERLIN_TZ = ZoneInfo("Europe/Berlin")
USER_AGENT = "StellenMonitor/1.0 (+https://github.com/moschle/daily)"
SEEN_FILE = Path(__file__).parent / "stellen_seen.json"
SEEN_TTL_DAYS = 90  # State-Aufräumung

# ─── Filter-Konfiguration ───
# Whitelist: mind. ein Treffer nötig (case-insensitive Wortvergleich, Substrings ok)
WHITELIST = [
    # Regional / sprachlich
    "iran", "persisch", "persophon", "tadschik", "tajik", "afghan",
    "zentralasien", "central asia", "indo-iran", "iranistik",
    "arabisch", "arabistik", "islamwiss", "islamic studies",
    "orientalist", "orientalistik", "vorder", "naher osten",
    "middle east", "near east", "morgenland", "kaukas", "kurd",
    "turkologie", "ottoman", "osman",
    # Methodisch
    "übersetz", "translation", "literarisch", "lyrik", "poet", "poesie",
    "comparativ", "komparat", "philolog",
    # Behörden / Sicherheit (BfV/BND/AA-Pipeline)
    "verfassungsschutz", "auswärtig", "auswartig", "auswaertig",
    "bundesnachrichten", "nachrichtendienst",
    "auswertung", "lage-", "extremism", "islamismus", "radikalis",
    # DH / Computational
    "digital humanities", "korpus", "computational linguist",
    # Verlag
    "lektorat", "verlag", "volontariat",
    # Migration / EZ / Maghreb (für MfD-artige Stellen)
    "maghreb", "marokko", "tunesi", "algeri", "westsahara",
    "circular migration", "rückkehrmanagement", "rueckkehr",
    "migration management", "fachkräfteeinwanderung", "fachkraefteeinwanderung",
    "internationale zusammenarbeit", "entwicklungszusammenarbeit",
]

# Blacklist: bei Treffer wird die Stelle aussortiert, auch wenn Whitelist matched
# (typisch: Stellen die nominell passen aber Profil-Hard-Stop haben)
BLACKLIST = [
    # Sozialarbeit-Pflicht (Hard-Stop laut Memory)
    "sozialarbeit erforderlich", "studium sozialer arbeit erforderlich",
    "studium der sozialen arbeit erforderlich",
    # Antike / klassische Philologie (Profil mismatch)
    "altorientalist", "ägyptolog", "egyptolog", "klassische archäolog",
    "altgriech", "altsemit", "neutestament", "alttestament",
    # Reine MINT/Medizin
    "ingenieur", "informatik vollzeit", "biotech", "pharmazi",
    "klinik ", "klinisch", "labor",
    # Praktika und Hilfskräfte (zu niederschwellig)
    "stud. hilfskraft", "studentische hilfskraft", "wiss. hilfskraft",
    "studienbegleitend", "minijob", "freiberuflich",
]

# ─── State Management ───

def load_seen():
    if not SEEN_FILE.exists():
        return {}
    try:
        with open(SEEN_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"State-Datei nicht lesbar: {e}", file=sys.stderr)
        return {}

def save_seen(seen):
    # Aufräumen: alle Einträge älter als SEEN_TTL_DAYS entfernen
    cutoff = (datetime.now(timezone.utc) - timedelta(days=SEEN_TTL_DAYS)).isoformat()
    cleaned = {k: v for k, v in seen.items() if v.get("first_seen", "9999") >= cutoff}
    removed = len(seen) - len(cleaned)
    if removed:
        print(f"State: {removed} alte Einträge entfernt", file=sys.stderr)
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(cleaned, f, ensure_ascii=False, indent=2)

def mark_seen(seen, job_id, source, title, url):
    if job_id not in seen:
        seen[job_id] = {
            "first_seen": datetime.now(timezone.utc).isoformat(),
            "source": source,
            "title": title[:200],
            "url": url,
        }

# ─── Filter ───

def matches_filters(text):
    """True wenn Whitelist trifft und Blacklist nicht trifft."""
    t = text.lower()
    if any(b in t for b in BLACKLIST):
        return False
    return any(w in t for w in WHITELIST)

# ─── HTTP Helper ───

def fetch_url(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")

# ─── Quelle 1: H-Soz-Kult Atom ───

def fetch_hsozkult():
    """H-Soz-Kult Atom-Feed parsen. Gibt Liste von dicts zurück."""
    url = "https://www.hsozkult.de/job/rss"
    try:
        data = fetch_url(url, timeout=30)
    except Exception as e:
        print(f"H-Soz-Kult Fehler: {e}", file=sys.stderr)
        return []

    jobs = []
    try:
        # Atom-Namespace
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        root = ET.fromstring(data)
        for entry in root.findall("atom:entry", ns):
            title_elem = entry.find("atom:title", ns)
            id_elem = entry.find("atom:id", ns)
            link_elem = entry.find("atom:link[@rel='alternate']", ns)
            summary_elem = entry.find("atom:summary", ns)
            updated_elem = entry.find("atom:updated", ns)

            title = (title_elem.text or "").strip() if title_elem is not None else ""
            job_id = (id_elem.text or "").strip() if id_elem is not None else ""
            url_link = link_elem.get("href", "") if link_elem is not None else ""
            summary = (summary_elem.text or "").strip() if summary_elem is not None else ""
            updated = (updated_elem.text or "").strip() if updated_elem is not None else ""

            if not title or not job_id:
                continue

            jobs.append({
                "source": "H-Soz-Kult",
                "id": job_id,
                "title": title,
                "url": url_link or job_id,
                "summary": summary,
                "updated": updated,
            })
    except ET.ParseError as e:
        print(f"H-Soz-Kult XML-Fehler: {e}", file=sys.stderr)

    print(f"H-Soz-Kult: {len(jobs)} Stellen geladen", file=sys.stderr)
    return jobs

# ─── Quelle 2: kultweet.de HTML ───

class KultweetParser(HTMLParser):
    """Sehr einfacher Parser für kultweet.de jobs.php."""
    def __init__(self):
        super().__init__()
        self.in_link = False
        self.current_href = None
        self.current_title = None
        self.in_title_attr = False
        self.collected_text = []
        self.jobs = []

    def handle_starttag(self, tag, attrs):
        attrs_d = dict(attrs)
        if tag == "a" and "href" in attrs_d:
            href = attrs_d["href"]
            title_attr = attrs_d.get("title", "")
            # kultweet-Job-Links haben title="Link zu #NUMMER - ..."
            m = re.match(r"Link zu #(\d+)\s*-\s*(.+)", title_attr)
            if m:
                self.current_href = href
                self.current_id = m.group(1)
                self.current_title_from_attr = m.group(2).strip()
                self.in_link = True
                self.collected_text = []

    def handle_endtag(self, tag):
        if tag == "a" and self.in_link:
            text_content = " ".join(self.collected_text).strip()
            text_content = re.sub(r"\s+", " ", text_content)
            self.jobs.append({
                "source": "kultweet",
                "id": f"kultweet-{self.current_id}",
                "title": self.current_title_from_attr,
                "url": self.current_href,
                "summary": text_content[:500],
                "updated": "",
            })
            self.in_link = False
            self.current_href = None
            self.collected_text = []

    def handle_data(self, data):
        if self.in_link:
            self.collected_text.append(data.strip())

def fetch_kultweet():
    """kultweet.de jobs.php parsen."""
    url = "https://www.kultweet.de/jobs.php"
    try:
        html = fetch_url(url, timeout=30)
    except Exception as e:
        print(f"kultweet Fehler: {e}", file=sys.stderr)
        return []

    parser = KultweetParser()
    try:
        parser.feed(html)
    except Exception as e:
        print(f"kultweet Parse-Fehler: {e}", file=sys.stderr)
        return []

    # Deduplizieren (manchmal gleicher Link mehrfach)
    seen_ids = set()
    deduped = []
    for j in parser.jobs:
        if j["id"] not in seen_ids:
            seen_ids.add(j["id"])
            deduped.append(j)

    print(f"kultweet: {len(deduped)} Stellen geladen", file=sys.stderr)
    return deduped

# ─── Quelle 3: UniBwM HTML ───

class UniBwMParser(HTMLParser):
    """Parser für unibw.de Stellenausschreibungs-Seiten.
    Echte Struktur: <a href="...pdf"><h2>Fakultät</h2>Stellentitel-Text</a>"""
    def __init__(self):
        super().__init__()
        self.in_relevant_link = False
        self.in_h2 = False
        self.current_href = None
        self.h2_buf = []
        self.text_buf = []
        self.jobs = []

    def handle_starttag(self, tag, attrs):
        attrs_d = dict(attrs)
        if tag == "a" and "href" in attrs_d:
            href = attrs_d["href"]
            # Nur PDF-Links innerhalb der Stellenausschreibungs-Pfade
            if ".pdf" in href and "stellenausschreibungen" in href:
                self.in_relevant_link = True
                self.current_href = href
                self.h2_buf = []
                self.text_buf = []
        elif tag == "h2" and self.in_relevant_link:
            self.in_h2 = True

    def handle_endtag(self, tag):
        if tag == "h2":
            self.in_h2 = False
        elif tag == "a" and self.in_relevant_link:
            faculty = re.sub(r"\s+", " ", " ".join(self.h2_buf)).strip()
            title_text = re.sub(r"\s+", " ", " ".join(self.text_buf)).strip()
            full_url = self.current_href
            if full_url.startswith("/"):
                full_url = "https://www.unibw.de" + full_url
            url_id = full_url.rsplit("/", 1)[-1].replace(".pdf", "")
            if title_text or faculty:
                self.jobs.append({
                    "source": "UniBwM",
                    "id": f"unibwm-{url_id}",
                    "title": f"{title_text} ({faculty})" if faculty else title_text,
                    "url": full_url,
                    "summary": faculty,
                    "updated": "",
                })
            self.in_relevant_link = False
            self.current_href = None
            self.h2_buf = []
            self.text_buf = []

    def handle_data(self, data):
        if self.in_h2:
            self.h2_buf.append(data.strip())
        elif self.in_relevant_link:
            self.text_buf.append(data.strip())

def fetch_unibwm():
    """UniBw München Stellenseite parsen."""
    url = "https://www.unibw.de/stellenausschreibungen/wissenschaftliche-mitarbeiter"
    try:
        html = fetch_url(url, timeout=30)
    except Exception as e:
        print(f"UniBwM Fehler: {e}", file=sys.stderr)
        return []
    parser = UniBwMParser()
    try:
        parser.feed(html)
    except Exception as e:
        print(f"UniBwM Parse-Fehler: {e}", file=sys.stderr)
        return []
    print(f"UniBwM: {len(parser.jobs)} Stellen geladen", file=sys.stderr)
    return parser.jobs

# ─── Quelle 4: service.bund.de RSS ───

def fetch_servicebund():
    """service.bund.de Stellen-RSS parsen."""
    url = "https://www.service.bund.de/Content/Globals/Functions/RSSFeed/RSSGenerator_Stellen.xml"
    try:
        data = fetch_url(url, timeout=30)
    except Exception as e:
        print(f"service.bund Fehler: {e}", file=sys.stderr)
        return []

    jobs = []
    try:
        # service.bund nutzt RSS 2.0 (kein Atom)
        root = ET.fromstring(data)
        for item in root.iter("item"):
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            desc = (item.findtext("description") or "").strip()
            guid = (item.findtext("guid") or link).strip()
            if not title or not link:
                continue
            # description enthält oft HTML — entkernen
            desc_clean = unescape(re.sub(r"<[^>]+>", " ", desc))
            desc_clean = re.sub(r"\s+", " ", desc_clean).strip()
            jobs.append({
                "source": "service.bund.de",
                "id": guid or link,
                "title": title,
                "url": link,
                "summary": desc_clean[:500],
                "updated": "",
            })
    except ET.ParseError as e:
        print(f"service.bund XML-Fehler: {e}", file=sys.stderr)

    print(f"service.bund.de: {len(jobs)} Stellen geladen", file=sys.stderr)
    return jobs

# ─── Mail ───

def build_html_mail(new_hits, total_seen, sources_status):
    """HTML-Body bauen."""
    today = datetime.now(BERLIN_TZ).strftime("%a, %d.%m.%Y")
    parts = [
        "<html><head><meta charset='utf-8'></head><body style='font-family:sans-serif;max-width:800px;'>",
        f"<h1>Stellen-Monitor — {today}</h1>",
    ]
    if not new_hits:
        parts.append("<p><em>Keine neuen passenden Stellen.</em></p>")
    else:
        parts.append(f"<p><strong>{len(new_hits)} neue passende Stellen</strong>:</p>")
        # Sortieren nach Quelle, dann Titel
        by_source = {}
        for h in new_hits:
            by_source.setdefault(h["source"], []).append(h)
        for source in sorted(by_source.keys()):
            parts.append(f"<h2>{source}</h2><ul>")
            for h in by_source[source]:
                title_safe = h["title"].replace("<", "&lt;").replace(">", "&gt;")
                summary_safe = h.get("summary", "").replace("<", "&lt;").replace(">", "&gt;")[:300]
                url_safe = h["url"]
                parts.append(
                    f"<li style='margin-bottom:1em;'>"
                    f"<a href='{url_safe}'><strong>{title_safe}</strong></a>"
                    + (f"<br><span style='color:#555;font-size:0.9em;'>{summary_safe}</span>" if summary_safe else "")
                    + "</li>"
                )
            parts.append("</ul>")

    parts.append("<hr style='margin-top:2em;'>")
    parts.append("<p style='color:#888;font-size:0.85em;'>Quellen-Status:<br>")
    for s, count in sources_status.items():
        parts.append(f"{s}: {count} geladen<br>")
    parts.append(f"Insgesamt im Gedächtnis: {total_seen} Stellen<br>")
    parts.append("</p>")
    parts.append("</body></html>")
    return "\n".join(parts)

def send_mail(html_body, subject, count):
    """Mail an GMAIL_ADDRESS senden (Self-Mail oder andere Empfänger-Adresse)."""
    ga = os.environ.get("GMAIL_ADDRESS")
    gp = os.environ.get("GMAIL_APP_PASSWORD")
    to_addr = os.environ.get("STELLEN_RECIPIENT") or ga
    if not all([ga, gp, to_addr]):
        print("Mail-Secrets fehlen — überspringe Versand", file=sys.stderr)
        return
    msg = MIMEMultipart("alternative")
    msg["From"] = ga
    msg["To"] = to_addr
    msg["Subject"] = subject
    # Plain-Text-Fallback
    plain = re.sub(r"<[^>]+>", " ", html_body)
    plain = re.sub(r"\s+", " ", plain).strip()
    msg.attach(MIMEText(plain, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(ga, gp)
        smtp.sendmail(ga, to_addr, msg.as_string())
    print(f"Stellen-Mail an {to_addr} gesendet ({count} neue Treffer)")

# ─── Main ───

def main():
    seen = load_seen()
    print(f"State geladen: {len(seen)} bekannte Stellen", file=sys.stderr)

    sources = [
        ("H-Soz-Kult", fetch_hsozkult),
        ("kultweet", fetch_kultweet),
        ("UniBwM", fetch_unibwm),
        ("service.bund.de", fetch_servicebund),
    ]

    all_jobs = []
    sources_status = {}
    for name, fetch_fn in sources:
        try:
            jobs = fetch_fn()
            sources_status[name] = len(jobs)
            all_jobs.extend(jobs)
        except Exception as e:
            print(f"Quelle {name} komplett gescheitert: {e}", file=sys.stderr)
            sources_status[name] = -1  # -1 = Fehler

    # Filter und Diff gegen State
    new_hits = []
    for job in all_jobs:
        full_text = f"{job['title']} {job.get('summary', '')}"
        if not matches_filters(full_text):
            continue
        if job["id"] in seen:
            continue
        new_hits.append(job)
        mark_seen(seen, job["id"], job["source"], job["title"], job["url"])

    print(f"Neue Treffer: {len(new_hits)} von {len(all_jobs)} insgesamt", file=sys.stderr)

    # State immer speichern (auch bei null Treffern, um TTL-Aufräumung zu triggern)
    save_seen(seen)

    # Mail-Versand: nur wenn echte Treffer ODER wenn DEBUG=1
    debug = os.environ.get("DEBUG_STELLEN") == "1"
    if new_hits or debug:
        html = build_html_mail(new_hits, len(seen), sources_status)
        subject = f"Stellen-Monitor: {len(new_hits)} neue Treffer" if new_hits else "Stellen-Monitor: keine Treffer (Debug)"
        send_mail(html, subject, len(new_hits))
    else:
        print("Keine neuen Treffer, keine Mail.", file=sys.stderr)

if __name__ == "__main__":
    main()
