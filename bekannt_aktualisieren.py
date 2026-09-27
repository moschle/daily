#!/usr/bin/env python3
"""Erzeugt bekannt_fa.json aus der lokalen Anki-Sammlung (Deck "Persisch").

gelernt = mindestens eine Karte der Notiz wurde schon einmal richtig beantwortet.
Nur diese Woerter gelten fuer den Morgenbrief als bekannt; alle Woerter des Decks
werden aber mitgeschrieben, damit keine Dubletten als neue Vokabeln kommen.

Aufruf am Mac:  /usr/bin/python3 bekannt_aktualisieren.py
"""
import json, re, shutil, sqlite3, tempfile
from pathlib import Path

SAMMLUNG = Path.home() / "Library/Application Support/Anki2/Benutzer 1/collection.anki2"
DECK = "Persisch"
ZIEL = Path(__file__).parent / "bekannt_fa.json"


def sauber(s):
    s = re.sub(r"<[^>]+>", " ", s).replace("&nbsp;", " ")
    return re.sub(r"\s+", " ", s).strip()


def main():
    tmp = Path(tempfile.mkdtemp()) / "c.anki2"
    shutil.copy(SAMMLUNG, tmp)
    wal = SAMMLUNG.with_name(SAMMLUNG.name + "-wal")
    if wal.exists():  # noch nicht zurückgeschriebene Änderungen, wenn Anki offen ist
        shutil.copy(wal, tmp.with_name(tmp.name + "-wal"))
    con = sqlite3.connect(tmp)
    con.create_collation("unicase", lambda a, b: (a.lower() > b.lower()) - (a.lower() < b.lower()))
    did = con.execute("select id from decks where name=?", (DECK,)).fetchone()[0]
    zeilen = con.execute(
        """select n.flds,
                  max(exists(select 1 from revlog r where r.cid = c.id and r.ease >= 2))
           from notes n join cards c on c.nid = n.id
           where c.did = ? group by n.id""", (did,)).fetchall()
    daten = []
    for flds, gelernt in zeilen:
        f = flds.split("\x1f")
        daten.append({"word": sauber(f[0]), "meaning": sauber(f[1]) if len(f) > 1 else "",
                      "gelernt": bool(gelernt)})
    ZIEL.write_text(json.dumps(daten, ensure_ascii=False, indent=0), encoding="utf-8")
    print(f"{len(daten)} Notizen, davon gelernt: {sum(d['gelernt'] for d in daten)}")


if __name__ == "__main__":
    main()
