#!/usr/bin/env python3
"""Jurabrief. Teil I = wörtlicher Urteilsschnitt, keine Umschreibung."""
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
STRAF = (
    "angeklagte", "staatsanwaltschaft", "strafkammer", "stpo",
    "revisionen des angeklagten", "grosse strafkammer",
)
PLACEHOLDER = ("[kläger", "[beklag", "[name]", "[datum]", "firma/name", "gericht/senat")

RUBRUM_SV = (
    "Bearbeitervermerk\nSicht des erkennenden Gerichts. Fertigen Sie den Kopf des Urteils.\n\n"
    "Sachverhalt\nAmtsgericht Neukoelln, Abteilung 12, Az. 12 C 310/24. "
    "Letzte muendliche Verhandlung am 3. April 2025 vor dem Richter am Amtsgericht Dr. Mueller.\n\n"
    "Klaegerin und Widerbeklagte: Rabe Schneedienst GmbH, Kochstrasse 34, 12047 Berlin, "
    "gesetzlich vertreten durch den Geschaeftsfuehrer Martin Mueller, ebenda.\n\n"
    "Streithelferin der Klaegerin: Mega AG, gesetzlich vertreten durch die Vorstandsmitglieder "
    "Herbert Mueller und Ralf Schubert, Sonnenallee 93, 12199 Berlin.\n\n"
    "Beklagter zu 1) und Widerklaeger: der unter der Firma Dieter Teufel handelnde Kaufmann "
    "Rainer Zufall, Peststrasse 14, 12345 Berlin.\n\n"
    "Beklagte zu 2) und Widerklaegerin: die am 12. Dezember 2015 geborene Erika Hage, "
    "Sanderweg 2, 12047 Berlin, gesetzlich vertreten durch ihre Eltern Maria und Lutz Hage, ebenda.\n\n"
    "Fertigen Sie den Kopf des Urteils einschliesslich der Formel Im Namen des Volkes."
)
TENOR_SV = (
    "Bearbeitervermerk\nSicht des erkennenden Gerichts. Fertigen Sie allein die Urteilsformel.\n\n"
    "Sachverhalt\nDie Klage der Rabe Schneedienst GmbH gegen Rainer Zufall und Erika Hage "
    "auf Zahlung von 2.559,45 EUR nebst Zinsen in Hoehe von 5 Prozentpunkten ueber dem "
    "Basiszinssatz seit dem 10. Dezember 2024 ist begruendet. Die Widerklage ist unbegruendet. "
    "Gesamtschuld. Vollstreckung nach § 709 ZPO, Sicherheit Betrag zuzueglich 10 %.\n\n"
    "Fertigen Sie die Urteilsformel (Hauptsache, Kosten, vorlaeufige Vollstreckbarkeit)."
)
TATBESTAND_SV = (
    "Bearbeitervermerk\nFertigen Sie den Tatbestand. Unerhebliches weglassen. "
    "Unstreitiges im Indikativ, Streitiges im Konjunktiv. Antraege wörtlich.\n\n"
    "Sachverhalt\nKlage der Rabe Schneedienst GmbH gegen Zufall und Hage auf 2.559,45 EUR. "
    "Die Beklagten bestreiten die Hoehe. Widerklage auf Feststellung, dass der Vertrag nichtig sei. "
    "In der Klageschrift steht eine Seite Unternehmensgeschichte der Klaegerin; das ist nicht entscheidungserheblich. "
    "Letzte muendliche Verhandlung am 3. April 2025.\n\n"
    "Fertigen Sie den Tatbestand nach Abschnitt D des Skripts."
)
GRUENDE_SV = (
    "Bearbeitervermerk\nFertigen Sie die Entscheidungsgruende im Urteilsstil.\n\n"
    "Sachverhalt\nZahlungsklage 2.559,45 EUR der Rabe Schneedienst GmbH. Widerklage abzuweisen. "
    "Zulaessigkeit unproblematisch.\n\n"
    "Fertigen Sie die Entscheidungsgruende. Obersatz voran."
)
FALLBACK = {
    "zr-001": RUBRUM_SV,
    "zr-002": TENOR_SV,
    "zr-003": TATBESTAND_SV,
    "zr-004": GRUENDE_SV,
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
    return case.get("aufgabe") or "Bearbeiten Sie den Abschnitt nach dem Skript."


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


def _is_straf(text: str, slug: str = "") -> bool:
    t = (text + " " + slug).lower()
    if any(s in t for s in STRAF):
        return True
    if re.search(r"\bss\s*\d", t) or "-ss-" in t:
        return True
    return False


def _is_placeholder(text: str) -> bool:
    t = text.lower()
    return any(p in t for p in PLACEHOLDER)


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
    if _is_placeholder(text) or _is_straf(text):
        return None
    low = text.lower()
    start = 0
    for m in ("im namen des volkes", "in dem rechtsstreit", "tenor"):
        i = low.find(m)
        if i != -1:
            start = i
            break
    chunk = text[start:start + 3500].strip()
    if len(chunk) < 180:
        return None
    if _is_placeholder(chunk):
        return None
    return chunk


def search_related_case(case, seen_slugs: list[str]):
    seen = set(seen_slugs or [])
    terms = [
        "Im Namen des Volkes Landgericht Klaegerin Beklagte",
        "Oberlandesgericht Zivilsenat In dem Rechtsstreit",
        "Landgericht Zivilkammer Urteil Klaegerin",
        "Landgericht Halle Zivilkammer Urteil",
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
            if _is_straf(raw, slug) or _is_placeholder(raw):
                continue
            court = _court_name(r.get("court"))
            if not _court_ok(court, case):
                continue
            shaped = slice_urteil(raw)
            if not shaped:
                continue
            return {
                "gericht": court,
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
