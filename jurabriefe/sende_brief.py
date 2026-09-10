#!/usr/bin/env python3
"""Briefversand mit 3-5 kuratierten Karten."""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
for p in (REPO, HERE):
    s = str(p)
    if s not in sys.path:
        sys.path.insert(0, s)

from generate_jurabrief import (
    AKTE, CASES_FILE, FALLBACK, LERNPLAN_FILE,
    load_json, load_progress, load_skript_section, now_berlin,
    pick_case, resolve_to, save_progress, save_state,
    search_related_case, send_mail,
)
from fsrs_scheduler import auto_wertung, markiere_gezeigt
from karten_wahl import als_aufgabe, markiere, waehle


def main() -> int:
    cases = load_json(CASES_FILE, {}).get("cases", [])
    if not cases:
        return 1
    state = load_json(HERE / "state.json", {"done": [], "seen_slugs": []})
    progress = load_progress()
    for c in cases:
        auto_wertung(progress, c["id"])
    case, grund = pick_case(cases, state, progress)
    pack = waehle(case.get("skript_id") or "", progress)
    if pack:
        aufgabe = als_aufgabe(pack)
        state.setdefault("offene_packs", {})[case["id"]] = {
            "case_id": case["id"],
            "karten": [{"nr": n, "id": k["id"], "frage": k["frage"],
                        "loesung": k["loesung"], "typ": k.get("typ"),
                        "gewicht": k.get("gewicht", 2)}
                       for n, k in enumerate(pack, 1)],
        }
    else:
        aufgabe = FALLBACK.get(case["id"]) or case.get("aufgabe") or AKTE
    rules = load_skript_section(case)
    related = search_related_case(case, state.get("seen_slugs", []))
    if related and related.get("slug"):
        state.setdefault("seen_slugs", []).append(related["slug"])
    if related:
        lesen = (f"I. Lesetext\n{related['gericht']}, {related['entscheidungstyp']} vom "
                 f"{related['datum']}, {related['aktenzeichen']}\n")
        if related.get("url"):
            lesen += related["url"] + "\n"
        lesen += "\n" + related["text"] + "\n"
    else:
        lesen = "I. Lesetext\nKein Urteil der passenden Gerichtsbarkeit.\n"
    body = (f"Jurabrief — {now_berlin().strftime('%A, %d. %B %Y')}\n{case['gebiet']}\n\n"
            f"{lesen}\n\nII. Bearbeitung\n{case['gebiet']}\n{case.get('quelle', '')}\n\n{aufgabe}\n")
    if rules and not pack:
        body += "\n--- Skript (Regeln) ---\n" + rules + "\n"
    send_mail(f"Jurabrief — {case['gebiet']} [{case['id']}] ({now_berlin().strftime('%d.%m.')})",
              body, resolve_to())
    markiere_gezeigt(progress, case["id"])
    if pack:
        markiere(progress, pack)
    save_progress(progress)
    save_state(state)
    print(f"Fall {case['id']} ({grund}) karten={len(pack)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
