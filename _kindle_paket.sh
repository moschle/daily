#!/bin/bash
# Kindle-Paket zusammenstellen: ranki, Simple UI, Woerterbuecher, Anleitung.
pkill -f _dict_suche.sh 2>/dev/null
P="$HOME/Downloads/kindle_paket"
mkdir -p "$P/extensions" "$P/plugins" "$P/dict" "$P/documents"
cd "$P" || exit 1

# --- ranki ---
URL=$(curl -s https://api.github.com/repos/crazy-electron/ranki/releases/latest \
      | grep -o 'https://[^"]*ranki[^"]*\.zip' | head -1)
if [ -n "$URL" ]; then
  echo "ranki: $URL"
  curl -sL -o /tmp/ranki.zip "$URL" && unzip -qo /tmp/ranki.zip -d "$P/extensions" && rm -f /tmp/ranki.zip
  find "$P/extensions" -maxdepth 2 -name '*.sh' | head -5
else
  echo "ranki: kein Release gefunden"
fi

# --- Simple UI aus seinen Downloads ---
if [ -d "$HOME/Downloads/simpleui.koplugin" ]; then
  rm -rf "$P/plugins/simpleui.koplugin"
  cp -R "$HOME/Downloads/simpleui.koplugin" "$P/plugins/"
  [ -f "$HOME/Downloads/simpleuiconfigshared.sui" ] && cp "$HOME/Downloads/simpleuiconfigshared.sui" "$P/plugins/"
  echo "Simple UI uebernommen"
fi

# --- Woerterbuecher ---
EP="$HOME/Projects/English-Persian-Kindle-Custom-Dictionary/English Persian Dictionary stardic"
if [ -d "$EP" ]; then
  mkdir -p "$P/dict/englisch_persisch"
  cp "$EP"/* "$P/dict/englisch_persisch/" 2>/dev/null
  # KOReader liest .dict lieber unkomprimiert
  if [ -f "$P/dict/englisch_persisch/English Persian Dictionary.dict.dz" ]; then
    gunzip -c "$P/dict/englisch_persisch/English Persian Dictionary.dict.dz" \
      > "$P/dict/englisch_persisch/English Persian Dictionary.dict" 2>/dev/null \
      && rm -f "$P/dict/englisch_persisch/English Persian Dictionary.dict.dz"
  fi
  echo "Englisch-Persisch uebernommen"
fi

echo
echo "=== Paketinhalt ==="
find "$P" -maxdepth 3 -not -path '*/.*' | sed "s|$HOME|~|" | head -40
echo
echo "=== Groesse ==="; du -sh "$P"
