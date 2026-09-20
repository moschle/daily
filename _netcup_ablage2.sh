#!/bin/bash
# Die Ablage im OPDS-Katalog gehoert in die Sendefunktion selbst,
# dann greift sie in beiden Wegen - regulaerer Brief wie Notfassung.
cat > /tmp/nc_ablage2.sh <<'OUTER'
set -e
cd /automat/daily
python3 - <<'PY'
import pathlib
p = pathlib.Path("generate_morgenbrief.py")
s = p.read_text(encoding="utf-8")

# frueher eingefuegte Stelle in run_morgenbrief.py wieder entfernen
r = pathlib.Path("run_morgenbrief.py")
rs = r.read_text(encoding="utf-8")
start = rs.find("    # zusaetzlich in den OPDS-Katalog legen")
if start != -1:
    ende = rs.find("if __name__", start)
    rs = rs[:start] + "\n" + rs[ende:]
    r.write_text(rs, encoding="utf-8")
    print("run_morgenbrief.py zurueckgebaut")

if "OPDS-Katalog" in s:
    print("generate_morgenbrief.py schon angepasst")
else:
    marke = "def send_to_kindle(epub_path):"
    i = s.index(marke)
    j = s.index("\n", i) + 1
    einschub = '''    # Ablage im OPDS-Katalog, damit KOReader den Brief holen kann
    try:
        import shutil
        katalog = Path("/hosting248937.af957.netcup.net/httpdocs/lese/buecher")
        if katalog.is_dir():
            ziel = katalog / f"Morgenbrief_{now_berlin().strftime('%Y-%m-%d')}.epub"
            shutil.copyfile(epub_path, ziel)
            print(f"Im Katalog abgelegt: {ziel.name}", file=sys.stderr)
    except Exception as e:
        print(f"Katalog-Ablage fehlgeschlagen: {e}", file=sys.stderr)
'''
    s = s[:j] + einschub + s[j:]
    p.write_text(s, encoding="utf-8")
    print("generate_morgenbrief.py angepasst")
PY
python3 -c "import ast;[ast.parse(open(f).read()) for f in ('generate_morgenbrief.py','run_morgenbrief.py')];print('Syntax ok')"
OUTER
scp -q /tmp/nc_ablage2.sh netcup:/tmp/ablage2.sh
ssh -o BatchMode=yes netcup '. /automat/umgebung.sh; bash /tmp/ablage2.sh' 2>&1 | tail -6
