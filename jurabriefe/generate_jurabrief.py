#!/usr/bin/env python3
"""Jurabrief: wählt einen Fall, sucht ein verwandtes Urteil (Open Legal Data),
formuliert eine Aufgabe und mailt sie.

Fall-DB basiert auf echten Themen aus den Berliner Ausbildungsskripten
(Kammergericht). Später: Scans Sachsen-Anhalt, Anki-Abgleich.
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

BERLIN_TZ = ZoneInfo("Europe/Berlin")
STATE_FILE = Path(__file__).parent / "state.json"
CASES_FILE = Path(__file__).parent / "cases.json"
OLD_BASE = "https://de.openlegaldata.io/api/cases/search/"

SEED_CASES = [
    {
        "id": "zr-001",
        "gebiet": "Zivilrecht staatliche Sicht — Rubrum / Parteibezeichnungen",
        "kernfrage": "Wie werden Parteien im Rubrum korrekt bezeichnet?",
        "behoerdensprache": ["des Klägers", "gegen den Beklagten"],
        "suchbegriffe": ["Kaufvertrag"],
        "cited_law": {"book": "zpo", "section": "253"},
    },
]


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
    return {"done": [], "next_index": 0}


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def pick_case(cases, state):
    done = set(state.get("done", []))
    remaining = [c for c in cases if c["id"] not in done]
    if not remaining:
        state["done"] = []
        remaining = cases
    idx = state.get("next_index", 0) % len(remaining)
    case = remaining[idx]
    state["done"].append(case["id"])
    state["next_index"] = (idx + 1) % len(remaining)
    return case


def search_related_case(case):
    """Sucht ein relevantes, nicht identisches Urteil über Open Legal Data.
    Filter: cited_law (book+section), Datum ab 2019, Volltext, nach Relevanz.
    """
    params = {
        "text": " ".join(case.get("suchbegriffe", [])),
        "cited_law_book": case["cited_law"]["book"],
        "cited_law_section": case["cited_law"]["section"],
        "start_date": "2019-01-01",
        "end_date": "2026-09-08",
        "order_by": "relevance",
        "return_text": "1",
        "page_size": "3",
    }
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
    # Erstes Ergebnis nehmen (höchste Relevanz, nicht identisch zum Skript-Beispiel)
    r = results[0]
    text = r.get("text") or ""
    # Text auf ~2500 Zeichen kürzen, damit der Prompt schlank bleibt
    snippet = text[:2500] + ("…" if len(text) > 2500 else "")
    return {
        "gericht": r.get("court", ""),
        "datum": r.get("date", ""),
        "aktenzeichen": r.get("slug", ""),
        "entscheidungstyp": r.get("decision_type", ""),
        "text": snippet,
        "url": f"https://de.openlegaldata.io/case/{r.get('slug', '')}/",
    }


def build_prompt(case, related, today_str):
    related_block = ""
    if related:
        related_block = (
            f"VERWANDTES URTEIL (zum Lesen, NICHT identisch mit dem Skript-Beispiel):\n"
            f"Gericht: {related['gericht']}, {related['datum']}, Az. {related['aktenzeichen']}\n"
            f"Typ: {related['entscheidungstyp']}\n"
            f"Text (Auszug):\n{related['text']}\n\n"
        )
    else:
        related_block = (
            "(Kein passendes Urteil gefunden — formuliere die Aufgabe rein aus dem Grundfall.)\n\n"
        )

    return (
        f"Du bist ein erfahrener AG-Leiter für die 2. juristische Staatsprüfung (Zivilrecht).\n"
        f"Heute ist {today_str}.\n\n"
        f"AUFGABE: Formuliere eine Klausur-Aufgabe (Sachverhalt + konkrete Frage).\n"
        f"Gebiet: {case['gebiet']}\n"
        f"Kernfrage: {case['kernfrage']}\n"
        f"Typische Behördensprache: {', '.join(case['behoerdensprache'])}\n\n"
        f"{related_block}"
        f"REGELN:\n"
        f"- Sachverhalt in 4-8 Sätzen, realistisch, mit klarer Struktur.\n"
        f"- Eine präzise Frage am Ende (z. B. 'Hat A gegen B einen Anspruch auf...?').\n"
        f"- Verwende die Behördensprache natürlich im Text.\n"
        f"- Beziehe dich NICHT wörtlich auf das angehängte Urteil; es dient nur als Lese-Hintergrund.\n"
        f"- Keine Lösung, nur die Aufgabe.\n"
        f"- Ausgabe als reiner Text, keine Markdown-Überschriften.\n"
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
    state = load_state()
    case = pick_case(cases, state)
    save_state(state)

    today = now_berlin().strftime("%A, %d. %B %Y")
    related = search_related_case(case)
    prompt = build_prompt(case, related, today)
    try:
        body = complete(prompt, max_tokens=1800)
    except Exception as e:
        print(f"Claude-Fehler: {e}", file=sys.stderr)
        body = (
            f"[Fallback] Heute: {case['gebiet']}.\n"
            f"Kernfrage: {case['kernfrage']}\n"
            f"Bitte manuell einen Sachverhalt dazu formulieren."
        )

    to_addr = os.environ.get("JURABRIEF_TO", os.environ.get("GMAIL_ADDRESS", ""))
    subject = f"Jurabrief — {case['gebiet']} ({now_berlin().strftime('%d.%m.')})"
    send_mail(subject, body, to_addr)


if __name__ == "__main__":
    main()
