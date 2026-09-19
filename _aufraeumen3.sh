#!/bin/bash
B="$HOME/Documents/Bewerbungen"
cd "$B" || exit 1

mkdir -p archiv/sonstiges archiv/2026_reserveoffizier
mkdir -p bewerbungsgrundlage/lebenslauf_alt

m() { [ -e "$1" ] && mv -n "$1" "$2"/ 2>/dev/null; }

# alte, abgeschlossene Verfahren ins Archiv
m "Schloss_Westerhaus" archiv
m "Studienstiftungen" archiv
m "bewerbung_bayreuth" archiv
m "bewerbung_hildesheim" archiv

# alte Lebenslauf-Fassungen bündeln
m "lebenslaeufe" bewerbungsgrundlage
m "Lebenslauf_Akademisch.pdf" bewerbungsgrundlage/lebenslauf_alt

# lose Bewerbungen einsortieren
m "01-Bewerbungsunterlagen ResOffz adW Schlenstedt Moritz copy.pdf" archiv/2026_reserveoffizier
m "Bewerbung als wissenschaftlicher Mitarbeiter für Diskurs und Wissenschaftskommunikation.pdf" 2026
m "Grad Vorabbewerbung.pdf" 2026

# Reste ohne erkennbaren Bezug
for f in "Selbstdarstellung.pdf" "bewerbung_schlenstedt.pdf" "Unknown.pdf" "Sans_titre.pages" "Linkliste.pages"; do m "$f" archiv/sonstiges; done

# gehört woanders hin
mkdir -p "$HOME/Documents/WARTE"
m "unabhängige_lesereihen.md" "$HOME/Documents/WARTE"
mkdir -p "$HOME/Documents/Verwaltung/Reise"
m "Lufthansa.pages" "$HOME/Documents/Verwaltung/Reise"

# git sauber halten
if [ ! -f .gitignore ]; then printf '.DS_Store\n' > .gitignore; fi
find . -name '.DS_Store' -delete 2>/dev/null

echo "--- OBERSTE EBENE:"; ls -1p
echo "--- ARCHIV:"; ls -1 archiv
echo "--- GRUNDLAGE:"; ls -1 bewerbungsgrundlage
