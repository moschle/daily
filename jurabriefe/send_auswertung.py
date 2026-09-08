#!/usr/bin/env python3
"""Sendet am Zwischentag (Di/Do) die Auswertung der gestrigen Klausur.

Liest last_grade.json, baut eine Mail mit Stärken, Lücken, Verbesserung und
nächstem FSRS-Termin, schickt sie an JURABRIEF_TO.
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

from fsrs_scheduler import next_review_date

TZ = ZoneInfo("Europe/Berlin")
ROOT = Path(__file__).parent
GRADE_FILE = ROOT / "last_grade.json"


def build_body(g: dict) -> str:
    cid = g.get("case_id", "?")
    next_due = next_review_date(cid)
    next_str = next_due[:10] if next_due else "noch offen"
    staerken = "\n".join(f"- {s}" for s in g.get("staerken", [])[:4]) or "- (keine notiert)"
    luecken = "\n".join(f"- {l}" for l in g.get("luecken", [])[:4]) or "- (keine)"
    verb = "\n".join(f"- {v}" for v in g.get("verbesserung", [])[:4]) or "- (keine)"
    muster = g.get("muster_kurz", "")
    punkte = g.get("punkte", "?")
    note = g.get("note", "?")
    return (
        f"Auswertung — {g.get('gebiet', cid)}\n\n"
        f"Punkte: {punkte}/18   Note: {note}/5\n\n"
        f"Stärken:\n{staerken}\n\n"
        f"Lücken:\n{luecken}\n\n"
        f"Nächstes Mal beachten:\n{verb}\n\n"
        f"Musterlösung (kurz): {muster}\n\n"
        f"Nächste Wiederholung (FSRS): {next_str}\n"
    )


def send(body: str, to_addr: str):
    gmail = (os.environ.get("GMAIL_ADDRESS") or "").strip()
    pw = (os.environ.get("GMAIL_APP_PASSWORD") or "").strip()
    if not gmail or not pw or "@" not in (to_addr or ""):
        print("Kein Empfänger oder keine SMTP-Secrets.", file=sys.stderr)
        raise SystemExit(2)
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = f"Jurabrief-Auswertung — {datetime.now(TZ).strftime('%d.%m.')}"
    msg["From"] = gmail
    msg["To"] = to_addr
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(gmail, pw)
        s.sendmail(gmail, [to_addr], msg.as_string())
    print("Auswertung gesendet.")


def main():
    if not GRADE_FILE.exists():
        print("Keine last_grade.json — erst grade_solution.py laufen lassen.")
        return
    g = json.loads(GRADE_FILE.read_text(encoding="utf-8"))
    if g.get("fehler"):
        print(f"Bewertung hatte Fehler: {g['fehler']}")
        return
    body = build_body(g)
    to_addr = (os.environ.get("JURABRIEF_TO") or os.environ.get("GMAIL_ADDRESS") or "").strip()
    send(body, to_addr)


if __name__ == "__main__":
    main()
