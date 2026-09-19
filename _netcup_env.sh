#!/bin/bash
# Zugangsdaten sicher laden statt sie als Shell-Code auszufuehren.
cat > /tmp/nc_env.sh <<'OUTER'
set -e
cat > /automat/umgebung.sh <<'ENVSH'
export PATH=/bin_local:$PATH
export LD_LIBRARY_PATH=/pylib:$LD_LIBRARY_PATH
# Werte zeilenweise lesen, ohne sie von der Shell auswerten zu lassen.
# So ueberleben Leerzeichen, & und Anfuehrungszeichen in Passwoertern.
if [ -f /automat/zugang.env ]; then
  while IFS= read -r zeile || [ -n "$zeile" ]; do
    case "$zeile" in ''|\#*) continue ;; esac
    schluessel=${zeile%%=*}
    wert=${zeile#*=}
    case "$schluessel" in *[!A-Za-z0-9_]*|'') continue ;; esac
    export "$schluessel=$wert"
  done < /automat/zugang.env
fi
cd /automat/daily
ENVSH
chmod +x /automat/umgebung.sh
. /automat/umgebung.sh
python3 - <<'PY'
import os
for k in ["ANTHROPIC_API_KEY","APPLE_ID","APPLE_APP_PASSWORD","GMAIL_ADDRESS",
          "GMAIL_APP_PASSWORD","ICAL_URL","KINDLE_EMAIL","STELLEN_RECIPIENT","JURABRIEF_TO"]:
    v = os.environ.get(k, "")
    print(f"{k:22} {len(v):>3} Zeichen" + ("  (mit Leerzeichen)" if " " in v else ""))
PY
OUTER
scp -q /tmp/nc_env.sh netcup:/tmp/env.sh
ssh -o BatchMode=yes netcup 'bash /tmp/env.sh' 2>&1 | tail -12
