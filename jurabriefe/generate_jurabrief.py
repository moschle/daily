#!/usr/bin/env python3
"""Jurabrief: Mail mit zwei Blöcken.

1) Verwandtes Urteil zum Lesen (Sprache, Tenor, Begründung)
2) Aufgabe aus dem Skript-Fall (lösen, keine neu generierte Klausur)

Der Betreff enthält die Fall-ID in eckigen Klammern, damit die Antwortmail
automatisch zugeordnet werden kann: [zr-001].
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

from claude_client import complete
from adaptive_plan import pick

BERLIN_TZ = ZoneInfo("Europe/Berlin")
STATE_FILE = Path(__file__).parent / "state.json"
CASES_FILE = Path(__file__).parent / "cases.json"
PROGRESS_FILE = Path(__file__).parent / "progress.json"
LERNPLAN_FILE = Path(__file__).parent / "lernplan.json"
OLD_BASE = "https://de.openlegaldata.io/api/cases/search/"

SEED_CASES = []


def now_berlin():
    return datetime.now(BERLIN_TZ)


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
    """Adaptiver Plan: Phase + FSRS-Fälligkeit + Gewicht. Fällt zurück auf
    zyklisches Picking, falls adaptive_plan nicht greift."""
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


def search_related_case(case):
    cited = case.get("cited_law") or {}
    params = {
        "text": " ".join(case.get("suchbegriffe", [])),
        "start_date": "2019-01-01",
        "end_date": now_berlin().strftime("%Y-%m-%d"),
        "order_by": "relevance",
        "return_text": "1",
        "page_size": "3",
    }
    if cited.get("book"):
        params["cited_law_book"] = cited["book"]
    if cited.get("section"):
        params["cited_law_section"] = cited["section"]
    url = OLD_BASE + "?" + urllib.parse.urlencode(params)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "jurabrief/1.0"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"Open Legal Data Fehler: {e}", file=sys.stderr)
        return None

    results = data.get("results", [])
    if not results:
        return None
    # Erstes Ergebnis, das nicht exakt dem Skript-Beispiel entspricht
    for r in results:
        text = r.get("text") or ""
        if len(text) > 200:  # Mindestlänge für Relevanz
            snippet = text[:4500] + (…" if len(text) > 4500 else "")
            return {
                "gericht": r.get("court", ""),
                "datum": r.get("date", ""),
                "aktenzeichen": r.get("slug", ""),
                "entscheidungstyp": r.get("decision_type", ""),
                "text": snippet,
                "url": f"https://de.openlegaldata.io/case/{r.get('slug', '')}/",
            }
    return None


def lesehinweis(case, related):
    """Kurzer Blickwinkel fürs Lesen — kein neuer Fall."""
    sprache = ", ".join(case.get("behoerdensprache", [])[:4])
    prompt = (
        "Schreibe auf Deutsch zwei bis drei kurze Sätze als Lesehinweis. "
        "Kein Sachverhalt, keine Klausuraufgabe, keine Lösung. "
        f"Thema: {case.get('gebiet', '')}. "
        f"Worauf achten: {case.get('kernfrage', '')}. "
        f"Typische Formulierungen: {sprache}. "
        "Sage der Leserin, worauf sie im Tenor und in den Gründen achten soll."
    )
    if related:
        prompt += f" Gericht des Textes: {related.get('gericht')} {related.get('datum')}."
    try:
        return complete(prompt, max_tokens=220).strip()
    except Exception as e:
        print(f"Claude-Fehler (Lesehinweis): {e}", file=sys.stderr)
        return (
            f"Achte beim Lesen auf Tenor und Begründungsaufbau. "
            f"Kernfrage zum Thema: {case.get('kernfrage', '')}"
        )


def build_mail(case, related, hint, today_str):
    quelle = case.get("quelle", "Berliner Ausbildungsskript")
    sprache = ", ".join(case.get("behoerdensprache", []))

    if related:
        lesen = (
            f"TEIL 1 — LESEN (Sprache und Aufbau)\n"
            f"Lies den Auszug. Löse ihn nicht. Er ist nur zum Einlesen.\n\n"
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
        f"Schreib deine Lösung in der Form, die das Skript verlangt "
        f"(staatlich: Urteilsteile; anwaltlich: Gutachten plus Schriftsatz).\n"
        f"Eine kurze Musterlösung kommt im nächsten Brief dazu.\n"
    )

    return (
        f"Jurabrief — {today_str}\n"
        f"Heute: {case['gebiet']}\n\n"
        f"{lesen}\n\n"
        f"{aufgabe}\n"
    )


def send_mail(subject, body, to_addr):
    gmail = os.environ.get("GMAIL_ADDRESS", "")
    pw = os.environ.get("GMAIL_APP_PASSWORD", "")
    if not gmail or not pw:
        print("Keine Gmail-Secrets, Mail wird nicht gesendet.", file=sys.stderr)
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

    to_addr = os.environ.get("JURABRIEF_TO", os.environ.get("GMAIL_ADDRESS", ""))
    subject = f"Jurabrief — {case['gebiet']} [{case['id']}] ({now_berlin().strftime('%d.%m.')})"
    send_mail(subject, body, to_addr)
    print(f"Fall {case['id']} gewählt ({grund}).")


if __name__ == "__main__":
    main()
