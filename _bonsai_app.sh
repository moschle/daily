#!/bin/bash
# Icon fuer Bonsai.app aus dem Logo des Repos bauen und die App registrieren.
set -e
APP="$HOME/Applications/Bonsai.app"
SVG="$HOME/Bonsai-demo/assets/bonsai-logo.svg"
TMP=$(mktemp -d)

chmod +x "$APP/Contents/MacOS/Bonsai"

# SVG -> PNG (qlmanage kann SVG rendern), dann -> icns
if [ -f "$SVG" ]; then
  qlmanage -t -s 1024 -o "$TMP" "$SVG" >/dev/null 2>&1 || true
  PNG=$(ls "$TMP"/*.png 2>/dev/null | head -1)
  if [ -n "$PNG" ]; then
    ICONSET="$TMP/bonsai.iconset"; mkdir -p "$ICONSET"
    for s in 16 32 64 128 256 512; do
      sips -z $s $s "$PNG" --out "$ICONSET/icon_${s}x${s}.png" >/dev/null 2>&1
      sips -z $((s*2)) $((s*2)) "$PNG" --out "$ICONSET/icon_${s}x${s}@2x.png" >/dev/null 2>&1
    done
    iconutil -c icns "$ICONSET" -o "$APP/Contents/Resources/bonsai.icns" 2>/dev/null && echo "Icon gebaut"
  else
    echo "SVG konnte nicht gerendert werden - App bekommt das Standardsymbol"
  fi
fi

touch "$APP"
/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -f "$APP" 2>/dev/null || true
rm -rf "$TMP"
echo "--- App:"; find "$APP" -type f | sed "s|$HOME|~|"
