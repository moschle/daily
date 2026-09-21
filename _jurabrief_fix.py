#!/usr/bin/env python3
"""Jurabrief-Fixes:

1. lesetext_aufbereiten: Fragen muessen selbsttragend sein — sie enthalten
   den relevanten Sachverhalt aus dem Urteil im Fragetext selbst.
   Eine Frage darf nie voraussetzen, dass der Leser den Lesetext gerade
   zur Hand hat oder sich erinnert.

2. Architektur: Lesetext-Karten kommen NICHT mehr in die regulaere
   Rotation. Sie werden einmalig zusammen mit ihrem Urteil gestellt;
   danach nicht gespeichert und nicht wiederverwendet.
   Hintergrund: gespeicherte Lesetext-Karten erschienen bisher in
   kuenftigen Briefen mit einem anderen Urteil — die Fragen
   referenzierten dann Inhalte, die nicht in der Mail standen.

3. Urteilstext: Das Modell bekommt und die Mail zeigt denselben
   Ausschnitt — maximal 25000 Zeichen. Damit ist sichergestellt,
   dass keine Frage aus dem nichtsichtbaren Restteil entsteht.
"""
import ast
import pathlib
import re

REPO = pathlib.Path.home() / "Projects/daily"
p = REPO / "jurabriefe/generate_jurabrief.py"
s = p.read_text(encoding="utf-8")

# ── 1. Urteilstext-Limit angleichen ──────────────────────────────────────
alt_max = "shaped = clean_ocr(raw)[:60000]"
neu_max = "shaped = clean_ocr(raw)[:25000]  # gleicher Ausschnitt fuer Mail und Fragegeneration"
assert alt_max in s, "Kuerzezeile nicht gefunden"
s = s.replace(alt_max, neu_max)

# ── 2. Prompt: selbsttragende Fragen ────────────────────────────────────
alt_pr = '''    prompt = (
        "Du stellst Aufgaben zu einer Gerichtsentscheidung fuer die Vorbereitung "
        "auf das zweite juristische Staatsexamen.\\n\\n"
        "Antworte NUR mit JSON, ohne Vorrede und ohne Codefence:\\n"
        \'{"fragen": [{"frage": "...", "loesung": "..."}, ...]}\\n\\n\'
        "Genau drei Fragen, in dieser Reihenfolge:\\n"
        "1. Erfassen: wer klagt gegen wen woraus, wie haben die Vorinstanzen "
        "entschieden, worum geht der Streit im Kern. Eine Frage, die sich nur "
        "beantworten laesst, wenn man den Sachverhalt und den Prozessverlauf "
        "gelesen hat.\\n"
        "2. Die tragende Rechtsfrage: woran haengt die Entscheidung, welcher "
        "Massstab wird angelegt.\\n"
        "3. Anwaltliche oder richterliche Konsequenz: was folgt daraus fuer die "
        "eigene Arbeit — was haette anders laufen muessen, worauf ist im "
        "naechsten vergleichbaren Fall zu achten.\\n\\n"
        "Die Fragen duerfen die Antwort nicht verraten und sollen in zwei bis "
        "vier Saetzen zu beantworten sein. Die Loesung nennt die tragenden "
        "Erwaegungen der Entscheidung, nicht nur das Ergebnis.\\n\\n"
        f"Entscheidung: {related.get(\'gericht\')}, {related.get(\'aktenzeichen\')} "
        f"vom {related.get(\'datum\')}\\n\\n{text}")'''
neu_pr = '''    prompt = (
        "Du stellst Aufgaben zu einer Gerichtsentscheidung fuer die Vorbereitung "
        "auf das zweite juristische Staatsexamen.\\n\\n"
        "Antworte NUR mit JSON, ohne Vorrede und ohne Codefence:\\n"
        \'{"fragen": [{"frage": "...", "loesung": "..."}, ...]}\\n\\n\'
        "WICHTIG — SELBSTTRAGENDE FRAGEN:\\n"
        "Jede Frage muss vollstaendig lesbar sein, ohne dass die Entscheidung "
        "daneben liegt. Das bedeutet: Die Frage nennt Gericht, Datum und "
        "Aktenzeichen. Sie fasst in zwei bis drei Saetzen den Kern des Sachverhalts "
        "zusammen, den sie voraussetzt. Dann erst kommt die eigentliche Aufgabe.\\n"
        "Falsch: \\"Was hat das Gericht zur Klagefrist entschieden?\\"\\n"
        "Richtig: \\"Im Urteil des OVG Muenster vom 12.03.2024 (4 A 1234/23) "
        "hatte der Klaeger gegen einen Planfeststellungsbeschluss geklagt. "
        "Die Vorinstanz hatte die Klage wegen Verspаetung abgewiesen. "
        "Unter welchen Voraussetzungen beginnt die Klagefrist in solchen Faellen "
        "erneut zu laufen?\\n\\n"
        "Genau drei Fragen, in dieser Reihenfolge:\\n"
        "1. Sachverhalt und Prozessverlauf: nenne die wesentlichen Fakten (Parteien, "
        "Streitgegenstand, Vorinstanzen) IN DER FRAGE selbst und frage dann, "
        "wie das Gericht entschieden hat und warum.\\n"
        "2. Die tragende Rechtsfrage: fasse den rechtlichen Kern kurz zusammen "
        "und frage nach dem anzulegenden Massstab.\\n"
        "3. Anwaltliche oder richterliche Konsequenz: nenne die Situation aus "
        "der Entscheidung und frage, was daraus fuer die eigene Arbeit folgt.\\n\\n"
        "Die Loesung nennt die tragenden Erwaegungen der Entscheidung, nicht "
        "nur das Ergebnis. Lieber ein Satz mehr als abgeschnitten.\\n\\n"
        f"Entscheidung: {related.get(\'gericht\')}, {related.get(\'aktenzeichen\')} "
        f"vom {related.get(\'datum\')}\\n\\n{text}")'''
assert alt_pr in s, "Prompt-Block nicht gefunden"
s = s.replace(alt_pr, neu_pr)

# ── 3. Lesetext-Karten nicht mehr speichern und nicht mehr in Rotation ───
# merke_lesetext_karte-Aufrufe entfernen
alt_merke = "            merke_lesetext_karte(karte)\n            heutige.append(karte)"
neu_merke = "            # Lesetext-Karte nur einmalig stellen, nicht speichern\n            heutige.append(karte)"
assert alt_merke in s, "merke_lesetext_karte-Aufruf nicht gefunden"
s = s.replace(alt_merke, neu_merke)

p.write_text(s, encoding="utf-8")
ast.parse(s)
print("generate_jurabrief.py geaendert")

# ── 4. kartenbrief.py: lesetexte.kuratiert.json nicht mehr laden ─────────
kb = REPO / "jurabriefe/kartenbrief.py"
ks = kb.read_text(encoding="utf-8")
alt_lade = '''def lade(skript_id: str) -> list[dict]:
    """Kuratierte Karten, erzeugte Karten und die Fragen aus frueheren Lesetexten."""
    return (_lies(KARTEN / f"{skript_id}.kuratiert.json")
            + _lies(KARTEN / f"{skript_id}.gen.json")
            + [k for k in _lies(LESETEXTE) if k.get("skript") == skript_id])'''
neu_lade = '''def lade(skript_id: str) -> list[dict]:
    """Kuratierte und erzeugte Karten.

    Lesetext-Karten werden hier bewusst NICHT geladen: Sie wurden zusammen
    mit einem bestimmten Urteil generiert und sind ohne diesen Text
    nicht sinnvoll beantwortbar. Sie kommen einmalig in dem Brief, in dem
    das Urteil gezeigt wird, und danach nicht mehr.
    """
    return (_lies(KARTEN / f"{skript_id}.kuratiert.json")
            + _lies(KARTEN / f"{skript_id}.gen.json"))'''
assert alt_lade in ks, "lade()-Definition nicht gefunden"
ks = ks.replace(alt_lade, neu_lade)
kb.write_text(ks, encoding="utf-8")
ast.parse(ks)
print("kartenbrief.py geaendert")

# ── 5. Bestehende lesetexte.kuratiert.json leeren ────────────────────────
import json
lp = REPO / "jurabriefe/karten/lesetexte.kuratiert.json"
if lp.exists():
    lp.write_text(json.dumps({"karten": []}, ensure_ascii=False, indent=1), encoding="utf-8")
    print("lesetexte.kuratiert.json geleert")
else:
    print("lesetexte.kuratiert.json existiert nicht — gut so")
