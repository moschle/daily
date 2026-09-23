#!/usr/bin/env python3
"""Postfachbericht: was ging raus, was kam zurueck, wurde es richtig zugeordnet?

Liest alle Jurabrief-Mails der letzten Wochen aus "Alle Nachrichten" (dorthin
verschiebt korrektur.py die verarbeiteten Antworten) und schickt eine Uebersicht
an GMAIL_ADDRESS — an den Betreiber, NICHT an JURABRIEF_TO.

Ins Action-Log geht nur eine Zaehlung. Das Repo ist oeffentlich, die Antworten
der Bearbeiterin gehoeren nicht in Logs oder Dateien.

    python jurabriefe/postfachbericht.py          # 21 Tage
    python jurabriefe/postfachbericht.py 42
"""
from __future__ import annotations

import email
import imaplib
import json
import os
import re
import smtplib
import sys
from datetime import date, timedelta
from email.header import decode_header, make_header
from email.message import EmailMessage
from email.utils import parsedate_to_datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from korrektur import _text_aus, einordnen, ohne_zitat  # noqa: E402


def _ordner(M: imaplib.IMAP4_SSL, flag: str) -> str | None:
    """Sonderordner per Kennzeichen finden (\\All, \\Sent) — sprachunabhaengig."""
    _, zeilen = M.list()
    for z in zeilen or []:
        z = z.decode(errors="replace")
        if flag in z:
            m = re.search(r'"([^"]+)"\s*$', z) or re.search(r"(\S+)\s*$", z)
            if m:
                return m.group(1)
    return None


def hole(tage: int) -> list[dict]:
    adresse = (os.environ.get("GMAIL_ADDRESS") or "").strip()
    pw = (os.environ.get("GMAIL_APP_PASSWORD") or "").strip()
    if not adresse or not pw:
        raise SystemExit("GMAIL_ADDRESS / GMAIL_APP_PASSWORD fehlen")
    seit = (date.today() - timedelta(days=tage)).strftime("%d-%b-%Y")
    mails, gesehen = [], set()
    with imaplib.IMAP4_SSL("imap.gmail.com") as M:
        M.login(adresse, pw)
        ordner = [o for o in (_ordner(M, "\\All"), _ordner(M, "\\Sent"), "INBOX") if o]
        for o in dict.fromkeys(ordner):
            if M.select(f'"{o}"', readonly=True)[0] != "OK":
                continue
            _, daten = M.search(None, f'(SUBJECT "Jurabrief" SINCE {seit})')
            for num in (daten[0].split() if daten and daten[0] else []):
                _, roh = M.fetch(num, "(BODY.PEEK[])")
                msg = email.message_from_bytes(roh[0][1])
                mid = (msg.get("Message-ID") or "").strip()
                if not mid or mid in gesehen:
                    continue
                if "Postfachbericht" in (msg.get("Subject") or ""):
                    continue
                gesehen.add(mid)
                try:
                    zeit = parsedate_to_datetime(msg.get("Date"))
                except (TypeError, ValueError):
                    zeit = None
                mails.append({
                    "zeit": zeit,
                    # Brief = kein "Re:" und kein Antwortbezug. Die Absenderadresse taugt
                    # nicht: googlemail.com und gmail.com sind dasselbe Postfach.
                    "eigen": not re.match(r"\s*(re|aw|antw)\s*:", str(msg.get("Subject", "")), re.I)
                             and not (msg.get("In-Reply-To") or msg.get("References")),
                    "subject": str(make_header(decode_header(msg.get("Subject", "")))),
                    "text": _text_aus(msg),
                })
    mails.sort(key=lambda m: (m["zeit"] is None, m["zeit"]))
    return mails


def bericht(mails: list[dict], state: dict) -> str:
    packs = state.get("offene_packs") or {}
    gesperrt = set(json.loads((HERE / "progress.json").read_text(encoding="utf-8"))
                   .get("gesperrt") or []) if (HERE / "progress.json").exists() else set()
    z = [f"Postfachbericht Jurabrief — {date.today():%d.%m.%Y}",
         f"{sum(m['eigen'] for m in mails)} Briefe, "
         f"{sum(not m['eigen'] for m in mails)} Antworten", ""]
    for m in mails:
        wann = m["zeit"].strftime("%d.%m. %H:%M") if m["zeit"] else "?"
        if m["eigen"]:
            aufgaben = m["text"].split("II. Aufgaben", 1)[-1] if "II. Aufgaben" in m["text"] else ""
            fragen = re.findall(r"(?m)^\s*(\d)\.\s+(.{0,90})", aufgaben)
            z.append(f"→ {wann}  BRIEF  {m['subject']}")
            z += [f"      {n}. {f}" for n, f in fragen[:6]]
        else:
            e = einordnen(m["subject"], m["text"]) or {}
            key = f"{e.get('case_id')}@{e.get('datum', '')}"
            zuordnung = ("Paket offen" if key in packs or e.get("case_id") in packs
                         else "kein offenes Paket (erledigt oder nie angelegt)")
            z.append(f"← {wann}  ANTWORT  {m['subject']}")
            z.append(f"      erkannt als: {e.get('art', 'NICHT ERKANNT')}"
                     f"{'  streichen ' + str(e['streichen']) if e.get('streichen') else ''}"
                     f"  |  {zuordnung}")
            anfang = [l.strip() for l in ohne_zitat(m["text"]).splitlines() if l.strip()][:3]
            z += [f"      » {l[:110]}" for l in anfang]
        z.append("")
    z += ["Offene Pakete: " + (", ".join(packs) or "keine"),
          "Gesperrte Karten: " + (", ".join(sorted(gesperrt)) or "keine")]
    return "\n".join(z)


def main() -> int:
    tage = int(sys.argv[1]) if len(sys.argv) > 1 else 21
    state_pfad = HERE / "state.json"
    state = json.loads(state_pfad.read_text(encoding="utf-8")) if state_pfad.exists() else {}
    mails = hole(tage)
    text = bericht(mails, state)
    adresse = os.environ["GMAIL_ADDRESS"].strip()
    msg = EmailMessage()
    msg["From"] = msg["To"] = adresse
    msg["Subject"] = f"Postfachbericht Jurabrief ({date.today():%d.%m.})"
    msg.set_content(text)
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(adresse, os.environ["GMAIL_APP_PASSWORD"].strip())
        s.send_message(msg)
    print(f"Bericht gesendet: {len(mails)} Mails")   # nur Zaehlung ins oeffentliche Log
    return 0


if __name__ == "__main__":
    sys.exit(main())
