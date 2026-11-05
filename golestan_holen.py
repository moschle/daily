"""Einmalig: Golestan (Saadi) von der Ganjoor-API holen nach GOLESTAN_DIR/teile.json.

Gemeinfreier Text; Ganjoor liefert ihn teilweise schon mit Kurzvokalen.
versePosition -1 = Prosa, 0/1 = erster/zweiter Halbvers.
"""
import json, os, re, sys, time, urllib.request
from pathlib import Path

ZIEL = Path(os.environ.get("GOLESTAN_DIR", "/automat/golestan"))
API = "https://api.ganjoor.net/api/ganjoor/page?url="
BAB = ["اول", "دوم", "سوم", "چهارم", "پنجم", "ششم", "هفتم", "هشتم"]


def holen(url):
    with urllib.request.urlopen(API + url, timeout=60) as r:
        return json.loads(r.read())


teile = []
for b in range(1, 9):
    seite = holen(f"/saadi/golestan/gbab{b}")
    for slug in re.findall(rf'href="/saadi/golestan/gbab{b}/(sh\d+)"', seite.get("htmlText", "")):
        p = holen(f"/saadi/golestan/gbab{b}/{slug}")["poem"]
        teile.append({"titel": f"باب {BAB[b - 1]}، {p['title']}", "url": f"https://ganjoor.net/saadi/golestan/gbab{b}/{slug}",
                      "zeilen": [[v["versePosition"], v["text"]] for v in p["verses"]]})
        time.sleep(0.3)
    print(b, len(teile), flush=True)
ZIEL.mkdir(parents=True, exist_ok=True)
(ZIEL / "teile.json").write_text(json.dumps(teile, ensure_ascii=False), encoding="utf-8")
print("fertig", len(teile))
