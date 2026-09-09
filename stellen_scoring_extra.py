#!/usr/bin/env python3
"""
Stellen-Monitor — Scoring v3

Behebt zwei Fehler von v2.0:

(1) ZU VIEL: `behörden_kern` gab 4 Punkte allein für den Arbeitgebernamen.
    Jede BfV-/BND-/LfV-Ausschreibung löste damit für sich aus — auch
    Fachinformatiker, Objektschutz, Elektroniker. Jetzt zählt der
    Arbeitgeber nur noch 2 Punkte und braucht ein zweites, fachliches
    Signal. Zusätzlich zieht ein Technik-Veto Punkte ab.

(2) ZU WENIG: Wissenschaftskommunikation, Kulturvermittlung und
    Kulturvermittlung kamen im Raster gar nicht vor. Die DHMD-Stelle
    („Wissenschaftliche Mitarbeit für Diskurs und Wissenschafts-
    kommunikation") hätte Score 0 bekommen.

Einbau: Datei neben stellen_check.py legen, dann dort in main()
    from stellen_scoring_extra import score_v3 as score_text
statt der lokalen Funktion verwenden. Sonst ändert sich nichts.
"""

import re

from stellen_check import CATEGORIES as BASIS_KATEGORIEN, HARD_BLACKLIST

MIN_SCORE = 3


# ─── (1) Arbeitgeber vom Fachthema trennen ───
# Ersetzt die alte Kategorie "behörden_kern".
BEHOERDEN_SPLIT = {
    # Reiner Arbeitgebername: löst NICHT mehr allein aus.
    "behörden_arbeitgeber": {
        "weight": 2,
        "terms": [
            r"verfassungsschutz", r"bundesnachrichten\w*",
            r"nachrichtendienst\w*", r"militärisch\w* abschirmdienst",
            r"auswärtig\w*", r"auswartig\w*", r"auswaertig\w*",
            r"bundeskriminalamt", r"bundesamt für migration",
        ],
    },
    # Fachliches Thema: löst weiterhin allein aus.
    "behörden_fachlich": {
        "weight": 4,
        "terms": [
            r"extremism\w*", r"islamismus", r"islamistisch\w*",
            r"radikalis\w*", r"deradikalis\w*", r"terrorismus\w*",
            r"salafis\w*", r"dschihadis\w*", r"jihadis\w*",
            r"hybride bedrohung\w*", r"desinformation\w*",
            r"lageanalyse", r"lagebild", r"osint",
            r"politischer islam", r"ausländerextremismus",
        ],
    },
}


# ─── (2) Fehlende Felder ───
ZUSATZ_KATEGORIEN = {
    # Wissenschaftskommunikation — das DHMD-Loch: 3 Punkte
    "wissenschaftskommunikation": {
        "weight": 3,
        "terms": [
            r"wissenschaftskommunikation", r"wissenschaftsvermittlung",
            r"science communication", r"public engagement",
            r"wissensvermittlung", r"wissenstransfer",
            r"bürgerdialog\w*", r"buergerdialog\w*",
            r"partizipative\w* format\w*", r"diskursive\w* format\w*",
            r"dialogische\w* format\w*", r"veranstaltungsformat\w*",
            r"kinder-?universität", r"kinder-?uni\b",
            r"museumskommunikation", r"vermittlungsformat\w*",
            r"bildungsprogramm\w*", r"diskursprogramm\w*",
        ],
    },
    # Kulturarbeit, Programm, Moderation: 2 Punkte
    "kulturarbeit_programm": {
        "weight": 2,
        "terms": [
            r"kulturvermittlung", r"kulturmanagement",
            r"programmkuration", r"programmleitung",
            r"festivalleitung", r"festivalorganisation",
            r"veranstaltungskonzeption", r"veranstaltungsprogramm\w*",
            r"lesungsreihe", r"literaturfestival", r"literaturprogramm",
            r"moderation\w* von veranstaltungen",
            r"kulturelle bildung",
        ],
    },
}


# ─── (2b) Literaturbetrieb: Zeitungen, Verlage, Feuilleton — 3 Punkte ───
LITERATUR_KATEGORIEN = {
    "literaturbetrieb": {
        "weight": 3,
        "terms": [
            r"feuilleton\w*", r"kulturredaktion", r"kulturressort",
            r"kulturjournalis\w*", r"literaturredaktion",
            r"literaturkritik\w*", r"rezensent\w*", r"rezensionsteil",
            r"literaturzeitschrift\w*", r"literarische zeitschrift",
            r"zeitschriftenredaktion", r"literaturbetrieb",
            r"literarisches colloquium", r"literaturwerkstatt",
            r"schreibwerkstatt", r"literarisches schreiben",
            r"creative writing", r"poetik\w*",
            r"poesiefestival", r"lyrikfestival", r"literaturfestival",
            r"autorenförderung", r"autorenbetreuung",
            r"verlagsleitung", r"programmleitung verlag",
            r"buchmesse", r"literaturarchiv\w*",
            r"hörfunkredaktion", r"radiofeature",
        ],
    },
}

# ─── (2c) Erweiterungen bestehender Kategorien ───
# Lyrik/Übersetzung von 3 auf 4: soll allein auslösen.
UEBERSETZUNG_LYRIK_NEU = {
    "weight": 4,
    "terms": [
        r"literarische übersetzung", r"literarisches übersetzen",
        r"literary translation", r"poetry translation",
        r"lyrikübersetzung", r"lyrikuebersetzung", r"nachdichtung\w*",
        r"übersetzerwerkstatt", r"uebersetzerwerkstatt",
        r"übersetzerhaus", r"übersetzerresidenz",
        r"übersetzungswiss\w*", r"übersetzungswerkstatt",
        r"lyrik\w*", r"poesie", r"poet\w*", r"dichtung\w*",
        r"gegenwartslyrik", r"versform", r"freie vers\w*",
        r"poetry", r"poetics",
    ],
}

# Iran/Afghanistan/Tadschikistan schärfen — "iranisch" fiel bisher durch,
# weil \biran\b nur den nackten Ländernamen trifft.
IRAN_ZUSATZ = [
    r"iranisch\w*", r"iranian", r"irans",
    r"afghanistan", r"tadschikistan", r"tajikistan",
    r"\bdari\b", r"paschtu\w*", r"pashto", r"\bfarsi\b",
    r"hazara\w*", r"belutsch\w*", r"baloch\w*",
    r"kabul", r"herat", r"masar-i-scharif",
    r"teheran", r"tehran", r"isfahan", r"maschhad", r"mashhad",
    r"duschanbe", r"dushanbe", r"chudschand", r"khujand",
    r"chorasan", r"khorasan", r"transoxanien", r"transoxania",
    r"samarkand", r"buchara", r"bukhara", r"usbek\w*", r"uzbek\w*",
    r"sogdisch\w*", r"pamir\w*", r"badachschan", r"badakhshan",
    r"persianate", r"neupersisch\w*",
]


# ─── (3) Technik-Veto: zieht Punkte ab statt hart zu sperren ───
# Negativ statt Blacklist, damit eine echte Grenzstelle
# („OSINT-Auswertung Iran") nicht mit rausfliegt.
VETO_KATEGORIEN = {
    "technik_veto": {
        "weight": -4,
        "terms": [
            r"fachinformatiker\w*", r"informatiker\w*",
            r"softwareentwickl\w*", r"software-entwickl\w*",
            r"anwendungsentwickl\w*", r"systemadministrat\w*",
            r"netzwerkadministrat\w*", r"datenbankadministrat\w*",
            r"it-sicherheit", r"it-security", r"cyber-?sicherheit",
            r"penetrationstest\w*", r"rechenzentrum",
            r"nachrichtentechnik", r"fernmelde\w*",
            r"elektroniker\w*", r"elektrotechnik",
            r"mechatronik\w*", r"kraftfahrer\w*", r"berufskraftfahrer\w*",
            r"objektschutz", r"wachdienst", r"sicherheitsdienst",
            r"haustechnik", r"gebäudemanagement", r"gebaeudemanagement",
            r"schreinerei", r"schlosserei",
            r"\bsap\b", r"devops", r"cloud-?architekt\w*",
            r"data engineer\w*", r"\bkerntechnik\w*",
        ],
    },
    # Sprachdienstleistung als Beruf: nicht das Niveau, das gesucht wird.
    # Literarisches Übersetzen bleibt unberührt (eigene Kategorie).
    "sprachdienst_veto": {
        "weight": -3,
        "terms": [
            r"sprachendienst", r"sprachmittl\w*", r"sprachmittler\w*",
            r"dolmetsch\w*", r"simultandolmetsch\w*",
            r"bundessprachenamt", r"sprachsachverständig\w*",
            r"sprachanalyst\w*", r"terminologiearbeit",
            r"muttersprachlich\w* niveau",
        ],
    },
    "verwaltung_veto": {
        "weight": -3,
        "terms": [
            r"buchhaltung", r"rechnungswesen", r"controlling",
            r"vergabestelle", r"vergaberecht", r"beschaffungsstelle",
            r"personalsachbearbeit\w*", r"lohnbuchhaltung",
            r"haushaltssachbearbeit\w*", r"reisekostenabrechnung",
            r"fuhrpark\w*", r"poststelle", r"registratur",
            r"materialverwaltung", r"liegenschaftsverwaltung",
        ],
    },
}


# ─── Zusammenbau ───
def _baue_kategorien():
    kat = dict(BASIS_KATEGORIEN)
    kat.pop("behörden_kern", None)          # ersetzt durch den Split
    kat.update(BEHOERDEN_SPLIT)
    kat.update(ZUSATZ_KATEGORIEN)
    kat.update(LITERATUR_KATEGORIEN)
    kat["übersetzung_lyrik"] = UEBERSETZUNG_LYRIK_NEU
    kern = dict(kat["iran_islam_kern"])
    kern["terms"] = list(kern["terms"]) + IRAN_ZUSATZ
    kat["iran_islam_kern"] = kern
    kat.update(VETO_KATEGORIEN)
    return kat


ALLE_KATEGORIEN = _baue_kategorien()


def _kompiliere(kategorien):
    out = {}
    for name, data in kategorien.items():
        muster = []
        for term in data["terms"]:
            if r"\b" in term:
                muster.append(re.compile(term, re.IGNORECASE))
            else:
                muster.append(re.compile(r"\b" + term + r"\b", re.IGNORECASE))
        out[name] = (data["weight"], muster)
    return out


_COMPILED = _kompiliere(ALLE_KATEGORIEN)


def score_v3(text):
    """Wie score_text in v2.0, aber mit Split, Veto und neuen Kategorien.

    Rückgabe: (score, [kategorien]) — identische Signatur, damit main()
    unverändert bleibt. Negative Summen werden auf 0 geklemmt.
    """
    t_lower = text.lower()
    if any(b in t_lower for b in HARD_BLACKLIST):
        return (0, [])

    summe = 0
    treffer = []
    for name, (gewicht, muster) in _COMPILED.items():
        if any(p.search(text) for p in muster):
            summe += gewicht
            treffer.append(name)

    return (max(summe, 0), treffer)


# ─── Selbsttest: reale Fälle aus der bisherigen Pipeline ───
_FAELLE = [
    # (Text, soll durchkommen?)
    ("Wissenschaftliche Mitarbeit (m/w/d) für Diskurs und Wissenschaftskommunikation, "
     "Abteilung Diskurs & Wissen, Kinder-Universität mit der TU Dresden", True),
    ("Referent/in (m/w/d) Auswertung Islamismus beim Bundesamt für Verfassungsschutz", True),
    ("Fachinformatiker (m/w/d) Systemintegration beim Bundesamt für Verfassungsschutz", False),
    ("Elektroniker (m/w/d) für den Bundesnachrichtendienst", False),
    ("Sachbearbeitung Haushalt und Beschaffung beim Verfassungsschutz", False),
    ("Wissenschaftliche Volontärin (m/w/d) Gedenkstätte Buchenwald", True),
    ("Sprachmittler (m/w/d) Persisch/Dari beim Bundessprachenamt", False),
    ("Übersetzerwerkstatt persische Lyrik, literarisches Übersetzen", True),
    ("Kuratorisches Volontariat Ausstellungskonzeption Museum", True),
    ("Projektleitung Prävention und Deradikalisierung, AwareNet Hannover", True),
    ("Berufskraftfahrer (m/w/d) im Fuhrpark einer Bundesbehörde", False),
    ("Online Marketing Manager (m/w/d)", False),
    ("Lektorat Belletristik in einem unabhängigen Verlag", True),  # Verlagsschiene bleibt drin
    ("OSINT-Auswertung Naher Osten, Cyber-Sicherheit als Teilaspekt", True),
    ("Redakteur (m/w/d) Feuilleton, Schwerpunkt Literaturkritik", True),
    ("Lektorat Lyrik und Nachdichtung in einem unabhängigen Verlag", True),
    ("Wissenschaftliche Mitarbeit, Projekt zur iranischen Gegenwartsliteratur", True),
    ("Programmkoordination Übersetzerwerkstatt, Literarisches Colloquium", True),
    ("Landesreferent (m/w/d) Afghanistan und Tadschikistan, Entwicklungszusammenarbeit", True),
    ("Sachbearbeitung Fuhrparkverwaltung, Feuilletonabo inklusive", False),
]


def selbsttest():
    fehler = 0
    for text, soll in _FAELLE:
        score, kats = score_v3(text)
        ist = score >= MIN_SCORE
        ok = "OK  " if ist == soll else "FAIL"
        if ist != soll:
            fehler += 1
        print(f"{ok} score={score:>2} soll={'JA ' if soll else 'NEIN'} | {text[:64]}")
        print(f"          {', '.join(kats) or '—'}")
    print(f"\n{len(_FAELLE) - fehler}/{len(_FAELLE)} korrekt")


if __name__ == "__main__":
    selbsttest()
