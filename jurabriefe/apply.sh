#!/usr/bin/env bash
# Im Wurzelverzeichnis von daily ausfuehren:  bash jurabriefe/apply.sh
set -e
cd "$(dirname "$0")/.."
test -f jurabriefe/karten.py && test -f jurabriefe/kuratieren.py || { echo "karten.py / kuratieren.py fehlen in jurabriefe/"; exit 1; }

python jurabriefe/karten.py
python jurabriefe/kuratieren.py --alle --pruefen

if [ -n "$ANTHROPIC_API_KEY" ]; then
  python jurabriefe/kuratieren.py --alle
else
  echo "ANTHROPIC_API_KEY nicht gesetzt — Kuration uebersprungen, nur Rohkarten gebaut."
fi

echo "fertig — jurabriefe/karten/INDEX.md zeigt die Zaehlung"
