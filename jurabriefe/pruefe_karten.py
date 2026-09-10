#!/usr/bin/env python3
"""Kartenbestand pruefen. Bricht ab, wenn ein Lauf ihn verschlechtert hat.

    python jurabriefe/pruefe_karten.py            pruefen, Kennzahlen ausgeben
    python jurabriefe/pruefe_karten.py --setzen   aktuellen Stand als Referenz festschreiben

Vor jedem Commit ausfuehren. Exit 0 = committen, Exit 1 = nicht committen.

Geprueft wird auch, ob Frage und Loesung einer kuratierten Karte aus derselben
Rohkarte stammen. Abschnitt und Randnummer reisen mit der Loesung mit; weichen
sie von der Rohkarte mit demselben Loesungstext ab, sind Frage und Loesung
auseinandergelaufen.

Hintergrund: der zweite Kurationslauf hat den Bestand von 145 auf 105 Karten
gesenkt und alle Fehler- und Aufbaukarten verloren — bemerkt hat es niemand,
weil die Dateien ueberschrieben wurden. Diese Pruefung macht so etwas sichtbar,
bevor es im Repo landet.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
KARTEN = HERE / "karten"
REFERENZ = KARTEN / "referenz.json"
TYPEN = ("formulierung", "fall", "fehler", "aufbau")

TOLERANZ = 0.02          # 2 % Schwund sind Rauschen, mehr nicht
MIN_FRAGE = 15
MAX_LOESUNG = 2000


def _laden() -> dict[str, list[dict]]:
    return {p.stem.replace(".kuratiert", ""):
            json.loads(p.read_text(encoding="utf-8")).get("karten", [])
            for p in sorted((q for q in KARTEN.glob("*.kuratiert.json") if q.stem != "lesetexte.kuratiert"))}


def kennzahlen(bestand: dict[str, list[dict]]) -> dict:
    alle = [k for v in bestand.values() for k in v]
    return {
        "gesamt": len(alle),
        "je_skript": {s: len(v) for s, v in bestand.items()},
        "je_typ": {t: sum(1 for k in alle if k.get("typ") == t) for t in TYPEN},
    }


def maengel(bestand: dict[str, list[dict]], bekannt: set[str] | None = None) -> list[str]:
    """Harte Fehler im Bestand — unabhaengig vom Vergleich mit der Referenz."""
    import kuratieren as ku
    from karten import EXTRACTED, clean

    bekannt = bekannt or set()
    fehler = []
    for sid, karten in bestand.items():
        pfad = EXTRACTED / f"{sid}.txt"
        skript = clean(pfad.read_text(encoding="utf-8", errors="replace")) if pfad.exists() else ""
        roh_pfad = KARTEN / f"{sid}.json"
        roh = {r["loesung"]: (r.get("abschnitt"), r.get("rn"))
               for r in json.loads(roh_pfad.read_text(encoding="utf-8")).get("karten", [])
               if r.get("loesung")} if roh_pfad.exists() else {}
        ids = set()
        for k in karten:
            wo = f"{sid}/{k.get('id', '?')}"
            if k.get("id") in ids:
                fehler.append(f"{wo}: doppelte id")
            ids.add(k.get("id"))
            if len((k.get("frage") or "").strip()) < MIN_FRAGE:
                fehler.append(f"{wo}: Frage zu kurz")
            if not (k.get("loesung") or "").strip():
                fehler.append(f"{wo}: keine Loesung")
            elif len(k["loesung"]) > MAX_LOESUNG:
                fehler.append(f"{wo}: Loesung ueber {MAX_LOESUNG} Zeichen")
            elif skript and not ku.woertlich_im_skript(k["loesung"], skript):
                fehler.append(f"{wo}: Loesung steht nicht woertlich im Skript")
            if k.get("gewicht") not in (1, 2, 3):
                fehler.append(f"{wo}: Gewicht {k.get('gewicht')!r} ungueltig")
            from karten import ohne_fussnoten
            if ohne_fussnoten(k.get("loesung") or "") != (k.get("loesung") or ""):
                fehler.append(f"{wo}: Fussnotenziffer in der Loesung")
            herkunft = roh.get(k.get("loesung"))
            if (herkunft and herkunft != (k.get("abschnitt"), k.get("rn"))
                    and k.get("id") not in bekannt):
                fehler.append(f"{wo}: Loesung stammt aus {herkunft[0]!r} Rn {herkunft[1]}, "
                              f"Karte behauptet {k.get('abschnitt')!r} Rn {k.get('rn')}")
    return fehler


def vergleich(jetzt: dict, referenz: dict) -> list[str]:
    warnungen = []
    grenze = int(referenz["gesamt"] * (1 - TOLERANZ))
    if jetzt["gesamt"] < grenze:
        warnungen.append(f"Bestand {jetzt['gesamt']} unter Referenz {referenz['gesamt']} "
                         f"(zulaessig ab {grenze})")
    for t, n in referenz["je_typ"].items():
        if n > 0 and jetzt["je_typ"].get(t, 0) == 0:
            warnungen.append(f"Kartentyp {t} vollstaendig verschwunden (Referenz: {n})")
    for s, n in referenz["je_skript"].items():
        neu = jetzt["je_skript"].get(s, 0)
        if neu < n * (1 - TOLERANZ) - 1:
            warnungen.append(f"{s}: {neu} statt {n} Karten")
    return warnungen


def main() -> int:
    if not KARTEN.exists():
        print("kein karten/-Verzeichnis — erst python jurabriefe/karten.py", file=sys.stderr)
        return 1
    bestand = _laden()
    jetzt = kennzahlen(bestand)

    print(f"{jetzt['gesamt']} kuratierte Karten")
    print("  je Typ:   " + ", ".join(f"{t} {n}" for t, n in jetzt["je_typ"].items()))
    print("  je Skript: " + ", ".join(f"{s} {n}" for s, n in sorted(jetzt["je_skript"].items())))

    if "--setzen" in sys.argv:
        alt = json.loads(REFERENZ.read_text(encoding="utf-8")) if REFERENZ.exists() else {}
        jetzt["zuordnung_bekannt"] = alt.get("zuordnung_bekannt") or []
        REFERENZ.write_text(json.dumps(jetzt, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"\nReferenz gesetzt: {REFERENZ}")
        return 0

    bekannt = set()
    if REFERENZ.exists():
        bekannt = set(json.loads(REFERENZ.read_text(encoding="utf-8")).get("zuordnung_bekannt") or [])
    probleme = maengel(bestand, bekannt)
    if probleme:
        print(f"\n{len(probleme)} Maengel im Bestand:", file=sys.stderr)
        for p in probleme[:20]:
            print(f"  {p}", file=sys.stderr)
        if len(probleme) > 20:
            print(f"  … und {len(probleme) - 20} weitere", file=sys.stderr)

    warnungen = []
    if REFERENZ.exists():
        warnungen = vergleich(jetzt, json.loads(REFERENZ.read_text(encoding="utf-8")))
        if warnungen:
            print("\nVerschlechterung gegenueber der Referenz:", file=sys.stderr)
            for w in warnungen:
                print(f"  {w}", file=sys.stderr)
    else:
        print("\nkeine Referenz — mit --setzen festschreiben", file=sys.stderr)

    if probleme or warnungen:
        print("\nNICHT COMMITTEN. Ursache beheben oder, wenn der Rueckgang gewollt ist, "
              "mit --setzen neu festschreiben.", file=sys.stderr)
        return 1
    print("\nBestand in Ordnung — committen.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
