#!/usr/bin/env python3
"""Liest Antwortmails auf den Jurabrief (IMAP) und speichert die Lösung.

Konvention in der Antwortmail:
  BETREFF: Re: Jurabrief — … [zr-001] …
  ERSTE ZEILE: SCORE: 1-5   (1 = unsicher, 5 = sitzt)
  Rest: Lösungstext

Schreibt pending_solution.json mit case_id + Lösung, damit der nächste
Schritt (grade_solution.py) sie bewerten kann. Kein manuelles Anlegen nötig.
"""
from __future__ import annotations

import email
import imaplib
import json
import os
import re
from datetime import datetime
from email.header import decode_header
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).parent
PROGRESS = ROOT / "progress.json"
STATE = ROOT / "state.json"
PENDING = ROOT / "pending_solution.json"
TZ = ZoneInfo("Europe/Berlin")


def _dec(val) -> str:
    if not val:
        return ""
    parts = decode_header(val)
    out = []
    for text, enc in parts:
        if isinstance(text, bytes):
            out.append(text.decode(enc or "utf-8", errors="replace"))
        else:
            out.append(text)
    return "".join(out)


def load_progress():
    if PROGRESS.exists():
        return json.loads(PROGRESS.read_text(encoding="utf-8"))
    return {"gewichte": {}, "feedback": [], "letzte_anpassung": None}


def apply_score(progress, case_id: str, score: int):
    w = progress["gewichte"].get(case_id, 1.0)
    if score <= 2:
        w = min(3.0, w + 0.5)
    elif score >= 4:
        w = max(0.4, w - 0.3)
    progress["gewichte"][case_id] = round(w, 2)


def extract_solution(body: str) -> str:
    """Entfernt die SCORE-Zeile und führt den Rest als Lösungstext zurück."""
    lines = body.splitlines()
    start = 0
    for i, line in enumerate(lines):
        if re.match(r"^\s*SCORE:\s*[1-5]\b", line, re.I):
            start = i + 1
            break
    sol = "\n".join(lines[start:]).strip()
    sol = re.sub(r"\n{3,}", "\n\n", sol)
    return sol


def extract_case_id_from_subject(subj: str) -> str | None:
    m = re.search(r"\[([a-z]{2}-\d{3})\]", subj)
    return m.group(1) if m else None


def main() -> None:
    user = os.environ.get("GMAIL_ADDRESS", "")
    pw = os.environ.get("GMAIL_APP_PASSWORD", "")
    if not user or not pw:
        print("Keine Gmail-Secrets.")
        return

    state = {}
    if STATE.exists():
        state = json.loads(STATE.read_text(encoding="utf-8"))
    last_id = state.get("last_id")

    progress = load_progress()
    seen = {f.get("uid") for f in progress.get("feedback", [])}

    imap = imaplib.IMAP4_SSL("imap.gmail.com")
    imap.login(user, pw)
    imap.select("INBOX")
    typ, data = imap.search(None, '(SUBJECT "Jurabrief")')
    if typ != "OK":
        print("Suche fehlgeschlagen.")
        return

    new = 0
    for uid in data[0].split():
        uid_s = uid.decode()
        if uid_s in seen:
            continue
        typ, msgdata = imap.fetch(uid, "(RFC822)")
        if typ != "OK":
            continue
        msg = email.message_from_bytes(msgdata[0][1])
        subj = _dec(msg.get("Subject", ""))
        if not subj.lower().startswith("re:"):
            continue
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    raw = part.get_payload(decode=True) or b""
                    body = raw.decode(part.get_content_charset() or "utf-8", errors="replace")
                    break
        else:
            raw = msg.get_payload(decode=True) or b""
            body = raw.decode(msg.get_content_charset() or "utf-8", errors="replace")

        m = re.search(r"SCORE:\s*([1-5])", body, re.I)
        score = int(m.group(1)) if m else None
        case_id = extract_case_id_from_subject(subj) or last_id
        sol = extract_solution(body)

        if score and case_id:
            apply_score(progress, case_id, score)
        if sol and case_id:
            PENDING.write_text(
                json.dumps({"case_id": case_id, "loesung": sol, "score": score,
                            "at": datetime.now(TZ).isoformat(timespec="seconds")},
                           ensure_ascii=False, indent=2), encoding="utf-8")
        progress["feedback"].append({
            "uid": uid_s,
            "subject": subj,
            "case_id": case_id,
            "score": score,
            "len": len(body),
            "at": datetime.now(TZ).isoformat(timespec="seconds"),
        })
        new += 1

    progress["letzte_anpassung"] = datetime.now(TZ).isoformat(timespec="seconds")
    PROGRESS.write_text(json.dumps(progress, ensure_ascii=False, indent=2), encoding="utf-8")
    imap.logout()
    print(f"neue Antworten: {new}")


if __name__ == "__main__":
    main()
