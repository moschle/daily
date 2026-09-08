#!/usr/bin/env python3
"""Jurabrief: rotierendes Kapitel, wechselnder Lesetext, vollstaendige Aufgabe."""
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
from claude_client import complete

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
    "revisionen des angeklagten", "grosse strafkammer", "jugendkammer",
)

RUBRUM_SV = (
    "Bearbeitervermerk\nSicht des erkennenden Gerichts. Fertigen Sie den Kopf des Urteils.\n\n"
    "Sachverhalt\nAmtsgericht Neukoelln, Abteilung 12, Az. 12 C 310/24. "
    "Letzte muendliche Verhandlung am 3. April 2025 vor dem Richter am Amtsgericht Dr. Mueller.\n\n"
    "Klaegerin und Widerbeklagte: Rabe Schneedienst GmbH, Kochstrasse 34, 12047 Berlin, "
    "gesetzlich vertreten durch den Geschaeftsfuehrer Martin Mueller, ebenda. "
    "Prozessbevollmaechtigte: Rechtsanwaelte Martina Klage und Karl Meier, Parkstrasse 101, 12165 Berlin.\n\n"
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
    "Basiszinssatz seit dem 10. Dezember 2024 ist begruendet. Die Widerklage der Beklagten "
    "ist unbegruendet. Die Beklagten haften als Gesamtschuldner. "
    "Vollstreckung nach § 709 ZPO, Sicherheitsleistung Betrag zuzueglich 10 %.\n\n"
    "Fertigen Sie die Urteilsformel (Hauptsache, Kosten, vorlaeufige Vollstreckbarkeit)."
)

FALLBACK = {
    "zr-001": RUBRUM_SV,
    "zr-002": TENOR_SV,
}

EXCERPT_PROMPT = """Anfang eines deutschen ZIVILURTEILS. Nur Rubrum und Tenor.
Strafsache, Angeklagter, StPO: UNPASSEND.\n\nText:\n{text}\n"""

AUFGABE_PROMPT = """Assessorklausur zum vorliegenden Skriptabschnitt.
Nur die Aufgabe. Keine Loesung. Auftragssatz am Ende.\n\nSkript:\n{text}\n"""


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


def load_skript_section(case: dict) -> tuple[str, str]:
    sid = case.get("skript_id")
    path = EXTRACTED / f"{sid}.txt" if sid else None
    if not path or not path.exists():
        return "", ""
    text = path.read_text(encoding="utf-8")
    i = _find_body(text, case.get("skript_start") or "")
    end = case.get("skript_end") or ""
    j = _find_body(text, end) if end else min(len(text), i + 25000)
    if j <= i:
        j = min(len(text), i + 25000)
    return _cut_clean(text[i:j], 4500), ""


def aufgabe_aus_skript(case: dict, rules: str, muster: str) -> str:
    cid = case.get("id", "")
    if cid in FALLBACK:
        return FALLBACK[cid]
    quelle = rules[:7000]
    if not quelle:
        return case.get("aufgabe") or "Bearbeiten Sie den Abschnitt nach dem Skript."
    try:
        out = complete(AUFGABE_PROMPT.format(text=quelle), max_tokens=700).strip()
        out = re.sub(r"\*\*+", "", out)
        if len(out) > 180:
            return out
    except Exception as e:
        print(f"Aufgabe: {e}", file=sys.stderr)
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


def _is_zivil(case):
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


def _court_ok(court, case):
    c = (court or "").lower()
    if _is_zivil(case):
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


def shape_excerpt(text: str):
    try:
        out = complete(EXCERPT_PROMPT.format(text=text[:8000]), max_tokens=1200).strip()
    except Exception as e:
        print(f"Zuschnitt: {e}", file=sys.stderr)
        low = text.lower()
        i = low.find("im namen des volkes")
        return text[i if i >= 0 else 0: (i if i >= 0 else 0) + 3800]
    if not out or out.upper().startswith("UNPASSEND"):
        return None
    if _is_straf(out):
        return None
    return out[:4000]


def search_related_case(case, seen_slugs: list[str]):
    seen = set(seen_slugs or [])
    terms = [
        "Landgericht Urteil Klaegerin Beklagte ZPO",
        "Oberlandesgericht Zivilsenat Tenor Klaegerin",
        "Bundesgerichtshof Urteil ZPO Klaeger",
        "Landgericht Halle Urteil Klaegerin",
        "Landgericht Magdeburg Urteil Zivilkammer",
    ] + list(case.get("suchbegriffe") or [])
    if _is_verw(case):
        terms = ["Verwaltungsgericht Im Namen des Volkes Klaeger"] + terms
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
            if _is_straf(raw, slug):
                continue
            court = _court_name(r.get("court"))
            if not _court_ok(court, case):
                continue
            if len(raw) < 200:
                continue
            shaped = shape_excerpt(raw)
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
    rules, muster = load_skript_section(case)
    aufgabe = aufgabe_aus_skript(case, rules, muster)
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
