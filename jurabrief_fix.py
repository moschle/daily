#!/usr/bin/env python3
"""Jurabrief-Reparatur. Im Wurzelverzeichnis von daily ausfuehren, Basis aaac528.

Jede Ersetzung ist abgesichert: passt der Ausgangstext nicht genau einmal,
bricht das Skript ab, bevor irgendetwas geschrieben wird.
"""
import json
import sys
from pathlib import Path

J = Path("jurabriefe")
K = J / "karten"
if not (J / "korrektur.py").exists():
    sys.exit("jurabriefe/korrektur.py fehlt — falsches Verzeichnis?")

AENDERUNGEN = []


def sub(pfad, alt, neu):
    AENDERUNGEN.append((Path(pfad), alt, neu))


# ---------------- fsrs_scheduler.py ----------------
sub(J / "fsrs_scheduler.py",
    "MIN_INTERVALL, MAX_INTERVALL = 1, 180",
    "MIN_INTERVALL, MAX_INTERVALL = 1, 180\n"
    "GNADENFRIST = 3          # Tage, die eine Aufgabe Zeit hat, bevor sie als unbeantwortet gilt")

sub(J / "fsrs_scheduler.py",
    '''def offene_wertung(progress: dict, case_id: str) -> bool:
    c = (progress.get("cards") or {}).get(case_id) or {}
    gezeigt, bewertet = c.get("gezeigt"), c.get("last")
    return bool(gezeigt and (not bewertet or bewertet < gezeigt))''',
    '''def offene_wertung(progress: dict, case_id: str, tag: date | None = None) -> bool:
    """Offen ist eine Aufgabe erst, wenn die Gnadenfrist abgelaufen ist UND
    danach mindestens ein Korrekturlauf sie nicht gefunden hat. Ohne die zweite
    Bedingung verbucht ein spaet verschickter Brief sich selbst als unbeantwortet."""
    tag = tag or heute()
    c = (progress.get("cards") or {}).get(case_id) or {}
    gezeigt, bewertet = c.get("gezeigt"), c.get("last")
    if not gezeigt or (bewertet and bewertet >= gezeigt):
        return False
    if (tag - date.fromisoformat(gezeigt)).days < GNADENFRIST:
        return False
    lauf = progress.get("letzter_korrekturlauf")
    return bool(lauf and lauf > gezeigt)''')

sub(J / "fsrs_scheduler.py",
    """    tag = tag or heute()
    if not offene_wertung(progress, case_id):
        return None""",
    """    tag = tag or heute()
    if not offene_wertung(progress, case_id, tag):
        return None""")

# ---------------- korrektur.py ----------------
sub(J / "korrektur.py",
    """from email.header import decode_header, make_header
from email.message import EmailMessage
from pathlib import Path""",
    """from datetime import date, timedelta
from email.header import decode_header, make_header
from email.message import EmailMessage
from pathlib import Path""")

sub(J / "korrektur.py", "MIN_KLAUSUR = 400",
    "MIN_KLAUSUR = 400\nFENSTER = 14             # Tage, die rueckwaerts nach Antworten gesucht wird")

sub(J / "korrektur.py",
    '''def hole_antworten() -> list[dict]:
    adresse = (os.environ.get("GMAIL_ADDRESS") or "").strip()
    pw = (os.environ.get("GMAIL_APP_PASSWORD") or "").strip()
    if not adresse or not pw:
        raise SystemExit("GMAIL_ADDRESS / GMAIL_APP_PASSWORD fehlen")
    gefunden = []
    with imaplib.IMAP4_SSL("imap.gmail.com") as M:
        M.login(adresse, pw)
        M.select("INBOX")
        _, daten = M.search(None, \'(UNSEEN SUBJECT "Jurabrief")\')
        for num in (daten[0].split() if daten and daten[0] else []):
            _, roh = M.fetch(num, "(RFC822)")
            msg = email.message_from_bytes(roh[0][1])
            subject = str(make_header(decode_header(msg.get("Subject", ""))))
            eintrag = einordnen(subject, _text_aus(msg))
            if eintrag:
                gefunden.append(eintrag)
            M.store(num, "+FLAGS", "\\\\Seen")
    return gefunden''',
    '''def hole_antworten(erledigt: set[str], tage: int = FENSTER) -> list[dict]:
    """Alle Jurabrief-Mails der letzten Tage, unabhaengig vom Gelesen-Status.

    Das Gelesen-Flag taugt nicht als Gedaechtnis: die Mail liegt im eigenen
    Postfach und wird beilaeufig geoeffnet. Gemerkt wird stattdessen die
    Message-ID in state.json."""
    adresse = (os.environ.get("GMAIL_ADDRESS") or "").strip()
    pw = (os.environ.get("GMAIL_APP_PASSWORD") or "").strip()
    if not adresse or not pw:
        raise SystemExit("GMAIL_ADDRESS / GMAIL_APP_PASSWORD fehlen")
    seit = (date.today() - timedelta(days=tage)).strftime("%d-%b-%Y")
    gefunden = []
    with imaplib.IMAP4_SSL("imap.gmail.com") as M:
        M.login(adresse, pw)
        M.select("INBOX")
        _, daten = M.search(None, f\'(SUBJECT "Jurabrief" SINCE {seit})\')
        for num in (daten[0].split() if daten and daten[0] else []):
            _, roh = M.fetch(num, "(RFC822)")
            msg = email.message_from_bytes(roh[0][1])
            mid = (msg.get("Message-ID") or "").strip()
            if not mid or mid in erledigt:
                continue
            if adresse.lower() in (msg.get("From") or "").lower():
                continue                      # eigener Brief, keine Antwort
            subject = str(make_header(decode_header(msg.get("Subject", ""))))
            eintrag = einordnen(subject, _text_aus(msg))
            if not eintrag:
                print(f"verworfen: {subject!r}", file=sys.stderr)
                continue
            eintrag["mid"] = mid
            gefunden.append(eintrag)
    return gefunden''')

sub(J / "korrektur.py", "def send_mail(betreff: str, body: str) -> None:",
    '''def aufraeumen(mids: set[str], tage: int = FENSTER) -> int:
    """Verarbeitete Antworten aus der INBOX nehmen.

    Laeuft erst, wenn progress.json und state.json geschrieben sind — bricht der
    Lauf vorher ab, bleibt die Mail liegen und wird beim naechsten Mal geholt.
    Bei Gmail wandert eine aus der INBOX expungte Mail in "Alle Nachrichten"."""
    if not mids:
        return 0
    adresse = (os.environ.get("GMAIL_ADDRESS") or "").strip()
    pw = (os.environ.get("GMAIL_APP_PASSWORD") or "").strip()
    seit = (date.today() - timedelta(days=tage)).strftime("%d-%b-%Y")
    n = 0
    with imaplib.IMAP4_SSL("imap.gmail.com") as M:
        M.login(adresse, pw)
        M.select("INBOX")
        _, daten = M.search(None, f\'(SUBJECT "Jurabrief" SINCE {seit})\')
        for num in (daten[0].split() if daten and daten[0] else []):
            _, roh = M.fetch(num, "(BODY.PEEK[HEADER.FIELDS (MESSAGE-ID)])")
            kopf = roh[0][1].decode("utf-8", "replace") if roh and roh[0] else ""
            mid = kopf.split(":", 1)[1].strip() if ":" in kopf else ""
            if mid and mid in mids:
                M.store(num, "+FLAGS", "\\\\Deleted")
                n += 1
        if n:
            M.expunge()
    print(f"{n} Antwortmail(s) aus der INBOX geraeumt", file=sys.stderr)
    return n


def send_mail(betreff: str, body: str) -> None:''')

sub(J / "korrektur.py",
    """    antworten = hole_antworten()
    print(f"{len(antworten)} Antworten", file=sys.stderr)""",
    """    erledigt = set(state.get("erledigte_mails") or [])
    frisch: set[str] = set()
    antworten = hole_antworten(erledigt)
    print(f"{len(antworten)} Antworten", file=sys.stderr)""")

sub(J / "korrektur.py",
    '''    for a in antworten:
        case = cases.get(a["case_id"])''',
    '''    for a in antworten:
        erledigt.add(a["mid"])
        frisch.add(a["mid"])
        case = cases.get(a["case_id"])''')

sub(J / "korrektur.py",
    '''        offen = state.get("offen") or {}
        pack = offen.get("karten") or []
        if pack and offen.get("case_id") == case["id"]:''',
    '''        packs = state.setdefault("offene_packs", {})
        eintrag = packs.get(case["id"])
        if not eintrag and (state.get("offen") or {}).get("case_id") == case["id"]:
            eintrag = state["offen"]          # Uebergang vom alten Einzelslot
        pack = (eintrag or {}).get("karten") or []
        if pack:''')

sub(J / "korrektur.py",
    '''            print(f"{case['id']} {len(k['karten'])} Karten, Schnitt {k['gesamt']}", file=sys.stderr)
            state["offen"] = {}
            state_pfad.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
            continue''',
    '''            print(f"{case['id']} {len(k['karten'])} Karten, Schnitt {k['gesamt']}", file=sys.stderr)
            packs.pop(case["id"], None)
            if (state.get("offen") or {}).get("case_id") == case["id"]:
                state["offen"] = {}
            continue''')

sub(J / "korrektur.py",
    """    _save(progress)
    return 0""",
    '''    progress["letzter_korrekturlauf"] = date.today().isoformat()
    _save(progress)
    state["erledigte_mails"] = sorted(erledigt)[-300:]
    state_pfad.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    if frisch and os.environ.get("JURABRIEF_AUFRAEUMEN", "1") != "0":
        aufraeumen(frisch)
    return 0''')

# ---------------- generate_jurabrief.py ----------------
sub(J / "generate_jurabrief.py",
    '    zuletzt = [k["id"] for k in (state.get("offen") or {}).get("karten", [])]',
    '    zuletzt = [k["id"] for p in (state.get("offene_packs") or {}).values()\n'
    '               for k in p.get("karten", [])]')

sub(J / "generate_jurabrief.py",
    '    state["offen"] = zurueckhalten(heutige, case["id"])',
    '''    packs = state.setdefault("offene_packs", {})
    packs[case["id"]] = zurueckhalten(heutige, case["id"])
    for alt in list(packs)[:-3]:              # hoechstens drei Briefe offen halten
        packs.pop(alt)
    state["offen"] = {}''')

# ---------------- sende_brief.py ----------------
sub(J / "sende_brief.py",
    '''        state["offen"] = {
            "case_id": case["id"],
            "karten": [{"id": k["id"], "frage": k["frage"],
                         "loesung": k["loesung"], "typ": k.get("typ")}
                        for k in pack],
        }
    else:
        aufgabe = FALLBACK.get(case["id"]) or case.get("aufgabe") or AKTE
        state["offen"] = {"case_id": case["id"], "karten": []}''',
    '''        state.setdefault("offene_packs", {})[case["id"]] = {
            "case_id": case["id"],
            "karten": [{"nr": n, "id": k["id"], "frage": k["frage"],
                        "loesung": k["loesung"], "typ": k.get("typ"),
                        "gewicht": k.get("gewicht", 2)}
                       for n, k in enumerate(pack, 1)],
        }
    else:
        aufgabe = FALLBACK.get(case["id"]) or case.get("aufgabe") or AKTE''')

# ---------------- pruefe_karten.py ----------------
sub(J / "pruefe_karten.py",
    "Hintergrund: der zweite Kurationslauf hat den Bestand von 145 auf 105 Karten",
    """Geprueft wird auch, ob Frage und Loesung einer kuratierten Karte aus derselben
Rohkarte stammen. Abschnitt und Randnummer reisen mit der Loesung mit; weichen
sie von der Rohkarte mit demselben Loesungstext ab, sind Frage und Loesung
auseinandergelaufen.

Hintergrund: der zweite Kurationslauf hat den Bestand von 145 auf 105 Karten""")

sub(J / "pruefe_karten.py",
    "def maengel(bestand: dict[str, list[dict]]) -> list[str]:",
    "def maengel(bestand: dict[str, list[dict]], bekannt: set[str] | None = None) -> list[str]:")

sub(J / "pruefe_karten.py",
    """    fehler = []
    for sid, karten in bestand.items():""",
    """    bekannt = bekannt or set()
    fehler = []
    for sid, karten in bestand.items():""")

sub(J / "pruefe_karten.py",
    '''        skript = clean(pfad.read_text(encoding="utf-8", errors="replace")) if pfad.exists() else ""
        ids = set()''',
    '''        skript = clean(pfad.read_text(encoding="utf-8", errors="replace")) if pfad.exists() else ""
        roh_pfad = KARTEN / f"{sid}.json"
        roh = {r["loesung"]: (r.get("abschnitt"), r.get("rn"))
               for r in json.loads(roh_pfad.read_text(encoding="utf-8")).get("karten", [])
               if r.get("loesung")} if roh_pfad.exists() else {}
        ids = set()''')

sub(J / "pruefe_karten.py",
    '''            from karten import ohne_fussnoten
            if ohne_fussnoten(k.get("loesung") or "") != (k.get("loesung") or ""):
                fehler.append(f"{wo}: Fussnotenziffer in der Loesung")
    return fehler''',
    '''            from karten import ohne_fussnoten
            if ohne_fussnoten(k.get("loesung") or "") != (k.get("loesung") or ""):
                fehler.append(f"{wo}: Fussnotenziffer in der Loesung")
            herkunft = roh.get(k.get("loesung"))
            if (herkunft and herkunft != (k.get("abschnitt"), k.get("rn"))
                    and k.get("id") not in bekannt):
                fehler.append(f"{wo}: Loesung stammt aus {herkunft[0]!r} Rn {herkunft[1]}, "
                              f"Karte behauptet {k.get('abschnitt')!r} Rn {k.get('rn')}")
    return fehler''')

sub(J / "pruefe_karten.py",
    '''    if "--setzen" in sys.argv:
        REFERENZ.write_text(json.dumps(jetzt, ensure_ascii=False, indent=1), encoding="utf-8")''',
    '''    if "--setzen" in sys.argv:
        alt = json.loads(REFERENZ.read_text(encoding="utf-8")) if REFERENZ.exists() else {}
        jetzt["zuordnung_bekannt"] = alt.get("zuordnung_bekannt") or []
        REFERENZ.write_text(json.dumps(jetzt, ensure_ascii=False, indent=1), encoding="utf-8")''')

sub(J / "pruefe_karten.py", "    probleme = maengel(bestand)",
    '''    bekannt = set()
    if REFERENZ.exists():
        bekannt = set(json.loads(REFERENZ.read_text(encoding="utf-8")).get("zuordnung_bekannt") or [])
    probleme = maengel(bestand, bekannt)''')

# ---------------- Workflow ----------------
sub(Path(".github/workflows/jurabrief-antwort.yml"),
    "    - cron: '0 17 * * 2,4,6'", "    - cron: '0 17 * * *'")
sub(Path(".github/workflows/jurabrief-antwort.yml"),
    "          git add jurabriefe/progress.json",
    "          git add jurabriefe/progress.json jurabriefe/state.json")

# ======== erst pruefen, dann schreiben ========
inhalt = {}
for pfad, alt, neu in AENDERUNGEN:
    s = inhalt.get(pfad) or pfad.read_text(encoding="utf-8")
    if s.count(alt) != 1:
        sys.exit(f"ABBRUCH {pfad}: Ausgangstext {s.count(alt)}x gefunden, erwartet 1x\n{alt[:120]}")
    inhalt[pfad] = s.replace(alt, neu)
for pfad, s in inhalt.items():
    pfad.write_text(s, encoding="utf-8")
    print("geaendert:", pfad)

# ---------------- Karten ----------------
for sid, cid in [("revision", "revision:form:021"), ("zr-anwalt", "zr-anwalt:form:017")]:
    p = K / f"{sid}.kuratiert.json"
    d = json.loads(p.read_text(encoding="utf-8"))
    vor = len(d["karten"])
    d["karten"] = [k for k in d["karten"] if k["id"] != cid]
    if len(d["karten"]) == vor:
        sys.exit(f"ABBRUCH: {cid} nicht gefunden")
    p.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Karte entfernt: {cid} ({vor} -> {len(d['karten'])})")

bestand = {q.stem.replace(".kuratiert", ""): json.loads(q.read_text(encoding="utf-8"))["karten"]
           for q in sorted(K.glob("*.kuratiert.json"))}
alle = [k for v in bestand.values() for k in v]
(K / "referenz.json").write_text(json.dumps(
    {"gesamt": len(alle),
     "je_skript": {s: len(v) for s, v in bestand.items()},
     "je_typ": {t: sum(1 for k in alle if k.get("typ") == t)
                for t in ("formulierung", "fall", "fehler", "aufbau")},
     "zuordnung_bekannt": ["revision:fall:019", "verwr-staat:form:020"]},
    ensure_ascii=False, indent=1), encoding="utf-8")
print("referenz.json neu:", len(alle), "Karten")

# ---------------- progress.json: Buchung vom 09.09. zuruecknehmen ----------------
BETROFFEN = ["zr-006", "zr-anwalt:form:011", "zr-anwalt:form:012",
             "zr-anwalt:form:013", "zr-anwalt:form:014"]
p = J / "progress.json"
d = json.loads(p.read_text(encoding="utf-8"))
vor = len(d["feedback"])
d["feedback"] = [f for f in d["feedback"]
                 if not (f.get("date") == "2026-09-09" and f.get("note") == "unbeantwortet"
                         and f.get("case_id") in BETROFFEN)]
for cid in BETROFFEN:
    c = d["cards"].get(cid)
    if c:
        c.pop("unbeantwortet", None)
        c["due"] = None
d["letzter_korrekturlauf"] = None
p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"progress.json: {vor} -> {len(d['feedback'])} Feedback-Eintraege")

# ---------------- state.json: Pack zu zr-006 wiederherstellen ----------------
REIHENFOLGE = ["zr-anwalt:form:012", "zr-anwalt:form:013",
               "zr-anwalt:form:014", "zr-anwalt:form:011"]
kur = {k["id"]: k for k in
       json.loads((K / "zr-anwalt.kuratiert.json").read_text(encoding="utf-8"))["karten"]}
p = J / "state.json"
st = json.loads(p.read_text(encoding="utf-8"))
packs = st.setdefault("offene_packs", {})
if st.get("offen"):
    packs[st["offen"]["case_id"]] = st["offen"]
packs["zr-006"] = {
    "case_id": "zr-006", "datum": "2026-09-08",
    "karten": [{"nr": n, "id": cid, "typ": kur[cid].get("typ"),
                "frage": kur[cid]["frage"], "loesung": kur[cid]["loesung"][:1200],
                "gewicht": kur[cid].get("gewicht", 2), "skript": kur[cid].get("skript"),
                "abschnitt": kur[cid].get("abschnitt", "")}
               for n, cid in enumerate(REIHENFOLGE, 1)]}
st["offen"] = {}
st.setdefault("erledigte_mails", [])
p.write_text(json.dumps(st, ensure_ascii=False, indent=2), encoding="utf-8")
print("state.json: offene Packs =", list(packs))
print("\nfertig.")
