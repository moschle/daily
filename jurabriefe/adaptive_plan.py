#!/usr/bin/env python3
"""Adaptiver Lernplan: wählt den nächsten Fall nach Phase + FSRS-Fälligkeit + Gewicht.

- Phase aus lernplan.json (nach Datum)
- Innerhalb der Phase: fällige Fälle zuerst (fsrs_scheduler.due_today)
- Danach nach Gewicht (progress.json) sortiert — schwache Gebiete öfter
- Gibt case_id + Begründung aus; generate_jurabrief.py nutzt das.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from fsrs_scheduler import due_today

TZ = ZoneInfo("Europe/Berlin")
ROOT = Path(__file__).parent


def current_phase(plan: dict) -> dict:
    today = datetime.now(TZ).date()
    for ph in plan.get("phasen", []):
        if datetime.fromisoformat(ph["bis"]).date() >= today:
            return ph
    return plan["phasen"][-1]


def pick(cases: list[dict], plan: dict, progress: dict) -> dict:
    phase = current_phase(plan)
    pool = [c for c in cases if c["id"] in phase.get("gebiete", [])]
    if not pool:
        pool = cases
    due = set(due_today([c["id"] for c in pool]))
    weights = progress.get("gewichte", {})
    pool.sort(key=lambda c: (0 if c["id"] in due else 1, -weights.get(c["id"], 1.0)))
    chosen = pool[0]
    reason = "fällig" if chosen["id"] in due else f"Gewicht {weights.get(chosen['id'], 1.0)}"
    return {"case": chosen, "phase": phase["name"], "grund": reason}


if __name__ == "__main__":
    cases = json.loads((ROOT / "cases.json").read_text(encoding="utf-8")).get("cases", [])
    plan = json.loads((ROOT / "lernplan.json").read_text(encoding="utf-8"))
    progress = json.loads((ROOT / "progress.json").read_text(encoding="utf-8"))
    print(json.dumps(pick(cases, plan, progress), ensure_ascii=False, indent=2))
