#!/bin/bash
# Laufskripte und Zugangsdaten-Vorlage auf netcup anlegen.
cat > /tmp/nc_runner.sh <<'OUTER'
set -e
cd /automat/daily

# Vorlage fuer die Zugangsdaten - Werte traegt Moritz selbst ein
if [ ! -f /automat/zugang.env ]; then
cat > /automat/zugang.env <<'ENVV'
# Zugangsdaten fuer die Automatisierungen.
# Dieselben Werte wie bisher in den GitHub-Secrets. Ohne Anfuehrungszeichen.
ANTHROPIC_API_KEY=
APPLE_ID=
APPLE_APP_PASSWORD=
GMAIL_ADDRESS=
GMAIL_APP_PASSWORD=
ICAL_URL=
KINDLE_EMAIL=
STELLEN_RECIPIENT=
JURABRIEF_TO=
ENVV
chmod 600 /automat/zugang.env
fi

# Gemeinsamer Kopf fuer alle Laeufe
cat > /automat/umgebung.sh <<'ENVSH'
export PATH=/bin_local:$PATH
export LD_LIBRARY_PATH=/pylib:$LD_LIBRARY_PATH
set -a
[ -f /automat/zugang.env ] && . /automat/zugang.env
set +a
cd /automat/daily
ENVSH

cat > /automat/morgenbrief.sh <<'RUN'
#!/bin/bash
. /automat/umgebung.sh
exec python3 run_morgenbrief.py >> /automat/logs/morgenbrief.log 2>&1
RUN

cat > /automat/stellen.sh <<'RUN'
#!/bin/bash
. /automat/umgebung.sh
exec python3 stellen_boot.py >> /automat/logs/stellen.log 2>&1
RUN

chmod +x /automat/morgenbrief.sh /automat/stellen.sh
mkdir -p /automat/logs
echo "--- angelegt:"
ls -l /automat
echo "--- Vorlage:"
sed 's/=.*/=/' /automat/zugang.env
OUTER
scp -q /tmp/nc_runner.sh netcup:/tmp/runner.sh
ssh -o BatchMode=yes netcup 'bash /tmp/runner.sh' 2>&1 | tail -25
