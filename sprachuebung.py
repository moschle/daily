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
GANZ_NEU_MAX = 2          # davon höchstens so viele, die noch gar nicht im Deck stehen
RUECKSTAND_ANGEBOT = 60   # ungelernte Deck-Karten, die dem Modell angeboten werden
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


# ─── Stufen nach dem Gemeinsamen Europäischen Referenzrahmen ───────────────
# Die Stufe richtet sich nach der Zahl gelernter Notizen (Anki + Morgenbrief-Gedächtnis).
# Schwellen sind Richtwerte für Wortschatzgrößen je GER-Stufe; seit 29.10.2026 bis C2.
STUFEN = [  # (ab Notizen, Name, Beschreibung nach GER)
    (0, "A2+",
     "Kurze Hauptsätze, höchstens ein einfacher Nebensatz pro Satz. Präsens, einfache Vergangenheit, "
     "Perfekt. Alltagsnahe, konkrete Sätze über unmittelbare Bedürfnisse und vertraute Situationen."),
    (800, "B1",
     "Echtes B1, kein A2: zusammenhängender Text über vertraute Themen, eine kleine Erzählung oder eine "
     "begründete Meinung statt einer Aufzählung von Fakten. Pflicht: mindestens zwei Relativsätze mit که, "
     "mindestens ein Subjunktiv (باید/شاید/اگر + Subjunktiv), mindestens ein Nebensatz mit چون, وقتی oder "
     "با این که, Imperfekt (می‌رفتم) neben dem einfachen Präteritum. Mittellange Sätze, klare Sprache."),
    (1500, "B1+",
     "Oberes B1: wie B1, dazu längere Satzgefüge, Vergleich zweier Standpunkte, Ursache und Folge. "
     "Noch keine gehobene Schriftsprache."),
    (2500, "B2",
     "B2: Text zu konkreten und abstrakten Themen wie in einem Zeitungsartikel oder Kommentar, mit klarer "
     "Argumentation (Vor- und Nachteile, Gegenargument, Schluss). Standardschriftsprache, auch Passiv und "
     "Konzessivsätze, verschiedene Konnektoren (اما، با این حال، از طرف دیگر، در نتیجه). Längere, "
     "gut gegliederte Sätze; Fachwörter des Themas sind erlaubt."),
    (4000, "C1",
     "C1: anspruchsvoller Sachtext, Essay oder Rezension mit impliziten Bedeutungen und Abwägung. "
     "Gehobene Schriftsprache (رسمی/ادبی): Nominalstil, Verbalnomen, Partizipialkonstruktionen, gehobene "
     "Konnektoren (حال آنکه، از آنجا که، چنانچه، مگر آنکه), arabische Plurale und Masdar-Formen. "
     "Präzise, stilistisch variiert, aber nicht künstlich."),
    (6500, "C2",
     "C2: Text wie von einem gebildeten iranischen Autor: Kolumne, literarische Prosa oder Essay mit "
     "feinen Bedeutungsnuancen, Ironie, Redewendungen und Sprichwörtern, Wechsel der Register. Klassische "
     "und literarische Formen dürfen vorkommen (به‌ + Präteritum, همی، چو، ز، دگر), sparsam und korrekt."),
]


def stufe(n_bekannt_eintraege: int) -> tuple[str, str]:
    name, txt = STUFEN[0][1:]
    for ab, n, t in STUFEN:
        if n_bekannt_eintraege >= ab:
            name, txt = n, t
    return name, txt


def ab_b1(stufe_name: str) -> bool:
    return stufe_name.split()[0] in ("B1", "B1+", "B2", "C1", "C2")


# ─── Themen nach GER-Stufe (Lebensbereiche und Textsorten) ─────────────────
THEMEN = {
    "A2": ["Tagesablauf", "Einkaufen auf dem Markt", "meine Wohnung", "Familie und Freunde", "Essen und Kochen",
           "Wetter und Jahreszeiten", "Freizeit am Wochenende", "Weg zur Arbeit", "Arzttermin", "Geburtstag"],
    "B1": ["eine Reise, die anders lief als geplant", "ein Erlebnis bei der Arbeit", "Pläne für das nächste Jahr",
           "ein Buch oder Film, der mir gefallen hat", "Gesundheit und Sport im Alltag", "Musik und Kunst in meinem Leben",
           "Leben in der Stadt oder auf dem Land", "ein Missverständnis unter Freunden", "Feste und Bräuche",
           "Erinnerung an die Schulzeit", "Wohnungssuche", "ein Ehrenamt"],
    "B2": ["Vor- und Nachteile sozialer Medien", "Klimawandel und Wasserknappheit", "Migration und Arbeitsmarkt",
           "Bildungssystem und Chancengleichheit", "Tourismus und Kulturerbe", "Stadtentwicklung und Verkehr",
           "Übersetzen zwischen Kulturen", "Pressefreiheit", "Künstliche Intelligenz im Alltag", "Generationenkonflikte"],
    "C1": ["Rezension eines Romans der Gegenwart", "Sprache und Identität in der persischsprachigen Welt",
           "Erinnerungskultur und Geschichtsschreibung", "Wissenschaftsethik", "Recht und Gerechtigkeit",
           "die Rolle der Lyrik in der iranischen Gesellschaft", "Urbanisierung in Zentralasien",
           "Übersetzungstheorie", "Religion und Säkularität", "Exilliteratur"],
    "C2": ["Kolumne mit ironischem Blick auf den Alltag in Teheran", "Essay über Hafis und die Mehrdeutigkeit",
           "literarische Skizze: ein Abend am Fluss in Duschanbe", "Glosse über Bürokratie",
           "Nachruf auf einen fiktiven Dichter", "Essay über Heimat und Fremde", "Satire über Expertentum",
           "Betrachtung über Zeit und Vergänglichkeit"],
}


def thema(stufe_name: str, heute: date | None = None) -> str:
    k = stufe_name.split()[0].rstrip("+")
    liste = THEMEN.get(k, THEMEN["B1"])
    return liste[(heute or date.today()).toordinal() % len(liste)]


# ─── Grammatik-Progression je Stufe ─────────────────────────────────────
# Wöchentlich ein Schwerpunkt aus der Liste der aktuellen Stufe; Strukturen früherer
# Stufen bleiben erlaubt. Muster: Regex zur Kontrolle, None = nicht automatisch prüfbar.
_PART = r"\S+(?:ده|ته)"          # Partizip Perfekt: رفته، آمده، کرده
_E = r"(?=[\s.،؛!؟:»)]|$)"
_KAUS = (r"(?:^|\s)\S*[^ه\u200c\s](?<![\s\u200c]د)(?<![\s\u200c]م)(?<![\s\u200c]ر)(?<![\s\u200c]خو)"
         r"(?<![\s\u200c]تو)(?<!^د)(?<!^م)(?<!^خو)(?<!^تو)اند(?:ن|م|ی|یم|ید|ند)?" + _E)
GRAMMATIK_STUFEN = {
    "A2": [
        ("Perfekt", "رفته‌ام، دیده است", _PART + r"(?:‌(?:ام|ای|ایم|اید|اند)|\s+است)" + _E),
        ("Subjunktiv nach باید / می‌خواهم", "باید بروم، می‌خواهم بخوانم", r"(?:باید|می‌خواه\S*)\s+ب\S+"),
        ("Komparativ und Superlativ", "بزرگ‌تر، بهترین", r"\S+‌?(?:تر|ترین)" + _E),
        ("Imperativ", "بیا، بنشین، نرو", None),
    ],
    "B1": [
        ("Verlaufsform mit داشتن", "دارم می‌نویسم، داشت می‌رفت",
         r"(?:^|\s)(?:دار(?:م|ی|د|یم|ید|ند)|داشت(?:م|ی|یم|ید|ند)?)\s+(?:\S+\s+)?می‌"),
        ("Perfekt und Plusquamperfekt", "رفته‌ام، رفته بودم",
         _PART + r"(?:‌(?:ام|ای|ایم|اید|اند)|\s+است|\s+بود(?:م|ی|یم|ید|ند)?)" + _E),
        ("realer Bedingungssatz", "اگر وقت داشته باشم، می‌آیم", r"(?:^|\s)اگر\s"),
        ("indirekte Rede", "گفت که فردا می‌آید",
         r"(?:گفت|گفتند|می‌گوید|می‌گویند|می‌گفت|نوشت|اعلام کرد|توضیح داد)\s+(?:\S+\s+){0,3}?که\s"),
        ("Infinitiv als Satzglied", "خواندن این کتاب آسان نیست",
         r"(?:^|\s)(?!می‌)\S+(?:دن|تن)(?:\s+\S+){0,3}\s+(?:است|نیست|بود|می‌شود|را)" + _E),
        ("Temporalsätze mit پیش از آن که / بعد از آن که", "بعد از آن که رسید، زنگ زد",
         r"(?:پیش|قبل|بعد)\s+از\s+(?:آن|این)\s*‌?که"),
        ("Finalsätze mit تا / برای اینکه", "آمدم تا ببینم", r"(?:^|\s)(?:تا|برای\s+این\s*‌?که)\s+ب\S+"),
    ],
    "B2": [
        ("Passiv mit شدن", "ساخته شد، گفته می‌شود",
         _PART + r"\s+(?:شد|شده|شود|شوند|می‌شود|می‌شوند|شدند|خواهد شد)" + _E),
        ("irrealer Bedingungssatz", "اگر می‌دانستم، می‌گفتم؛ اگر رفته بودم …",
         r"اگر\s[^.؟!]*?(?:می‌\S+[دت](?:م|ی|یم|ید|ند)?|" + _PART + r"\s+بود\S*)" + _E),
        ("Subjunktiv Perfekt", "شاید رفته باشد", _PART + r"\s+باش(?:م|ی|د|یم|ید|ند)" + _E),
        ("Kausativ auf ‑اندن", "خنداندن، رساندن", _KAUS),
        ("Konzessivsätze", "با این که خسته بود، کار کرد؛ اگرچه … اما",
         r"(?:با\s+این\s*‌?که|با\s+وجود\s+این\s*‌?که|اگرچه|هرچند)"),
        ("Partizip als Attribut", "کتابِ نوشته‌شده، درِ بسته", r"\S+(?:ده|ته)‌?شده" + _E),
        ("Futur der Schriftsprache", "خواهد رفت، خواهند گفت", r"(?:^|\s)خواه(?:م|ی|د|یم|ید|ند)\s+\S+[دت]" + _E),
        ("unpersönliche Konstruktionen", "می‌توان گفت، باید دانست", r"(?:می‌توان|نمی‌توان|باید|نباید)\s+\S+[دت]" + _E),
    ],
    "C1": [
        ("Nominalstil mit Verbalnomen", "با توجه به افزایش …، انجام این کار", r"(?:با\s+توجه\s+به|در\s+پی|به\s+منظور)"),
        ("Partizipialkonstruktion statt Nebensatz", "با رسیدن به شهر، …؛ پس از بازگشت",
         r"(?:با|پس\s+از|پیش\s+از|هنگام)\s+\S+(?:دن|تن)"),
        ("gehobene Konnektoren", "حال آنکه، از آنجا که، چنانچه، مگر آنکه",
         r"(?:حال\s*آن\s*‌?که|از\s+آنجا\s+که|چنانچه|مگر\s+آن\s*‌?که|در\s+صورتی\s+که)"),
        ("Perfekt der Berichterstattung", "گفته‌اند که …، نوشته است", _PART + r"‌?(?:اند|است)\s+که"),
        ("Kurzinfinitiv", "می‌توان رفت، باید دانست", r"(?:می‌توان|نمی‌توان|باید|نباید|بتوان)\s+\S+[دت]" + _E),
        ("arabische Plurale und Masdar-Formen", "تحولات، مسائل، استقبال", None),
    ],
    "C2": [
        ("klassische Verbformen", "بگفت، برفت، همی‌رفت", r"(?:^|\s)(?:ب\S+[دت]" + _E + r"|همی\s*‌?\S+)"),
        ("Sprichwörter und Redewendungen", "آب که از سر گذشت، چه یک وجب چه صد وجب", None),
        ("poetische Kurzformen", "ز، دگر، چو، اندر", r"(?:^|\s)(?:ز|دگر|چو|اندر)\s"),
        ("Ironie und Registerwechsel", "gehobene Wendung neben Umgangssprache", None),
    ],
}
GRAMMATIK = [g for liste in GRAMMATIK_STUFEN.values() for g in liste]
GRAMMATIK_START = date(2026, 10, 26)
_FOKUS = ""
_FOKUS_RE = None


def grammatik_fokus(stufe_name: str = "B1", heute: date | None = None):
    k = stufe_name.split()[0].rstrip("+")
    liste = GRAMMATIK_STUFEN.get(k, GRAMMATIK_STUFEN["B1"])
    woche = max(0, ((heute or date.today()) - GRAMMATIK_START).days // 7) % len(liste)
    return liste[woche], [g[0] for g in liste[:woche]]


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
    if _FOKUS_RE is not None and not _FOKUS_RE.search(t):
        m.append(f"Wochenschwerpunkt {_FOKUS} fehlt")
    return m


# ─── Claude-Aufruf ────────────────────────────────────────────────────────
def _prompt(lang_ex, bekannt_liste, stufe_txt, due, feedback, rueckstand=""):
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
- Die neuen Wörter nimmst du ZUERST aus dieser Liste (Karten, die in seinem Anki-Deck stehen, aber noch nicht gelernt sind): {rueckstand or "-"}
  Höchstens {GANZ_NEU_MAX} der neuen Wörter dürfen außerhalb dieser Liste liegen.
- Schreib KEINE Glossen und keine Klammern in Text und Nachricht; die Übersetzungen setzt ein Programm.
- Zusammengesetzte Verben und feste Verbverbindungen (ارتباط برقرار کردن، لذت بردن، به نمایش گذاشتن، از سر گرفتن) sind eigene Vokabeln, auch wenn die Einzelteile bekannt sind: Infinitiv des ganzen Gefüges in "neue_vokabeln".
- Ohne Kurzvokalzeichen im Fließtext, aber normale Rechtschreibung: Madde (آب, آمد, می‌آورد, آلودگی), Hamze und Halbabstand (ZWNJ) immer setzen.
- Lieber ein schlichter Satz als ein seltenes, gehobenes oder unpassendes Wort. Keine Füllsätze, keine schiefen Aussagen, keine Substantivierungen, die kein Iraner so sagen würde (z. B. nicht „غمگینی می‌آورد“).
{wh}- Nachricht: in 3–4 einfachen Sätzen auf Persisch nacherzählen, ebenfalls fast nur mit bekannten Wörtern; höchstens 2 weitere neue Wörter. NUR Inhalte aus Schlagzeile und Meldungstext unten, nichts hinzufügen. Die Quelle bleibt erhalten: Wenn Medien oder eine Person etwas berichten oder behaupten, schreib das so (رسانه‌های آمریکا گزارش می‌دهند …), nicht als Tatsache und nicht als Aussage eines Staates. Aus „bereitet sich vor“ wird nicht „will“. Jeder Satz trägt eine Information aus der Meldung; keine Füllsätze wie „این خبر امروز آمد“ oder „مردم این خبر را می‌شنوند“.
- Eigennamen (Personen, Orte, Länder, Organisationen) sind keine Vokabeln, nicht in "neue_vokabeln". Grammatik (z. B. die Verlaufsform) ist keine Vokabel.
{nachricht}{feedback}
Antworte NUR mit JSON, ohne Markdown:
{{"titel": "persischer Titel",
  "text": "Übungstext ohne Klammern",
  "nachricht": "Nacherzählung auf Persisch oder leer",
  "neue_vokabeln": [{{"fa": "Grundform mit Kurzvokalzeichen", "de": "knappe deutsche Bedeutung (1–3 Wörter)", "form": "die Wortform genau so, wie sie im Text steht"}}]}}
In "neue_vokabeln" steht jedes Wort und jedes Verbgefüge aus Text und Nachricht, das nicht in der Wortschatzliste steht (Verben als Infinitiv, Nomen im Singular)."""


def _lektorat(d: dict, K: set[str], quote: float, complete, stufe_name: str = "B1") -> dict:
    """Zweiter Durchgang: ein iranischer Lektor glättet Text und Nacherzählung."""
    p = f"""Du bist Lektor für Persisch (Muttersprachler, Teheran). Unten steht eine Leseübung für einen Lerner auf Stufe {stufe_name}.
Vereinfache die Grammatik NICHT: Relativsätze, Subjunktiv, Vergangenheitsformen{(' und der Wochenschwerpunkt ' + _FOKUS) if _FOKUS else ''} bleiben erhalten.
Überarbeite Text und Nacherzählung so, dass sie klingen, wie ein gebildeter Iraner einfach und natürlich schreibt.
- Korrigiere schiefe Aussagen, unidiomatische Wendungen, falsche Kollokationen, Füllsätze und Rechtschreibung (Madde, Hamze, Halbabstand).
- Behalte Inhalt, Satzzahl und Schwierigkeit bei. Ersetze kein einfaches Wort durch ein schwierigeres; neue Wörter nur, wenn es wirklich nicht anders geht.
- Der Text enthält keine Glossen; füge keine Klammern ein. Änderst du ein Wort aus "neue_vokabeln", passe dort "fa", "de" und "form" an.
- Die Nacherzählung darf nichts enthalten, was nicht in der Meldung steht.
Antworte NUR mit JSON im selben Format, Felder "titel", "text", "nachricht", "neue_vokabeln" (Einträge mit "fa", "de", "form").

{json.dumps({k: d.get(k) for k in ("titel", "text", "nachricht", "neue_vokabeln")}, ensure_ascii=False)}"""
    try:
        neu = _json(complete(p, max_tokens=2500))
        if not neu.get("text"):
            return d
        formen = {w for v in neu.get("neue_vokabeln", []) for w in _formen(v.get("fa", ""))}
        q2, _ = pruefe(neu.get("text", "") + " " + neu.get("nachricht", ""), K | formen)
        if q2 > quote + 0.03:          # Lektorat hat den Text deutlich schwerer gemacht
            return d
        if ab_b1(stufe_name) and len(b1_maengel(neu["text"])) > len(b1_maengel(d.get("text", ""))):
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


def _kurz(de: str) -> str:
    """Glosse kurz und ohne verschachtelte Klammern (30.10.: „las gerade (Bücher) vor – …“)."""
    de = re.sub(r"\([^)]*\)", "", de).split("–")[0].split(";")[0]
    return ", ".join(t.strip() for t in de.split(",")[:2] if t.strip())


_ENDUNG = re.compile(r"(?:‌?(?:ها|های|هایی|ان|ات))?(?:‌?(?:ی|ای|یی|م|ت|ش|مان|تان|شان|ام|ات|اش|اند|ست|تر|ترین))?$")


def _glossieren(text: str, glossen) -> tuple[str, set]:
    """Glosse hinter die angegebene Textform, beim ersten Vorkommen; ohne Form nur bei
    exakt passendem Einzelwort (30.10.: lockerer Abgleich glossierte نشستم als „waschen“)."""
    gesetzt = set()
    for fa, de, form in glossen:
        de = _kurz(de)
        if not de:
            continue
        if form:
            muster = r"(?<![\u0600-\u06FF\u200c])" + r"[\s\u200c]*".join(re.escape(t) for t in form.split()) \
                     + r"(?![\u0600-\u06FF\u200c])"
        else:
            if " " in fa.strip() or norm(fa).endswith(("دن", "تن")):
                continue
            stamm = HAR.sub("", fa).strip()
            muster = r"(?<![\u0600-\u06FF\u200c])" + re.escape(stamm) + _ENDUNG.pattern[:-1] + r"(?![\u0600-\u06FF\u200c])"
        m = re.search(muster, text)
        if not m or re.match(r"\s*\(", text[m.end():]):
            continue
        text = f"{text[:m.end()]} ({de}){text[m.end():]}"
        gesetzt.add(norm(fa))
    return text, gesetzt


def _annotieren(text: str, woerter, complete):
    """Bedeutungen für unbekannte Wörter und alle Verbgefüge im Text."""
    p = ("Persischer Lesetext unten.\n"
         "1. Gib für jedes Wort der Liste die Grundform (Verben als Infinitiv, Nomen im Singular) mit "
         "Kurzvokalzeichen und eine knappe deutsche Bedeutung (1–3 Wörter), wie sie IN DIESEM TEXT gemeint ist; "
         "\"form\" ist das Wort genau wie in der Liste. Eigennamen weglassen. Ist das Wort Teil eines Verbgefüges, "
         "gehört es nur unter 2.\n"
         "2. Finde ALLE zusammengesetzten Verben und festen Verbverbindungen im Text (Nomen, Adjektiv oder "
         "Präpositionalgruppe + کردن، شدن، دادن، گرفتن، بردن، زدن، داشتن، گذاشتن، آمدن، کشیدن usw.; "
         "z. B. ارتباط برقرار کردن، لذت بردن، به نمایش گذاشتن، از سر گرفتن). Für jedes: \"form\" = die "
         "Wortfolge exakt wie im Text, vom ersten bis zum letzten Bestandteil; \"fa\" = Infinitiv des "
         "Gefüges mit Kurzvokalzeichen; \"de\" = deutsche Bedeutung des Ganzen.\n"
         'Antworte NUR mit JSON: {"woerter": [{"form": "", "fa": "", "de": ""}], "verben": [{"form": "", "fa": "", "de": ""}]}\n\n'
         "WÖRTER:\n" + ("\n".join(woerter) or "-") + "\n\nTEXT:\n" + text)
    try:
        d = _json(complete(p, max_tokens=1500))
    except Exception:
        return [], []
    w = [((x.get("form") or "").strip(), (x.get("fa") or "").strip(), (x.get("de") or "").strip())
         for x in d.get("woerter", [])]
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
    global _FOKUS, _FOKUS_RE
    _FOKUS, _FOKUS_RE = "", None
    (fokus, bsp, muster), vorher = grammatik_fokus(stufe_name)
    _FOKUS = fokus
    _FOKUS_RE = re.compile(muster) if muster and ab_b1(stufe_name) else None
    stufe_txt += (f" GRAMMATIKSCHWERPUNKT DIESER WOCHE: {fokus} (z. B. {bsp}); mindestens zweimal, "
                  f"natürlich eingebettet. Strukturen der früheren Stufen sind selbstverständlich erlaubt.")
    if vorher:
        stufe_txt += " Auf dieser Stufe bereits eingeführt, gern wiederholen: " + ", ".join(vorher) + "."
    lang_ex = {**lang_ex, "topic": thema(stufe_name)}
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
    # Anki-Rückstand: ungelernte Karten zuerst einsetzen (29.10.2026: 1272 von 2109 ungelernt)
    deck_alle, offen_karten = set(), []
    if BEKANNT_FILE.exists():
        for e in json.loads(BEKANNT_FILE.read_text(encoding="utf-8")):
            deck_alle |= _formen(e.get("word", ""))
            if not e.get("gelernt", True) and HAR.sub("", e.get("word", "")).strip():
                offen_karten.append(HAR.sub("", e["word"]).strip())
    import random as _r
    _r.Random(date.today().toordinal()).shuffle(offen_karten)
    rueckstand = ", ".join(offen_karten[:RUECKSTAND_ANGEBOT])

    def ganz_neu(d):
        return [v.get("fa", "") for v in d.get("neue_vokabeln", [])
                if v.get("fa") and " " not in norm(v["fa"]) and not (_formen(v["fa"]) <= deck_alle)]

    bestes, feedback = None, ""
    for _ in range(VERSUCHE):
        try:
            d = _json(complete(_prompt(lang_ex, bekannt_liste, f"{stufe_name}: {stufe_txt}", due, feedback,
                                       rueckstand), max_tokens=2500))
        except Exception as e:
            feedback = f"\nACHTUNG: Die letzte Antwort war kein gültiges JSON ({e}).\n"
            continue
        neu = {w for v in d.get("neue_vokabeln", []) for w in _formen(v.get("fa", ""))}
        quote, fremd = pruefe(d.get("text", "") + " " + d.get("nachricht", ""), K | neu)
        maengel = b1_maengel(d.get("text", "")) if ab_b1(stufe_name) else []
        zu_viel = max(0, len(ganz_neu(d)) - GANZ_NEU_MAX)
        wert = quote + 0.05 * len(maengel) + 0.02 * zu_viel
        if bestes is None or wert < bestes[2]:
            bestes = (quote, d, wert)
        if quote <= MAX_UNBEKANNT and not maengel and not zu_viel:
            break
        feedback = ""
        if zu_viel:
            feedback += ("\nZU VIELE GANZ NEUE WÖRTER: " + ", ".join(ganz_neu(d))
                         + f". Höchstens {GANZ_NEU_MAX}; nimm die übrigen aus der Liste der ungelernten Anki-Karten.\n")
        if quote > MAX_UNBEKANNT:
            feedback += ("\nDER LETZTE ENTWURF WAR ZU SCHWER. Diese Wörter kennt er nicht und sie waren nicht "
                         "als neu markiert. Ersetze sie durch Wörter aus der Liste oder einfache Umschreibungen:\n"
                         + ", ".join(fremd[:40]) + "\n")
        if maengel:
            feedback += ("\nDER LETZTE ENTWURF WAR NUR A2, NICHT B1. Es fehlte: " + "; ".join(maengel)
                         + ". Schreib eine kleine Erzählung in der Vergangenheit zum Thema, nicht eine Beschreibung im Präsens.\n")
    if bestes is None:
        raise RuntimeError("Leseübung konnte nicht erzeugt werden")
    if bestes[0] > MAX_UNBEKANNT:
        # Notlauf statt zu schweren Text verschicken (28./29.10.: 82 % bzw. 86 % bekannt)
        try:
            notfall = feedback + ("\nLETZTER VERSUCH: Schreib nur 5 kurze Sätze, ausschließlich mit Wörtern aus der "
                                  "Wortschatzliste und den neuen Wörtern. Lieber schlicht als zu schwer.\n")
            d = _json(complete(_prompt(lang_ex, bekannt_liste, f"{stufe_name}: {stufe_txt}", due, notfall,
                                       rueckstand), max_tokens=2500))
            neu = {w for v in d.get("neue_vokabeln", []) for w in _formen(v.get("fa", ""))}
            q, _ = pruefe(d.get("text", "") + " " + d.get("nachricht", ""), K | neu)
            if q < bestes[0]:
                bestes = (q, d, q)
        except Exception:
            pass

    quote, d, _ = bestes
    d = _lektorat(d, K, quote, complete, stufe_name)
    # Maßstab für Glossen ist allein das Gelernte im Anki-Deck. Bis 29.10.2026 galten
    # Morgenbrief-Wörter 60 Tage als bekannt und verloren ihre Klammer, obwohl die
    # Karte nie gelernt war (مختلف، روزانه، پیشرفت ohne Glosse im Text).
    deck, gelernt, ganz_deck, ganz_gelernt = set(), set(), set(), set()
    if BEKANNT_FILE.exists():
        for e in json.loads(BEKANNT_FILE.read_text(encoding="utf-8")):
            f, g = _formen(e.get("word", "")), _ganz(e.get("word", ""))
            deck |= f
            ganz_deck |= g
            if e.get("gelernt", True):
                gelernt |= f
                ganz_gelernt |= g
    # Glossen setzt nur noch das Programm; was das Modell trotzdem einklammert, fliegt raus,
    # ebenso unmittelbar doppelte Wortfolgen (30.10.: „تبدیل شود تبدیل شود“)
    for feld in ("text", "nachricht"):
        if d.get(feld):
            t = re.sub(r"\s*\([^)]*[A-Za-zÄÖÜäöüß][^)]*\)", "", d[feld])
            t = re.sub(r"(?<![\u0600-\u06FF\u200c])((?:[\u0600-\u06FF\u200c]+ ){0,2}[\u0600-\u06FF\u200c]+) \1(?![\u0600-\u06FF\u200c])", r"\1", t)
            d[feld] = t
    if ab_b1(stufe_name) and b1_maengel(d.get("text", "")):
        stufe_name = f"{stufe_name}, verfehlt: " + "; ".join(b1_maengel(d.get("text", "")))   # Label nicht schönen

    def tauglich(fa, de):
        return (fa and de and not NAME.search(de) and len(fa.split()) <= 4
                and not re.search(r"[A-Za-z+?؟]", fa))

    liste = [((v.get("fa") or "").strip(), (v.get("de") or "").strip(), (v.get("form") or "").strip())
             for v in d.get("neue_vokabeln", [])]
    liste = [x for x in liste if tauglich(x[0], x[1])]
    alles = d.get("text", "") + " " + d.get("nachricht", "")
    abgedeckt = {norm(t) for _, _, form in liste for t in form.split()}
    _, rest = pruefe(alles, gelernt | {w for fa, _, _ in liste for w in _formen(fa)})
    offen = [t for t in rest if norm(t) not in abgedeckt]
    woerter, verben = _annotieren(alles, offen, complete)
    liste += [(fa, de, form or "") for form, fa, de in woerter if tauglich(fa, de)]
    for form, fa, de in verben:
        if form and tauglich(fa, de) and not (_ganz(fa) & ganz_gelernt):
            liste.append((fa, de, form))
    liste.sort(key=lambda x: len(x[2].split()), reverse=True)   # Verbgefüge vor Einzelwörtern
    mem_woerter = {norm(v["word"]) for v in mem.get("fa", [])}
    gesehen, kandidaten = set(), []
    for fa, de, form in liste:
        n = norm(fa)
        varianten = _ganz(fa) | {n}
        if varianten & gesehen:
            continue
        gesehen |= varianten
        if " " in n.replace(ZWNJ, " ").strip():
            im_deck, ist_gelernt = bool(_ganz(fa) & ganz_deck), bool(_ganz(fa) & ganz_gelernt)
        else:
            f = _formen(fa)
            im_deck, ist_gelernt = bool(f) and f <= deck, bool(f) and f <= gelernt
        if not ist_gelernt:
            kandidaten.append((fa, de, form, im_deck))
    # Fällige und schwache Wörter (bei Vince: zuletzt "Nochmal") bekommen eine Klammer,
    # gehen aber nicht ins Anki-Paket.
    glossen = [(fa, de, form) for fa, de, form, _ in kandidaten]
    glossen += [(v["word"], v["meaning"], "") for v in due
                if v.get("word") and v.get("meaning") and norm(v["word"]) not in gesehen]
    gesetzt = set()
    for feld in ("text", "nachricht"):
        if d.get(feld):
            d[feld], g = _glossieren(d[feld], glossen)
            gesetzt |= g
    # In Liste und Anki-Paket nur, was im Text tatsächlich glossiert steht
    anzeige, neue = [], []
    for fa, de, form, im_deck in kandidaten:
        if norm(fa) not in gesetzt:
            continue
        if im_deck:
            anzeige.append(f"{fa} – {_kurz(de)} (schon im Deck, noch nicht gelernt)")
            continue
        zusatz = " (Wiederholung, bisher ohne Anki-Karte)" if norm(fa) in mem_woerter else ""
        anzeige.append(f"{fa} – {_kurz(de)}" + zusatz)
        neue.append((fa, _kurz(de)))
    woerter = "\n".join(anzeige) or "–"
    abschnitt = (
        f"SPRACHÜBUNG - TEXT\n{d.get('titel', '')}\n\n{d.get('text', '')}\n\n"
        f"NEUE WÖRTER (Stufe {stufe_name}{', Grammatik: ' + _FOKUS if _FOKUS else ''}, {round((1 - quote) * 100)} % bekannt; Anki-Paket im Anhang)\n{woerter}\n\n"
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
