#!/bin/bash
# Morgenbrief legt sein ePub zusaetzlich im OPDS-Katalog ab.
cat > /tmp/nc_ablage.sh <<'OUTER'
set -e
KAT=/hosting248937.af957.netcup.net/httpdocs/lese/buecher
cd /automat/daily
python3 - <<'PY'
import pathlib, re
p = pathlib.Path("run_morgenbrief.py")
s = p.read_text(encoding="utf-8")
alt = "    epub = g.create_epub(text, g.now_berlin().strftime(\"%Y-%m-%d\"))\n    g.send_to_kindle(epub)"
neu = """    epub = g.create_epub(text, g.now_berlin().strftime("%Y-%m-%d"))
    g.send_to_kindle(epub)
    # zusaetzlich in den OPDS-Katalog legen, damit KOReader es holen kann
    try:
        import shutil, pathlib as _p
        katalog = _p.Path("/hosting248937.af957.netcup.net/httpdocs/lese/buecher")
        if katalog.is_dir():
            ziel = katalog / f"Morgenbrief_{g.now_berlin().strftime('%Y-%m-%d')}.epub"
            shutil.copyfile(epub, ziel)
            print(f"Morgenbrief im Katalog abgelegt: {ziel.name}")
    except Exception as e:
        print(f"Katalog-Ablage fehlgeschlagen: {e}")"""
if "OPDS-Katalog" in s:
    print("schon angepasst")
else:
    assert alt in s, "Stelle nicht gefunden"
    p.write_text(s.replace(alt, neu), encoding="utf-8")
    print("run_morgenbrief.py angepasst")
PY
python3 -c "import ast;ast.parse(open('run_morgenbrief.py').read());print('Syntax ok')"
OUTER
scp -q /tmp/nc_ablage.sh netcup:/tmp/ablage.sh
ssh -o BatchMode=yes netcup '. /automat/umgebung.sh; bash /tmp/ablage.sh' 2>&1 | tail -6
