#!/bin/bash
set -e
K="root@192.168.1.209"
P="$HOME/Downloads/kindle_paket"
SSH="ssh -p 2222 -i $HOME/.ssh/kindle -o StrictHostKeyChecking=no -o BatchMode=yes"
SCP="scp -P 2222 -i $HOME/.ssh/kindle -o StrictHostKeyChecking=no -r"

echo "=== Simple UI ==="
$SSH $K 'mkdir -p /mnt/us/koreader/plugins'
$SCP "$P/plugins/simpleui.koplugin" $K:/mnt/us/koreader/plugins/
$SCP "$P/plugins/simpleuiconfigshared.sui" $K:/mnt/us/
echo "  OK"

echo "=== Woerterbuecher ==="
$SSH $K 'mkdir -p /mnt/us/koreader/data/dict'
$SCP "$P/dict/persisch_anki" $K:/mnt/us/koreader/data/dict/
$SCP "$P/dict/englisch_persisch" $K:/mnt/us/koreader/data/dict/
echo "  OK"

echo "=== ranki Shortcut ==="
$SCP "$P/extensions/ranki/shortcut_ranki.sh" $K:/mnt/us/documents/
echo "  OK"

echo "=== Kaliber Buecher ==="
LIB="$HOME/Calibre Library"
anz=0
while IFS= read -r f; do
    bname=$(basename "$f")
    if ! $SSH $K "test -f /mnt/us/documents/$bname" 2>/dev/null; then
        $SCP "$f" $K:/mnt/us/documents/ 2>/dev/null && anz=$((anz+1))
    fi
done < <(find "$LIB" -type f \( -iname "*.epub" -o -iname "*.azw3" -o -iname "*.mobi" \) 2>/dev/null)
echo "  $anz Buecher kopiert"

echo ""
echo "Fertig. KOReader neu starten damit Simple UI und Woerterbuecher aktiv werden."
