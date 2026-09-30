"""Persisch-Leseübung für den Morgenbrief, aufgebaut auf dem eigenen Wortschatz.

- Bekannt sind die Anki-Karten, die schon einmal richtig beantwortet wurden
  (bekannt_fa.json, erzeugt mit bekannt_aktualisieren.py), dazu die Wörter,
  die der Morgenbrief in den letzten 60 Tagen eingeführt hat.
- Pro Tag höchstens NEU_PRO_TAG neue Wörter, alle glossiert.
- Nach dem Schreiben wird der Text gegen den Wortschatz geprüft; zu viele
  unbekannte Wörter -> neu schreiben lassen (mit Liste der Problemwörter).
- Die neuen Wörter kommen als .apkg für das Deck "Persisch" mit.
"""
from __future__ import annotations

import json
import re
from datetime import date, datetime
from pathlib import Path

HERE = Path(__file__).parent
BEKANNT_FILE = HERE / "bekannt_fa.json"
NEU_PRO_TAG = 5
MAX_UNBEKANNT = 0.05       # Anteil unbekannter Wörter, ab dem neu geschrieben wird
VERSUCHE = 3

# Notiztyp und Deck aus der eigenen Sammlung (IDs unverändert übernehmen,
# damit der Import in das bestehende Deck und den bestehenden Notiztyp geht)
MODELL_ID = 1697886913420
DECK_ID = 1786007267462

HAR = re.compile("[\u064B-\u0652\u0670\u0640]")
ZWNJ = "\u200c"
FUNKTION = set("""و در به از که این آن را با برای تا هم یا اما ولی است هست نیست بود
نبود شد می من تو او ما شما آنها ایشان یک چه چی چرا کجا کی هر همه خیلی بسیار نه بله
اگر وقتی چون پس بعد قبل روی زیر بین هیچ دیگر خود همین همان آیا ای ها های""".split())
PRAEFIX = ("نمی", "می", "ن", "ب")
SUFFIXE = sorted("""هایشان هایتان هایمان هایش هایت هایم های ها ترین تر یشان یتان یمان
شان تان مان ایم اید اند ام ات اش یم ید ند ای ی م ت ش د ه ن""".split(), key=len, reverse=True)


def norm(s: str) -> str:
    s = HAR.sub("", s).replace("ي", "ی").replace("ك", "ک").replace("أ", "ا").replace("آ", "ا")
    return s.strip()


# ─── Wortschatz ────────────────────────────────────────────────────────────
def _formen(eintrag: str) -> set[str]:
    """Aus einem Deck-Eintrag die Wortformen gewinnen, die als bekannt gelten."""
    out = set()
    eintrag = norm(re.sub(r"\(.*?\)", " ", eintrag))
    for teil in re.split(r"[/،,؛;↔…\.\?!؟]", eintrag):
        for w in teil.replace(ZWNJ, " ").split():
            if not re.search("[\u0600-\u06FF]", w):
                continue
            out.add(w)
            if w.endswith("ن") and len(w) > 3:      # Infinitiv -> Vergangenheitsstamm
                out.add(w[:-1])
                if w.endswith("یدن"):
                    out.add(w[:-3])                   # -idan -> Präsensstamm
    return out


def wortschatz(memory: dict) -> tuple[set[str], set[str]]:
    """(bekannt für die Lesbarkeit, alle Deck-Wörter für Dubletten)"""
    bekannt, alle = set(), set()
    if BEKANNT_FILE.exists():
        for e in json.loads(BEKANNT_FILE.read_text(encoding="utf-8")):
            f = _formen(e.get("word", ""))
            alle |= f
            if e.get("gelernt", True):
                bekannt |= f
    heute = date.today()
    for v in memory.get("fa", []):
        try:
            tage = (heute - datetime.fromisoformat(v["first_seen"]).date()).days
        except Exception:
            tage = 0
        if tage <= 60:
            bekannt |= _formen(v["word"])
        alle |= _formen(v["word"])
    return bekannt, alle


def ist_bekannt(tok: str, K: set[str]) -> bool:
    t = norm(tok)
    if not t or t in FUNKTION or t in K:
        return True
    kandidaten = {t, t.replace(ZWNJ, ""), t.split(ZWNJ)[0]}
    for k in list(kandidaten):
        for p in PRAEFIX:
            if k.startswith(p) and len(k) - len(p) >= 2:
                kandidaten.add(k[len(p):].lstrip(ZWNJ))
    for k in list(kandidaten):
        rest = k
        for _ in range(2):
            for s in SUFFIXE:
                if rest.endswith(s) and len(rest) - len(s) >= 2:
                    rest = rest[: -len(s)].rstrip(ZWNJ)
                    kandidaten.add(rest)
                    break
    return any(k in K or k in FUNKTION for k in kandidaten)


def pruefe(text: str, K: set[str]) -> tuple[float, list[str]]:
    ohne_glossen = re.sub(r"\([^)]*\)", " ", text)
    toks = [t for t in re.findall(r"[\u0600-\u06FF\u200c]+", ohne_glossen) if len(norm(t)) > 1]
    if not toks:
        return 1.0, []
    unbekannt = [t for t in toks if not ist_bekannt(t, K)]
    return len(unbekannt) / len(toks), sorted(set(unbekannt))


# ─── Stufe aus dem Wortschatz statt aus dem Kalender ──────────────────────
def stufe(n_bekannt_eintraege: int) -> tuple[str, str]:
    if n_bekannt_eintraege < 800:
        return "A2+", ("Kurze Hauptsätze, höchstens ein einfacher Nebensatz pro Satz. "
                       "Präsens, einfache Vergangenheit, Perfekt. Alltagsnahe Sätze.")
    if n_bekannt_eintraege < 1500:
        return "B1", "Mittellange Sätze, Relativsätze und Konjunktiv erlaubt. Klare, natürliche Sprache."
    return "B1+", "Auch längere Sätze und Passiv; weiterhin natürliche, keine gehobene Schriftsprache."


# ─── Claude-Aufruf ────────────────────────────────────────────────────────
def _prompt(lang_ex, bekannt_liste, stufe_txt, due, feedback):
    wh = ""
    if due:
        wh = ("Diese Wörter hat er in den letzten Tagen neu gelernt. Verwende davon zwei bis vier, "
              "aber nur, wo sie natürlich passen, und nicht glossieren:\n"
              + ", ".join(v["word"] for v in due[:10]) + "\n")
    nachricht = ""
    if lang_ex.get("headline"):
        nachricht = (f"\nNACHRICHT (BBC Persian) zum Nacherzählen:\nSchlagzeile: {lang_ex['headline']}\n"
                     f"{(lang_ex.get('news_text') or '')[:900]}\n")
    return f"""Du schreibst eine persische Leseübung (Farsi, Standardsprache, kein Slang) für einen deutschen Lerner.

ZIEL: Er soll den Text ohne Wörterbuch lesen können. Mindestens 95 % der Wörter müssen aus seinem bekannten Wortschatz stammen.

BEKANNTER WORTSCHATZ (Grundformen; Endungen, Plural, Ezafe und Konjugation sind erlaubt):
{bekannt_liste}

REGELN
- Stufe {stufe_txt}
- Thema: "{lang_ex['topic']}". 6–8 Sätze. Natürliches Persisch, wie es ein Iraner schreiben würde; keine Wörter nur um sie unterzubringen.
- Neben Funktionswörtern nur Wörter aus der Liste, dazu GENAU {NEU_PRO_TAG} neue Wörter. Die neuen Wörter sollen häufig und nützlich sein und zum Thema passen.
- Jedes neue Wort beim ersten Vorkommen direkt hinter der VOLLSTÄNDIGEN Wortform (mit Plural- und Personalendungen) glossieren: سلاح‌ها (Waffen), nie سلاح (Waffe) ها. Sonst keine Glossen.
- Ohne Kurzvokalzeichen im Fließtext, aber normale Rechtschreibung: Madde (آب, آمد, می‌آورد, آلودگی), Hamze und Halbabstand (ZWNJ) immer setzen.
- Lieber ein schlichter Satz als ein seltenes, gehobenes oder unpassendes Wort. Keine Füllsätze, keine schiefen Aussagen, keine Substantivierungen, die kein Iraner so sagen würde (z. B. nicht „غمگینی می‌آورد“).
{wh}- Danach 2–3 Verständnisfragen auf Deutsch.
- Nachricht: in 3–4 einfachen Sätzen auf Persisch nacherzählen, ebenfalls fast nur mit bekannten Wörtern; höchstens 2 weitere neue Wörter, genauso glossiert. NUR Inhalte aus Schlagzeile und Meldungstext unten, nichts hinzufügen, keine Sätze wie „این خبر امروز آمد“.
{nachricht}{feedback}
Antworte NUR mit JSON, ohne Markdown:
{{"titel": "persischer Titel",
  "text": "Übungstext mit Glossen",
  "fragen": ["...", "..."],
  "nachricht": "Nacherzählung auf Persisch oder leer",
  "neue_vokabeln": [{{"fa": "Wort mit Kurzvokalzeichen", "de": "knappe deutsche Bedeutung, ohne persische Schrift"}}]}}
In "neue_vokabeln" stehen ALLE glossierten Wörter aus Text und Nachricht (Verben als Infinitiv, Nomen im Singular) und jedes weitere Wort, das nicht in der Wortschatzliste steht."""


def _lektorat(d: dict, K: set[str], quote: float, complete) -> dict:
    """Zweiter Durchgang: ein iranischer Lektor glättet Text und Nacherzählung."""
    p = f"""Du bist Lektor für Persisch (Muttersprachler, Teheran). Unten steht eine Leseübung für einen Lerner auf Stufe A2/B1.
Überarbeite Text und Nacherzählung so, dass sie klingen, wie ein gebildeter Iraner einfach und natürlich schreibt.
- Korrigiere schiefe Aussagen, unidiomatische Wendungen, falsche Kollokationen, Füllsätze und Rechtschreibung (Madde, Hamze, Halbabstand).
- Behalte Inhalt, Satzzahl und Schwierigkeit bei. Ersetze kein einfaches Wort durch ein schwierigeres; neue Wörter nur, wenn es wirklich nicht anders geht.
- Glossen in Klammern bleiben erhalten und stehen hinter der vollständigen Wortform. Wird ein glossiertes Wort ersetzt, passe die Glosse an.
- Die Nacherzählung darf nichts enthalten, was nicht in der Meldung steht.
Antworte NUR mit JSON im selben Format, Felder "titel", "text", "nachricht", "neue_vokabeln" (alle glossierten Wörter mit Kurzvokalen und deutscher Bedeutung).

{json.dumps({k: d.get(k) for k in ("titel", "text", "nachricht", "neue_vokabeln")}, ensure_ascii=False)}"""
    try:
        neu = _json(complete(p, max_tokens=2500))
        if not neu.get("text"):
            return d
        formen = {w for v in neu.get("neue_vokabeln", []) for w in _formen(v.get("fa", ""))}
        q2, _ = pruefe(neu.get("text", "") + " " + neu.get("nachricht", ""), K | formen)
        if q2 > quote + 0.03:          # Lektorat hat den Text deutlich schwerer gemacht
            return d
        return {**d, **{k: neu[k] for k in ("titel", "text", "nachricht", "neue_vokabeln") if neu.get(k) is not None}}
    except Exception:
        return d


def _glossen_nachtragen(woerter, complete) -> list[tuple[str, str]]:
    """Unbekannte, nicht deklarierte Wörter nachträglich übersetzen lassen."""
    if not woerter:
        return []
    p = ("Gib für jedes dieser persischen Wörter die Grundform (Verben als Infinitiv, Nomen im Singular) "
         "mit Kurzvokalzeichen und eine knappe deutsche Bedeutung. Antworte NUR mit JSON: "
         '[{"fa": "...", "de": "..."}]\n' + "\n".join(woerter))
    try:
        roh = complete(p, max_tokens=800).strip()
        roh = re.sub(r"^```(?:json)?|```$", "", roh, flags=re.M).strip()
        liste = json.loads(roh[roh.find("["): roh.rfind("]") + 1])
        return [((v.get("fa") or "").strip(), (v.get("de") or "").strip()) for v in liste]
    except Exception:
        return []


def _json(roh: str) -> dict:
    roh = roh.strip()
    roh = re.sub(r"^```(?:json)?|```$", "", roh, flags=re.M).strip()
    start, ende = roh.find("{"), roh.rfind("}")
    return json.loads(roh[start: ende + 1])


def erzeuge(lang_ex: dict, complete) -> dict:
    """Liefert {'abschnitt': Text für den Brief, 'neue': [(fa, de)], 'quote': float}."""
    mem = lang_ex.get("memory") or {}
    K, alle = wortschatz(mem)
    eintraege = []
    if BEKANNT_FILE.exists():
        eintraege = [norm(e["word"]) for e in json.loads(BEKANNT_FILE.read_text(encoding="utf-8"))
                     if e.get("gelernt", True)]
    eintraege += [norm(v["word"]) for v in mem.get("fa", [])]
    stufe_name, stufe_txt = stufe(len(eintraege))
    bekannt_liste = ", ".join(dict.fromkeys(eintraege))
    due = lang_ex.get("due_vocab") or []

    bestes, feedback = None, ""
    for _ in range(VERSUCHE):
        try:
            d = _json(complete(_prompt(lang_ex, bekannt_liste, f"{stufe_name}: {stufe_txt}", due, feedback),
                               max_tokens=2500))
        except Exception as e:
            feedback = f"\nACHTUNG: Die letzte Antwort war kein gültiges JSON ({e}).\n"
            continue
        neu = {w for v in d.get("neue_vokabeln", []) for w in _formen(v.get("fa", ""))}
        quote, fremd = pruefe(d.get("text", "") + " " + d.get("nachricht", ""), K | neu)
        if bestes is None or quote < bestes[0]:
            bestes = (quote, d)
        if quote <= MAX_UNBEKANNT:
            break
        feedback = ("\nDER LETZTE ENTWURF WAR ZU SCHWER. Diese Wörter kennt er nicht und sie waren nicht "
                    "als neu markiert. Ersetze sie durch Wörter aus der Liste oder einfache Umschreibungen:\n"
                    + ", ".join(fremd[:40]) + "\n")
    if bestes is None:
        raise RuntimeError("Leseübung konnte nicht erzeugt werden")

    quote, d = bestes
    d = _lektorat(d, K, quote, complete)
    liste = [((v.get("fa") or "").strip(), (v.get("de") or "").strip()) for v in d.get("neue_vokabeln", [])]
    liste = [(fa, de) for fa, de in liste if fa and de]
    # Was jetzt noch unbekannt ist, wurde weder ersetzt noch deklariert -> nachtragen
    neu_formen = {w for fa, _ in liste for w in _formen(fa)}
    _, rest = pruefe(d.get("text", "") + " " + d.get("nachricht", ""), K | neu_formen)
    liste += [(fa, de) for fa, de in _glossen_nachtragen(rest, complete) if fa and de]
    # Brief: alle Wörter; Anki: nur, was noch nicht vollständig im Deck steht
    gesehen, anzeige, neue = set(), [], []
    for fa, de in liste:
        if norm(fa) in gesehen:
            continue
        gesehen.add(norm(fa))
        im_deck = bool(_formen(fa)) and _formen(fa) <= alle
        anzeige.append(f"{fa} – {de}" + (" (schon im Deck)" if im_deck else ""))
        if not im_deck:
            neue.append((fa, de))
    fragen = "\n".join(f"{i}. {q}" for i, q in enumerate(d.get("fragen", []), 1))
    woerter = "\n".join(anzeige) or "–"
    abschnitt = (
        f"SPRACHÜBUNG - TEXT\n{d.get('titel', '')}\n\n{d.get('text', '')}\n\n"
        f"NEUE WÖRTER (Stufe {stufe_name}, {round((1 - quote) * 100)} % bekannt; Anki-Paket im Anhang)\n{woerter}\n\n"
        f"SPRACHÜBUNG - FRAGEN\n{fragen}\n\n"
        f"NACHRICHTEN\n{lang_ex.get('headline') or ''}\n\n{d.get('nachricht', '')}\n"
    )
    return {"abschnitt": abschnitt, "neue": neue, "quote": quote}


# ─── Anki-Paket ───────────────────────────────────────────────────────────
def anki_paket(neue: list[tuple[str, str]], ziel_dir: Path) -> Path | None:
    if not neue:
        return None
    import genanki
    modell = genanki.Model(
        MODELL_ID, "Einfach (beide Richtungen)",
        fields=[{"name": "Vorderseite"}, {"name": "Rückseite"}],
        templates=[
            {"name": "Karte 1", "qfmt": "{{Vorderseite}}",
             "afmt": "{{FrontSide}}\n\n<hr id=answer>\n\n{{Rückseite}}"},
            {"name": "Karte 2", "qfmt": "{{Rückseite}}",
             "afmt": "{{FrontSide}}\n\n<hr id=answer>\n\n{{Vorderseite}}"},
        ])
    deck = genanki.Deck(DECK_ID, "Persisch")
    tag = date.today().isoformat()
    for fa, de in neue:
        deck.add_note(genanki.Note(model=modell, fields=[fa, de],
                                   guid=genanki.guid_for("morgenbrief-fa", norm(fa)),
                                   tags=["morgenbrief", f"mb_{tag}"]))
    pfad = ziel_dir / f"persisch_morgenbrief_{tag}.apkg"
    genanki.Package(deck).write_to_file(str(pfad))
    return pfad
