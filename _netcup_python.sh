#!/bin/bash
# Wrapper-Skript fuer Python auf dem netcup-Webhosting anlegen und testen.
# Wird per ssh dorthin uebertragen und ausgefuehrt.
cat > /tmp/netcup_setup.sh <<'EOF'
set -e
mkdir -p /bin_local
cat > /bin_local/python3 <<'WRAP'
#!/bin/bash
export LD_LIBRARY_PATH=/pylib:$LD_LIBRARY_PATH
exec /opt/python/bin/python3 "$@"
WRAP
cat > /bin_local/pip3 <<'WRAP'
#!/bin/bash
export LD_LIBRARY_PATH=/pylib:$LD_LIBRARY_PATH
exec /opt/python/bin/python3 -m pip "$@"
WRAP
chmod +x /bin_local/python3 /bin_local/pip3
grep -q bin_local /.bashrc 2>/dev/null || echo 'export PATH=/bin_local:$PATH' >> /.bashrc
/bin_local/python3 -V
/bin_local/pip3 install --quiet requests beautifulsoup4 feedparser ebooklib
/bin_local/python3 -c "import requests, bs4, feedparser, ebooklib; print('requests', requests.__version__, '| bs4', bs4.__version__, '| feedparser', feedparser.__version__, '| ebooklib ok')"
EOF
scp -q /tmp/netcup_setup.sh netcup:/tmp/setup.sh
ssh -o BatchMode=yes netcup 'bash /tmp/setup.sh' 2>&1 | tail -5
