#!/bin/bash
cd "$HOME/Documents/Bewerbungen/bewerbungsgrundlage/lebenslauf" || exit 1
export PATH="/Library/TeX/texbin:$PATH"
if ! fc-list : family 2>/dev/null | grep -qi carlito; then
  sed -i '' 's/^\\setmainfont{Carlito}/\\setmainfont{Helvetica Neue}/' Lebenslauf_Akademisch.tex
  echo "Carlito fehlt - auf Helvetica Neue umgestellt"
fi
xelatex -interaction=nonstopmode Lebenslauf_Akademisch.tex > /tmp/cvlog.txt 2>&1
grep -m1 "Output written" /tmp/cvlog.txt || grep -m3 "^!" /tmp/cvlog.txt
rm -f Lebenslauf_Akademisch.aux Lebenslauf_Akademisch.log
ls -1
