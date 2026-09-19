#!/bin/bash
C="$HOME/Library/Mobile Documents/com~apple~CloudDocs"
D="$HOME/Documents"
V="$D/Verwaltung"

# Reste aus CloudDocs/Verwaltung (Namensdubletten, deshalb mit Suffix)
[ -f "$C/Verwaltung/Ausweise/Personalausweis.pdf" ] && mv -n "$C/Verwaltung/Ausweise/Personalausweis.pdf" "$V/Ausweise/Personalausweis_icloud.pdf"
[ -f "$C/Verwaltung/Wohnen/Untermietvetrag.pdf" ] && mv -n "$C/Verwaltung/Wohnen/Untermietvetrag.pdf" "$V/Wohnen/Untermietvertrag_icloud.pdf"
find "$C/Verwaltung" -type d -empty -delete 2>/dev/null

# jurabrief-Skripte zu den vorhandenen Jura-Skripten
mkdir -p "$D/Jura/Skripte"
mv -n "$C/jurabrief"/* "$D/Jura/Skripte/" 2>/dev/null
rmdir "$C/jurabrief" 2>/dev/null

# tajikpoetry zum Masterarbeitsmaterial
mkdir -p "$D/Akademisch/MA/tajikpoetry"
mv -n "$C/tajikpoetry"/* "$D/Akademisch/MA/tajikpoetry/" 2>/dev/null
rmdir "$C/tajikpoetry" 2>/dev/null

# CloudDocs/Downloads ins Downloads-Archiv, damit es einen Ort gibt statt zwei
mkdir -p "$HOME/Downloads/_Archiv/aus_icloud"
mv -n "$C/Downloads"/* "$HOME/Downloads/_Archiv/aus_icloud/" 2>/dev/null
rmdir "$C/Downloads" 2>/dev/null

echo "=== iCloud Wurzel:"; ls -1p "$C"
echo "=== Jura/Skripte:"; ls -1 "$D/Jura/Skripte" | wc -l
echo "=== aus_icloud:"; ls -1 "$HOME/Downloads/_Archiv/aus_icloud" 2>/dev/null | wc -l
