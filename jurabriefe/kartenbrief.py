#!/usr/bin/env python3
"""Karten fuer einen Brief auswaehlen und den Brieftext bauen.

Die Karten ersetzen den festen Bearbeitervermerk. Ausgewaehlt wird aus dem
Skript des heutigen Falls: erst was faellig ist, dann Neues, aufgefuellt nach
Gewicht. Jede Karte traegt ihre Loesung — die bleibt bis zur Auswertung in
state.json und geht nicht mit der Mail raus.

FSRS laeuft je Karte, nicht je Fall: wenn die Kostenquote danebenlag, kommt
die Kostenquote wieder, nicht der ganze Abschnitt C.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from fsrs_scheduler import due_today, heute, unseen

HERE = Path(__file__).resolve().parent
KARTEN = HERE / "karten"

PRO_BRIEF = 4
LOESUNG_MAX = 2500


LESETEXTE = KARTEN / "lesetexte.kuratiert.json"


def _lies(pfad: Path) -> list[dict]:
    if not pfad.exists():
        return []
    try:
        return json.loads(pfad.read_text(encoding="utf-8")).get("karten", [])
    except json.JSONDecodeError:
        return []


def lade(skript_id: str) -> list[dict]:
    """Kuratierte Karten, erzeugte Karten und die Fragen aus frueheren Lesetexten."""
    return (_lies(KARTEN / f"{skript_id}.kuratiert.json")
            + _lies(KARTEN / f"{skript_id}.gen.json")
            + [k for k in _lies(LESETEXTE) if k.get("skript") == skript_id])


def kurz_ort(k: dict) -> str:
    """Letzte brauchbare Ueberschrift plus Randnummer.

    Die Ueberschriftenerkennung des Extraktors haelt auch Rubrumszeilen und
    Satzfragmente fuer Ueberschriften. Was auf Komma oder Punkt endet oder
    laenger als 60 Zeichen ist, ist keine."""
    teile = [t.strip().rstrip(":") for t in (k.get("abschnitt") or "").split("›")]
    kopf = ""
    for t in reversed([t for t in teile if t]):
        if len(t) <= 60 and not t.endswith((",", ".")):
            kopf = t
            break
    rn = f"Rn {k['rn']}" if k.get("rn") else ""
    return " › ".join(x for x in (kopf, rn) if x)


def waehle(karten: list[dict], progress: dict, tag: date | None = None,
           anzahl: int = PRO_BRIEF, meiden: list[str] | None = None) -> list[dict]:
    """Faellige zuerst, dann ungesehene, dann nach Gewicht auffuellen."""
    tag = tag or heute()
    meiden = set(meiden or [])
    by_id = {k["id"]: k for k in karten}
    ids = [k["id"] for k in karten if k["id"] not in meiden]

    # Solange ungesehene Karten existieren, bleibt mindestens ein Platz fuer
    # Neues frei — sonst belegen faellige Karten dauerhaft alle Plaetze und
    # die Haelfte des Bestands wird nie gestellt.
    neu_vorhanden = unseen(progress, ids)
    platz_fuer_faellige = anzahl - 1 if neu_vorhanden else anzahl

    # Hoechstens eine Karte je Randnummer: sonst steht dieselbe Formulierung
    # zweimal im Brief und wird als eine Antwort zurueckgeschickt.
    belegt: set[tuple] = set()

    def frei(i: str) -> bool:
        k = by_id[i]
        schl = (k.get("skript"), k.get("rn"))
        if not k.get("rn") or schl not in belegt:
            belegt.add(schl)
            return True
        return False

    gewaehlt: list[str] = []
    for i in due_today(progress, ids, tag):
        if len(gewaehlt) >= platz_fuer_faellige:
            break
        if i not in gewaehlt and frei(i):
            gewaehlt.append(i)
    for i in neu_vorhanden:
        if len(gewaehlt) >= anzahl:
            break
        if i not in gewaehlt and frei(i):
            gewaehlt.append(i)
    if len(gewaehlt) < anzahl:
        cards = progress.get("cards") or {}
        rest = sorted((i for i in ids if i not in gewaehlt),
                      key=lambda i: (-int(by_id[i].get("gewicht") or 2),
                                     (cards.get(i) or {}).get("due") or "0000", i))
        gewaehlt += [i for i in rest if frei(i)][: anzahl - len(gewaehlt)]

    # schwer zuerst — was am wenigsten sitzt, wird zuerst geschrieben
    ausgewaehlt = [by_id[i] for i in gewaehlt[:anzahl]]
    ausgewaehlt.sort(key=lambda k: -int(k.get("gewicht") or 2))
    return ausgewaehlt


def brieftext(karten: list[dict]) -> str:
    """Nur Fragen. Die Loesungen bleiben zurueck."""
    if not karten:
        return "Heute keine Karten fuer dieses Skript.\n"
    zeilen = ["II. Aufgaben",
              "Antworte auf diese Mail. Pro Aufgabe eine Zeile, nummeriert.",
              ""]
    for n, k in enumerate(karten, 1):
        ort = kurz_ort(k)
        zeilen.append(f"{n}. {k['frage'].strip()}")
        if ort:
            zeilen.append(f"   ({ort})")
        zeilen.append("")
    return "\n".join(zeilen)


def zurueckhalten(karten: list[dict], case_id: str, tag: date | None = None) -> dict:
    """Was bis zur Auswertung in state.json wartet."""
    return {
        "case_id": case_id,
        "datum": (tag or heute()).isoformat(),
        "karten": [{"nr": n, "id": k["id"], "typ": k.get("typ"),
                    "frage": k["frage"], "loesung": k["loesung"][:LOESUNG_MAX],
                    "gewicht": k.get("gewicht", 2), "skript": k.get("skript"),
                    "abschnitt": k.get("abschnitt", "")}
                   for n, k in enumerate(karten, 1)],
    }


def waehle_fall(cases: list[dict], phase_ids: list[str], progress: dict,
                state: dict, tag: date | None = None) -> dict:
    """Fall nach dem Zustand seiner Karten waehlen.

    FSRS liegt jetzt auf den Karten. Ein zweiter FSRS-Lauf auf Fallebene
    wuerde dagegen arbeiten — er hat in der Simulation einen Fall 23-mal und
    einen anderen einmal gezogen. Massgeblich ist: welches Skript hat die
    meisten faelligen und die schwaechsten Karten, und was war lange nicht dran.
    """
    tag = tag or heute()
    im_plan = [c for c in cases if c["id"] in phase_ids] or cases
    zuletzt = list(dict.fromkeys(reversed(state.get("done") or [])))[:2]
    kandidaten = [c for c in im_plan if c["id"] not in zuletzt] or im_plan

    cards = progress.get("cards") or {}
    zaehler = {c["id"]: (state.get("done") or []).count(c["id"]) for c in kandidaten}

    def rang(case: dict):
        karten = lade(case.get("skript_id") or "")
        ids = [k["id"] for k in karten]
        faellig = len(due_today(progress, ids, tag))
        ungesehen = len(unseen(progress, ids))
        punkte = [cards[i]["schnitt"] for i in ids
                  if i in cards and cards[i].get("schnitt") is not None]
        schnitt = sum(punkte) / len(punkte) if punkte else 9.0
        # Reihum durch alle Gebiete der Phase: was am seltensten dran war,
        # kommt zuerst. Faelligkeit und Schwaeche entscheiden nur den Gleichstand
        # — sonst gewinnt immer dasselbe Skript, weil seine Karten faellig sind.
        return (zaehler.get(case["id"], 0), schnitt, -faellig, -ungesehen, case["id"])

    return sorted(kandidaten, key=rang)[0]
