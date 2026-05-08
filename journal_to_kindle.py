#!/usr/bin/env python3
"""
journal_to_kindle.py
─────────────────────────────────────────────────────────────────────────
Pusht akademische Journal-Inhalte automatisch an den Kindle.

Drei Quellen:
  1. ASEEES NewsNet  →  PDF-Direktpush (öffentlich, kein Login)
  2. Slavic Review (Cambridge Core)  →  TOC-Watcher → Click-Liste im Morgenbrief
  3. Central Asian Survey (T&F)       →  TOC-Watcher → Click-Liste im Morgenbrief

Workflow:
  - Liest journal_state.json: was wurde schon gepusht / verlinkt?
  - NewsNet: parst aseees.org/publications/newsnet/ nach neuestem Issue,
             holt PDF, schickt via Gmail SMTP an Kindle. State aktualisieren.
  - Slavic Review + CAS: holt RSS-Feed, vergleicht mit State, schreibt neue
                          Artikel als 'click_list' in journal_state.json.
                          Der Morgenbrief liest diese Liste und blendet sie
                          beim nächsten Lauf ein.

Cron:
  - Wöchentlich (Sonntag) reicht — keine Quelle erscheint öfter als monatlich.

Secrets / Env:
  GMAIL_ADDRESS, GMAIL_APP_PASSWORD, KINDLE_EMAIL  (wie generate_morgenbrief.py)
"""

from __future__ import annotations

import json
import os
import re
import smtplib
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from zoneinfo import ZoneInfo

# ─── Konfiguration ─────────────────────────────────────────────────────

BERLIN_TZ = ZoneInfo("Europe/Berlin")
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 " \
             "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

ROOT = Path(__file__).parent
STATE_FILE = ROOT / "journal_state.json"

NEWSNET_INDEX_URL = "https://aseees.org/publications/newsnet/"

# Cambridge Core und T&F bieten Atom/RSS-Feeds pro Journal an.
# Bei Bedarf kann hier ein weiteres Journal ergänzt werden.
TOC_FEEDS = {
    "slavic_review": {
        "title": "Slavic Review",
        "feed_url": "https://www.cambridge.org/core/journals/slavic-review/latest-issue/rss",
        "publisher": "Cambridge Core",
        "kindle_hint": "Cambridge Core hat 'Save to Kindle' nativ pro Artikel. "
                       "no-reply@cambridge.org muss in der Approved Personal "
                       "Document E-Mail List freigegeben sein.",
    },
    "central_asian_survey": {
        "title": "Central Asian Survey",
        "feed_url": "https://www.tandfonline.com/feed/rss/ccas20",
        "publisher": "Taylor & Francis",
        "kindle_hint": "T&F hat keinen nativen Kindle-Push. Artikel-PDF via "
                       "MLU-Alumni-Shibboleth herunterladen, dann an "
                       f"{os.environ.get('KINDLE_EMAIL', '<KINDLE>')} mailen.",
    },
}

# Schlagwörter, die auf einen Volltext-Artikel hindeuten (zum Aussortieren
# von Buchbesprechungen, Editorials, Errata etc.).
ARTICLE_KEYWORDS_NEGATIVE = (
    "book review", "review of", "errata", "corrigendum", "editor's note",
    "introduction to", "in memoriam", "in this issue",
)

# ─── State ────────────────────────────────────────────────────────────


def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception as exc:
            print(f"[state] Konnte journal_state.json nicht lesen: {exc}",
                  file=sys.stderr)
    return {
        "newsnet_last_pushed": None,   # z.B. "2026-01"
        "toc_seen": {},                # {journal_key: [list of seen item ids]}
        "click_list": [],              # vom Morgenbrief auszuwertende Liste
        "updated_at": None,
    }


def save_state(state: dict) -> None:
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    STATE_FILE.write_text(
        json.dumps(state, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


# ─── HTTP-Helfer ───────────────────────────────────────────────────────


def http_get(url: str, timeout: int = 30) -> bytes:
    """GET mit Browser-User-Agent (manche Verlagsseiten blocken sonst)."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def http_get_text(url: str, timeout: int = 30) -> str:
    return http_get(url, timeout=timeout).decode("utf-8", errors="replace")


# ─── Mail an Kindle (analog generate_morgenbrief.py) ──────────────────


def send_pdf_to_kindle(pdf_bytes: bytes, filename: str, subject: str) -> None:
    ga = os.environ.get("GMAIL_ADDRESS")
    gp = os.environ.get("GMAIL_APP_PASSWORD")
    ka = os.environ.get("KINDLE_EMAIL")
    if not all([ga, gp, ka]):
        sys.exit("Gmail/Kindle Secrets unvollständig")

    msg = MIMEMultipart()
    msg["From"] = ga
    msg["To"] = ka
    msg["Subject"] = subject
    msg.attach(MIMEText("", "plain"))

    part = MIMEBase("application", "pdf")
    part.set_payload(pdf_bytes)
    encoders.encode_base64(part)
    part.add_header("Content-Disposition", f"attachment; filename={filename}")
    msg.attach(part)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(ga, gp)
        smtp.sendmail(ga, ka, msg.as_string())
    print(f"[kindle] {filename} an {ka} geschickt", file=sys.stderr)


# ─── 1. NewsNet ───────────────────────────────────────────────────────


_NEWSNET_ISSUE_PATTERN = re.compile(
    r'href="(https?://aseees\.org/newsnet-issue/'
    r'(january|march|may|july|september|november)-(\d{4})/?)"',
    re.IGNORECASE,
)

_NEWSNET_PDF_PATTERN = re.compile(
    r'href="(https?://aseees\.org/wp-content/uploads/[^"]+\.pdf)"',
    re.IGNORECASE,
)


def find_newest_newsnet_issue() -> tuple[str, str] | None:
    """
    Parst die NewsNet-Übersichtsseite und gibt (issue_id, issue_url) für die
    neueste Ausgabe zurück. issue_id ist z.B. 'january-2026'.
    """
    try:
        html = http_get_text(NEWSNET_INDEX_URL)
    except Exception as exc:
        print(f"[newsnet] Index-Fetch fehlgeschlagen: {exc}", file=sys.stderr)
        return None

    matches = _NEWSNET_ISSUE_PATTERN.findall(html)
    if not matches:
        print("[newsnet] Keine Issue-Links gefunden — Layout geändert?",
              file=sys.stderr)
        return None

    month_order = {
        "january": 1, "march": 3, "may": 5,
        "july": 7, "september": 9, "november": 11,
    }
    parsed = []
    for url, month, year in matches:
        try:
            parsed.append((int(year), month_order[month.lower()],
                           f"{month.lower()}-{year}", url))
        except (KeyError, ValueError):
            continue

    if not parsed:
        return None

    parsed.sort(reverse=True)
    _, _, issue_id, issue_url = parsed[0]
    return issue_id, issue_url


def find_newsnet_pdf_url(issue_url: str) -> str | None:
    """Extrahiert den PDF-Download-Link aus einer Issue-Detailseite."""
    try:
        html = http_get_text(issue_url)
    except Exception as exc:
        print(f"[newsnet] Issue-Seite-Fetch fehlgeschlagen: {exc}",
              file=sys.stderr)
        return None

    pdf_matches = _NEWSNET_PDF_PATTERN.findall(html)
    # Bevorzuge URLs, in denen 'newsnet' im Dateinamen vorkommt.
    for url in pdf_matches:
        if "newsnet" in url.lower():
            return url
    return pdf_matches[0] if pdf_matches else None


def push_newsnet(state: dict) -> None:
    issue = find_newest_newsnet_issue()
    if not issue:
        return
    issue_id, issue_url = issue

    if state.get("newsnet_last_pushed") == issue_id:
        print(f"[newsnet] Aktuelle Ausgabe ({issue_id}) bereits gepusht.",
              file=sys.stderr)
        return

    pdf_url = find_newsnet_pdf_url(issue_url)
    if not pdf_url:
        print(f"[newsnet] PDF-Link in {issue_url} nicht gefunden",
              file=sys.stderr)
        return

    try:
        pdf_bytes = http_get(pdf_url, timeout=120)
    except Exception as exc:
        print(f"[newsnet] PDF-Download fehlgeschlagen: {exc}",
              file=sys.stderr)
        return

    if len(pdf_bytes) < 50_000:
        print(f"[newsnet] PDF verdächtig klein ({len(pdf_bytes)} Bytes) — "
              "Push abgebrochen.", file=sys.stderr)
        return

    filename = f"NewsNet_{issue_id}.pdf"
    subject = f"ASEEES NewsNet {issue_id.replace('-', ' ').title()}"
    send_pdf_to_kindle(pdf_bytes, filename, subject)
    state["newsnet_last_pushed"] = issue_id
    print(f"[newsnet] {issue_id} gepusht ({len(pdf_bytes)} Bytes)",
          file=sys.stderr)


# ─── 2. + 3. TOC-Watcher (Slavic Review, Central Asian Survey) ────────


_RSS_ITEM_RE = re.compile(r"<item[^>]*>(.*?)</item>", re.DOTALL | re.IGNORECASE)
_TAG_RE = re.compile(r"<([a-zA-Z:]+)[^>]*>(.*?)</\1>", re.DOTALL)


def parse_rss_items(xml_text: str) -> list[dict]:
    """
    Minimaler RSS-Parser, ausreichend für Cambridge Core und T&F.
    Wir nutzen kein feedparser, um die Abhängigkeiten schlank zu halten.
    """
    items = []
    for raw in _RSS_ITEM_RE.findall(xml_text):
        fields = {}
        for tag, content in _TAG_RE.findall(raw):
            tag = tag.lower().split(":")[-1]  # 'dc:creator' → 'creator'
            content = content.strip()
            # CDATA-Wrapper entfernen
            content = re.sub(r"^<!\[CDATA\[(.*)\]\]>$", r"\1", content,
                             flags=re.DOTALL)
            content = re.sub(r"<[^>]+>", "", content).strip()
            fields[tag] = content
        if fields.get("title") and fields.get("link"):
            items.append(fields)
    return items


def is_real_article(item: dict) -> bool:
    """Filtert Buchbesprechungen, Editorials, Front Matter raus."""
    title = item.get("title", "").lower()
    if not title:
        return False
    return not any(k in title for k in ARTICLE_KEYWORDS_NEGATIVE)


def collect_toc_items(state: dict) -> list[dict]:
    """
    Holt RSS, vergleicht mit State, gibt neue Items zurück. State wird
    aktualisiert (toc_seen).
    """
    seen_state = state.setdefault("toc_seen", {})
    new_items: list[dict] = []

    for key, cfg in TOC_FEEDS.items():
        try:
            xml = http_get_text(cfg["feed_url"], timeout=30)
        except Exception as exc:
            print(f"[toc:{key}] RSS-Fetch fehlgeschlagen: {exc}",
                  file=sys.stderr)
            continue

        items = parse_rss_items(xml)
        if not items:
            print(f"[toc:{key}] Keine Items im Feed gefunden", file=sys.stderr)
            continue

        seen = set(seen_state.get(key, []))
        fresh = []
        all_links = []
        for item in items:
            link = item.get("link", "")
            all_links.append(link)
            if not link or link in seen:
                continue
            if not is_real_article(item):
                continue
            fresh.append({
                "journal_key": key,
                "journal_title": cfg["title"],
                "publisher": cfg["publisher"],
                "title": item.get("title", "(ohne Titel)"),
                "authors": item.get("creator")
                           or item.get("dc:creator")
                           or item.get("author", ""),
                "link": link,
                "pubdate": item.get("pubdate") or item.get("date") or "",
                "kindle_hint": cfg["kindle_hint"],
                "first_seen": datetime.now(timezone.utc).isoformat(),
            })

        # State-Update: alle aktuell sichtbaren Links als 'gesehen' markieren,
        # damit alte Items beim nächsten Lauf nicht erneut auftauchen.
        seen_state[key] = sorted(set(all_links))
        new_items.extend(fresh)
        print(f"[toc:{key}] {len(fresh)} neue Artikel "
              f"(von {len(items)} im Feed)", file=sys.stderr)

    return new_items


# ─── click_list-Schreiber für den Morgenbrief ─────────────────────────


def update_click_list(state: dict, new_items: list[dict]) -> None:
    """
    Hängt neue TOC-Items an die click_list an. Items älter als 30 Tage
    werden entfernt (sonst wächst die Liste unbegrenzt).
    """
    existing = state.get("click_list", [])
    existing_links = {item["link"] for item in existing}

    cutoff = datetime.now(timezone.utc).timestamp() - 30 * 24 * 3600
    pruned = []
    for item in existing:
        try:
            ts = datetime.fromisoformat(item["first_seen"]).timestamp()
        except Exception:
            ts = cutoff  # broken → drop
        if ts >= cutoff:
            pruned.append(item)

    for item in new_items:
        if item["link"] not in existing_links:
            pruned.append(item)

    state["click_list"] = pruned


# ─── Main ─────────────────────────────────────────────────────────────


def main() -> None:
    state = load_state()

    print(f"[journal_to_kindle] Lauf {datetime.now(BERLIN_TZ):%Y-%m-%d %H:%M}",
          file=sys.stderr)

    # 1. NewsNet automatisch pushen
    try:
        push_newsnet(state)
    except Exception as exc:
        print(f"[newsnet] Unerwarteter Fehler: {exc}", file=sys.stderr)

    # 2./3. TOC-Watcher für Slavic Review + Central Asian Survey
    try:
        new_items = collect_toc_items(state)
        update_click_list(state, new_items)
    except Exception as exc:
        print(f"[toc] Unerwarteter Fehler: {exc}", file=sys.stderr)

    save_state(state)
    print(f"[journal_to_kindle] Fertig. click_list: "
          f"{len(state.get('click_list', []))} Einträge", file=sys.stderr)


if __name__ == "__main__":
    main()
