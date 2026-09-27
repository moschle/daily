#!/bin/bash
# Gleicht den gelernten Anki-Wortschatz ab, sobald der Mac läuft (LaunchAgent de.schlenstedt.bekannt).
# Nur bei Änderung: committen, pushen und direkt auf den netcup-Server kopieren.
export PATH=/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin
cd "$HOME/Projects/daily" || exit 1
/usr/bin/python3 bekannt_aktualisieren.py || exit 1
if ! git diff --quiet -- bekannt_fa.json; then
  git add bekannt_fa.json
  git commit -q -m "bekannt_fa: Anki-Stand $(date +%F)"
  git pull -q --rebase && git push -q
  scp -q -o BatchMode=yes bekannt_fa.json netcup:/automat/daily/bekannt_fa.json
  echo "$(date '+%F %T') aktualisiert"
else
  echo "$(date '+%F %T') unverändert"
fi
