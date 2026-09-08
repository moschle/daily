#!/usr/bin/env python3
"""FSRS-Wiederholung auf progress.json. Eine Generation, ein Speicherort."""
from __future__ import annotations

import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Berlin")
HERE = Path(__file__).resolve().parent

NOTEN = {"wieder": 1, "nochmal": 1, "again": 1, "1": 1,
         "schwer": 2, "hard": 2, "2": 2,
         "gut": 3, "ok": 3, "good": 3, "3": 3,
         "leicht": 4, "easy": 4, "4": 4}
NOTE_NAME = {1: "wieder", 2: "schwer", 3: "gut", 4: "leicht"}
PUNKTE_NOTE = [(0, 3, 1), (4, 5, 2), (6, 8, 3), (9, 18, 4)]
START_STABILITAET = {1: 1.0, 2: 2.0, 3: 4.0, 4: 8.0}
MIN_INTERVALL, MAX_INTERVALL = 1, 180


def heute() -> date:
    return datetime.now(TZ).date()


def parse_note(text: str) -> int | None:
    return NOTEN.get((text or "").strip().lower())


def punkte_zu_note(punkte: float) -> str:
    p = max(0, min(18, float(punkte)))
    for lo, hi, grade in PUNKTE_NOTE:
        if lo <= p <= hi:
            return NOTE_NAME[grade]
    return "gut"


def card(progress: dict, case_id: str) -> dict:
    return progress.setdefault("cards", {}).setdefault(
        case_id, {"stability": 0.0, "difficulty": 5.0, "due": None,
                  "last": None, "gezeigt": None, "reps": 0})


def ensure_card(progress: dict, case_id: str) -> dict:
    return card(progress, case_id)


def unseen(progress: dict, ids: list[str]) -> list[str]:
    cards = progress.get("cards") or {}
    return [i for i in ids if not (cards.get(i) or {}).get("gezeigt")]


def due_today(progress: dict, ids: list[str], tag: date | None = None) -> list[str]:
    tag = tag or heute()
    cards = progress.get("cards") or {}
    faellig = [i for i in ids
               if (cards.get(i) or {}).get("due") and (cards[i]["due"] <= tag.isoformat())]
    return sorted(faellig, key=lambda i: (cards[i]["due"], i))


def next_review_date(progress: dict, case_id: str) -> str | None:
    return (progress.get("cards") or {}).get(case_id, {}).get("due")


def mark_introduced(progress: dict, case_id: str, tag: date | None = None) -> dict:
    tag = tag or heute()
    c = card(progress, case_id)
    if not c.get("gezeigt"):
        c["gezeigt"] = tag.isoformat()
    return c


def markiere_gezeigt(progress: dict, case_id: str, tag: date | None = None) -> dict:
    tag = tag or heute()
    c = card(progress, case_id)
    c["gezeigt"] = tag.isoformat()
    return c


def review(progress: dict, case_id: str, note, detail: str = "",
           tag: date | None = None) -> dict:
    tag = tag or heute()
    grade = note if isinstance(note, int) else parse_note(str(note))
    if grade not in (1, 2, 3, 4):
        raise ValueError(f"unbekannte Note: {note!r}")
    c = card(progress, case_id)
    stab = float(c.get("stability") or 0.0)
    diff = float(c.get("difficulty") or 5.0)
    verstrichen = 0
    if c.get("last"):
        verstrichen = max(0, (tag - date.fromisoformat(c["last"])).days)
    diff = max(1.0, min(10.0, diff + 0.15 * (3 - grade)))
    if stab <= 0:
        stab = START_STABILITAET[grade]
    elif grade == 1:
        stab = max(1.0, stab * 0.4)
    else:
        faktor = 1.0 + (2.6 - 0.1 * diff) * {2: 0.4, 3: 1.0, 4: 1.6}[grade]
        bonus = 1.0 + min(0.3, verstrichen / max(1.0, stab) * 0.1)
        stab = stab * faktor * bonus
    intervall = max(MIN_INTERVALL, min(MAX_INTERVALL, round(stab)))
    faellig = tag + timedelta(days=intervall)
    c.update({"stability": round(stab, 2), "difficulty": round(diff, 2),
              "due": faellig.isoformat(), "last": tag.isoformat(),
              "reps": int(c.get("reps") or 0) + 1})
    progress.setdefault("gewichte", {})[case_id] = round(2.0 - grade * 0.3, 2)
    eintrag = {"date": tag.isoformat(), "case_id": case_id,
               "note": NOTE_NAME[grade], "grade": grade,
               "interval": intervall, "detail": (detail or "")[:400]}
    progress.setdefault("feedback", []).append(eintrag)
    progress["feedback"] = progress["feedback"][-200:]
    return {**eintrag, "due": c["due"]}


def review_punkte(progress: dict, case_id: str, punkte: float, detail: str = "",
                  tag: date | None = None) -> dict:
    res = review(progress, case_id, punkte_zu_note(punkte), detail, tag)
    res["punkte"] = round(float(punkte), 1)
    c = card(progress, case_id)
    verlauf = list(c.get("punkte") or [])
    verlauf.append({"date": res["date"], "wert": res["punkte"]})
    c["punkte"] = verlauf[-20:]
    c["schnitt"] = round(sum(x["wert"] for x in c["punkte"]) / len(c["punkte"]), 1)
    if progress.get("feedback"):
        progress["feedback"][-1]["punkte"] = res["punkte"]
    return res


def offene_wertung(progress: dict, case_id: str) -> bool:
    c = (progress.get("cards") or {}).get(case_id) or {}
    gezeigt, bewertet = c.get("gezeigt"), c.get("last")
    return bool(gezeigt and (not bewertet or bewertet < gezeigt))


def auto_wertung(progress: dict, case_id: str, tag: date | None = None) -> dict | None:
    tag = tag or heute()
    if not offene_wertung(progress, case_id):
        return None
    c = card(progress, case_id)
    c["unbeantwortet"] = int(c.get("unbeantwortet") or 0) + 1
    verschub = min(7, 2 + c["unbeantwortet"])
    c["due"] = (tag + timedelta(days=verschub)).isoformat()
    progress.setdefault("feedback", []).append(
        {"date": tag.isoformat(), "case_id": case_id, "note": "unbeantwortet",
         "grade": None, "interval": verschub, "detail": ""})
    progress["feedback"] = progress["feedback"][-200:]
    return {"case_id": case_id, "note": "unbeantwortet", "interval": verschub, "due": c["due"]}


def _load(pfad: Path | None = None) -> dict:
    p = pfad or (HERE / "progress.json")
    d = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    d.setdefault("cards", {})
    d.setdefault("feedback", [])
    d.setdefault("gewichte", {})
    return d


def _save(progress: dict, pfad: Path | None = None) -> None:
    p = pfad or (HERE / "progress.json")
    p.write_text(json.dumps(progress, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    pr = _load()
    if len(sys.argv) > 1 and sys.argv[1] == "due":
        ids = list((pr.get("cards") or {}).keys())
        print("\n".join(due_today(pr, ids)) or "nichts faellig")
    else:
        for cid, c in sorted((pr.get("cards") or {}).items()):
            print(f"{cid:10} due={c.get('due') or '-':10} stab={c.get('stability'):6} "
                  f"diff={c.get('difficulty'):5} schnitt={c.get('schnitt', '-')}")
