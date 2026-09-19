#!/bin/bash
D="$HOME/Documents/Verwaltung"
W="$HOME/Documents/Wichtige Dokumente"
mkdir -p "$D/Versicherungen" "$D/Gesundheit" "$D/Kaeufe_und_Garantien" "$D/Arbeit" "$D/Kontakte" "$D/Schluessel_und_Zertifikate"
mkdir -p "$HOME/Pictures/Screenshots"

m() { [ -e "$1" ] && mv -n "$1" "$2"/ 2>/dev/null; }

cd "$W" || exit 1
m "Schlenstedt_Personalausweis.pdf" "$D/Ausweise"
m "visa" "$D/Ausweise"
m "Versicherungsvertrag-ID DE1348508532026.PDF" "$D/Versicherungen"
m "Protect Dokumente.pdf" "$D/Versicherungen"
m "Rechnung_Osteopathie_098_2025_01.pdf" "$D/Gesundheit"
m "GarantieStaubsauger.pdf" "$D/Kaeufe_und_Garantien"
m "Rechnung Staubsauger.PDF" "$D/Kaeufe_und_Garantien"
m "Invoice-963.pdf" "$D/Kaeufe_und_Garantien"
m "DE_eBay_T&C_15_Jul_2020.pdf" "$D/Kaeufe_und_Garantien"
m "eBay_IPID_2019_DE_with_bikes.pdf" "$D/Kaeufe_und_Garantien"
m "Haushaltspauschale.pages" "$D/Wohnen"
m "Klingelschild88.pages" "$D/Wohnen"
m "Verfassungstreueprüfung.pdf" "$D/Arbeit"
m "Punkt.vcf" "$D/Kontakte"
m "iCloud.vcf" "$D/Kontakte"
m "TAN.pdf" "$D/Schluessel_und_Zertifikate"
m "Der persönliche Sicherheitsschlüssel für Ihre Akte.pdf" "$D/Schluessel_und_Zertifikate"
m "Ihr persönlicher Wiederherstellungsschlüssel für TK-Safe.pdf" "$D/Schluessel_und_Zertifikate"
m "annas-archive-secret-key.txt" "$D/Schluessel_und_Zertifikate"
m "moschle_elster_04.04.2024_13.11.pfx" "$D/Schluessel_und_Zertifikate"
m "moschle_elster_09.12.2017_21.56.pfx" "$D/Schluessel_und_Zertifikate"
m "Bildschirm"*.png "$HOME/Pictures/Screenshots"

cd "$D/2026" 2>/dev/null || exit 0
m "A1-Formular_Schlenstedt.pdf" "$D/Arbeit"
m "Stundenzettel.pdf" "$D/Arbeit"
m "Brief Lufthansa.pdf" "$D/Reise"
m "DerGläserneHaushalt_Schlenstedt.pdf" "$D/Wohnen"
m "Einzelheiten zum Kauf | eBay.pdf" "$D/Kaeufe_und_Garantien"
m "Rechnung_RE-2026-21233_2026-09-09.pdf" "$D/Kaeufe_und_Garantien"
m "Rechnung Osteopathie 098_2026_03.pdf" "$D/Gesundheit"
rm -f "Personalausweis.pdf" 2>/dev/null

cd "$HOME/Documents"
rmdir "$W" 2>/dev/null && echo "Wichtige Dokumente entfernt (war leer)"
rmdir "$D/2026" 2>/dev/null && echo "Verwaltung/2026 entfernt (war leer)"
echo "--- VERWALTUNG:"; ls -1 "$D"
echo "--- Reste in Wichtige Dokumente:"; ls -1 "$W" 2>/dev/null
echo "--- Reste in 2026:"; ls -1 "$D/2026" 2>/dev/null
