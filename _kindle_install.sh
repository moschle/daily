#!/bin/bash
# Alles auf den Kindle kopieren. Erst ausfuehren, wenn das Geraet gemountet ist,
# also nachdem KOReader auf dem Kindle beendet wurde.
set -e
P="$HOME/Downloads/kindle_paket"

# Kindle finden
K=""
for v in /Volumes/*/; do
  if [ -d "$v/documents" ] || [ -d "$v/koreader" ] || [ -d "$v/extensions" ]; then K="${v%/}"; fi
done
if [ -z "$K" ]; then
  echo "Kindle nicht gefunden. Auf dem Geraet KOReader beenden, dann erscheint das Laufwerk."
  ls -1 /Volumes
  exit 1
fi
echo "Kindle: $K"

mkdir -p "$K/koreader/plugins" "$K/koreader/data/dict" "$K/extensions" "$K/documents/Bibliothek"

# 1) Simple UI
rm -rf "$K/koreader/plugins/simpleui.koplugin"
cp -R "$P/plugins/simpleui.koplugin" "$K/koreader/plugins/"
[ -f "$P/plugins/simpleuiconfigshared.sui" ] && cp "$P/plugins/simpleuiconfigshared.sui" "$K/koreader/"
echo "  Simple UI kopiert"

# 2) Woerterbuecher
for d in "$P"/dict/*/; do
  name=$(basename "$d")
  rm -rf "$K/koreader/data/dict/$name"
  cp -R "$d" "$K/koreader/data/dict/$name"
  echo "  Woerterbuch $name kopiert"
done

# 3) ranki
if [ -d "$P/extensions/ranki" ]; then
  rm -rf "$K/extensions/ranki"
  cp -R "$P/extensions/ranki" "$K/extensions/"
  chmod +x "$K/extensions/ranki/"*.sh 2>/dev/null || true
  chmod +x "$K/extensions/ranki/ranki-arm"* 2>/dev/null || true
  [ -f "$P/extensions/ranki/shortcut_ranki.sh" ] && cp "$P/extensions/ranki/shortcut_ranki.sh" "$K/documents/"
  echo "  ranki kopiert"
fi

# 4) Bibliothek aus Calibre
LIB="$HOME/Calibre Library"
anz=0
if [ -d "$LIB" ]; then
  while IFS= read -r datei; do
    ziel="$K/documents/Bibliothek/$(basename "$datei")"
    [ -f "$ziel" ] || cp "$datei" "$ziel"
    anz=$((anz+1))
  done < <(find "$LIB" -type f \( -iname '*.epub' -o -iname '*.azw3' -o -iname '*.mobi' -o -iname '*.pdf' \) 2>/dev/null)
fi
echo "  $anz Buecher kopiert"

echo
echo "Fertig. Kindle auswerfen, KOReader starten."
df -h "$K" | tail -1
