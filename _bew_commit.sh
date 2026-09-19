#!/bin/bash
export PATH="/opt/homebrew/bin:$PATH"
cd "$HOME/Documents/Bewerbungen" || exit 1
rm -f .git/index.lock
git add -A
git commit -q -m "Struktur aufgeraeumt: archiv, bewerbungsgrundlage/lebenslauf, lebenslauf_alt"
git log -1 --format="%h %s"
git status --short | head -5
