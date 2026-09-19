#!/bin/bash
# 1) iCloud-Drive-Ordner in die bestehende Dokumentenstruktur einhaengen
# 2) Downloads-Archiv nach Namensmustern in dieselbe Struktur einsortieren
C="$HOME/Library/Mobile Documents/com~apple~CloudDocs"
D="$HOME/Documents"
V="$D/Verwaltung"

mkdir -p "$V/Finanzen" "$V/Vertraege" "$V/Wohnen" "$V/Ausweise" "$V/Versicherungen" \
         "$V/Rechnungen" "$V/Arbeit" "$V/Jobcenter" "$V/Steuer" "$V/Gesundheit" \
         "$D/Akademisch/Quellen" "$D/Akademisch/Texte" "$D/WARTE" "$D/Ungeklaert" \
         "$D/Texte/ebooks" "$HOME/Pictures/Archiv_Downloads" "$HOME/Downloads/_Archiv/software"

# --- 1) iCloud-Wurzelordner einhaengen ---
for sub in Finanzen Vertraege Wohnen Ausweise Versicherungen Rechnungen Arbeit; do
  [ -d "$C/Verwaltung/$sub" ] && mv -n "$C/Verwaltung/$sub"/* "$V/$sub/" 2>/dev/null
  rmdir "$C/Verwaltung/$sub" 2>/dev/null
done
rmdir "$C/Verwaltung" 2>/dev/null
[ -d "$C/Akademisch/Quellen" ] && mv -n "$C/Akademisch/Quellen"/* "$D/Akademisch/Quellen/" 2>/dev/null
[ -d "$C/Akademisch/Texte" ]   && mv -n "$C/Akademisch/Texte"/*   "$D/Akademisch/Texte/" 2>/dev/null
rmdir "$C/Akademisch/Quellen" "$C/Akademisch/Texte" "$C/Akademisch" 2>/dev/null
[ -d "$C/Verein" ]     && mv -n "$C/Verein"/*     "$D/WARTE/" 2>/dev/null; rmdir "$C/Verein" 2>/dev/null
[ -d "$C/Ungeklaert" ] && mv -n "$C/Ungeklaert"/* "$D/Ungeklaert/" 2>/dev/null; rmdir "$C/Ungeklaert" 2>/dev/null
[ -d "$C/Bilder" ]     && mv -n "$C/Bilder"/*     "$HOME/Pictures/Archiv_Downloads/" 2>/dev/null; rmdir "$C/Bilder" 2>/dev/null

# --- 2) Downloads-Archiv nach Namensmustern ---
cd "$HOME/Downloads/_Archiv" || exit 1
shopt -s nullglob nocaseglob
for f in 2026/* aelter/*; do
  [ -f "$f" ] || continue
  b=$(basename "$f")
  case "$b" in
    *Rechnung*|*rechnung*|*Invoice*|*Quittung*|*Mahnung*|*Zahlungserinnerung*) mv -n "$f" "$V/Rechnungen/" ;;
    *Bescheid*|*bescheid*|*Jobcenter*|*Leistungsnachweis*|*EKS*|*Bewilligung*)   mv -n "$f" "$V/Jobcenter/" ;;
    *Vertrag*|*vertrag*|*Kündigung*|*Kuendigung*)                                mv -n "$f" "$V/Vertraege/" ;;
    *Versicherung*|*Police*|*VRK*|*AOK*|*Krankenkasse*)                          mv -n "$f" "$V/Versicherungen/" ;;
    *Steuer*|*Elster*|*elster*)                                                  mv -n "$f" "$V/Steuer/" ;;
    *Kontoauszug*|*Depot*|*Wertpapier*|*Gehalt*|*Lohn*)                          mv -n "$f" "$V/Finanzen/" ;;
    *Miet*|*Wohnung*|*Nebenkosten*|*Strom*|*Meldebescheinigung*)                 mv -n "$f" "$V/Wohnen/" ;;
    *Lebenslauf*|*Anschreiben*|*Bewerbung*|*Zeugnis*|*Arbeitszeugnis*)           mv -n "$f" "$D/Bewerbungen/04_abgeschlossen/undatiert/" ;;
    *Attest*|*Arztbrief*|*Befund*|*Osteopathie*)                                 mv -n "$f" "$V/Gesundheit/" ;;
    *.epub)                                                                      mv -n "$f" "$D/Texte/ebooks/" ;;
    *.jpeg|*.jpg|*.png|*.heic|*.gif|*.tiff)                                      mv -n "$f" "$HOME/Pictures/Archiv_Downloads/" ;;
    *.dmg|*.pkg|*.zip|*.gpkg|*.gz|*.tar)                                         mv -n "$f" "$HOME/Downloads/_Archiv/software/" ;;
  esac
done
shopt -u nocaseglob

echo "=== iCloud Wurzel:"; ls -1p "$C"
echo "=== Downloads/_Archiv/2026 uebrig:"; ls -1 2026 2>/dev/null | wc -l
echo "=== _Archiv/aelter uebrig:"; ls -1 aelter 2>/dev/null | wc -l
echo "=== Verwaltung:"; for d in "$V"/*/; do printf '%-22s %s\n' "$(basename "$d")" "$(ls -1 "$d" | wc -l)"; done
