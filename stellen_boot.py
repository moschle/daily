#!/usr/bin/env python3
"""Einstieg Stellen-Monitor: Zusatzquellen + Scoring v3.

stellen_check.py bleibt unverändert. Die Action ruft diese Datei.
"""
from __future__ import annotations

import os
import re
import sys
import unicodedata

import stellen_check as sc
from stellen_quellen_extra import (
    fetch_museumsbund,
    ist_leiche,
)
from stellen_scoring_extra import score_v3


ZWSP = dict.fromkeys(range(0x200b, 0x2010), None)   # kultweet haengt Zero-Width-Muell an


def _norm(text: str) -> str:
    """Titel auf einen Vergleichskern eindampfen."""
    t = text.translate(ZWSP)
    t = unicodedata.normalize("NFKD", t.lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = re.sub(r"^\s*(job|stelle|stellenangebot)\s*:\s*", " ", t)   # H-Soz-Kult-Praefix
    t = t.split("|")[0]                                              # kultweet: "Titel | Ort"
    t = re.sub(r"\(?\b[mwdfx](?:\s*/\s*[mwdfx])+\b\)?", " ", t)     # (m/w/d)
    t = re.sub(r"[^a-z0-9]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def _ort_marke(job: dict) -> str:
    """Ort oder Arbeitgeber, damit zwei gleichnamige Volontariate
    verschiedener Haeuser NICHT zusammenfallen. Leer = unbekannt."""
    text = f"{job.get('title','')} {job.get('summary','')}".translate(ZWSP)
    # Arbeitgeber zuerst: der steht in beiden Quellen gleich da, waehrend
    # die PLZ nur service.bund.de mitliefert — sonst faellt dieselbe Stelle
    # in zwei verschiedene Schluessel.
    m = re.search(r"Arbeitgeber\s*:\s*(.{3,60}?)(?:\s+Ort\s*:|\s+Bewerbungsfrist|\||$)", text)
    if m:
        return _norm(m.group(1))[:25]
    m = re.search(r"\b(\d{5})\b", text)
    if m:
        return m.group(1)
    return ""


def dedupliziere(jobs: list) -> list:
    """Gleiche Stelle aus mehreren Quellen zu einem Eintrag zusammenfassen.

    Schluessel ist Titelkern + Ort/Arbeitgeber. Eintraege ohne erkennbaren
    Ort (museumsbund liefert blanke Titel) werden nachtraeglich an einen
    Titelzwilling angehaengt, aber nur wenn es genau einen gibt.
    """
    haupt: dict = {}
    reihenfolge: list = []
    ohne_ort: list = []

    def einfuegen(schluessel, job):
        if schluessel not in haupt:
            job = dict(job)
            job["sources"] = [job["source"]]
            haupt[schluessel] = job
            reihenfolge.append(schluessel)
            return
        vorhanden = haupt[schluessel]
        if job["source"] not in vorhanden["sources"]:
            vorhanden["sources"].append(job["source"])
        if len(job.get("summary", "")) > len(vorhanden.get("summary", "")):
            quellen = vorhanden["sources"]
            neu_eintrag = dict(job)
            neu_eintrag["sources"] = quellen
            haupt[schluessel] = neu_eintrag

    for job in jobs:
        titel = _norm(job.get("title", ""))
        if not titel:
            continue
        ort = _ort_marke(job)
        if ort:
            einfuegen((titel, ort), job)
        else:
            ohne_ort.append((titel, job))

    for titel, job in ohne_ort:
        zwillinge = [s for s in haupt if s[0] == titel]
        if len(zwillinge) == 1:
            einfuegen(zwillinge[0], job)
        else:
            einfuegen((titel, ""), job)

    return [haupt[s] for s in reihenfolge]


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
        # bpb ist aus, bis das href-Muster sitzt: die Seite liefert
        # Artikel statt Ausschreibungen, und Titel wie "Zeichen von
        # Radikalisierung" holen sich über behörden_fachlich 4 Punkte.
        # Sie kaemen also als Treffer durch und landen im Seen-Store.
        # Wieder aktivieren: fetch_bpb_infodienst importieren und
        # hier eintragen.
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
            sources_status[name] = f"{type(e).__name__}: {e}"

    vorher = len(all_jobs)
    all_jobs = dedupliziere(all_jobs)
    print(f"Dedupliziert: {vorher} -> {len(all_jobs)}", file=sys.stderr)

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
