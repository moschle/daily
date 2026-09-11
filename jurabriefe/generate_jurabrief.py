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
from fsrs_scheduler import _load as load_progress, _save as save_progress, auto_wertung, markiere_gezeigt
from kartenbrief import brieftext, lade, waehle, waehle_fall, zurueckhalten

BERLIN_TZ = ZoneInfo("Europe/Berlin")
STATE_FILE = _HERE / "state.json"
CASES_FILE = _HERE / "cases.json"
PROGRESS_FILE = _HERE / "progress.json"
LERNPLAN_FILE = _HERE / "lernplan.json"
EXTRACTED = _HERE / "extracted"
OLD_BASE = "https://de.openlegaldata.io/api/cases/search/"
OLD_CASE = "https://de.openlegaldata.io/api/cases/{}/"
ZR_MARK = (
    "landgericht", "oberlandesgericht", "bundesgerichtshof", "kammergericht",
    "amtsgericht", "lg-", "olg-", "bgh", "kg-",
)
ZR_SLUG = ("lg", "olg", "bgh", "kg")
VR_MARK = (
    "verwaltungsgericht", "oberverwaltungsgericht", "bundesverwaltungsgericht",
    "verwaltungsgerichtshof", "vg-", "ovg", "bverwg", "vgh",
)
VR_SLUG = ("vg", "ovg", "bverwg", "vgh")
STRAF = ("angeklagte", "staatsanwaltschaft", "strafkammer", "stpo", "-ss-")
PLACEHOLDER = ("[kläger", "[beklag", "[name]", "[datum]", "firma/name")
PAGE = re.compile(r"(?m)^=+ SEITE \d+ =+$")
FOOT = re.compile(r"(?m)^\d{1,3}\s{2}\S")
HEAD = re.compile(r"(?m)^[A-ZÄÖÜIVX][^\n]{0,60}?\s+\d{1,3}\s*$")
TAG = re.compile(r"<[^>]+>")

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
    state["letzter_brief"] = now_berlin().strftime("%Y-%m-%d")
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def pick_case(cases, state, progress):
    recent = []
    for cid in reversed(state.get("done", [])):
        if cid not in recent:
            recent.append(cid)
        if len(recent) >= 4:
            break
    try:
        res = pick(cases, load_json(LERNPLAN_FILE, {"phasen": []}), progress, exclude_ids=recent)
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
    text = TAG.sub("\n", text)
    text = re.sub(r"(?m)^\s*\d{1,3}(?=[A-ZÄÖÜ])", "", text)
    text = re.sub(r"(?<=\n)\d{1,3}(?=[A-Za-zÄÖÜäöü])", "", text)
    text = re.sub(r"(?m)^\s*\d{1,3}\s*$", "", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def clean_skript(text: str) -> str:
    notes, out = [], []
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

load_skript = load_skript_section


def _bad(text, slug=""):
    t = (text + " " + slug).lower()
    return any(s in t for s in STRAF) or any(p in t for p in PLACEHOLDER)


def _court_name(court):
    if isinstance(court, dict):
        return " ".join(str(court.get(k) or "") for k in ("name", "slug"))
    return str(court or "")


def _slug_prefix(s: str) -> str:
    s = re.sub(r"[^a-z]", "", (s or "").lower())
    for p in ZR_SLUG + VR_SLUG:
        if s.startswith(p):
            return p
    return ""


def _is_verw(case):
    geb = (case.get("gerichtsbarkeit") or "") + " " + case.get("gebiet", "")
    return "verwalt" in geb.lower()


def _court_ok(court, case):
    c = court.lower()
    pref = _slug_prefix(c)
    if _is_verw(case):
        return pref in VR_SLUG or any(t in c for t in VR_MARK)
    if pref in VR_SLUG or any(t in c for t in VR_MARK):
        return False
    return pref in ZR_SLUG or any(t in c for t in ZR_MARK)


def slice_urteil(text):
    text = clean_ocr(text)
    if _bad(text):
        return None
    low = text.lower()
    treffer = []
    for m in ("im namen des volkes", "in dem rechtsstreit", "tatbestand",
              "entscheidungsgründe", "gründe"):
        hit = re.search(r"\b" + re.escape(m) + r"\b", low)
        if hit:
            treffer.append(hit.start())
    start = min(treffer) if treffer else 0
    chunk = text[start:start + 3500].strip()
    return chunk if len(chunk) >= 180 and not _bad(chunk) else None


def _http_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "jurabrief/1.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _old_search(params):
    url = OLD_BASE + "?" + urllib.parse.urlencode(params)
    try:
        return (_http_json(url).get("results") or [])
    except Exception as e:
        print(f"OLD: {e}", file=sys.stderr)
        return []


def _fetch_case(cid, slug=""):
    try:
        d = _http_json(OLD_CASE.format(cid))
    except Exception as e:
        print(f"OLD case {cid}: {e}", file=sys.stderr)
        return None
    text = d.get("content") or d.get("text") or ""
    court = _court_name(d.get("court")) or slug
    return {"text": text, "court": court, "date": d.get("date", ""),
            "file_number": d.get("file_number") or "",
            "typ": d.get("type") or d.get("decision_type") or "Urteil",
            "slug": d.get("slug") or slug}


def search_related_case(case, seen_slugs):
    seen = set(seen_slugs or [])
    generic = [
        "Im Namen des Volkes Klaegerin Beklagte", "Landgericht Urteil Klaegerin",
        "Oberlandesgericht Zivilsenat", "Landgericht Halle", "Landgericht Magdeburg"]
    terms = list(case.get("suchbegriffe") or []) + generic
    if _is_verw(case):
        terms = list(case.get("suchbegriffe") or []) + ["Verwaltungsgericht Im Namen des Volkes"] + generic
    for q in terms:
        hits = _old_search({"text": q, "page_size": "10"})
        print(f"OLD {q!r} {len(hits)} {[str(r.get('court')) for r in hits][:6]}", file=sys.stderr)
        for r in hits:
            slug = r.get("slug") or ""
            if slug in seen:
                continue
            year = (r.get("date") or "")[:4]
            if year and year < "2019":
                continue
            court = _court_name(r.get("court"))
            if not _court_ok(court + " " + slug, case):
                continue
            detail = _fetch_case(r.get("id"), slug) if r.get("id") else None
            raw = detail["text"] if detail else ""
            if detail:
                court = detail["court"] or court
            if not raw:
                raw = "\n".join(s.get("text", "") for s in (r.get("snippets") or []) if isinstance(s, dict))
            if _bad(raw, slug):
                continue
            shaped = slice_urteil(raw)
            if not shaped:
                continue
            az = (detail or {}).get("file_number") or slug
            return {"gericht": court.strip() or slug,
                    "datum": (detail or {}).get("date") or r.get("date", ""),
                    "aktenzeichen": az,
                    "entscheidungstyp": (detail or {}).get("typ") or r.get("decision_type") or "Urteil",
                    "text": shaped,
                    "roh": clean_ocr(raw)[:12000],
                    "url": f"https://de.openlegaldata.io/case/{slug}/" if slug else "",
                    "slug": slug}
    return None


def lesetext_aufbereiten(related):
    """Tenor, zwei Saetze Sachverhalt und eine Frage, die als Karte weiterlebt.

    Ohne Frage ist der Lesetext Dekoration: sie liest im Referendariat ohnehin
    den ganzen Tag Urteile. Schlaegt der Aufruf fehl, bleibt es beim rohen
    Auszug — ein magerer Brief ist besser als keiner."""
    from claude_client import complete
    roh = (related.get("roh") or related.get("text") or "")[:12000]
    prompt = (
        "Du bereitest eine Entscheidung als Lesetext fuer das zweite juristische "
        "Staatsexamen auf. Antworte NUR mit JSON, ohne Vorrede und ohne Codefence:\n"
        '{"tenor": "...", "sachverhalt": "...", "frage": "...", "loesung": "..."}'"\n\n"
        "tenor: das Ergebnis der Entscheidung in einem Satz.\n"
        "sachverhalt: genau zwei Saetze — was geschehen ist und worum gestritten wird.\n"
        "frage: eine Frage zur tragenden Rechtsfrage, ein Satz, ohne die Antwort zu verraten.\n"
        "loesung: die Antwort in zwei bis vier Saetzen, gestuetzt auf die Entscheidung.\n\n"
        f"Entscheidung: {related.get('gericht')}, {related.get('aktenzeichen')}\n\n{roh}")
    try:
        antwort = complete(prompt, max_tokens=4000).strip()
        antwort = re.sub(r"^```(?:json)?|```$", "", antwort, flags=re.M).strip()
        d = json.loads(antwort)
        for feld in ("tenor", "sachverhalt", "frage", "loesung"):
            if not (d.get(feld) or "").strip():
                raise ValueError(f"{feld} fehlt")
        return d
    except Exception as e:
        print(f"Lesetext-Aufbereitung fehlgeschlagen: {e}", file=sys.stderr)
        return None


def merke_lesetext_karte(karte):
    """Die Frage wandert in einen eigenen Stapel und damit in die Wiederholung."""
    from kartenbrief import LESETEXTE
    bestand = {"karten": []}
    if LESETEXTE.exists():
        try:
            bestand = json.loads(LESETEXTE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    if any(k.get("id") == karte["id"] for k in bestand.get("karten", [])):
        return
    bestand.setdefault("karten", []).append(karte)
    bestand["karten"] = bestand["karten"][-200:]
    LESETEXTE.write_text(json.dumps(bestand, ensure_ascii=False, indent=1), encoding="utf-8")


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
    heute = now_berlin().strftime("%Y-%m-%d")
    if state.get("letzter_brief") == heute:
        print(f"Brief fuer {heute} ist schon raus — nichts zu tun", file=sys.stderr)
        return 0
    progress = load_progress()
    for c in cases:
        auto_wertung(progress, c["id"])
    for kid in list((progress.get("cards") or {}).keys()):
        if ":" in kid:
            auto_wertung(progress, kid)
    from adaptive_plan import current_phase
    phase = current_phase(load_json(LERNPLAN_FILE, {"phasen": []}))
    case = waehle_fall(cases, phase.get("gebiete", []), progress, state)
    grund = phase.get("name", "Plan")
    state.setdefault("done", []).append(case["id"])
    state["done"] = state["done"][-40:]
    state["last_id"] = case["id"]
    # load_skript_section wird weiterhin von korrektur.py benutzt, im Brief nicht mehr

    alle = lade(case.get("skript_id") or "")
    zuletzt = [k["id"] for p in (state.get("offene_packs") or {}).values()
               for k in p.get("karten", [])]
    heutige = waehle(alle, progress, meiden=zuletzt)
    related = search_related_case(case, state.get("seen_slugs", []))
    if related and related.get("slug"):
        state.setdefault("seen_slugs", []).append(related["slug"])
    if related:
        lesen = (f"I. Lesetext — {case['gebiet']}\n"
                 f"{related['gericht']}, {related['entscheidungstyp']} vom "
                 f"{related['datum']}, {related['aktenzeichen']}\n")
        if related.get("url"):
            lesen += related["url"].rstrip("/") + "\n"
        auf = lesetext_aufbereiten(related)
        if auf:
            lesen += (f"\nTenor: {auf['tenor'].strip()}\n"
                      f"\nSachverhalt: {auf['sachverhalt'].strip()}\n"
                      f"\n{related['text']}\n")
            karte = {"id": f"lesetext:{related.get('slug') or case['id']}",
                     "typ": "fall", "gewicht": 2, "skript": case["skript_id"],
                     "rn": "", "frage": auf["frage"].strip(),
                     "loesung": auf["loesung"].strip(),
                     "abschnitt": f"Lesetext {related['gericht']} {related['aktenzeichen']}"}
            merke_lesetext_karte(karte)
            heutige.append(karte)
        else:
            lesen += "\n" + related["text"] + "\n"
    else:
        lesen = "I. Lesetext\nKein Urteil der passenden Gerichtsbarkeit.\n"
    aufgabe = brieftext(heutige)
    body = (f"Jurabrief — {now_berlin().strftime('%A, %d. %B %Y')}\n\n"
            f"{lesen}\n\n{aufgabe}\n"
            f"Quelle: {case.get('quelle', '')}\n")
    # Der Skript-Rohblock ist raus: die Musterloesung steht in der Auswertung,
    # nach dem eigenen Versuch. Davor nimmt sie nur die Gelegenheit zu formulieren.
    send_mail(f"Jurabrief [{case['id']}] ({now_berlin().strftime('%d.%m.')})",
              body, resolve_to())
    markiere_gezeigt(progress, case["id"])
    for k in heutige:
        markiere_gezeigt(progress, k["id"])
    packs = state.setdefault("offene_packs", {})
    packs[case["id"]] = zurueckhalten(heutige, case["id"])
    for alt in list(packs)[:-3]:              # hoechstens drei Briefe offen halten
        packs.pop(alt)
    state["offen"] = {}
    save_progress(progress)
    save_state(state)
    print(f"Fall {case['id']} ({grund}), {len(heutige)} Karten: "
          f"{', '.join(k['id'] for k in heutige)}")


if __name__ == "__main__":
    main()
