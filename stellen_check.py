#!/usr/bin/env python3
"""
Stellen-Monitor: tägliche Suche nach passenden Wissenschafts-/Behörden-Stellen.
Quellen: H-Soz-Kult (Atom), kultweet.de (HTML), UniBwM (HTML), service.bund.de (RSS).
Filter: Score-basiert mit Wortgrenzen-Matching + Hard-Blacklist.
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
from urllib.parse import urljoin
from xml.etree import ElementTree as ET
from zoneinfo import ZoneInfo

BERLIN_TZ = ZoneInfo("Europe/Berlin")
USER_AGENT = "StellenMonitor/1.2 (+https://github.com/moschle/daily)"
SEEN_FILE = Path(__file__).parent / "stellen_seen.json"
SEEN_TTL_DAYS = 90

# ─── Filter-Konfiguration: Score-basiert mit Wortgrenzen ───
# Kategorie-Wertesystem: jede Kategorie liefert max. einmal ihren Weight.
# Stelle passiert, wenn Summe der Kategorie-Scores >= MIN_SCORE.
# WICHTIG: Begriffe werden mit Wortgrenzen gematcht (\b...\b),
# damit "iran" nicht in "Tirana" und "algeri" nicht in "Sozialgericht" matched.
# Mehrwort-Phrasen ("digital humanities") werden als ganze Phrase gesucht.

MIN_SCORE = 3

CATEGORIES = {
    # ── Kerngebiet: 4 Punkte (löst alleine aus) ──
    "iran_islam_kern": {
        "weight": 4,
        "terms": [
            r"iran", r"iranistik", r"iranist\w*", r"persisch\w*",
            r"persophon\w*", r"tadschik\w*", r"tajik\w*", r"afghan\w*",
            r"zentralasien\w*", r"central asia", r"indo-iran\w*",
            r"islamwiss\w*", r"islamic studies", r"islamistik",
            r"arabisch\w*", r"arabist\w*",  # NEU: arabisch als Kern (UniBwM-Stelle)
            r"orientalist\w*", r"orientalistik",
            r"turkologie", r"turkolog\w*",
            r"kurd\w*",  # bleibt — wenn "Kurdistan" matched, ist das oft relevant; Yekmal jetzt in Hard-Blacklist
        ],
    },
    # ── Sicherheit/Behörden: 4 Punkte ──
    "behörden_kern": {
        "weight": 4,
        "terms": [
            r"verfassungsschutz", r"bundesnachrichten\w*",
            r"auswärtig\w*", r"auswartig\w*", r"auswaertig\w*",
            r"auswärtiges amt", r"auswaertiges amt",
            r"nachrichtendienst\w*",
            r"extremism\w*", r"islamismus", r"radikalis\w*",
        ],
    },
    # ── Region Vorderer Orient/Mittlerer Osten: 3 Punkte ──
    "region_orient": {
        "weight": 3,
        "terms": [
            r"vorderer orient", r"vorder orient",
            r"naher osten", r"mittlerer osten",
            r"middle east", r"near east", r"morgenland\w*",
            r"maghreb", r"marokko\w*", r"tunesi\w*", r"algeri\w*",
            r"westsahara",
            r"ottoman\w*", r"osman\w*",
        ],
    },
    # ── Übersetzung & Lyrik: 3 Punkte ──
    "übersetzung_lyrik": {
        "weight": 3,
        "terms": [
            r"literarische übersetzung", r"literarisches übersetzen",
            r"übersetzungswiss\w*", r"übersetzungswerkstatt",
            r"lyrik\w*", r"poesie", r"persische lyrik", r"lyriker\w*",
        ],
    },
    # ── DH / Computational: 3 Punkte ──
    "digital_humanities": {
        "weight": 3,
        "terms": [
            r"digital humanities", r"digital-humanities",
            r"computational linguist\w*",
            r"korpuslinguist\w*", r"korpus-",
            r"computerphilolog\w*",
        ],
    },
    # ── Migration/EZ Maghreb-spezifisch: 3 Punkte ──
    "migration_ez": {
        "weight": 3,
        "terms": [
            r"circular migration", r"rückkehrmanagement",
            r"rueckkehrmanagement",
            r"migration management", r"fachkräfteeinwanderung",
            r"fachkraefteeinwanderung",
            r"entwicklungszusammenarbeit", r"internationale zusammenarbeit",
        ],
    },
    # ── Erinnerungskultur / Gedenkstätten: 2 Punkte ──
    "erinnerungskultur": {
        "weight": 2,
        "terms": [
            r"gedenkstätte\w*", r"gedenk- und bildung\w*", r"gedenkstaette\w*",
            r"erinnerungskultur", r"erinnerungsort\w*",
            r"konzentrationslager", r"\bkz-",
            r"kulturgutverluste", r"kolonial\w*",
            r"ettersberg", r"buchenwald",
            r"andreasstraße", r"andreasstrasse",
            r"langenstein", r"zwieberge",
            r"stiftung topographie", r"stasi-unterlagen",
            r"denkmalpflege", r"stolperstein\w*",
            r"ns-dokumentation\w*", r"ns-zeit",
            r"holocaust", r"shoah",
        ],
    },
    # ── DDR-Literatur / Ostdeutsche Kultur: 2 Punkte ──
    "ostdeutsche_kultur": {
        "weight": 2,
        "terms": [
            r"ddr-museum", r"ddr museum", r"ddr-literatur",
            r"ddr-geschichte",
            r"ostdeutsch\w*", r"neues deutschland",
            r"verlag 8\. mai",
            r"melodie & rhythmus", r"melodie und rhythmus",
            r"stiftung aufarbeitung",
            r"sonntag", r"der sonntag",  # Moritz hat zur Sonntag geforscht
        ],
    },
    # ── Klassische Musik / Chormusik: 2 Punkte ──
    "klassische_musik": {
        "weight": 2,
        "terms": [
            r"klassische musik", r"philharmoniker", r"philharmonie",
            r"chormusik", r"chorprojekt\w*", r"kammermusik",
            r"alte musik", r"neue musik",
            r"haus der kulturen der welt",
            r"musik und klangpraktiken", r"musik & klangpraktiken",
            r"kreuzchor", r"thomanerchor",
            r"barockmusik", r"liedgut",
        ],
    },
    # ── Verlagswelt (gezielt): 2 Punkte ──
    "verlag_geistes": {
        "weight": 2,
        "terms": [
            r"lektorat belletristik", r"belletristik-lektorat",
            r"lektorat geisteswiss\w*", r"lektorat sachbuch",
            r"verlagslektorat", r"lyriklektorat",
            r"redaktionsvolontariat", r"verlagsvolontariat",
            r"wissenschaftslektorat",
            r"literaturvermittlung", r"literaturhaus",
        ],
    },
    # ── Kuratorisches / Wissenschaftliches Volo: 2 Punkte ──
    "kuratorisch_wiss_volo": {
        "weight": 2,
        "terms": [
            r"kuratorisches volontariat", r"wissenschaftliches volontariat",
            r"wiss\. volontariat", r"wiss\. volontär\w*",
            r"wissenschaftliche volontär\w*",
            r"kurator\w*", r"kuratierung",
            r"ausstellungskonzept\w*", r"sammlungsleitung",
        ],
    },
    # ── Schwache Signale: 1 Punkt ──
    "schwach_methodisch": {
        "weight": 1,
        "terms": [
            r"philolog\w*", r"kulturwiss\w*", r"geisteswiss\w*",
            r"literaturwiss\w*", r"interkultur\w*",
            r"regionalstud\w*", r"area studies",
            r"übersetz\w*", r"translation",
            r"deutsch als fremdsprache", r"\bdaf\b", r"\bdaz\b",
            r"sprachlehrer\w*", r"sprachlehre",
            r"lektorat", r"volontariat", r"verlag\w*",
            r"literaturhaus",
            r"auswertung\w*",
        ],
    },
    "schwach_regional": {
        "weight": 1,
        "terms": [
            r"südasien", r"south asia",
            r"\basien\b", r"\basia\b",  # nicht in 'Klassische Archäologie'
            r"bibliothek geisteswiss\w*", r"philologisch\w*",
            r"ostslawisch\w*", r"russistik", r"slavistik", r"slawistik",
            r"osteuropa\w*", r"südosteuropa\w*", r"balkan\w*",
            r"\bafrika\w*", r"subsahara\w*",
        ],
    },
}

# ── Hard-Blacklist: sortiert sofort aus, egal wie hoch der Score ──
# Diese werden mit einfachem 'in' gematcht (Substring), da es längere Phrasen sind.
HARD_BLACKLIST = [
    # Sozialarbeit-Pflicht
    "studium der sozialen arbeit erforderlich",
    "studium sozialer arbeit erforderlich",
    "abgeschlossenes studium der sozialen arbeit",
    "abschluss in sozialer arbeit erforderlich",
    "diplom-sozialarbeiter",
    "studium soziale arbeit erforderlich",
    # Pädagogik-Pflicht ohne Bezug
    "pädagogische fachkraft",
    "abgeschlossene pädagogische ausbildung erforderlich",
    # Antike / klassische Philologie
    "altorientalist", "ägyptolog", "egyptolog",
    "klassische archäolog", "klassische archaeolog",
    "altgriech", "altsemit",
    "neutestament", "alttestament",
    "ur-/ vor- und frühgeschichte", "prähistorische archäologie",
    "provinzialrömische archäologie",
    # Reine MINT/Medizin/Wirtschaft
    "ingenieur", "biotech", "pharmazi",
    "klinik ", "klinisch", "klinikum",
    # Hilfskräfte / niederschwellig
    "stud. hilfskraft", "studentische hilfskraft",
    "wiss. hilfskraft", "wissenschaftliche hilfskraft",
    "studienbegleitend", "minijob", "minjob",
    # Berufe ohne thematischen Bezug, häufige False Positives
    "online marketing", "marketing manager", "marketingmanager",
    "people lead",
    "office management erwünscht",
    "veranstaltungsreferent",
    "pressereferent",
    "abschlussredaktor",
    "natur und garten", "natur & garten",
    "redaktion kochen", "kochbuch",
    "sachbearbeiter (m/w/d) digitale normen",
    "lektorat kinder- und jugend",
    "länderreferent asien",
    "länderreferentin/en für mittelamerika",
    "länderreferent mittelamerika",
    "evangelischer kirchenkreis",
    "erf medien",
    # Neu nach Test-Lauf:
    "personalwesen erforderlich",
    "bachelor in sozialer arbeit",
    "redakteur (w/m/d) berlin/ ostdeutschland",  # zu generischer Lokaljournalismus
]


# ─── Filter ───
# Pre-compile alle Patterns für Effizienz
def _compile_patterns():
    """Wandelt jeden Term in ein Regex mit Wortgrenzen um."""
    compiled = {}
    for cat_name, cat_data in CATEGORIES.items():
        patterns = []
        for term in cat_data["terms"]:
            # Wenn term schon \b enthält (z.B. r"\basien\b"), nicht doppelt einklammern
            if r"\b" in term:
                patterns.append(re.compile(term, re.IGNORECASE))
            else:
                # Standard: Wortgrenzen drumherum
                patterns.append(re.compile(r"\b" + term + r"\b", re.IGNORECASE))
        compiled[cat_name] = (cat_data["weight"], patterns)
    return compiled

_COMPILED = _compile_patterns()


def score_text(text):
    """Berechnet Score und Liste der getroffenen Kategorien."""
    t_lower = text.lower()
    if any(b in t_lower for b in HARD_BLACKLIST):
        return (0, [])
    total = 0
    hit_categories = []
    for cat_name, (weight, patterns) in _COMPILED.items():
        if any(p.search(text) for p in patterns):
            total += weight
            hit_categories.append(cat_name)
    return (total, hit_categories)


def matches_filters(text):
    score, _ = score_text(text)
    return score >= MIN_SCORE


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
    cutoff = (datetime.now(timezone.utc) - timedelta(days=SEEN_TTL_DAYS)).isoformat()
    cleaned = {k: v for k, v in seen.items() if v.get("first_seen", "9999") >= cutoff}
    removed = len(seen) - len(cleaned)
    if removed:
        print(f"State: {removed} alte Einträge entfernt", file=sys.stderr)
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(cleaned, f, ensure_ascii=False, indent=2)

def mark_seen(seen, job_id, source, title, url, score=0, categories=None):
    if job_id not in seen:
        seen[job_id] = {
            "first_seen": datetime.now(timezone.utc).isoformat(),
            "source": source,
            "title": title[:200],
            "url": url,
            "score": score,
            "categories": categories or [],
        }


# ─── HTTP Helper ───
def fetch_url(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


# ─── Quelle 1: H-Soz-Kult Atom ───
def fetch_hsozkult():
    url = "https://www.hsozkult.de/job/rss"
    try:
        data = fetch_url(url, timeout=30)
    except Exception as e:
        print(f"H-Soz-Kult Fehler: {e}", file=sys.stderr)
        return []
    jobs = []
    try:
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
                "url": urljoin(url, url_link) if url_link else job_id,
                "summary": summary,
                "updated": updated,
            })
    except ET.ParseError as e:
        print(f"H-Soz-Kult XML-Fehler: {e}", file=sys.stderr)
    print(f"H-Soz-Kult: {len(jobs)} Stellen geladen", file=sys.stderr)
    return jobs


# ─── Quelle 2: kultweet.de HTML ───
class KultweetParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_link = False
        self.current_href = None
        self.collected_text = []
        self.jobs = []
        self.current_id = None
        self.current_title_from_attr = None

    def handle_starttag(self, tag, attrs):
        attrs_d = dict(attrs)
        if tag == "a" and "href" in attrs_d:
            href = attrs_d["href"]
            title_attr = attrs_d.get("title", "")
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
    for j in parser.jobs:
        j["url"] = urljoin(url, j["url"])
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
    """Echte Struktur: <a href="...pdf"><h2>Fakultät</h2>Stellentitel-Text</a>"""
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
            full_url = urljoin("https://www.unibw.de/stellenausschreibungen/wissenschaftliche-mitarbeiter", self.current_href)
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
    url = "https://www.service.bund.de/Content/Globals/Functions/RSSFeed/RSSGenerator_Stellen.xml"
    try:
        data = fetch_url(url, timeout=30)
    except Exception as e:
        print(f"service.bund Fehler: {e}", file=sys.stderr)
        return []
    jobs = []
    try:
        root = ET.fromstring(data)
        for item in root.iter("item"):
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            desc = (item.findtext("description") or "").strip()
            guid = (item.findtext("guid") or link).strip()
            if not title or not link:
                continue
            desc_clean = unescape(re.sub(r"<[^>]+>", " ", desc))
            desc_clean = re.sub(r"\s+", " ", desc_clean).strip()
            jobs.append({
                "source": "service.bund.de",
                "id": guid or link,
                "title": title,
                "url": urljoin(url, link),
                "summary": desc_clean[:500],
                "updated": "",
            })
    except ET.ParseError as e:
        print(f"service.bund XML-Fehler: {e}", file=sys.stderr)
    print(f"service.bund.de: {len(jobs)} Stellen geladen", file=sys.stderr)
    return jobs


# ─── Mail ───
def build_html_mail(scored_hits, total_seen, sources_status):
    today = datetime.now(BERLIN_TZ).strftime("%a, %d.%m.%Y")
    parts = [
        "<html><head><meta charset='utf-8'></head><body style='font-family:sans-serif;max-width:800px;'>",
        f"<h1>Stellen-Monitor — {today}</h1>",
    ]
    if not scored_hits:
        parts.append("<p><em>Keine neuen passenden Stellen.</em></p>")
    else:
        parts.append(f"<p><strong>{len(scored_hits)} neue passende Stellen</strong> (sortiert nach Score):</p>")
        scored_hits_sorted = sorted(scored_hits, key=lambda x: -x[1])
        for job, score, cats in scored_hits_sorted:
            title_safe = job["title"].replace("<", "&lt;").replace(">", "&gt;")
            summary_safe = job.get("summary", "").replace("<", "&lt;").replace(">", "&gt;")[:300]
            url_safe = job["url"]
            cats_label = ", ".join(c.replace("_", " ") for c in cats)
            score_color = "#1a7a1a" if score >= 4 else "#7a5a1a" if score >= 3 else "#888"
            parts.append(
                f"<div style='margin-bottom:1.2em;padding:0.4em;border-left:3px solid {score_color};'>"
                f"<div style='font-size:0.8em;color:{score_color};'>"
                f"<strong>{job['source']}</strong> · Score {score} · {cats_label}"
                f"</div>"
                f"<a href='{url_safe}'><strong>{title_safe}</strong></a>"
                + (f"<br><span style='color:#555;font-size:0.9em;'>{summary_safe}</span>" if summary_safe else "")
                + "</div>"
            )
    parts.append("<hr style='margin-top:2em;'>")
    parts.append("<p style='color:#888;font-size:0.85em;'>Quellen-Status:<br>")
    for s, count in sources_status.items():
        parts.append(f"{s}: {count} geladen<br>")
    parts.append(f"Insgesamt im Gedächtnis: {total_seen} Stellen<br>")
    parts.append(f"Min-Score: {MIN_SCORE}<br>")
    parts.append("</p></body></html>")
    return "\n".join(parts)

def send_mail(html_body, subject, count):
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
            sources_status[name] = -1

    scored_hits = []
    for job in all_jobs:
        full_text = f"{job['title']} {job.get('summary', '')}"
        score, cats = score_text(full_text)
        if score < MIN_SCORE:
            continue
        if job["id"] in seen:
            continue
        scored_hits.append((job, score, cats))
        mark_seen(seen, job["id"], job["source"], job["title"], job["url"], score, cats)

    print(f"Neue Treffer: {len(scored_hits)} von {len(all_jobs)} insgesamt (Min-Score {MIN_SCORE})", file=sys.stderr)
    save_seen(seen)

    debug = os.environ.get("DEBUG_STELLEN") == "1"
    if scored_hits or debug:
        html = build_html_mail(scored_hits, len(seen), sources_status)
        subject = f"Stellen-Monitor: {len(scored_hits)} neue Treffer" if scored_hits else "Stellen-Monitor: keine Treffer (Debug)"
        send_mail(html, subject, len(scored_hits))
    else:
        print("Keine neuen Treffer, keine Mail.", file=sys.stderr)

if __name__ == "__main__":
    main()
