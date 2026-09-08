#!/usr/bin/env python3
"""Naechsten Fall nach Phase, FSRS und Rotation waehlen."""
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
    return plan["phasen"][-1] if plan.get("phasen") else {}


def pick(cases: list[dict], plan: dict, progress: dict, exclude_ids: list[str] | None = None) -> dict:
    phase = current_phase(plan)
    pool = [c for c in cases if c["id"] in phase.get("gebiete", [])]
    if not pool:
        pool = list(cases)
    skip = set(exclude_ids or [])
    rotated = [c for c in pool if c["id"] not in skip]
    if rotated:
        pool = rotated
    due = set(due_today([c["id"] for c in pool]))
    weights = progress.get("gewichte", {})
    pool.sort(key=lambda c: (0 if c["id"] in due else 1, -weights.get(c["id"], 1.0), c["id"]))
    chosen = pool[0]
    reason = "faellig" if chosen["id"] in due else f"Gewicht {weights.get(chosen['id'], 1.0)}"
    return {"case": chosen, "phase": phase.get("name", "?"), "grund": reason}


if __name__ == "__main__":
    cases = json.loads((ROOT / "cases.json").read_text(encoding="utf-8")).get("cases", [])
    plan = json.loads((ROOT / "lernplan.json").read_text(encoding="utf-8"))
    progress = json.loads((ROOT / "progress.json").read_text(encoding="utf-8"))
    print(json.dumps(pick(cases, plan, progress), ensure_ascii=False, indent=2))
