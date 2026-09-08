#!/usr/bin/env python3
"""Jurabrief. Eine Akte, rotierende Urteilsteile, Urteilstext unangetastet."""
from __future__ import annotations

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
ZR_COURTS = ("lg", "olg", "bgh", "kg")
VR_COURTS = ("vg", "ovg", "bverwg", "vgh")
STRAF = ("angeklagte", "staatsanwaltschaft", "strafkammer", "stpo", "-ss-")
PLACEHOLDER = ("[kläger", "[beklag", "[name]", "[datum]", "firma/name")

AKTE = """Akte 12 C 310/24 — Amtsgericht Neukoelln, Abteilung 12
Letzte muendliche Verhandlung: 3. April 2025, Richter am Amtsgericht Dr. Mueller.

Parteien
Klaegerin und Widerbeklagte: Rabe Schneedienst GmbH, Kochstrasse 34, 12047 Berlin,
gesetzlich vertreten durch den Geschaeftsfuehrer Martin Mueller, ebenda.
Prozessbevollmaechtigte: Rechtsanwaelte Martina Klage und Karl Meier, Parkstrasse 101, 12165 Berlin.

Streithelferin der Klaegerin: Mega AG, gesetzlich vertreten durch die Vorstandsmitglieder
Herbert Mueller und Ralf Schubert, Sonnenallee 93, 12199 Berlin.
Prozessbevollmaechtigte: Rechtsanwaelte Karl Boot u. a., Oberweg 12, 12498 Berlin.
Die Mega AG hat den Winterdienst als Subunternehmerin ausgefuehrt und der Klaegerin
den Werklohn bereits erstattet. Sie will den Rechtsstreit auf Klaegerseite unterstuetzen.

Beklagter zu 1) und Widerklaeger: der unter der Firma Dieter Teufel handelnde Kaufmann
Rainer Zufall, Peststrasse 14, 12345 Berlin.

Beklagte zu 2) und Widerklaegerin: die am 12. Dezember 2015 geborene Erika Hage,
Sanderweg 2, 12047 Berlin, gesetzlich vertreten durch ihre Eltern Maria und Lutz Hage, ebenda.
Prozessbevollmaechtigter der Beklagten zu 2): Rechtsanwalt Herbert Sol, Kalckreuthweg 56, 10787 Berlin.

Unstreitig
Die Klaegerin raeumte und streute im Winter 2023/2024 die Zufahrt Peststrasse 14 auf Grundlage
eines schriftlichen Winterdienstvertrags vom 2. November 2023. Vertragspartner auf Auftraggeberseite
ist der Beklagte zu 1). Die Beklagte zu 2) wohnt im Anwesen und unterzeichnete den Vertrag nicht.
Die Klaegerin stellte am 10. Dezember 2024 2.559,45 EUR in Rechnung (netto 2.151,64 EUR zuzueglich USt.).
Die Rechnung ist nicht bezahlt.

Streitig — Klaegerin
Die Arbeiten seien vollstaendig und maengelfrei. Beide Beklagte haefteten als Gesamtschuldner,
die Beklagte zu 2) aus konkludentem Mitschluss und aus Geschaeftsfuehrung ohne Auftrag.
Zinsen: 5 Prozentpunkte ueber dem Basiszinssatz seit dem 10. Dezember 2024.

Streitig — Beklagte
Die Beklagte zu 2) sei nicht Vertragspartnerin. Der Beklagte zu 1) rechne mit einem Schaden
von 800 EUR auf, weil am 12. Januar 2024 Streusalz Lackschaeden am Pkw verursacht habe.
Widerklage beider Beklagter: Feststellung, der Vertrag sei wegen Wuchers nichtig, hilfsweise Rueckzahlung
bereits geleisteter 200 EUR.

Antraege
Klaegerin: Verurteilung der Beklagten als Gesamtschuldner zur Zahlung von 2.559,45 EUR
nebst Zinsen in Hoehe von 5 Prozentpunkten ueber dem Basiszinssatz seit dem 10. Dezember 2024;
Abweisung der Widerklage.
Beklagte: Klageabweisung; Widerklage wie vor.

Prozess
Zustellung der Klage am 8. Januar 2025. Muendliche Verhandlung am 3. April 2025.
Die Unternehmensgeschichte der Klaegerin (drei Seiten in der Klageschrift) ist nicht entscheidungserheblich.
"""

FALLBACK = {
    "zr-001": (
        "Bearbeitervermerk\nFertigen Sie allein den Kopf des Urteils. Parteistellung rechtsbuendig. "
        "Grammatik nach dem Skript. Im Namen des Volkes.\n\n" + AKTE + "\nFertigen Sie den Urteilskopf."
    ),
    "zr-002": (
        "Bearbeitervermerk\nFertigen Sie allein die Urteilsformel. Hauptsache, Kosten, vorlaeufige Vollstreckbarkeit. "
        "§ 308 Abs. 1 ZPO. § 709 ZPO (Geldforderung, Sicherheit Betrag zuzueglich 10 %).\n\n" + AKTE +
        "\nErgebnis der Kammer: Klage in Hoehe von 2.559,45 EUR nebst den geltend gemachten Zinsen begruendet. "
        "Gesamtschuld. Widerklage unbegruendet.\n\nFertigen Sie die Urteilsformel."
    ),
    "zr-003": (
        "Bearbeitervermerk\nFertigen Sie den Tatbestand. Unerhebliches weglassen. Unstreitiges Indikativ, Streitiges Konjunktiv. "
        "Antraege. Salvatorische Klausel. Keine Unternehmensgeschichte.\n\n" + AKTE + "\nFertigen Sie den Tatbestand."
    ),
    "zr-004": (
        "Bearbeitervermerk\nFertigen Sie die Entscheidungsgruende im Urteilsstil. Praesens. Keine Ueberschriften. "
        "Zulaessigkeit knapp. Vertrag mit dem Beklagten zu 1), Haftung der Beklagten zu 2), Aufrechnung, Widerklage. "
        "Streithelferin: Wirkung des § 68 ZPO nur soweit der Beitritt reicht.\n\n" + AKTE +
        "\nFertigen Sie die Entscheidungsgruende."
    ),
    "zr-005": (
        "Bearbeitervermerk\nAnwaltliche Sicht. Ein Sachbericht ist nicht zu fertigen.\n"
        "Gliederung: Mandantenbegehren, Gutachten, Zweckmaessigkeit, Schriftsatz.\n"
        "Im Gutachten: Anspruch gegen Zufall; Haftung Hage; Aufrechnung Lackschaden; Widerklage Wucher.\n"
        "In der Zweckmaessigkeit: Beitritt der Mega AG als Streithelferin — Nutzen und Risiko fuer die Mandantin; "
        "ob der Beitritt anzuregen oder zurueckzuweisen ist.\n\n"
        "Mandantin: Rabe Schneedienst GmbH. Ziel: Durchsetzung der Werklohnforderung und Abwehr der Widerklage.\n\n" + AKTE
    ),
    "zr-008": (
        "Bearbeitervermerk\nPruefen Sie eine Vollstreckungsabwehrklage nach § 767 ZPO. Ein Sachbericht ist nicht zu fertigen.\n\n"
        "Titel: Urteil 12 C 310/24 ueber 2.559,45 EUR. Nach Schluss der muendlichen Verhandlung zahlt der Beklagte zu 1) "
        "1.000 EUR und rechnet mit einer erst danach faellig gewordenen Gegenforderung auf. § 767 Abs. 2 ZPO.\n\n" + AKTE
    ),
    "zr-009": (
        "Bearbeitervermerk\nTenorieren Sie die Stattgabe einer Anfechtungsklage und ein Bescheidungsurteil bei der Verpflichtungsklage."
    ),
    "zr-010": (
        "Bearbeitervermerk\nAntrag nach § 80 Abs. 5 VwGO. Ernstliche Zweifel, Interessenabwaegung, Tenor der Wiederherstellung."
    ),
}


def now_berlin():
    return datetime.now(BERLIN_TZ)


def resolve_to() -> str:
    return (os.environ.get("JURABRIEF_TO") or os.environ.get("GMAIL_ADDRESS") or "").strip()


def load_json(path: Path, default):
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return default


def save_state(state):
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


def _find_body(text: str, needle: str) -> int:
    if not needle:
        return 0
    pos, fallback = 0, -1
    while True:
        i = text.find(needle, pos)
        if i < 0:
            return fallback if fallback >= 0 else 0
        line = text[i: text.find("\n", i)]
        if "...." in line:
            if fallback < 0:
                fallback = i
            pos = i + len(needle)
            continue
        return i


def _cut_clean(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text.rstrip()
    cut = text.rfind("\n\n", 0, limit)
    if cut < limit // 3:
        cut = text.rfind("\n", 0, limit)
    return text[: cut if cut > limit // 3 else limit].rstrip()


def clean_ocr(text: str) -> str:
    text = text.replace(""", '"').replace("&", "&")
    text = re.sub(r"(?m)^\s*\d{1,3}(?=[A-ZÄÖÜ])", "", text)
    text = re.sub(r"(?<=\n)\d{1,3}(?=[A-Za-zÄÖÜäöü])", "", text)
    text = re.sub(r"(?m)^\s*\d{1,3}\s*$", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def load_skript_section(case: dict) -> str:
    sid = case.get("skript_id")
    path = EXTRACTED / f"{sid}.txt" if sid else None
    if not path or not path.exists():
        return ""
    text = path.read_text(encoding="utf-8")
    i = _find_body(text, case.get("skript_start") or "")
    end = case.get("skript_end") or ""
    j = _find_body(text, end) if end else min(len(text), i + 20000)
    if j <= i:
        j = min(len(text), i + 20000)
    return _cut_clean(text[i:j], 4500)


def aufgabe_aus_skript(case: dict) -> str:
    cid = case.get("id", "")
    if cid in FALLBACK:
        return FALLBACK[cid]
    return case.get("aufgabe") or "Bearbeiten Sie den Abschnitt nach dem Skript. Keine neuen Parteien."


def _old_search(params: dict) -> list:
    url = OLD_BASE + "?" + urllib.parse.urlencode(params)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "jurabrief/1.0"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8")).get("results") or []
    except Exception as e:
        print(f"OLD: {e}", file=sys.stderr)
        return []


def _is_zivil_case(case):
    return (case.get("gerichtsbarkeit") or "") == "zivil" or "zivil" in case.get("gebiet", "").lower()


def _is_verw(case):
    return (case.get("gerichtsbarkeit") or "") == "verwaltung" or "verwalt" in case.get("gebiet", "").lower()


def _bad(text: str, slug: str = "") -> bool:
    t = (text + " " + slug).lower()
    return any(s in t for s in STRAF) or any(p in t for p in PLACEHOLDER)


def _court_ok(court, case):
    c = (court or "").lower()
    if _is_zivil_case(case):
        return not any(t in c for t in VR_COURTS) and any(t in c for t in ZR_COURTS)
    if _is_verw(case):
        return any(t in c for t in VR_COURTS)
    return True


def _court_name(court):
    if isinstance(court, dict):
        return court.get("name") or court.get("slug") or ""
    return str(court or "")


def _result_text(r):
    if r.get("text"):
        return r["text"]
    return "\n".join(s.get("text", "") for s in (r.get("snippets") or []) if isinstance(s, dict))


def slice_urteil(text: str) -> str | None:
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
    if len(chunk) < 180 or _bad(chunk):
        return None
    return chunk


def search_related_case(case, seen_slugs: list[str]):
    seen = set(seen_slugs or [])
    terms = [
        "Im Namen des Volkes Landgericht Klaegerin Beklagte",
        "Oberlandesgericht Zivilsenat In dem Rechtsstreit",
        "Landgericht Zivilkammer Urteil Klaegerin",
        "Landgericht Halle Zivilkammer",
        "Landgericht Magdeburg Urteil Klaeger",
    ] + list(case.get("suchbegriffe") or [])
    if _is_verw(case):
        terms = ["Verwaltungsgericht Im Namen des Volkes"] + terms
    queries = []
    for t in terms:
        if t not in queries:
            queries.append(t)
    base = {
        "start_date": "2019-01-01",
        "end_date": now_berlin().strftime("%Y-%m-%d"),
        "order_by": "relevance",
        "return_text": "1",
        "page_size": "10",
    }
    for text_q in queries:
        hits = _old_search({**base, "text": text_q})
        print(f"OLD {text_q!r} {len(hits)}", file=sys.stderr)
        for r in hits:
            slug = r.get("slug") or ""
            if slug in seen:
                continue
            raw = _result_text(r)
            if _bad(raw, slug):
                continue
            if not _court_ok(_court_name(r.get("court")), case):
                continue
            shaped = slice_urteil(raw)
            if not shaped:
                continue
            return {
                "gericht": _court_name(r.get("court")),
                "datum": r.get("date", ""),
                "aktenzeichen": r.get("file_number") or slug,
                "entscheidungstyp": r.get("decision_type") or "Urteil",
                "text": shaped,
                "url": f"https://de.openlegaldata.io/case/{slug}/" if slug else "",
                "slug": slug,
            }
    return None


def build_mail(case, related, rules, aufgabe, today_str):
    quelle = case.get("quelle", "Berliner Ausbildungsskript")
    if related:
        lesen = (
            f"I. Lesetext\n"
            f"{related['gericht']}, {related['entscheidungstyp']} vom {related['datum']}, {related['aktenzeichen']}\n"
        )
        if related.get("url"):
            lesen += related["url"] + "\n"
        lesen += "\n" + related["text"] + "\n"
    else:
        lesen = "I. Lesetext\nKein Urteil der passenden Gerichtsbarkeit.\n"
    block2 = f"II. Bearbeitung\n{case['gebiet']}\n{quelle}\n\n{aufgabe}\n"
    if rules:
        block2 += "\n--- Skript (Regeln) ---\n" + rules + "\n"
    return f"Jurabrief — {today_str}\n{case['gebiet']}\n\n{lesen}\n\n{block2}\n"


def send_mail(subject, body, to_addr):
    gmail = (os.environ.get("GMAIL_ADDRESS") or "").strip()
    pw = (os.environ.get("GMAIL_APP_PASSWORD") or "").strip()
    if not gmail or not pw or "@" not in (to_addr or ""):
        print(body)
        return
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
    aufgabe = aufgabe_aus_skript(case)
    related = search_related_case(case, state.get("seen_slugs", []))
    if related and related.get("slug"):
        slugs = state.get("seen_slugs", [])
        slugs.append(related["slug"])
        state["seen_slugs"] = slugs[-40:]
    save_state(state)
    today = now_berlin().strftime("%A, %d. %B %Y")
    body = build_mail(case, related, rules, aufgabe, today)
    send_mail(
        f"Jurabrief — {case['gebiet']} [{case['id']}] ({now_berlin().strftime('%d.%m.')})",
        body,
        resolve_to(),
    )
    print(f"Fall {case['id']} ({grund})")


if __name__ == "__main__":
    main()
