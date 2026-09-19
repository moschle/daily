#!/bin/bash
B="$HOME/Documents/Bewerbungen"
cd "$B" || exit 1
mkdir -p 01_grundlagen 02_zeugnisse 03_laufend 04_abgeschlossen

m() { [ -e "$1" ] && mv -n "$1" "$2" 2>/dev/null; }

# Grundlagen: alles, woraus Bewerbungen gebaut werden
m bewerbungsgrundlage/lebenslauf 01_grundlagen/lebenslauf
m bewerbungsgrundlage/lebenslauf_alt 01_grundlagen/lebenslauf_alt
m bewerbungsgrundlage/Bewerbungsdesiderat_Schlenstedt.md 01_grundlagen/
m bewerbungsgrundlage/Lebenslauf_CSS_Schlenstedt.docx 01_grundlagen/
m bewerbungsgrundlage/Motivationsschreiben_CSS_Schlenstedt.docx 01_grundlagen/
m bewerbung_halle 01_grundlagen/stilvorlagen
rmdir bewerbungsgrundlage 2>/dev/null

# Zeugnisse
if [ -d zeugnisse ]; then mv -n zeugnisse/* 02_zeugnisse/ 2>/dev/null; rmdir zeugnisse 2>/dev/null; fi

# Laufend: 2026er Verfahren ohne Entscheidung
if [ -d 2026 ]; then mv -n 2026/* 03_laufend/ 2>/dev/null; rmdir 2026 2>/dev/null; fi

# Abgeschlossen
if [ -d archiv ]; then
  mv -n archiv/Schloss_Westerhaus 04_abgeschlossen/2015_schloss_westerhaus 2>/dev/null
  mv -n archiv/Studienstiftungen 04_abgeschlossen/2016_studienstiftungen 2>/dev/null
  mv -n archiv/bewerbung_bayreuth 04_abgeschlossen/2026_bayreuth 2>/dev/null
  mv -n archiv/bewerbung_hildesheim 04_abgeschlossen/2026_hildesheim 2>/dev/null
  mv -n archiv/2026_reserveoffizier 04_abgeschlossen/2026_reserveoffizier 2>/dev/null
  mv -n archiv/sonstiges 04_abgeschlossen/undatiert 2>/dev/null
  rmdir archiv 2>/dev/null
fi

find . -name '.DS_Store' -delete 2>/dev/null
echo "--- OBERSTE EBENE:"; ls -1p
echo "--- 01_grundlagen:"; ls -1 01_grundlagen
echo "--- 03_laufend:"; ls -1 03_laufend
echo "--- 04_abgeschlossen:"; ls -1 04_abgeschlossen
