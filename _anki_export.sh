#!/bin/bash
# Persisch-Wortschatz aus der Anki-Sammlung ziehen.
# Anki muss geschlossen sein, sonst ist die Datenbank gesperrt.
cp "$HOME/Library/Application Support/Anki2/Benutzer 1/collection.anki2" /tmp/anki_kopie.db 2>/dev/null
/usr/bin/python3 - <<'PY'
import sqlite3, json, re, html, sys
c = sqlite3.connect("/tmp/anki_kopie.db")
decks = {}
try:
    for r in c.execute("select id, name from decks"):
        decks[r[0]] = r[1]
except sqlite3.OperationalError:
    col = c.execute("select decks from col").fetchone()[0]
    for k, v in json.loads(col).items():
        decks[int(k)] = v["name"]
ziel = [i for i, n in decks.items() if "persisch" in n.lower()]
print("Decks:", [decks[i] for i in ziel], file=sys.stderr)
if not ziel:
    print("[]"); raise SystemExit
q = "select distinct n.flds from cards c join notes n on n.id=c.nid where c.did in (%s)" % ",".join("?"*len(ziel))
woerter = []
for (flds,) in c.execute(q, ziel):
    teile = flds.split("\x1f")
    if len(teile) >= 2:
        w = re.sub(r"<[^>]+>", "", html.unescape(teile[0])).strip()
        b = re.sub(r"<[^>]+>", "", html.unescape(teile[1])).strip()
        if w and b:
            woerter.append({"word": w, "meaning": b})
print("Eintraege:", len(woerter), file=sys.stderr)
json.dump(woerter, open("/tmp/persisch_bekannt.json", "w"), ensure_ascii=False, indent=1)
PY
echo "--- Datei:"; ls -lh /tmp/persisch_bekannt.json
/usr/bin/python3 -c "import json;d=json.load(open('/tmp/persisch_bekannt.json'));print(len(d),'Woerter');[print(' ',x['word'],'=',x['meaning'][:40]) for x in d[:5]]"
