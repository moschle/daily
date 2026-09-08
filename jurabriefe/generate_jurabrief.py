#!/usr/bin/env python3
"""Jurabrief: Mail mit zwei Bloecken.

1) Verwandtes Urteil zum Lesen (Sprache, Tenor, Begruendung)
2) Aufgabe aus dem Skript-Fall (loesen, keine neu generierte Klausur)
"""

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

SEED_CASES = []


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
            return json.load(f).get("cases", SEED_CASES)
    return SEED_CASES


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


def search_related_case(case):
    terms = [t for t in case.get("suchbegriffe", []) if t]
    cited = case.get("cited_law") or {}
    base = {
        "start_date": "2019-01-01",
        "end_date": now_berlin().strftime("%Y-%m-%d"),
        "order_by": "relevance",
        "return_text": "1",
        "page_size": "5",
    }
    attempts = []
    if terms:
        attempts.append({**base, "text": " ".join(terms)})
        attempts.append({**base, "text": terms[0]})
    if cited.get("book") and cited.get("section"):
        attempts.append({
            **base,
            "text": cited["book"].upper() + " " + str(cited["section"]),
            "cited_law_book": cited["book"],
            "cited_law_section": str(cited["section"]),
        })
    if not attempts:
        attempts.append({**base, "text": case.get("gebiet", "Urteil")})

    results = []
    for params in attempts:
        results = _old_search(params)
        print(f"OLD search text={params.get('text')!r} hits={len(results)}", file=sys.stderr)
        if results:
            break

    for r in results:
        text = r.get("text") or ""
        if not text:
            snippets = r.get("snippets") or []
            text = "\n".join(s.get("text", "") for s in snippets if isinstance(s, dict))
        if len(text) < 200:
            continue
        court = r.get("court") or ""
        if isinstance(court, dict):
            court = court.get("name") or court.get("slug") or ""
        snippet = text[:4500] + ("..." if len(text) > 4500 else "")
        slug = r.get("slug") or ""
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
        "Schreibe auf Deutsch zwei bis drei kurze Saetze als Lesehinweis. "
        "Kein Sachverhalt, keine Klausuraufgabe, keine Loesung. "
        f"Thema: {case.get('gebiet', '')}. "
        f"Worauf achten: {case.get('kernfrage', '')}. "
        f"Typische Formulierungen: {sprache}. "
        "Sage der Leserin, worauf sie im Tenor und in den Gruenden achten soll."
    )
    if related:
        prompt += f" Gericht des Textes: {related.get('gericht')} {related.get('datum')}."
    try:
        return complete(prompt, max_tokens=220).strip()
    except Exception as e:
        print(f"Claude-Fehler (Lesehinweis): {e}", file=sys.stderr)
        return (
            f"Achte beim Lesen auf Tenor und Begruendungsaufbau. "
            f"Kernfrage zum Thema: {case.get('kernfrage', '')}"
        )


def build_mail(case, related, hint, today_str):
    quelle = case.get("quelle", "Berliner Ausbildungsskript")
    sprache = ", ".join(case.get("behoerdensprache", []))

    if related:
        lesen = (
            f"TEIL 1 — LESEN (Sprache und Aufbau)\n"
            f"Lies den Auszug. Loese ihn nicht. Er ist nur zum Einlesen.\n\n"
            f"Gericht: {related['gericht']}\n"
            f"Datum: {related['datum']}\n"
            f"Aktenzeichen: {related['aktenzeichen']}\n"
            f"Typ: {related['entscheidungstyp']}\n"
            f"Link: {related['url']}\n\n"
            f"Worauf achten:\n{hint}\n\n"
            f"--- Urteil (Auszug) ---\n"
            f"{related['text']}\n"
        )
    else:
        lesen = (
            "TEIL 1 — LESEN\n"
            "Heute kein passendes Urteil gefunden. Geh direkt zur Aufgabe.\n"
        )

    aufgabe = (
        f"TEIL 2 — AUFGABE AUS DEM SKRIPT\n"
        f"Jetzt den Fall aus dem Skript durcharbeiten. Keine neue Klausur.\n\n"
        f"Gebiet: {case['gebiet']}\n"
        f"Quelle: {quelle}\n"
        f"Kernfrage: {case['kernfrage']}\n"
        f"Begrifflichkeiten aus dem Skript: {sprache}\n\n"
        f"Schreib deine Loesung in der Form, die das Skript verlangt "
        f"(staatlich: Urteilsteile; anwaltlich: Gutachten plus Schriftsatz).\n"
        f"Eine kurze Musterloesung kommt im naechsten Brief dazu.\n"
    )

    return (
        f"Jurabrief — {today_str}\n"
        f"Heute: {case['gebiet']}\n\n"
        f"{lesen}\n\n"
        f"{aufgabe}\n"
    )


def send_mail(subject, body, to_addr):
    gmail = (os.environ.get("GMAIL_ADDRESS") or "").strip()
    pw = (os.environ.get("GMAIL_APP_PASSWORD") or "").strip()
    if not gmail or not pw:
        print("Keine Gmail-Secrets, Mail wird nicht gesendet.", file=sys.stderr)
        print(body)
        return
    if not to_addr or "@" not in to_addr:
        print("Kein gueltiger Empfaenger. Mail wird nicht gesendet.", file=sys.stderr)
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
        print("Keine Faelle in cases.json.", file=sys.stderr)
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
    print(f"Fall {case['id']} gewaehlt ({grund}).")


if __name__ == "__main__":
    main()
