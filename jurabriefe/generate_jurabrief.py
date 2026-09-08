#!/usr/bin/env python3
"""Jurabrief: Lesetext + Aufgabe aus dem Skript-Volltext."""

from __future__ import annotations

import json
import os
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

EXCERPT_PROMPT = """Du erhaeltst den Anfang eines deutschen Gerichtsurteils.
Gib ausschliesslich den Text wieder, den eine Referendarin fuer Rubrum, Tenor und den Einstieg in den Tatbestand braucht.
Keine Anrede, kein Kommentar. Orientierungssatz weglassen, wenn Tenor vorhanden.
Tenor vollstaendig. Nicht umformulieren.
Wenn der Text nicht zur Gerichtsbarkeit passt: UNPASSEND.

Text:
{text}
"""

AUFGABE_PROMPT = """Formuliere eine Klausuraufgabe. Nur die Aufgabe.
Wenn ein vollstaendiges Musterrubrum vorkommt (Gericht, Aktenzeichen, Parteien, Tenor):
dieses eine Muster ist der Sachverhalt. Keine zweite Beispielgruppe dazu mischen.
Keine neuen Namen. Keine Loesung. Keine Anrede. Kein Fragenkatalog.
Auftrag: den Urteilskopf nach dem Skript fertigen.

Skript:
{text}
"""


def now_berlin():
    return datetime.now(BERLIN_TZ)


def resolve_to() -> str:
    to_addr = (os.environ.get("JURABRIEF_TO") or "").strip()
    if not to_addr:
        to_addr = (os.environ.get("GMAIL_ADDRESS") or "").strip()
    return to_addr


def load_cases():
    if CASES_FILE.exists():
        with open(CASES_FILE, encoding="utf-8") as f:
            return json.load(f).get("cases", [])
    return []


def load_state():
    if STATE_FILE.exists():
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {"done": [], "next_index": 0, "last_id": None}


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def load_progress():
    if PROGRESS_FILE.exists():
        return json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
    return {"gewichte": {}, "feedback": [], "letzte_anpassung": None}


def load_plan():
    if LERNPLAN_FILE.exists():
        return json.loads(LERNPLAN_FILE.read_text(encoding="utf-8"))
    return {"phasen": []}


def pick_case(cases, state):
    try:
        plan = load_plan()
        progress = load_progress()
        res = pick(cases, plan, progress)
        case = res["case"]
        state["last_id"] = case["id"]
        state.setdefault("done", []).append(case["id"])
        return case, res.get("grund", "adaptiv")
    except Exception as e:
        print(f"Adaptiver Plan Fehler, Fallback: {e}", file=sys.stderr)
        done = set(state.get("done", []))
        remaining = [c for c in cases if c["id"] not in done]
        if not remaining:
            state["done"] = []
            remaining = cases
        idx = state.get("next_index", 0) % len(remaining)
        case = remaining[idx]
        state["done"].append(case["id"])
        state["next_index"] = (idx + 1) % max(len(remaining), 1)
        state["last_id"] = case["id"]
        return case, "zyklus"


def _find_body(text: str, needle: str) -> int:
    if not needle:
        return 0
    pos = 0
    fallback = -1
    while True:
        i = text.find(needle, pos)
        if i < 0:
            return fallback if fallback >= 0 else 0
        line_end = text.find("\n", i)
        line = text[i: line_end if line_end > i else i + 80]
        if "...." in line or "\u2026" in line:
            if fallback < 0:
                fallback = i
            pos = i + len(needle)
            continue
        return i


def _cut_clean(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    cut = text.rfind("\n\n", 0, limit)
    if cut < limit // 2:
        cut = text.rfind("\n", 0, limit)
    if cut < limit // 2:
        cut = limit
    return text[:cut].rstrip()


def load_skript_section(case: dict) -> str:
    sid = case.get("skript_id")
    if not sid:
        return ""
    path = EXTRACTED / f"{sid}.txt"
    if not path.exists():
        print(f"kein Volltext {path}", file=sys.stderr)
        return ""
    text = path.read_text(encoding="utf-8")
    start = case.get("skript_start") or ""
    end = case.get("skript_end") or ""
    i = _find_body(text, start)
    j = _find_body(text, end) if end else -1
    if j <= i:
        j = min(len(text), i + 20000)
    chunk = text[i:j]
    muster_at = -1
    for mark in ("Amtsgericht Neukölln", "12 C 310/24", "Im Namen des Volkes"):
        k = chunk.find(mark)
        if k >= 0:
            muster_at = k
            if mark != "Im Namen des Volkes":
                break
    if muster_at >= 0:
        head = _cut_clean(chunk[:muster_at], 2200)
        tail = chunk[muster_at:]
        tail = _cut_clean(tail, 4500)
        chunk = (head + "\n\n" + tail).strip()
    else:
        chunk = _cut_clean(chunk.strip(), 7000)
    return chunk


def aufgabe_aus_skript(case: dict, section: str) -> str:
    if not section:
        return case.get("aufgabe") or case.get("kernfrage") or ""
    try:
        out = complete(AUFGABE_PROMPT.format(text=section[:6000]), max_tokens=400).strip()
        if out:
            return out
    except Exception as e:
        print(f"Aufgabe aus Skript: {e}", file=sys.stderr)
    return case.get("aufgabe") or ""


def _old_search(params: dict) -> list:
    url = OLD_BASE + "?" + urllib.parse.urlencode(params)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "jurabrief/1.0"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"Open Legal Data Fehler: {e}", file=sys.stderr)
        return []
    return data.get("results") or []


def _is_zivil(case: dict) -> bool:
    kind = (case.get("gerichtsbarkeit") or "").lower()
    return kind == "zivil" or "zivil" in case.get("gebiet", "").lower()


def _is_verw(case: dict) -> bool:
    kind = (case.get("gerichtsbarkeit") or "").lower()
    return kind == "verwaltung" or "verwalt" in case.get("gebiet", "").lower()


def _court_ok(court: str, case: dict) -> bool:
    c = (court or "").lower()
    if _is_zivil(case):
        if any(tok in c for tok in VR_COURTS):
            return False
        return any(tok in c for tok in ZR_COURTS)
    if _is_verw(case):
        return any(tok in c for tok in VR_COURTS)
    return True


def _court_name(court) -> str:
    if isinstance(court, dict):
        return court.get("name") or court.get("slug") or ""
    return str(court or "")


def _result_text(r: dict) -> str:
    text = r.get("text") or ""
    if text:
        return text
    snippets = r.get("snippets") or []
    return "\n".join(s.get("text", "") for s in snippets if isinstance(s, dict))


def _score_hit(text: str) -> int:
    t = text.lower()
    score = 0
    if "tenor" in t:
        score += 3
    if "im namen des volkes" in t:
        score += 4
    if "kläger" in t and "beklag" in t:
        score += 2
    if "prozessbevollm" in t:
        score += 2
    return score


def _cut_native(text: str) -> str:
    low = text.lower()
    start = 0
    for marker in ("im namen des volkes", "tenor", "urteil"):
        i = low.find(marker)
        if i != -1:
            start = i
            break
    return text[start:start + 3800].strip()


def shape_excerpt(text: str) -> str | None:
    try:
        out = complete(EXCERPT_PROMPT.format(text=text[:8000]), max_tokens=1200).strip()
    except Exception as e:
        print(f"Claude-Zuschnitt: {e}", file=sys.stderr)
        return _cut_native(text)
    if not out or out.upper().startswith("UNPASSEND"):
        return None
    return out[:4000]


def search_related_case(case):
    terms = [t for t in case.get("suchbegriffe", []) if t]
    if _is_zivil(case):
        terms = ["Im Namen des Volkes Tenor Landgericht"] + terms
    elif _is_verw(case):
        terms = ["Verwaltungsgericht Im Namen des Volkes Tenor"] + terms
    seen = set()
    queries = [t for t in terms if not (t in seen or seen.add(t))]
    base = {
        "start_date": "2019-01-01",
        "end_date": now_berlin().strftime("%Y-%m-%d"),
        "order_by": "relevance",
        "return_text": "1",
        "page_size": "8",
    }
    candidates = []
    for text_q in queries:
        hits = _old_search({**base, "text": text_q})
        print(f"OLD search text={text_q!r} hits={len(hits)}", file=sys.stderr)
        for r in hits:
            court = _court_name(r.get("court"))
            if not _court_ok(court, case):
                continue
            raw = _result_text(r)
            if len(raw) < 200:
                continue
            candidates.append((_score_hit(raw), r, court, raw))
        if any(s >= 5 for s, *_ in candidates):
            break
    candidates.sort(key=lambda x: x[0], reverse=True)
    for _score, r, court, raw in candidates:
        shaped = shape_excerpt(raw)
        if not shaped:
            continue
        slug = r.get("slug") or ""
        return {
            "gericht": court,
            "datum": r.get("date", ""),
            "aktenzeichen": r.get("file_number") or slug,
            "entscheidungstyp": r.get("decision_type") or r.get("type") or "Urteil",
            "text": shaped,
            "url": f"https://de.openlegaldata.io/case/{slug}/" if slug else "",
        }
    return None


def build_mail(case, related, section, aufgabe, today_str):
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
    if section:
        block2 += "\n--- Skript ---\n" + section + "\n"
    return f"Jurabrief — {today_str}\n{case['gebiet']}\n\n{lesen}\n\n{block2}\n"


def send_mail(subject, body, to_addr):
    gmail = (os.environ.get("GMAIL_ADDRESS") or "").strip()
    pw = (os.environ.get("GMAIL_APP_PASSWORD") or "").strip()
    if not gmail or not pw:
        print("Keine Gmail-Secrets, Mail wird nicht gesendet.", file=sys.stderr)
        print(body)
        return
    if not to_addr or "@" not in to_addr:
        print("Kein Empfaenger.", file=sys.stderr)
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
    cases = load_cases()
    if not cases:
        sys.exit(1)
    state = load_state()
    case, grund = pick_case(cases, state)
    save_state(state)
    section = load_skript_section(case)
    aufgabe = aufgabe_aus_skript(case, section)
    related = search_related_case(case)
    today = now_berlin().strftime("%A, %d. %B %Y")
    body = build_mail(case, related, section, aufgabe, today)
    send_mail(
        f"Jurabrief — {case['gebiet']} [{case['id']}] ({now_berlin().strftime('%d.%m.')})",
        body,
        resolve_to(),
    )
    print(f"Fall {case['id']} gewaehlt ({grund}), Skript {len(section)} Zeichen.")


if __name__ == "__main__":
    main()
