#!/bin/bash
# iCloud Drive aufräumen: lose Dateien der obersten Ebene nach Sachgebieten sortieren.
# Gleiche Logik wie ~/Documents/Verwaltung. Nichts wird gelöscht.
C="$HOME/Library/Mobile Documents/com~apple~CloudDocs"
cd "$C" || exit 1

mkdir -p Verwaltung/Finanzen Verwaltung/Vertraege Verwaltung/Wohnen Verwaltung/Ausweise \
         Verwaltung/Versicherungen Verwaltung/Rechnungen Verwaltung/Arbeit \
         Akademisch/Quellen Akademisch/Texte Bilder Verein Ungeklaert

m() { [ -e "$1" ] && mv -n "$1" "$2"/ 2>/dev/null; }

# Finanzen
for f in 1148243900_*.pdf "Kontoauszug.pdf" "Kontoauszug 2.pdf" "Lohnabrechnung Juni.pdf" \
         "Einkommensteuerbescheid.pdf" "Zuwendungsbescheid.pdf" "Zuwendungsbescheid 2.pdf"; do m "$f" Verwaltung/Finanzen; done

# Vertraege
for f in "HiWiVertrag.pdf" "Honorarvertrag Moritz Schlenstedt.pdf" "Vertrag - 16.10.2025.pdf" \
         "Your contract McFIT_ MEGA DEAL 12M Premium 2025.pdf" "Kündigung.pdf"; do m "$f" Verwaltung/Vertraege; done

# Wohnen
for f in "Untermietvetrag.pdf" "Wohnung.pdf" "Meldebescheinigung.pdf"; do m "$f" Verwaltung/Wohnen; done

# Ausweise
for f in "Personalausweis.pdf" "post-ident-coupon.pdf"; do m "$f" Verwaltung/Ausweise; done

# Versicherungen
m "HMR-809104688G60010-Versicherungsschein.pdf" Verwaltung/Versicherungen

# Rechnungen und Mahnungen
for f in "Rechnung - 1784.pdf" "Rechnung 6005806026.PDF" "Rechnung für versicherten Versand, 060526.pdf" \
         "Rechnung_RE-2026-21233_2026-09-09.pdf" "rechnung_schlenstedt.pdf" \
         "DB Rechnung 355789621725.pdf" "Zahlungserinnerung DB Vertrieb GmbH.PDF" \
         "Erinnerung zu Ihrer Kundennummer: 5604439869.PDF" "OR-039719.pdf" "Билет.pdf" "reise1.pdf"; do m "$f" Verwaltung/Rechnungen; done

# Arbeit und Bewerbung
for f in "Lebenslauf Pflege Schlenstedt.docx" "Lebenslauf Pflege Schlenstedt.pdf" \
         "Lebenslauf Schlenstedt.pdf" "Empfehlungsschreiben.pdf" "1764786247554_Antwortbogen.pdf"; do m "$f" Verwaltung/Arbeit; done

# Akademisch: persische und tadschikische Quellen
for f in "be mateh fekr mikonam 4.pdf" "be mateh fekr mikonam 5.pdf" "bo anore khamhun....pdf" \
         "typhonkho-i sokit.pdf" "tyfonkho-i sokit.pdf" "БОАНОРЕХАМХУН.doc" "Bijan Elahi.pdf" \
         "Nimeh Gomshodeh Man.zip" "farsi.txt" "poems.txt" \
         "CLLRCA_Volume 17_Issue 47_Pages 87-107.pdf"; do m "$f" Akademisch/Quellen; done

# Eigene Texte
for f in "kommst du spät, komm als gedicht.pdf" "A. Grab des Unbekannten 27. Mai.pdf" \
         "moonbrand 4.pdf" "briefe.pdf" "2. Teil.pdf" "Büdösch gekürzt.epub" \
         "Dankesrede von Eva Illouz für den Frank-Schirrmacher-Preis.jpeg.png"; do m "$f" Akademisch/Texte; done

# Verein und Seide
for f in "Rechnung Warte-Klumpen.pdf" "DP Mai - fürs Team.pdf" "ZedarSilk_Collection26.pdf" "stempel.pdf"; do m "$f" Verein; done

# Bilder
for f in *.HEIC *.JPG *.jpg *.PNG *.png *.jpeg; do m "$f" Bilder; done

# Unklare Namen
for f in "PDF-Dokument.pdf" "pdf.pdf" "Scanned Document.pdf" "Scanned Document 2.pdf" \
         "Gescanntes Dokument.pdf" "Text.txt" "separator.txt" "visualizer.txt" \
         "15243014.pdf" "15243015.pdf" "IMG_3273.pdf" "IMG_3695.pdf" \
         "d305A3A4BB8DFDSWIN1 2.pdf" "tajik-poem-analyzer.zip"; do m "$f" Ungeklaert; done

echo "--- oberste Ebene jetzt:"; ls -1p | head -30
echo "--- lose Dateien uebrig:"; ls -1p | grep -vc /
