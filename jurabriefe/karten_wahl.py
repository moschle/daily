#!/usr/bin/env python3
"""Auswahl kuratierter Karten fuer den Brief."""
from __future__ import annotations

import json
from pathlib import Path

from fsrs_scheduler import due_today, markiere_gezeigt, unseen
from karten import OUT

N_MIN, N_MAX = 3, 5


def lade_kuratiert(sid: str) -> list[dict]:
    p = OUT / f"{sid}.kuratiert.json"
    if not p.exists():
        return []
    data = json.loads(p.read_text(encoding="utf-8"))
    return list(data.get("karten") or [])


def waehle(sid: str, progress: dict, n: int = N_MAX) -> list[dict]:
    karten = lade_kuratiert(sid)
    if not karten:
        return []
    ids = [k["id"] for k in karten]
    by_id = {k["id"]: k for k in karten}
    n = max(N_MIN, min(n, len(karten)))
    due = [i for i in due_today(progress, ids) if i in by_id]
    neu = unseen(progress, ids)
    gewicht = sorted(ids, key=lambda i: (-int(by_id[i].get("gewicht") or 2), i))
    chosen, seen = [], set()
    for pool in (due, neu, gewicht):
        for i in pool:
            if i in seen:
                continue
            seen.add(i)
            chosen.append(by_id[i])
            if len(chosen) >= n:
                return chosen
    return chosen


def als_aufgabe(karten: list[dict]) -> str:
    teile = ["Bearbeitervermerk",
             "Loesen Sie die folgenden Aufgaben im Klausurstil. Kein Sachbericht.", ""]
    for i, k in enumerate(karten, 1):
        teile.append(f"{i}. [{k.get('typ', 'karte')}] {k['frage'].strip()}")
        teile.append("")
    return "\n".join(teile).strip() + "\n"


def als_loesung(karten: list[dict]) -> str:
    teile = []
    for i, k in enumerate(karten, 1):
        teile.append(f"{i}. {k['id']}\n{k.get('loesung', '').strip()}")
    return "\n\n".join(teile)


def markiere(progress: dict, karten: list[dict]) -> None:
    for k in karten:
        markiere_gezeigt(progress, k["id"])
