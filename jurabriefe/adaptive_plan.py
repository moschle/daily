from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

from fsrs_scheduler import due_today, mark_introduced, unseen

TZ = ZoneInfo("Europe/Berlin")
ZIEL = date(2027, 4, 30)


def current_phase(plan: dict, today: date | None = None) -> dict:
    today = today or datetime.now(TZ).date()
    for ph in plan.get("phasen", []):
        if datetime.fromisoformat(ph["bis"]).date() >= today:
            return ph
    return plan["phasen"][-1] if plan.get("phasen") else {}


def all_ids(plan: dict, cases: list) -> list[str]:
    seen = []
    for ph in plan.get("phasen", []):
        for i in ph.get("gebiete", []):
            if i not in seen:
                seen.append(i)
    for c in cases:
        if c["id"] not in seen:
            seen.append(c["id"])
    return seen


TAGE = tuple(range(7))


def _slots_left(today: date, tage=TAGE) -> int:
    n = sum(1 for o in range(today.toordinal(), ZIEL.toordinal() + 1)
            if date.fromordinal(o).weekday() in tage)
    return max(1, n)


def pick(cases, plan, progress, exclude_ids=None, today=None):
    today = today or datetime.now(TZ).date()
    phase = current_phase(plan, today)
    by_id = {c["id"]: c for c in cases}
    pool_ids = [i for i in phase.get("gebiete", []) if i in by_id] or [c["id"] for c in cases]
    universe = [i for i in all_ids(plan, cases) if i in by_id]
    skip = set(exclude_ids or [])

    neu = [i for i in universe if i not in skip]
    new_ids = unseen(progress, neu)
    due = [i for i in due_today(progress, universe, today) if i not in skip]

    remaining_new = len(unseen(progress, universe))
    slots = _slots_left(today)

    neu_in_phase = [i for i in new_ids if i in pool_ids]
    if neu_in_phase:
        chosen_id, grund = neu_in_phase[0], "einfuehren"
    elif due:
        chosen_id, grund = due[0], "fsrs-faellig"
    elif new_ids:
        chosen_id, grund = new_ids[0], "einfuehren-ausserhalb-phase"
    else:
        cards = progress.get("cards") or {}
        rest = [i for i in pool_ids if i not in skip] or pool_ids
        rest.sort(key=lambda i: (
            (cards.get(i) or {}).get("due") or "0000",
            -float((cards.get(i) or {}).get("difficulty") or 5),
            i,
        ))
        chosen_id, grund = rest[0], "auffuellen"

    case = by_id[chosen_id]
    mark_introduced(progress, case["id"], today)
    return {
        "case": case,
        "phase": phase.get("name", "?"),
        "grund": grund,
        "offen_neu": max(0, remaining_new - (1 if grund == "einfuehren" else 0)),
        "faellig": len(due),
        "slots": slots,
    }
