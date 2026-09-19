#!/bin/bash
# Dateileichen suchen: grosse Dateien, Installer, Dubletten
echo "=== geladenes mmproj"
ps aux | grep '[l]lama-server' | tr ' ' '\n' | grep -A0 mmproj -n >/dev/null
ps aux | grep '[l]lama-server' | sed -E 's/.*--mmproj ([^ ]+).*/\1/'

echo
echo "=== Dateien groesser 300 MB"
find "$HOME" -type f -size +300M \
  -not -path "*/Library/Caches/*" -not -path "*/.Trash/*" \
  -not -path "*/Library/Containers/com.docker*" 2>/dev/null \
  -exec du -h {} + 2>/dev/null | sort -h | tail -25

echo
echo "=== Installer (dmg, pkg)"
find "$HOME" -type f \( -name "*.dmg" -o -name "*.pkg" \) -not -path "*/.Trash/*" 2>/dev/null \
  -exec du -h {} + 2>/dev/null | sort -h | tail -20

echo
echo "=== Docker.raw"
du -h "$HOME/Library/Containers/com.docker.docker/Data/vms/0/data/Docker.raw" 2>/dev/null

echo
echo "=== Caches"
du -sh "$HOME/Library/Caches" "$HOME/.cache" "$HOME/.npm" "$HOME/Library/Application Support/Code/Cache" 2>/dev/null
