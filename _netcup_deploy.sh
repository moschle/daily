#!/bin/bash
# Morgenbrief + Stellenscraper auf netcup einrichten.
# git-over-https ist im Chroot kaputt (fehlende Bibliothek), deshalb per Tarball.
cat > /tmp/nc_deploy.sh <<'EOF'
set -e
export PATH=/bin_local:$PATH
export LD_LIBRARY_PATH=/pylib:$LD_LIBRARY_PATH

mkdir -p /automat
cd /automat
curl -sL -o /tmp/daily.tgz https://codeload.github.com/moschle/daily/tar.gz/refs/heads/main
rm -rf daily.neu && mkdir daily.neu
tar -xzf /tmp/daily.tgz -C daily.neu --strip-components=1
rm -f /tmp/daily.tgz
# Zustandsdateien aus dem alten Stand uebernehmen, damit nichts doppelt kommt
for f in stellen_seen.json gloss_state.json journal_state.json vocab_memory.json .env; do
  [ -f "daily/$f" ] && cp -p "daily/$f" "daily.neu/$f"
done
rm -rf daily.alt && [ -d daily ] && mv daily daily.alt
mv daily.neu daily
cd /automat/daily
python3 -m pip install --quiet -r requirements.txt 2>&1 | tail -3
echo "--- Stand:"
python3 -c "import sys; print('Python', sys.version.split()[0])"
ls -1 *.py | head -12
EOF
scp -q /tmp/nc_deploy.sh netcup:/tmp/deploy.sh
ssh -o BatchMode=yes netcup 'bash /tmp/deploy.sh' 2>&1 | tail -20
