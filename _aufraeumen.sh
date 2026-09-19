#!/bin/bash
cd "$HOME/Downloads" || exit 1

mkdir -p "$HOME/Documents/Jura/Skripte"
mkdir -p "$HOME/Documents/Verwaltung/Jobcenter"
mkdir -p "$HOME/Documents/Verwaltung/Krankenkasse"
mkdir -p "$HOME/Documents/Verwaltung/Steuer"
mkdir -p "$HOME/Documents/Verwaltung/Finanzen"
mkdir -p "$HOME/Documents/Verwaltung/Wohnen"
mkdir -p "$HOME/Documents/Verwaltung/Ausweise"
mkdir -p "$HOME/Documents/Verwaltung/Reise"
mkdir -p "$HOME/Documents/Bewerbungen/2026"
mkdir -p "$HOME/Documents/Akademisch/MA/anthologie"
mkdir -p "$HOME/Documents/Akademisch/MA/dilorom_fotos"
mkdir -p "$HOME/Documents/Akademisch/Persisch"
mkdir -p "$HOME/Documents/Akademisch/Quellen"
mkdir -p "$HOME/Projects/_eingang"

m() { [ -e "$1" ] && mv -n "$1" "$2"/ 2>/dev/null; }

# Jura-Skripte
for f in [0-9]*\ *.pdf [0-9][0-9]*\ *.pdf; do
  case "$f" in *Verwaltungsrecht*|*Europarecht*|*EMRK*|*Verwaltungsprozessrecht*|*Kommunalrecht*|*Polizei*|*Baurecht*|*Straßenrecht*|*Staat*|*Grundrechte*)
    mv -n "$f" "$HOME/Documents/Jura/Skripte"/ 2>/dev/null ;;
  esac
done

# Jobcenter
for f in 20260811_133533_Bewilligungsbescheid.pdf 20260820_004945_Leistungsnachweis.pdf 20260914_141213_Aufforderung_zur_Mitwirkung.pdf Anlage_EKS_vorlaeufig_09-2026.pdf anlageeks_ba033540-2.pdf; do m "$f" "$HOME/Documents/Verwaltung/Jobcenter"; done

# Krankenkasse
for f in AOK_Antrag_freiwillige_Mitgliedschaft_Punkt3.pdf AOK_Einkommensfragebogen_2026_ausgefuellt.pdf; do m "$f" "$HOME/Documents/Verwaltung/Krankenkasse"; done

# Steuer
m Einkommensteuerbescheid.pdf "$HOME/Documents/Verwaltung/Steuer"

# Finanzen
for f in "Account statement.pdf" "Vermögensentwicklung (EUR) Seit Kauf.csv" "Wertpapierabrechnung Nr. 45 | UnionDepot 31492548_2649499405.pdf" VRK_Jahresinformation_965-657515-W-06_15-05-2026.pdf; do m "$f" "$HOME/Documents/Verwaltung/Finanzen"; done

# Wohnen
for f in "Untermietvetrag.pdf" "Untermietvetrag (1).pdf"; do m "$f" "$HOME/Documents/Verwaltung/Wohnen"; done

# Reise / Beschwerde
for f in "Vielen Dank für Ihre Buchung  von Santia de Compostela nach Dresden am 04 Juni 2026.pdf" Lufthansa_Beschwerde_2026-07-04.pdf; do m "$f" "$HOME/Documents/Verwaltung/Reise"; done

# Bewerbungen 2026
for f in Anschreiben_AWV-2026-062.docx Anschreiben_AWV-2026-062.pdf Anschreiben_DFG_GRK3125.docx Anschreiben_DFG_GRK3125.pdf Anschreiben_Uni_Leipzig_Finanzen_119-2026.docx Anschreiben_Uni_Leipzig_Finanzen_119-2026.pdf BAMF-2026-300_Interamt-Hilfstexte.docx BAMF-2026-300_Interamt-Hilfstexte.pdf Bewerbung_2026_Reisestipendium_Schlenstedt_Moritz.pdf Bewerbung_Schlenstedt_III-15-2026.pdf Expose_DFG_GRK3125.pdf Bewerbungen_2026-09-16.zip paket Lebenslauf_Akademisch_neu.pdf; do m "$f" "$HOME/Documents/Bewerbungen/2026"; done

# Masterarbeit / Anthologie
for f in stille_stuerme.md stille_stuerme_manuskript.docx stille_stuerme_manuskript_LR.docx "stille stürme" ТОЛИБИЛУҚМОН25.docx; do m "$f" "$HOME/Documents/Akademisch/MA/anthologie"; done
m "New Folder With Items" "$HOME/Documents/Akademisch/MA/dilorom_fotos"

# Persisch
for f in Persisch-korrigiert.apkg persisch_neu_2026-09-09.txt; do m "$f" "$HOME/Documents/Akademisch/Persisch"; done

# Projekte
for f in gridlab "gridlab 2" "gridlab 3" "gridlab 4" gridlab.zip gridlab-paper.zip gridlab-paper-2.zip gridlab-paper-3.zip; do m "$f" "$HOME/Projects/_eingang"; done

# Persische Quellen aus Documents-Wurzel
cd "$HOME/Documents" || exit 1
for f in "be mateh fekr mikonam 1.pdf" "be mateh fekr mikonam 2.pdf" "be mateh fekr mikonam 3.pdf"; do m "$f" "$HOME/Documents/Akademisch/Quellen"; done
m "Zeugnis MA.pdf" "$HOME/Documents/Bewerbungen/zeugnisse"
m "Personalausweis.pdf" "$HOME/Documents/Verwaltung/Ausweise"
m "Gehaltsabrechnung Juni 2026.pdf" "$HOME/Documents/Verwaltung/Finanzen"
m "Rechnung Osteopathie 098_2026_03.pdf" "$HOME/Documents/Verwaltung/2026"
m "Lufthansa_Beschwerde_2026-07-04.md" "$HOME/Documents/Verwaltung/Reise"
m "Fed und EZB an der Kandare der Politik _ FAZ.pdf" "$HOME/Documents/Akademisch/Quellen"

echo "--- DOWNLOADS oben:"; ls -1 "$HOME/Downloads" | wc -l
echo "--- DOCUMENTS lose Dateien:"; ls -lp "$HOME/Documents" | grep -vc /
