#!/bin/bash
# Nach dem gekauften Woerterbuch suchen.
echo "=== Verlagsnamen ==="
find "$HOME" -maxdepth 6 \( -iname '*junker*' -o -iname '*alavi*' -o -iname '*steingass*' \
  -o -iname '*langenscheidt*' -o -iname '*pons*' -o -iname '*wehr*' -o -iname '*hueber*' \
  -o -iname '*duden*' -o -iname '*aryanpour*' \) 2>/dev/null \
  | grep -viE '/Library/|site-packages|node_modules' | head -15

echo
echo "=== weitere Woerterbuchformate ==="
find "$HOME" -maxdepth 6 \( -iname '*.azw' -o -iname '*.azw3' -o -iname '*.prc' -o -iname '*.mobi' \
  -o -iname '*.epub' \) 2>/dev/null | grep -iE 'dict|wört|worter|lexik|vocab' | head -10

echo
echo "=== Aryanpour ==="
ls -1 "$HOME/Projects/dictionary/external/AryanpourDictionary" 2>/dev/null | head
ls -1 "$HOME/Projects/dictionary/external/AryanpourDictionary/Aryanpour Dictionary" 2>/dev/null | head

echo
echo "=== Kindle angeschlossen? ==="
ls -1 /Volumes
system_profiler SPUSBDataType 2>/dev/null | grep -iA2 kindle | head -6
