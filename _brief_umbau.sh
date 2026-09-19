#!/bin/bash
# Zwei Aenderungen am Morgenbrief:
#   1) nur noch Persisch, kein Arabisch
#   2) Vokabelgedaechtnis genullt, dafuer Abgleich gegen den Anki-Wortschatz
set -e
cd "$HOME/Projects/daily"

/usr/bin/python3 - <<'PY'
import json, re, pathlib

p = pathlib.Path("generate_morgenbrief.py")
s = p.read_text(encoding="utf-8")

# 1) Sprache fest auf Persisch
alt = '    language, lc = ("Arabisch","ar") if doy%2==0 else ("Persisch","fa")'
neu = '    language, lc = ("Persisch", "fa")   # nur noch Persisch, Arabisch entfaellt'
assert alt in s, "Sprachzeile nicht gefunden"
s = s.replace(alt, neu)

# 2) bekannten Wortschatz laden und in den Prompt geben
alt2 = '    mem = load_vocab_memory()\n    due = get_due_vocab(lc, mem)'
neu2 = '''    mem = load_vocab_memory()
    due = get_due_vocab(lc, mem)
    bekannt = load_bekannt(lc)'''
assert alt2 in s
s = s.replace(alt2, neu2)

# Loader ergaenzen
anker = 'def get_due_vocab(lc, m):'
lader = '''BEKANNT_FILE = Path(__file__).parent / "bekannt_fa.json"

def load_bekannt(lc):
    """Woerter, die er aus Anki schon kann. Die sollen nicht als neu eingefuehrt werden."""
    if lc != "fa" or not BEKANNT_FILE.exists():
        return []
    try:
        with open(BEKANNT_FILE, "r", encoding="utf-8") as f:
            return [e["word"] for e in json.load(f) if e.get("word")]
    except Exception:
        return []

'''
s = s.replace(anker, lader + anker, 1)

# in den Rueckgabewert aufnehmen
alt3 = '            "memory":mem,"due_vocab":due}'
neu3 = '            "memory":mem,"due_vocab":due,"bekannt":bekannt}'
assert alt3 in s
s = s.replace(alt3, neu3)

# Prompt: Hinweis auf bekannte Woerter
alt4 = "              f\"- {lang['new_vocab_instruction']}\\n{lang['repetition_prompt']}\\n\""
neu4 = """              f"- {lang['new_vocab_instruction']}\\n{lang['repetition_prompt']}\\n"
              f"{bekannt_p}\\n\""""
assert alt4 in s
s = s.replace(alt4, neu4)

alt5 = "    lang_p = (f\"SPRACHÜBUNG - TEXT (RTL, in Originalschrift):\\n\""
neu5 = '''    bek = lang.get("bekannt") or []
    if bek:
        probe = ", ".join(bek[:400])
        bekannt_p = ("BEKANNTER WORTSCHATZ: Diese Woerter kennt er bereits aus seinem Anki-Deck. "
                     "Verwende sie gern im Text, fuehre sie aber NICHT als neue Vokabel auf. "
                     "Neue Vokabeln muessen ausserhalb dieser Liste liegen:\\n" + probe + "\\n")
    else:
        bekannt_p = ""
''' + alt5
assert alt5 in s
s = s.replace(alt5, neu5, 1)

p.write_text(s, encoding="utf-8")
print("generate_morgenbrief.py geaendert")

# 3) Vokabelgedaechtnis nullen
json.dump({"ar": [], "fa": []}, open("vocab_memory.json", "w"), ensure_ascii=False, indent=2)
print("vocab_memory.json genullt")

# 4) bekannten Wortschatz uebernehmen
bek = json.load(open("/tmp/persisch_bekannt.json"))
json.dump(bek, open("bekannt_fa.json", "w"), ensure_ascii=False, indent=1)
print("bekannt_fa.json angelegt:", len(bek), "Woerter")
PY

/usr/bin/python3 -c "import ast;ast.parse(open('generate_morgenbrief.py').read());print('Syntax ok')"
