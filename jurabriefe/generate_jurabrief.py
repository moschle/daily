#!/usr/bin/env python3
"""Jurabrief: Lesetext + Aufgabe aus dem Skript."""

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

from claude_client import complete
from adaptive_plan import pick

BERLIN_TZ = ZoneInfo("Europe/Berlin")
STATE_FILE = _HERE / "state.json"
CASES_FILE = _HERE / "cases.json"
PROGRESS_FILE = _HERE / "progress.json"
LERNPLAN_FILE = _HERE / "lernplan.json"
OLD_BASE = "https://de.openlegaldata.io/api/cases/search/"

ZR_COURTS = ("lg", "olg", "bgh", "kg", "ag")
VR_COURTS = ("vg", "ovg", "bverwg", "vgh")


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


def _court_ok(court: str, gebiet: str) -> bool:
    c = (court or "").lower()
    g = (gebiet or "").lower()
    if "zivil" in g:
        return any(tok in c for tok in ZR_COURTS)
    if "verwalt" in g:
        return any(tok in c for tok in VR_COURTS)
    return True


def search_related_case(case):
    terms = [t for t in case.get("suchbegriffe", []) if t]
    cited = case.get("cited_law") or {}
    base = {
        "start_date": "2019-01-01",
        "end_date": now_berlin().strftime("%Y-%m-%d"),
        "order_by": "relevance",
        "return_text": "1",
        "page_size": "8",
    }
    attempts = []
    if terms:
        attempts.append({**base, "text": " ".join(terms)})
        attempts.append({**base, "text": terms[0]})
    if cited.get("book") and cited.get("section"):
        attempts.append({
            **base,
            "text": f"{cited['book']} {cited['section']}",
        })

    pool = []
    for params in attempts:
        hits = _old_search(params)
        print(f"OLD search text={params.get('text')!r} hits={len(hits)}", file=sys.stderr)
        pool.extend(hits)
        if pool:
            break

    gebiet = case.get("gebiet", "")
    ranked = []
    for r in pool:
        court = r.get("court") or ""
        if isinstance(court, dict):
            court = court.get("name") or court.get("slug") or ""
        ranked.append((0 if _court_ok(str(court), gebiet) else 1, r, court))
    ranked.sort(key=lambda x: x[0])

    for _prio, r, court in ranked:
        text = r.get("text") or ""
        if not text:
            snippets = r.get("snippets") or []
            text = "\n".join(s.get("text", "") for s in snippets if isinstance(s, dict))
        if len(text) < 200:
            continue
        slug = r.get("slug") or ""
        snippet = text[:4500] + ("..." if len(text) > 4500 else "")
        return {
            "gericht": court,
            "datum": r.get("date", ""),
            "aktenzeichen": slug,
            "entscheidungstyp": r.get("decision_type", ""),
            "text": snippet,
            "url": f"https://de.openlegaldata.io/case/{slug}/" if slug else "",
        }
    return None


def lesehinweis(case, related):
    sprache = ", ".join(case.get("behoerdensprache", [])[:4])
    prompt = (
        "Zwei bis drei Sätze auf Deutsch, Urteilsstil, keine Anrede, keine Aufforderung. "
        "Nur worauf Tenor und Gründe für das Thema relevant sind. "
        f"Thema: {case.get('gebiet', '')}. "
        f"Kern: {case.get('kernfrage', '')}. "
        f"Begriffe: {sprache}."
    )
    if related:
        prompt += f" Gericht: {related.get('gericht')} {related.get('datum')}."
    try:
        return complete(prompt, max_tokens=180).strip()
    except Exception as e:
        print(f"Claude-Fehler (Lesehinweis): {e}", file=sys.stderr)
        return case.get("kernfrage", "")


def build_mail(case, related, hint, today_str):
    quelle = case.get("quelle", "Berliner Ausbildungsskript")
    sprache = ", ".join(case.get("behoerdensprache", []))
    form = (
        "staatliche Klausur: Rubrum, Tenor, Tatbestand, Gründe."
        if "staatlich" in case.get("gebiet", "").lower()
        else "anwaltliche Klausur: Gutachten und Schriftsatz."
    )

    if related:
        lesen = (
            f"I. Lesetext\n"
            f"{related['gericht']}, {related['entscheidungstyp']} vom {related['datum']}, {related['aktenzeichen']}\n"
            f"{related['url']}\n\n"
            f"{hint}\n\n"
            f"---\n"
            f"{related['text']}\n"
        )
    else:
        lesen = "I. Lesetext\nKein passendes Urteil in der Abfrage.\n"

    aufgabe = (
        f"II. Bearbeitung\n"
        f"{case['gebiet']}\n"
        f"{quelle}\n\n"
        f"{case['kernfrage']}\n\n"
        f"Form: {form}\n"
        f"Begriffe: {sprache}\n"
    )

    return f"Jurabrief — {today_str}\n{case['gebiet']}\n\n{lesen}\n\n{aufgabe}\n"


def send_mail(subject, body, to_addr):
    gmail = (os.environ.get("GMAIL_ADDRESS") or "").strip()
    pw = (os.environ.get("GMAIL_APP_PASSWORD") or "").strip()
    if not gmail or not pw:
        print("Keine Gmail-Secrets, Mail wird nicht gesendet.", file=sys.stderr)
        print(body)
        return
    if not to_addr or "@" not in to_addr:
        print("Kein gültiger Empfänger. Mail wird nicht gesendet.", file=sys.stderr)
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
        print("Keine Fälle in cases.json.", file=sys.stderr)
        sys.exit(1)

    state = load_state()
    case, grund = pick_case(cases, state)
    save_state(state)

    today = now_berlin().strftime("%A, %d. %B %Y")
    related = search_related_case(case)
    hint = lesehinweis(case, related)
    body = build_mail(case, related, hint, today)

    to_addr = resolve_to()
    subject = f"Jurabrief — {case['gebiet']} [{case['id']}] ({now_berlin().strftime('%d.%m.')})"
    send_mail(subject, body, to_addr)
    print(f"Fall {case['id']} gewählt ({grund}).")


if __name__ == "__main__":
    main()
