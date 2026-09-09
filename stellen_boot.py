#!/usr/bin/env python3
"""Einstieg Stellen-Monitor: Zusatzquellen + Scoring v3.

stellen_check.py bleibt unverändert. Die Action ruft diese Datei.
"""
from __future__ import annotations

import os
import sys

import stellen_check as sc
from stellen_quellen_extra import (
    fetch_museumsbund,
    fetch_bpb_infodienst,
    ist_leiche,
)
from stellen_scoring_extra import score_v3


def main() -> None:
    seen = sc.load_seen()
    print(f"State geladen: {len(seen)} bekannte Stellen", file=sys.stderr)

    sources = [
        ("H-Soz-Kult", sc.fetch_hsozkult),
        ("kultweet", sc.fetch_kultweet),
        ("UniBwM", sc.fetch_unibwm),
        ("service.bund.de", sc.fetch_servicebund),
        ("arthist.net", sc.fetch_arthist),
        ("jobs.ac.uk Languages", sc.fetch_jobsacuk_languages),
        ("jobs.ac.uk History", sc.fetch_jobsacuk_history),
        ("jobs.ac.uk Politics", sc.fetch_jobsacuk_politics),
        ("museumsbund", fetch_museumsbund),
        ("bpb Infodienst", fetch_bpb_infodienst),
    ]
    all_jobs = []
    sources_status = {}
    for name, fetch_fn in sources:
        try:
            jobs = fetch_fn()
            sources_status[name] = len(jobs)
            all_jobs.extend(jobs)
        except Exception as e:
            print(f"Quelle {name} komplett gescheitert: {e}", file=sys.stderr)
            sources_status[name] = -1

    scored_hits = []
    for job in all_jobs:
        full_text = f"{job['title']} {job.get('summary', '')}"
        if ist_leiche(full_text):
            continue
        score, cats = score_v3(full_text)
        if score < sc.MIN_SCORE:
            continue
        if job["id"] in seen:
            continue
        scored_hits.append((job, score, cats))
        sc.mark_seen(seen, job["id"], job["source"], job["title"], job["url"], score, cats)

    print(
        f"Neue Treffer: {len(scored_hits)} von {len(all_jobs)} insgesamt "
        f"(Min-Score {sc.MIN_SCORE}, scoring v3)",
        file=sys.stderr,
    )
    sc.save_seen(seen)

    debug = os.environ.get("DEBUG_STELLEN") == "1"
    if scored_hits or debug:
        html = sc.build_html_mail(scored_hits, len(seen), sources_status)
        subject = (
            f"Stellen-Monitor: {len(scored_hits)} neue Treffer"
            if scored_hits
            else "Stellen-Monitor: keine Treffer (Debug)"
        )
        sc.send_mail(html, subject, len(scored_hits))
    else:
        print("Keine neuen Treffer, keine Mail.", file=sys.stderr)


if __name__ == "__main__":
    main()
