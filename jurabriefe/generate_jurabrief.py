#!/usr/bin/env python3
"""Jurabrief: wählt einen Zivilrechts-Fall, formuliert eine Aufgabe und mailt sie.

Fall-DB basiert auf echten Themen aus den Berliner Ausbildungsskripten
(Kammergericht): Zivilrecht staatliche/anwaltliche Sicht, VerwR.
Später:
- deine Scans (Sachsen-Anhalt) einpflegen
- Anki-Abgleich
- Open Legal Data API für verwandte Urteile (return_text=1)
"""

from __future__ import annotations

import json
import os
import smtplib
import sys
from datetime import datetime
from email.mime.text import MIMEText
from pathlib import Path
from zoneinfo import ZoneInfo

from claude_client import complete

BERLIN_TZ = ZoneInfo("Europe/Berlin")
STATE_FILE = Path(__file__).parent / "state.json"
CASES_FILE = Path(__file__).parent / "cases.json"

SEED_CASES = [
    {
        "id": "zr-001",
        "gebiet": "Zivilrecht staatliche Sicht — Rubrum / Parteibezeichnungen",
        "kernfrage": "Wie werden Parteien, Streitgenossen, Kaufleute, Erben und gesetzliche Vertreter im Rubrum korrekt bezeichnet?",
        "behoerdensprache": ["des Klägers", "gegen den Beklagten", "Prozessbevollmächtigte"],
        "verwandte_urteile_hinweis": "Struktur nach §§ 253, 750 ZPO",
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


def build_prompt(case, today_str):
    return (
        f"Du bist ein erfahrener AG-Leiter für die 2. juristische Staatsprüfung (Zivilrecht).\n"
        f"Heute ist {today_str}.\n\n"
        f"AUFGABE: Formuliere eine Klausur-Aufgabe (Sachverhalt + konkrete Frage) zu folgendem Grundfall.\n"
        f"Gebiet: {case['gebiet']}\n"
        f"Kernfrage: {case['kernfrage']}\n"
        f"Typische Behördensprache, die vorkommen soll: {', '.join(case['behoerdensprache'])}\n"
        f"Hinweis auf verwandte Rspr.: {case['verwandte_urteile_hinweis']}\n\n"
        f"REGELN:\n"
        f"- Sachverhalt in 4-8 Sätzen, realistisch, mit klarer Struktur.\n"
        f"- Eine präzise Frage am Ende (z. B. 'Hat A gegen B einen Anspruch auf...?').\n"
        f"- Verwende die genannte Behördensprache natürlich im Text.\n"
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
    prompt = build_prompt(case, today)
    try:
        body = complete(prompt, max_tokens=1500)
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
