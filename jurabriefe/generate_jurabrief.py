#!/usr/bin/env python3
from __future__ import annotations

import html
import json
import os
import re
import smtplib
import sys
import urllib.parse
import urllib.request
from datetime import datetime
from email.mime.text import MIMEText
from pathlib import Path
from zoneinfo import ZoneInfo

_HERE = Path(__file__).resolve().parent
_REPO = _HERE.parent
for _p in (_REPO, _HERE):
    s = str(_p)
    if s not in sys.path:
        sys.path.insert(0, s)

from adaptive_plan import pick

BERLIN_TZ = ZoneInfo("Europe/Berlin")
STATE_FILE = _HERE / "state.json"
CASES_FILE = _HERE / "cases.json"
PROGRESS_FILE = _HERE / "progress.json"
LERNPLAN_FILE = _HERE / "lernplan.json"
EXTRACTED = _HERE / "extracted"
OLD_BASE = "https://de.openlegaldata.io/api/cases/search/"
ZR_MARK = (
    "landgericht", "oberlandesgericht", "bundesgerichtshof", "kammergericht",
    "amtsgericht", "lg-", "olg-", "bgh", "kg-",
)
VR_MARK = (
    "verwaltungsgericht", "oberverwaltungsgericht", "bundesverwaltungsgericht",
    "verwaltungsgerichtshof", "vg-", "ovg", "bverwg", "vgh",
)
STRAF = ("angeklagte", "staatsanwaltschaft", "strafkammer", "stpo", "-ss-")
PLACEHOLDER = ("[kläger", "[beklag", "[name]", "[datum]", "firma/name")
PAGE = re.compile(r"(?m)^=+ SEITE \d+ =+$")
FOOT = re.compile(r"(?m)^\d{1,3}\s{2}\S")
HEAD = re.compile(r"(?m)^[A-ZÄÖÜIVX][^\n]{0,60}?\s+\d{1,3}\s*$")

AKTE = """Akte 12 C 310/24 — Amtsgericht Neukoelln, Abteilung 12
Letzte muendliche Verhandlung: 3. April 2025, Richter am Amtsgericht Dr. Mueller.

Parteien
Klaegerin und Widerbeklagte: Rabe Schneedienst GmbH, Kochstrasse 34, 12047 Berlin,
gesetzlich vertreten durch den Geschaeftsfuehrer Martin Mueller, ebenda.
Prozessbevollmaechtigte: Rechtsanwaelte Martina Klage und Karl Meier, Parkstrasse 101, 12165 Berlin.

Streithelferin der Klaegerin: Mega AG (Subunternehmerin, Werklohn an Klaegerin erstattet),
gesetzlich vertreten durch Herbert Mueller und Ralf Schubert, Sonnenallee 93, 12199 Berlin.

Beklagter zu 1) und Widerklaeger: der unter der Firma Dieter Teufel handelnde Kaufmann
Rainer Zufall, Peststrasse 14, 12345 Berlin.

Beklagte zu 2) und Widerklaegerin: die am 12. Dezember 2015 geborene Erika Hage,
Sanderweg 2, 12047 Berlin, gesetzlich vertreten durch Maria und Lutz Hage, ebenda.

Unstreitig
Winterdienstvertrag 2. November 2023 mit dem Beklagten zu 1). Rechnung 2.559,45 EUR
vom 10. Dezember 2024 unbezahlt. Hage hat nicht unterzeichnet.

Streitig
Klaegerin: maengelfrei; Gesamtschuld; Haftung Hage aus konkludentem Mitschluss und GoA.
Beklagte: Hage nicht Vertragspartnerin; Aufrechnung 800 EUR Lackschaden; Widerklage Wucher,
hilfsweise Rueckzahlung 200 EUR.

Unternehmensgeschichte in der Klageschrift unerheblich.
"""

FALLBACK = {
    "zr-001": "Bearbeitervermerk\nFertigen Sie den Urteilskopf. Im Namen des Volkes.\n\n" + AKTE,
    "zr-002": "Bearbeitervermerk\nFertigen Sie die Urteilsformel. § 308, § 709 ZPO. Gesamtschuld. Widerklage abweisen.\n\n" + AKTE,
    "zr-003": "Bearbeitervermerk\nFertigen Sie den Tatbestand. Indikativ/Konjunktiv. Keine Unternehmensgeschichte.\n\n" + AKTE,
    "zr-004": "Bearbeitervermerk\nFertigen Sie die Entscheidungsgruende im Urteilsstil. § 68 ZPO zur Streithelferin.\n\n" + AKTE,
    "zr-005": (
        "Bearbeitervermerk\nAnwaltliche Sicht. Ein Sachbericht ist nicht zu fertigen.\n"
        "Gliederung: Mandantenbegehren, Gutachten, Zweckmaessigkeit, Schriftsatz.\n"
        "Zweckmaessigkeit: Beitritt Mega AG.\n\nMandantin: Rabe Schneedienst GmbH.\n\n" + AKTE
    ),
    "zr-008": "Bearbeitervermerk\nVollstreckungsabwehrklage § 767 ZPO. Kein Sachbericht.\n\n" + AKTE,
    "zr-009": "Bearbeitervermerk\nTenor Anfechtung und Bescheidungsurteil Verpflichtungsklage.",
    "zr-010": "Bearbeitervermerk\nAntrag § 80 Abs. 5 VwGO.",
}


def now_berlin():
    return datetime.now(BERLIN_TZ)


def resolve_to():
    return (os.environ.get("JURABRIEF_TO") or os.environ.get("GMAIL_ADDRESS") or "").strip()


def load_json(path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def save_state(state):
    state["done"] = (state.get("done") or [])[-20:]
    state["seen_slugs"] = (state.get("seen_slugs") or [])[-40:]
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def pick_case(cases, state):
    recent = []
    for cid in reversed(state.get("done", [])):
        if cid not in recent:
            recent.append(cid)
        if len(recent) >= 4:
            break
    try:
        res = pick(
            cases,
            load_json(LERNPLAN_FILE, {"phasen": []}),
            load_json(PROGRESS_FILE, {"gewichte": {}}),
            exclude_ids=recent,
        )
        case, grund = res["case"], res.get("grund", "adaptiv")
    except Exception as e:
        print(f"Plan: {e}", file=sys.stderr)
        remaining = [c for c in cases if c["id"] not in recent] or cases
        case, grund = remaining[0], "zyklus"
    state.setdefault("done", []).append(case["id"])
    state["last_id"] = case["id"]
    return case, grund


def clean_ocr(text):
    text = html.unescape(text)
    text = re.sub(r"(?m)^\s*\d{1,3}(?=[A-ZÄÖÜ])", "", text)
    text = re.sub(r"(?<=\n)\d{1,3}(?=[A-Za-zÄÖÜäöü])", "", text)
    text = re.sub(r"(?m)^\s*\d{1,3}\s*$", "", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def clean_skript(text: str) -> str:
    notes = []
    out = []
    for page in PAGE.split(text):
        m = FOOT.search(page)
        if m:
            notes.append(page[m.start():].strip())
            page = page[:m.start()]
        out.append(HEAD.sub("", page))
    t = "\n".join(out)
    t = re.sub(r"(\w)-\n(\w)", r"\1\2", t)
    t = re.sub(r"(?<=[a-zäöüß])(\d{1,2})(?=[\s.,;:)])", "", t)
    t = re.sub(r"(?m)[ \t]+$", "", t)
    t = re.sub(r"\n{3,}", "\n\n", t).strip()
    if notes:
        t += "\n\n--- Fußnoten ---\n" + "\n".join(notes)[:1800]
    return t


def _is_toc_line(text, pos):
    nl = text.find("\n", pos)
    line = text[pos: nl if nl != -1 else len(text)]
    return ".." in line or re.search(r"\s\d{1,3}\s*$", line) is not None


def load_skript_section(case):
    sid = case.get("skript_id") or ""
    text = ""
    for name in (f"{sid}.txt", f"{sid}-kopf.txt"):
        path = EXTRACTED / name
        if path.exists() and path.stat().st_size > 50:
            text = path.read_text(encoding="utf-8")
            break
    if not text:
        return ""
    text = clean_skript(text)
    start = case.get("skript_start") or ""
    i = 0
    if start:
        pat = re.compile(r"[ \t\u00a0]+".join(map(re.escape, start.split())))
        hits = [m.start() for m in pat.finditer(text)]
        real = [h for h in hits if not _is_toc_line(text, h)]
        if not real:
            print(f"Skript: nur TOC oder kein Treffer fuer {start!r}", file=sys.stderr)
            return ""
        i = real[0]
    end = case.get("skript_end") or ""
    j = -1
    if end:
        epat = re.compile(r"[ \t\u00a0]+".join(map(re.escape, end.split())))
        for m in epat.finditer(text, i + 1):
            if not _is_toc_line(text, m.start()):
                j = m.start()
                break
    j = j if j > i else min(len(text), i + 12000)
    chunk = text[i:j]
    if len(chunk) > 4500:
        cut = chunk.rfind("\n\n", 0, 4500)
        chunk = chunk[: cut if cut > 1000 else 4500]
    return chunk.rstrip()


def _bad(text, slug=""):
    t = (text + " " + slug).lower()
    return any(s in t for s in STRAF) or any(p in t for p in PLACEHOLDER)


def _court_name(court):
    if isinstance(court, dict):
        return " ".join(str(court.get(k) or "") for k in ("name", "slug"))
    return str(court or "")


def _is_verw(case):
    geb = (case.get("gerichtsbarkeit") or "") + " " + case.get("gebiet", "")
    return "verwalt" in geb.lower()


def _court_ok(court, case):
    c = court.lower()
    if _is_verw(case):
        return any(t in c for t in VR_MARK)
    if any(t in c for t in VR_MARK):
        return False
    return any(t in c for t in ZR_MARK)


def slice_urteil(text):
    text = clean_ocr(text)
    if _bad(text):
        return None
    low = text.lower()
    start = 0
    for m in ("im namen des volkes", "in dem rechtsstreit"):
        i = low.find(m)
        if i != -1:
            start = i
            break
    chunk = text[start:start + 3500].strip()
    return chunk if len(chunk) >= 180 and not _bad(chunk) else None


def _old_search(params):
    url = OLD_BASE + "?" + urllib.parse.urlencode(params)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "jurabrief/1.0"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data.get("results") or data.get("items") or []
    except Exception as e:
        print(f"OLD: {e}", file=sys.stderr)
        return []


def search_related_case(case, seen_slugs):
    seen = set(seen_slugs or [])
    terms = [
        "Im Namen des Volkes Klaegerin Beklagte",
        "Landgericht Urteil Klaegerin",
        "Oberlandesgericht Zivilsenat",
        "Landgericht Halle",
        "Landgericht Magdeburg",
    ] + list(case.get("suchbegriffe") or [])
    if _is_verw(case):
        terms = ["Verwaltungsgericht Im Namen des Volkes"] + terms
    for q in terms:
        hits = _old_search({"text": q, "page_size": "10"})
        courts = [_court_name(r.get("court")) for r in hits]
        print(f"OLD {q!r} {len(hits)} {courts[:6]}", file=sys.stderr)
        for r in hits:
            slug = r.get("slug") or ""
            if slug in seen:
                continue
            raw = r.get("text") or ""
            court = _court_name(r.get("court"))
            if _bad(raw, slug) or not _court_ok(court, case):
                continue
            year = (r.get("date") or "")[:4]
            if year and year < "2019":
                continue
            shaped = slice_urteil(raw)
            if not shaped:
                continue
            return {
                "gericht": court.strip() or slug,
                "datum": r.get("date", ""),
                "aktenzeichen": r.get("file_number") or r.get("ecli") or slug,
                "entscheidungstyp": r.get("type") or r.get("decision_type") or "Urteil",
                "text": shaped,
                "url": f"https://de.openlegaldata.io/case/{slug}/" if slug else "",
                "slug": slug,
            }
    return None


def send_mail(subject, body, to_addr):
    gmail = (os.environ.get("GMAIL_ADDRESS") or "").strip()
    pw = (os.environ.get("GMAIL_APP_PASSWORD") or "").strip()
    if not gmail or not pw or "@" not in (to_addr or ""):
        print("Kein Empfaenger oder keine SMTP-Secrets.", file=sys.stderr)
        raise SystemExit(2)
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = gmail
    msg["To"] = to_addr
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(gmail, pw)
        s.sendmail(gmail, [to_addr], msg.as_string())
    print(f"Mail an {to_addr} gesendet.")


def main():
    cases = load_json(CASES_FILE, {}).get("cases", [])
    if not cases:
        sys.exit(1)
    state = load_json(STATE_FILE, {"done": [], "seen_slugs": []})
    case, grund = pick_case(cases, state)
    rules = load_skript_section(case)
    aufgabe = FALLBACK.get(case["id"]) or case.get("aufgabe") or AKTE
    related = search_related_case(case, state.get("seen_slugs", []))
    if related and related.get("slug"):
        state.setdefault("seen_slugs", []).append(related["slug"])
    save_state(state)
    if related:
        lesen = (
            f"I. Lesetext\n{related['gericht']}, {related['entscheidungstyp']} vom "
            f"{related['datum']}, {related['aktenzeichen']}\n"
        )
        if related.get("url"):
            lesen += related["url"] + "\n"
        lesen += "\n" + related["text"] + "\n"
    else:
        lesen = "I. Lesetext\nKein Urteil der passenden Gerichtsbarkeit.\n"
    body = (
        f"Jurabrief — {now_berlin().strftime('%A, %d. %B %Y')}\n{case['gebiet']}\n\n"
        f"{lesen}\n\nII. Bearbeitung\n{case['gebiet']}\n{case.get('quelle', '')}\n\n{aufgabe}\n"
    )
    if rules:
        body += "\n--- Skript (Regeln) ---\n" + rules + "\n"
    send_mail(
        f"Jurabrief — {case['gebiet']} [{case['id']}] ({now_berlin().strftime('%d.%m.')})",
        body,
        resolve_to(),
    )
    print(f"Fall {case['id']} ({grund})")


if __name__ == "__main__":
    main()
