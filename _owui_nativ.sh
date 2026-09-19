#!/bin/bash
# Open WebUI nativ aus dem Bonsai-Repo installieren, Docker abschalten.
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/bin:/bin"
cd "$HOME/Bonsai-demo" || exit 1
LOG=/tmp/owui_install.log
echo "=== $(date) Installation" > "$LOG"

# 1) Docker-Container stoppen und Autostart abschalten (Daten bleiben im Volume)
/usr/local/bin/docker update --restart=no open-webui >> "$LOG" 2>&1
/usr/local/bin/docker stop open-webui >> "$LOG" 2>&1
echo "Container gestoppt" >> "$LOG"

# 2) Open WebUI in die Projektumgebung installieren
uv pip install ".[webui]" >> "$LOG" 2>&1
echo "EXIT_INSTALL=$?" >> "$LOG"
tail -3 "$LOG"
