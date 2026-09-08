#!/usr/bin/env python3
"""FSRS-basierter Scheduler für den adaptiven Lernplan.

Nutzt die Open-Source-Bibliothek `fsrs` (PyPI), die denselben Algorithmus
wie Anki seit 2023 verwendet. Gewichte und Stabilität werden pro Fall-ID
geführt; schwache Fälle kommen früher wieder, sichere seltener.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

try:
    from fsrs import Card, Rating, Scheduler, State
except ImportError:  # Fallback ohne Bibliothek (z. B. lokaler Smoke-Test)
    Card = Rating = Scheduler = State = None  # type: ignore

TZ = ZoneInfo("Europe/Berlin")
ROOT = Path(__file__).parent
CARDS_FILE = ROOT / "fsrs_cards.json"

# Mapping: Antwort-Score 1-5 -> FSRS-Rating
SCORE_TO_RATING = {
    1: "AGAIN",
    2: "HARD",
    3: "GOOD",
    4: "GOOD",
    5: "EASY",
}


def _load():
    if CARDS_FILE.exists():
        return json.loads(CARDS_FILE.read_text(encoding="utf-8"))
    return {"cards": {}, "reviews": []}


def _save(data):
    CARDS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _card_obj(entry: dict) -> "Card":
    if Card is None:
        return None
    c = Card()
    if entry.get("due"):
        c.due = datetime.fromisoformat(entry["due"])
    if entry.get("stability") is not None:
        c.stability = entry["stability"]
    if entry.get("difficulty") is not None:
        c.difficulty = entry["difficulty"]
    if entry.get("reps") is not None:
        c.reps = entry["reps"]
    if entry.get("lapses") is not None:
        c.lapses = entry["lapses"]
    if entry.get("state") is not None and State is not None:
        try:
            c.state = State(entry["state"])
        except Exception:
            pass
    return c


def _dump_card(c: "Card") -> dict:
    return {
        "due": c.due.isoformat() if c.due else None,
        "stability": c.stability,
        "difficulty": c.difficulty,
        "reps": c.reps,
        "lapses": c.lapses,
        "state": int(c.state) if c.state is not None else None,
    }


def ensure_card(case_id: str) -> dict:
    data = _load()
    if case_id not in data["cards"]:
        data["cards"][case_id] = _dump_card(Card()) if Card else {
            "due": datetime.now(TZ).isoformat(), "stability": None,
            "difficulty": None, "reps": 0, "lapses": 0, "state": None,
        }
        _save(data)
    return data["cards"][case_id]


def review(case_id: str, score: int, note: str = "") -> dict:
    """Wertet eine gelöste Klausur aus und plant die nächste Wiederholung."""
    data = _load()
    entry = data["cards"].get(case_id) or _dump_card(Card()) if Card else ensure_card(case_id)
    rating_name = SCORE_TO_RATING.get(score, "GOOD")
    rating = getattr(Rating, rating_name) if Rating else None

    if Card and Scheduler and rating is not None:
        sched = Scheduler()
        c = _card_obj(entry)
        c, log = sched.review_card(c, rating)
        entry = _dump_card(c)
        data["reviews"].append({
            "case_id": case_id,
            "score": score,
            "rating": rating_name,
            "due_after": entry["due"],
            "stability": entry["stability"],
            "note": note[:500],
            "at": datetime.now(TZ).isoformat(timespec="seconds"),
        })
    else:
        # grober Fallback ohne fsrs-Bibliothek
        days = {1: 1, 2: 2, 3: 4, 4: 7, 5: 14}.get(score, 4)
        entry["due"] = (datetime.now(TZ) + timedelta(days=days)).isoformat()
        entry["reps"] = entry.get("reps", 0) + 1
        if score <= 2:
            entry["lapses"] = entry.get("lapses", 0) + 1
        data["reviews"].append({
            "case_id": case_id, "score": score, "rating": rating_name or "GOOD",
            "due_after": entry["due"], "note": note[:500],
            "at": datetime.now(TZ).isoformat(timespec="seconds"),
        })

    data["cards"][case_id] = entry
    _save(data)
    return entry


def due_today(case_ids: list[str] | None = None) -> list[str]:
    """Gibt die Fall-IDs zurück, die heute (oder überfällig) fällig sind."""
    data = _load()
    today = datetime.now(TZ).date()
    out = []
    pool = case_ids or list(data["cards"].keys())
    for cid in pool:
        entry = data["cards"].get(cid)
        if not entry or not entry.get("due"):
            out.append(cid)
            continue
        due = datetime.fromisoformat(entry["due"]).date()
        if due <= today:
            out.append(cid)
    return out


def next_review_date(case_id: str) -> str | None:
    data = _load()
    entry = data["cards"].get(case_id)
    return entry.get("due") if entry else None


if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 3 and sys.argv[1] == "review":
        cid = sys.argv[2]
        sc = int(sys.argv[3]) if len(sys.argv) > 3 else 3
        note = sys.argv[4] if len(sys.argv) > 4 else ""
        r = review(cid, sc, note)
        print(json.dumps(r, ensure_ascii=False, indent=2))
    elif len(sys.argv) >= 2 and sys.argv[1] == "due":
        print(due_today())
    else:
        print("Nutzung: fsrs_scheduler.py review <case_id> <score> [note]")
        print("         fsrs_scheduler.py due")
