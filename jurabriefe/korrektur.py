#!/usr/bin/env python3
"""Antworten auswerten — die einzige Korrekturkette."""
from __future__ import annotations

import email
import imaplib
import json
import os
import re
import smtplib
import sys
from email.header import decode_header, make_header
from email.message import EmailMessage
from pathlib import Path

from claude_client import complete
from fsrs_scheduler import _load, _save, parse_note, review, review_punkte

HERE = Path(__file__).resolve().parent
MIN_KLAUSUR = 400
ID = re.compile(r"\[([a-z]{2,4}-\d{3})\]", re.I)
ZITAT = re.compile(r"^\s*(>|Am .+ schrieb|On .+ wrote|Von:|Gesendet:|-{2,}\s*$|_{5,})", re.I)

RASTER = """Gewichtung:
  35 % Form (Urteilsstil, Tenor, Zeitformen, Aufbau)
  30 % Erfassen des Streitstoffs
  25 % Rechtliche Richtigkeit gegen die Skriptloesung
  10 % Sprache und Knappheit"""

PROMPT = """Du korrigierst eine Bearbeitung im juristischen Vorbereitungsdienst
(zweite Staatspruefung, Sachsen-Anhalt). Massstab: 4 Punkte Bestehensgrenze,
9 Punkte vollbefriedigend. Klausurstil, keine Hoeflichkeit.

AUFGABE:
{aufgabe}

SKRIPTLOESUNG (woertlich, nicht umformulieren):
{regeln}

{raster}

BEARBEITUNG:
{bearbeitung}

Antworte nur als JSON, ohne Markdown:
{{"punkte": <0-18>, "note": "<amtliche Notenbezeichnung>",
  "tragend": "<zwei Saetze: warum diese Punktzahl>",
  "gelungen": ["<konkret>"],
  "fehler": [{{"stelle": "<Zitat aus der Bearbeitung, max 12 Woerter>",
               "warum": "<verletzte Regel>", "besser": "<Fassung aus der Skriptloesung>"}}],
  "naechster_schritt": "<eine konkrete Uebung>"}}
Weicht die Bearbeitung von der Skriptloesung ab, nimm die Skriptfassung als richtig."""


def ohne_zitat(body: str) -> str:
    zeilen = []
    for z in (body or "").splitlines():
        if ZITAT.match(z):
            break
        zeilen.append(z)
    return "\n".join(zeilen).strip()


def erste_zeile(body: str) -> str:
    for z in (body or "").splitlines():
        if z.strip() and not ZITAT.match(z):
            return z.strip()
    return ""


def einordnen(subject: str, body: str) -> dict | None:
    m = ID.search(subject or "")
    if not m:
        return None
    case_id = m.group(1).lower()
    eigen = ohne_zitat(body)
    if len(eigen) >= MIN_KLAUSUR:
        return {"art": "klausur", "case_id": case_id, "text": eigen}
    kopf = erste_zeile(body)
    p = re.match(r"\s*(?:SCORE:\s*)?(\d{1,2})\s*(?:punkte|p)?\b", kopf, re.I)
    if p:
        wert = int(p.group(1))
        punkte = wert if "punkt" in kopf.lower() or wert > 5 else {1: 2, 2: 4, 3: 7, 4: 10, 5: 13}[wert]
        return {"art": "punkte", "case_id": case_id, "punkte": punkte}
    wort = re.match(r"\s*([\wäöüß]+)", kopf)
    if wort and parse_note(wort.group(1)) is not None:
        rest = kopf[wort.end():].strip(" :,-\u2013\u2014")
        return {"art": "note", "case_id": case_id, "note": wort.group(1).lower(), "detail": rest}
    return None


def _text_aus(msg) -> str:
    if not msg.is_multipart():
        return msg.get_payload(decode=True).decode(msg.get_content_charset() or "utf-8", "replace")
    for teil in msg.walk():
        if teil.get_content_type() == "text/plain":
            return teil.get_payload(decode=True).decode(teil.get_content_charset() or "utf-8", "replace")
    return ""


def hole_antworten() -> list[dict]:
    adresse = (os.environ.get("GMAIL_ADDRESS") or "").strip()
    pw = (os.environ.get("GMAIL_APP_PASSWORD") or "").strip()
    if not adresse or not pw:
        raise SystemExit("GMAIL_ADDRESS / GMAIL_APP_PASSWORD fehlen")
    gefunden = []
    with imaplib.IMAP4_SSL("imap.gmail.com") as M:
        M.login(adresse, pw)
        M.select("INBOX")
        _, daten = M.search(None, '(UNSEEN SUBJECT "Jurabrief")')
        for num in (daten[0].split() if daten and daten[0] else []):
            _, roh = M.fetch(num, "(RFC822)")
            msg = email.message_from_bytes(roh[0][1])
            subject = str(make_header(decode_header(msg.get("Subject", ""))))
            eintrag = einordnen(subject, _text_aus(msg))
            if eintrag:
                gefunden.append(eintrag)
            M.store(num, "+FLAGS", "\\Seen")
    return gefunden


def send_mail(betreff: str, body: str) -> None:
    adresse = (os.environ.get("GMAIL_ADDRESS") or "").strip()
    pw = (os.environ.get("GMAIL_APP_PASSWORD") or "").strip()
    to = (os.environ.get("JURABRIEF_TO") or adresse).strip()
    if not (adresse and pw and to):
        raise SystemExit("Mail-Zugangsdaten fehlen")
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = adresse, to, betreff
    msg.set_content(body)
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(adresse, pw)
        s.send_message(msg)
    print(f"Auswertung an {to} gesendet", file=sys.stderr)


def korrigiere(aufgabe: str, regeln: str, bearbeitung: str) -> dict:
    roh = complete(PROMPT.format(aufgabe=aufgabe[:6000], regeln=(regeln or "\u2014")[:8000],
                                 raster=RASTER, bearbeitung=bearbeitung[:20000]),
                   max_tokens=2000)
    roh = re.sub(r"^```(?:json)?|```$", "", roh.strip(), flags=re.M).strip()
    d = json.loads(roh)
    d["punkte"] = max(0, min(18, int(d.get("punkte", 0))))
    return d


def als_mail(case: dict, k: dict, schnitt=None) -> str:
    z = [f"Auswertung — {case['gebiet']} [{case['id']}]", "",
         f"{k['punkte']} Punkte ({k.get('note', '')})", "", k.get("tragend", ""), "", "Gelungen"]
    z += [f"  + {g}" for g in (k.get("gelungen") or ["\u2014"])]
    z += ["", "Zu korrigieren"]
    for f in k.get("fehler") or []:
        z += [f"  - {f.get('stelle','')}", f"    {f.get('warum','')}", f"    besser: {f.get('besser','')}"]
    z += ["", f"Naechster Schritt: {k.get('naechster_schritt','')}"]
    if schnitt is not None:
        z += ["", f"Schnitt in diesem Gebiet: {schnitt} Punkte"]
    z += ["", "Widerspruch? Antworte mit: punkte 9 — <Begruendung>."]
    return "\n".join(z)


KARTEN_PROMPT = """Du korrigierst Uebungsantworten fuer die zweite juristische
Staatspruefung. Zu jeder Aufgabe gibt es eine woertliche Skriptloesung. Vergleiche
die Antwort damit. Massstab: 4 Punkte Bestehensgrenze, 9 Punkte vollbefriedigend.
Klausurstil, keine Hoeflichkeit, keine Erklaerung des Offensichtlichen.

AUFGABEN MIT SKRIPTLOESUNG:
{aufgaben}

ANTWORT DER BEARBEITERIN (nummeriert, kann Luecken haben):
{antwort}

Bewerte jede Aufgabe einzeln. Fehlt eine Antwort, gib 0 Punkte und sage das.
Inhaltlich richtig, aber anders formuliert: das ist kein Fehler, solange die
Skriptformulierung nicht praeziser ist — dann sage, warum sie praeziser ist.

Nur JSON ohne Markdown:
{{"karten": [{{"nr": <n>, "punkte": <0-18>, "treffer": "<was sass, ein Satz>",
   "fehlt": "<was fehlt oder falsch ist, ein Satz; leer wenn nichts>"}}],
  "gesamt": <0-18>, "naechster_schritt": "<eine konkrete Uebung>"}}"""


def korrigiere_karten(pack: list[dict], antwort: str) -> dict:
    aufgaben = "\n\n".join(
        f"{k['nr']}. {k['frage']}\n   SKRIPTLOESUNG: {k['loesung']}" for k in pack)
    roh = complete(KARTEN_PROMPT.format(aufgaben=aufgaben[:9000], antwort=antwort[:9000]),
                   max_tokens=2500)
    roh = re.sub(r"^```(?:json)?|```$", "", roh.strip(), flags=re.M).strip()
    d = json.loads(roh)
    for k in d.get("karten", []):
        k["punkte"] = max(0, min(18, int(k.get("punkte", 0))))
    if not d.get("karten"):
        raise ValueError("Korrektur ohne Kartenbewertung")
    d["gesamt"] = max(0, min(18, int(d.get("gesamt") or
                       round(sum(k["punkte"] for k in d["karten"]) / len(d["karten"])))))
    return d


def karten_mail(case: dict, pack: list[dict], k: dict, schnitt=None) -> str:
    nach_nr = {c["nr"]: c for c in pack}
    z = [f"Auswertung — {case['gebiet']} [{case['id']}]", "",
         f"{k['gesamt']} Punkte im Schnitt", ""]
    for b in sorted(k["karten"], key=lambda x: x.get("nr", 0)):
        c = nach_nr.get(b.get("nr"), {})
        z += [f"{b.get('nr')}. {c.get('frage', '')[:120]}",
              f"   {b['punkte']} Punkte — {b.get('treffer', '')}"]
        if b.get("fehlt"):
            z.append(f"   fehlt: {b['fehlt']}")
        z += [f"   Skript: {c.get('loesung', '')}", ""]
    z += [f"Naechster Schritt: {k.get('naechster_schritt', '')}"]
    if schnitt is not None:
        z += ["", f"Schnitt in diesem Gebiet: {schnitt} Punkte"]
    z += ["", "Widerspruch? Antworte mit: punkte 9 — <Begruendung>."]
    return "\n".join(z)


def main() -> int:
    from generate_jurabrief import load_skript_section as load_skript

    cases = {c["id"]: c for c in json.loads((HERE / "cases.json").read_text(encoding="utf-8"))["cases"]}
    progress = _load()
    state_pfad = HERE / "state.json"
    state = json.loads(state_pfad.read_text(encoding="utf-8")) if state_pfad.exists() else {}

    antworten = hole_antworten()
    print(f"{len(antworten)} Antworten", file=sys.stderr)
    for a in antworten:
        case = cases.get(a["case_id"])
        if not case:
            print(f"unbekannter Fall {a['case_id']}", file=sys.stderr)
            continue
        if a["art"] == "note":
            review(progress, a["case_id"], a["note"], a.get("detail", ""))
            print(f"{a['case_id']} Note {a['note']}", file=sys.stderr)
            continue
        if a["art"] == "punkte":
            review_punkte(progress, a["case_id"], a["punkte"], "selbst gemeldet")
            print(f"{a['case_id']} {a['punkte']} Punkte (selbst)", file=sys.stderr)
            continue

        offen = state.get("offen") or {}
        pack = offen.get("karten") or []
        if pack and offen.get("case_id") == case["id"]:
            k = korrigiere_karten(pack, a["text"])
            nach_nr = {c["nr"]: c for c in pack}
            for b in k["karten"]:
                c = nach_nr.get(b.get("nr"))
                if c:
                    review_punkte(progress, c["id"], b["punkte"], b.get("fehlt", ""))
            review_punkte(progress, case["id"], k["gesamt"], k.get("naechster_schritt", ""))
            send_mail(f"Auswertung — {case['gebiet']} [{case['id']}] {k['gesamt']} Punkte",
                      karten_mail(case, pack, k, progress["cards"][case["id"]].get("schnitt")))
            print(f"{case['id']} {len(k['karten'])} Karten, Schnitt {k['gesamt']}", file=sys.stderr)
            state["offen"] = {}
            state_pfad.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
            continue

        aufgabe = case.get("bearbeitervermerk") or case.get("gebiet", "")
        k = korrigiere(aufgabe, load_skript(case), a["text"])
        res = review_punkte(progress, case["id"], k["punkte"], k.get("tragend", ""))
        send_mail(f"Auswertung — {case['gebiet']} [{case['id']}] {k['punkte']} Punkte",
                  als_mail(case, k, progress["cards"][case["id"]].get("schnitt")))
        print(f"{case['id']} {k['punkte']} Punkte -> +{res['interval']}d", file=sys.stderr)

    _save(progress)
    return 0


if __name__ == "__main__":
    sys.exit(main())
