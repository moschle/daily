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
NEU_PRO_TAG = 7
MAX_UNBEKANNT = 0.08       # Anteil unbekannter Wörter, ab dem neu geschrieben wird
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
    return any(k in K or k in FUNKTION for k in _kandidaten(t))


def _kandidaten(t: str) -> set[str]:
    kandidaten = {t, t.replace(ZWNJ, "")}
    # Vor dem Halbabstand steht der Stamm nur, wenn danach eine Endung folgt
    # (کتاب‌ها, خانه‌ای). Bei Komposita wie تاب‌آوری ist der erste Teil (تاب)
    # bekannt, das Wort aber nicht - so ist am 08.10.2026 "Resilienz" durchgerutscht.
    if ZWNJ in t:
        kopf, _, rest = t.partition(ZWNJ)
        if rest.replace(ZWNJ, "") in SUFFIXE:
            kandidaten.add(kopf)
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
    return kandidaten


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
    b1 = ("Das ist echtes B1, kein A2: zusammenhängender Text mit eigener Meinung oder kleiner "
          "Erzählung statt einer Aufzählung von Fakten. Pflicht: mindestens zwei Relativsätze mit که, "
          "mindestens ein Subjunktiv (باید/شاید/اگر + Subjunktiv), mindestens ein Nebensatz mit چون, "
          "وقتی oder با این که, Vergangenheit im Imperfekt (می‌رفتم) neben dem einfachen Präteritum. "
          "Mittellange Sätze. Klare, natürliche Sprache.")
    if n_bekannt_eintraege < 1500:
        return "B1", b1
    return "B1+", b1 + " Dazu Passiv und längere Satzgefüge; keine gehobene Schriftsprache."


# ─── Grammatik-Progression ──────────────────────────────────────────────
# Bis 29.10.2026 gab es nur drei Stufen nach Wortschatzgröße mit immer gleicher
# B1-Checkliste. Jetzt kommt wöchentlich ein Schwerpunkt dazu; frühere bleiben erlaubt.
GRAMMATIK = [
    ("Verlaufsform mit داشتن", "دارم می‌نویسم، داشت می‌رفت"),
    ("Perfekt und Plusquamperfekt", "رفته‌ام، رفته بودم"),
    ("realer Bedingungssatz", "اگر وقت داشته باشم، می‌آیم"),
    ("Passiv mit شدن", "ساخته شد، گفته می‌شود"),
    ("indirekte Rede", "گفت که فردا می‌آید"),
    ("irrealer Bedingungssatz", "اگر می‌دانستم، می‌گفتم"),
    ("Subjunktiv Perfekt", "شاید رفته باشد"),
    ("Infinitiv als Satzglied", "خواندن این کتاب آسان نیست"),
    ("Kausativ auf ‑اندن", "خنداندن، رساندن"),
    ("Temporalsätze mit پیش از آن که / بعد از آن که", "بعد از آن که رسید، زنگ زد"),
]
GRAMMATIK_START = date(2026, 10, 26)
_FOKUS = ""


def grammatik_fokus(heute: date | None = None):
    woche = max(0, ((heute or date.today()) - GRAMMATIK_START).days // 7) % len(GRAMMATIK)
    return GRAMMATIK[woche], [g[0] for g in GRAMMATIK[:woche]]


# ─── B1-Prüfung ───────────────────────────────────────────────────────────
# Die Stufe kam bisher nur aus der Größe des Wortschatzes. Am 11.10.2026 stand
# "B1" über einem reinen A2-Präsens-Text ("شهر من"). Jetzt wird der Text auf die
# B1-Pflichtmerkmale geprüft; fehlen sie, wird neu geschrieben bzw. ehrlich
# als A2+ ausgewiesen.
_ENDE = r"(?=[\s.،؛!؟:»)]|$)"
VERGANGENHEIT = re.compile(
    # Imperfekt: می‌ + Vergangenheitsstamm (+ Endung); می‌کند/می‌روند fallen nicht darunter
    r"(?:^|\s)(?:می‌|نمی‌)\S+?(?:[دت](?:م|ی|یم|ید|ند)|ت)" + _ENDE +
    # einfaches Präteritum häufiger Verben (nicht generisch: مردم ist ein Nomen)
    r"|(?:^|\s)(?:می‌|نمی‌|ن)?(?:بود|شد|رفت|آمد|کرد|داشت|گفت|دید|خورد|خواند|نوشت|زد|ماند|گذشت|خرید|پرسید|شنید|خواست|توانست|دانست|گرفت|ساخت|شناخت|نشست|آورد|داد|فهمید|زندگی کرد)(?:م|ی|یم|ید|ند)?" + _ENDE)
SUBJUNKTIV = re.compile(r"(?:^|\s)(?:باید|شاید|اگر|تا|می‌خواهم|می‌خواست|بهتر است)\s")


def b1_maengel(text: str) -> list[str]:
    t = re.sub(r"\([^)]*\)", " ", text or "")
    m = []
    if len(re.findall(r"(?:^|\s)که\s", t)) < 2:
        m.append("mindestens zwei Relativsätze mit که")
    if not SUBJUNKTIV.search(t):
        m.append("mindestens ein Subjunktiv (باید/شاید/اگر/تا + Subjunktiv)")
    if not VERGANGENHEIT.search(t):
        m.append("Erzählung in der Vergangenheit: einfaches Präteritum UND Imperfekt (می‌رفتم), kein reiner Präsens-Beschreibungstext")
    return m


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

ZIEL: Er soll den Text ohne Wörterbuch lesen können. Mindestens 92 % der Wörter müssen aus seinem bekannten Wortschatz stammen.

BEKANNTER WORTSCHATZ (Grundformen; Endungen, Plural, Ezafe und Konjugation sind erlaubt):
{bekannt_liste}

REGELN
- Stufe {stufe_txt}
- Thema: "{lang_ex['topic']}". 6–8 Sätze. Natürliches Persisch, wie es ein Iraner schreiben würde; keine Wörter nur um sie unterzubringen.
- Neben Funktionswörtern nur Wörter aus der Liste, dazu GENAU {NEU_PRO_TAG} neue Wörter. Die neuen Wörter sollen häufig und nützlich sein und zum Thema passen.
- Jedes neue Wort beim ersten Vorkommen direkt hinter der VOLLSTÄNDIGEN Wortform (mit Plural- und Personalendungen) glossieren: سلاح‌ها (Waffen), nie سلاح (Waffe) ها. Sonst keine Glossen.
- Zusammengesetzte Verben und feste Verbverbindungen (ارتباط برقرار کردن، لذت بردن، به نمایش گذاشتن، از سر گرفتن) sind eigene Vokabeln, auch wenn die Einzelteile bekannt sind: Glosse hinter der vollständigen Verbform, Infinitiv des ganzen Gefüges in "neue_vokabeln".
- Ohne Kurzvokalzeichen im Fließtext, aber normale Rechtschreibung: Madde (آب, آمد, می‌آورد, آلودگی), Hamze und Halbabstand (ZWNJ) immer setzen.
- Lieber ein schlichter Satz als ein seltenes, gehobenes oder unpassendes Wort. Keine Füllsätze, keine schiefen Aussagen, keine Substantivierungen, die kein Iraner so sagen würde (z. B. nicht „غمگینی می‌آورد“).
{wh}- Danach 2–3 Verständnisfragen auf Deutsch.
- Nachricht: in 3–4 einfachen Sätzen auf Persisch nacherzählen, ebenfalls fast nur mit bekannten Wörtern; höchstens 2 weitere neue Wörter, genauso glossiert. NUR Inhalte aus Schlagzeile und Meldungstext unten, nichts hinzufügen. Die Quelle bleibt erhalten: Wenn Medien oder eine Person etwas berichten oder behaupten, schreib das so (رسانه‌های آمریکا گزارش می‌دهند …), nicht als Tatsache und nicht als Aussage eines Staates. Aus „bereitet sich vor“ wird nicht „will“. Jeder Satz trägt eine Information aus der Meldung; keine Füllsätze wie „این خبر امروز آمد“ oder „مردم این خبر را می‌شنوند“.
- Glossiere NUR die neuen Wörter. Wörter aus der Wortschatzliste bekommen keine Klammer.
- Eigennamen (Personen, Orte, Länder, Organisationen) sind keine Vokabeln: nicht glossieren, nicht in "neue_vokabeln".
{nachricht}{feedback}
Antworte NUR mit JSON, ohne Markdown:
{{"titel": "persischer Titel",
  "text": "Übungstext mit Glossen",
  "fragen": ["...", "..."],
  "nachricht": "Nacherzählung auf Persisch oder leer",
  "neue_vokabeln": [{{"fa": "Wort mit Kurzvokalzeichen", "de": "knappe deutsche Bedeutung, ohne persische Schrift"}}]}}
In "neue_vokabeln" stehen ALLE glossierten Wörter aus Text und Nachricht (Verben als Infinitiv, Nomen im Singular) und jedes weitere Wort, das nicht in der Wortschatzliste steht."""


def _lektorat(d: dict, K: set[str], quote: float, complete, stufe_name: str = "B1") -> dict:
    """Zweiter Durchgang: ein iranischer Lektor glättet Text und Nacherzählung."""
    p = f"""Du bist Lektor für Persisch (Muttersprachler, Teheran). Unten steht eine Leseübung für einen Lerner auf Stufe {stufe_name}.
Vereinfache die Grammatik NICHT: Relativsätze, Subjunktiv, Vergangenheitsformen{(' und der Wochenschwerpunkt ' + _FOKUS) if _FOKUS else ''} bleiben erhalten.
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
        if stufe_name.startswith("B1") and len(b1_maengel(neu["text"])) > len(b1_maengel(d.get("text", ""))):
            return d                   # Lektorat hat B1-Merkmale weggeglättet
        return {**d, **{k: neu[k] for k in ("titel", "text", "nachricht", "neue_vokabeln") if neu.get(k) is not None}}
    except Exception:
        return d


def _glossen_nachtragen(woerter, complete) -> list[tuple[str, str]]:
    """Unbekannte, nicht deklarierte Wörter nachträglich übersetzen lassen."""
    if not woerter:
        return []
    p = ("Gib für jedes dieser persischen Wörter die Grundform (Verben als Infinitiv, Nomen im Singular) "
         "mit Kurzvokalzeichen und eine knappe deutsche Bedeutung. Eigennamen (Personen, Orte, Länder) weglassen. Antworte NUR mit JSON: "
         '[{"fa": "...", "de": "..."}]\n' + "\n".join(woerter))
    try:
        roh = complete(p, max_tokens=800).strip()
        roh = re.sub(r"^```(?:json)?|```$", "", roh, flags=re.M).strip()
        liste = json.loads(roh[roh.find("["): roh.rfind("]") + 1])
        return [((v.get("fa") or "").strip(), (v.get("de") or "").strip()) for v in liste]
    except Exception:
        return []


# Eigennamen gehoeren nicht ins Deck (09.10.: Putin, Wladimir, Masoud, Peseschkian).
NAME = re.compile(r"eigenname|\bname\b|präsident|minister|politiker|hauptstadt|\((stadt|land|ort)\b", re.I)


GLOSSE = re.compile(r"([\u0600-\u06FF\u200c]+)\s*\(([^)]*[A-Za-zÄÖÜäöüß][^)]*)\)")


def _glossen_bereinigen(d: dict, K: set[str]) -> dict:
    """Klammern hinter bekannten Woertern entfernen (08.10.: آسمان (Himmel), ابر (Wolke)).

    Glossiert bleibt nur, was in neue_vokabeln steht oder nicht im Wortschatz ist."""
    neu = {w for v in d.get("neue_vokabeln", []) for w in _formen(v.get("fa", ""))}

    def ersetze(m):
        wort = m.group(1)
        if ist_bekannt(wort, K) and not ist_bekannt(wort, neu):
            return wort
        return m.group(0)

    for feld in ("text", "nachricht"):
        if d.get(feld):
            d[feld] = GLOSSE.sub(ersetze, d[feld])
    return d


def _ganz(eintrag: str) -> set[str]:
    """Ganze Deck-Einträge normalisiert, damit Verbgefüge als Einheit geprüft werden."""
    e = norm(re.sub(r"\(.*?\)", " ", eintrag)).replace(ZWNJ, " ")
    out = {" ".join(t.split()) for t in re.split(r"[/،,؛;]", e) if t.strip()}
    # "لذت بردن از" und "لذت بردن" sind dasselbe Gefüge
    return out | {re.sub(r" (?:از|به|با|را)$", "", x) for x in out}


WORT = re.compile(r"[\u0600-\u06FF\u200c]+")


def _glossieren(text: str, glossen) -> str:
    """Jedes nicht gelernte Wort bzw. Verbgefüge beim ersten Vorkommen glossieren."""
    for fa, de, form in glossen:
        ende = None
        if form:
            muster = r"\s*(?:\([^)]*\)\s*)?".join(re.escape(t) for t in form.split())
            m = re.search(muster, text)
            ende = m.end() if m else None
        else:
            ziel = _formen(fa)
            for m in WORT.finditer(text):
                t = norm(m.group())
                if len(t) > 1 and t not in FUNKTION and (t in ziel or _kandidaten(t) & ziel):
                    ende = m.end()
                    break
        if ende is None or re.match(r"\s*\(", text[ende:]):
            continue
        text = f"{text[:ende]} ({de}){text[ende:]}"
    return text


def _annotieren(text: str, woerter, complete):
    """Bedeutungen für unbekannte Wörter und alle Verbgefüge im Text."""
    p = ("Persischer Lesetext unten.\n"
         "1. Gib für jedes Wort der Liste die Grundform (Verben als Infinitiv, Nomen im Singular) mit "
         "Kurzvokalzeichen und eine knappe deutsche Bedeutung. Eigennamen weglassen.\n"
         "2. Finde ALLE zusammengesetzten Verben und festen Verbverbindungen im Text (Nomen, Adjektiv oder "
         "Präpositionalgruppe + کردن، شدن، دادن، گرفتن، بردن، زدن، داشتن، گذاشتن، آمدن، کشیدن usw.; "
         "z. B. ارتباط برقرار کردن، لذت بردن، به نمایش گذاشتن، از سر گرفتن). Für jedes: \"form\" = die "
         "Wortfolge exakt wie im Text, vom ersten bis zum letzten Bestandteil; \"fa\" = Infinitiv des "
         "Gefüges mit Kurzvokalzeichen; \"de\" = deutsche Bedeutung des Ganzen.\n"
         'Antworte NUR mit JSON: {"woerter": [{"fa": "", "de": ""}], "verben": [{"form": "", "fa": "", "de": ""}]}\n\n'
         "WÖRTER:\n" + ("\n".join(woerter) or "-") + "\n\nTEXT:\n" + text)
    try:
        d = _json(complete(p, max_tokens=1500))
    except Exception:
        return [], []
    w = [((x.get("fa") or "").strip(), (x.get("de") or "").strip()) for x in d.get("woerter", [])]
    v = [((x.get("form") or "").strip(), (x.get("fa") or "").strip(), (x.get("de") or "").strip())
         for x in d.get("verben", [])]
    return w, v


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
    global _FOKUS
    _FOKUS = ""
    if stufe_name.startswith("B1"):
        (fokus, bsp), vorher = grammatik_fokus()
        _FOKUS = fokus
        stufe_txt += (f" GRAMMATIKSCHWERPUNKT DIESER WOCHE: {fokus} (z. B. {bsp}); mindestens zweimal, "
                      f"natürlich eingebettet.")
        if vorher:
            stufe_txt += " Bereits eingeführt, gern wiederholen: " + ", ".join(vorher) + "."
    # Die Liste fuer das Modell in echter Schreibung (nur ohne Kurzvokale). norm()
    # tilgt auch das Madde; mit dieser Liste vor Augen schrieb das Modell dann
    # اسمان, امده, افتابی statt آسمان, آمده, آفتابی.
    anzeige_eintraege = []
    if BEKANNT_FILE.exists():
        anzeige_eintraege = [HAR.sub("", e["word"]).strip()
                             for e in json.loads(BEKANNT_FILE.read_text(encoding="utf-8"))
                             if e.get("gelernt", True)]
    anzeige_eintraege += [HAR.sub("", v["word"]).strip() for v in mem.get("fa", [])]
    bekannt_liste = ", ".join(dict.fromkeys(anzeige_eintraege))
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
        maengel = b1_maengel(d.get("text", "")) if stufe_name.startswith("B1") else []
        wert = quote + 0.05 * len(maengel)
        if bestes is None or wert < bestes[2]:
            bestes = (quote, d, wert)
        if quote <= MAX_UNBEKANNT and not maengel:
            break
        feedback = ""
        if quote > MAX_UNBEKANNT:
            feedback += ("\nDER LETZTE ENTWURF WAR ZU SCHWER. Diese Wörter kennt er nicht und sie waren nicht "
                         "als neu markiert. Ersetze sie durch Wörter aus der Liste oder einfache Umschreibungen:\n"
                         + ", ".join(fremd[:40]) + "\n")
        if maengel:
            feedback += ("\nDER LETZTE ENTWURF WAR NUR A2, NICHT B1. Es fehlte: " + "; ".join(maengel)
                         + ". Schreib eine kleine Erzählung in der Vergangenheit zum Thema, nicht eine Beschreibung im Präsens.\n")
    if bestes is None:
        raise RuntimeError("Leseübung konnte nicht erzeugt werden")

    quote, d, _ = bestes
    d = _lektorat(d, K, quote, complete, stufe_name)
    # Maßstab für Glossen ist allein das Gelernte im Anki-Deck. Bis 29.10.2026 galten
    # Morgenbrief-Wörter 60 Tage als bekannt und verloren ihre Klammer, obwohl die
    # Karte nie gelernt war (مختلف، روزانه، پیشرفت ohne Glosse im Text).
    deck, gelernt, ganz_deck, ganz_gelernt, bedeutung = set(), set(), set(), set(), {}
    if BEKANNT_FILE.exists():
        for e in json.loads(BEKANNT_FILE.read_text(encoding="utf-8")):
            f, g = _formen(e.get("word", "")), _ganz(e.get("word", ""))
            deck |= f
            ganz_deck |= g
            if e.get("gelernt", True):
                gelernt |= f
                ganz_gelernt |= g
            else:
                for w in f:
                    bedeutung.setdefault(w, (e["word"], e.get("meaning", "")))
    d = _glossen_bereinigen(d, gelernt)
    if stufe_name.startswith("B1") and b1_maengel(d.get("text", "")):
        stufe_name = "A2+ (Ziel B1 verfehlt)"   # Label nicht schönen
    liste = [((v.get("fa") or "").strip(), (v.get("de") or "").strip(), "") for v in d.get("neue_vokabeln", [])]
    liste = [x for x in liste if x[0] and x[1] and not NAME.search(x[1])]
    alles = d.get("text", "") + " " + d.get("nachricht", "")
    _, rest = pruefe(alles, gelernt | {w for fa, _, _ in liste for w in _formen(fa)})
    wiederholt, offen = set(), []
    for tok in rest:
        v = next((v for v in mem.get("fa", []) if ist_bekannt(tok, _formen(v["word"]))), None)
        if v:
            liste.append((v["word"], v.get("meaning", ""), ""))
            wiederholt.add(norm(v["word"]))
            continue
        b = next((bedeutung[w] for w in bedeutung if ist_bekannt(tok, {w})), None)
        if b:
            liste.append((b[0], b[1], ""))
        else:
            offen.append(tok)
    woerter, verben = _annotieren(re.sub(r"\([^)]*\)", " ", alles), offen, complete)
    liste += [(fa, de, "") for fa, de in woerter if fa and de and not NAME.search(de)]
    for form, fa, de in verben:
        if form and fa and de and _ganz(fa) and not (_ganz(fa) & ganz_gelernt):
            liste.append((fa, de, form))
    liste.sort(key=lambda x: not x[2])   # Verbgefüge vor Einzelwörtern
    gefuege_teile = {w for fa, _, form in liste if form for w in min(_ganz(fa), key=len).split()[:-1]}
    gesehen, anzeige, neue, glossen = set(), [], [], []
    for fa, de, form in liste:
        n = norm(fa)
        varianten = _ganz(fa) | {n}
        if varianten & gesehen or (not form and n in gefuege_teile):
            continue
        gesehen |= varianten
        if form:
            im_deck, ist_gelernt = bool(_ganz(fa) & ganz_deck), False
        else:
            f = _formen(fa)
            im_deck, ist_gelernt = bool(f) and f <= deck, bool(f) and f <= gelernt
        if ist_gelernt:
            continue
        glossen.append((fa, de, form))
        if im_deck:
            anzeige.append(f"{fa} – {de} (schon im Deck, noch nicht gelernt)")
            continue
        zusatz = " (Wiederholung, bisher ohne Anki-Karte)" if n in wiederholt else ""
        anzeige.append(f"{fa} – {de}" + zusatz)
        neue.append((fa, de))
    for feld in ("text", "nachricht"):
        if d.get(feld):
            d[feld] = _glossieren(d[feld], glossen)
    fragen = "\n".join(f"{i}. {q}" for i, q in enumerate(d.get("fragen", []), 1))
    woerter = "\n".join(anzeige) or "–"
    abschnitt = (
        f"SPRACHÜBUNG - TEXT\n{d.get('titel', '')}\n\n{d.get('text', '')}\n\n"
        f"NEUE WÖRTER (Stufe {stufe_name}{', Grammatik: ' + _FOKUS if _FOKUS else ''}, {round((1 - quote) * 100)} % bekannt; Anki-Paket im Anhang)\n{woerter}\n\n"
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
        ],
        # Gleiche MODELL_ID wie der Notiztyp im Deck: ohne css ersetzt der Import
        # dessen Styling durch genankis Vorgabe ohne Zentrierung (09.10.2026).
        css=".card {\n font-family: arial;\n font-size: 20px;\n text-align: center;\n"
            " color: black;\n background-color: white;\n}\n")
    deck = genanki.Deck(DECK_ID, "Persisch")
    tag = date.today().isoformat()
    for fa, de in neue:
        deck.add_note(genanki.Note(model=modell, fields=[fa, de],
                                   guid=genanki.guid_for("morgenbrief-fa", norm(fa)),
                                   tags=["morgenbrief", f"mb_{tag}"]))
    pfad = ziel_dir / f"persisch_morgenbrief_{tag}.apkg"
    genanki.Package(deck).write_to_file(str(pfad))
    return pfad
