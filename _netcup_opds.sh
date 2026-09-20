#!/bin/bash
# OPDS-Katalog fuer den Kindle auf netcup einrichten.
# Der Morgenbrief legt sein ePub dort ab, KOReader holt es sich, Altes faellt weg.
cat > /tmp/nc_opds.sh <<'OUTER'
set -e
KAT=/hosting248937.af957.netcup.net/httpdocs/lese
mkdir -p "$KAT/buecher"

cat > "$KAT/index.php" <<'PHP'
<?php
// OPDS-Katalog. Liefert alle ePubs aus ./buecher als Feed, den KOReader lesen kann.
// Dateien aelter als AUFBEWAHRUNG Tage werden bei jedem Abruf entfernt.
const AUFBEWAHRUNG = 7;

$verzeichnis = __DIR__ . '/buecher';
$basis = (isset($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off' ? 'https' : 'http')
       . '://' . $_SERVER['HTTP_HOST'] . rtrim(dirname($_SERVER['SCRIPT_NAME']), '/');

// aufraeumen
foreach (glob($verzeichnis . '/*.epub') as $datei) {
    if (time() - filemtime($datei) > AUFBEWAHRUNG * 86400) {
        @unlink($datei);
    }
}

$dateien = glob($verzeichnis . '/*.epub');
usort($dateien, fn($a, $b) => filemtime($b) <=> filemtime($a));

header('Content-Type: application/atom+xml; charset=utf-8');
echo '<?xml version="1.0" encoding="UTF-8"?>' . "\n";
?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:opds="http://opds-spec.org/2010/catalog">
  <id>urn:moritz:lese</id>
  <title>Lesestoff</title>
  <updated><?= date(DATE_ATOM) ?></updated>
  <author><name>Moritz Schlenstedt</name></author>
  <link rel="self" href="<?= htmlspecialchars($basis) ?>/" type="application/atom+xml;profile=opds-catalog"/>
<?php foreach ($dateien as $datei):
    $name = basename($datei);
    $titel = pathinfo($name, PATHINFO_FILENAME);
    $titel = str_replace(['_', '-'], ' ', $titel);
?>
  <entry>
    <title><?= htmlspecialchars($titel) ?></title>
    <id>urn:datei:<?= md5($name) ?></id>
    <updated><?= date(DATE_ATOM, filemtime($datei)) ?></updated>
    <content type="text"><?= date('d.m.Y H:i', filemtime($datei)) ?>, <?= round(filesize($datei)/1024) ?> kB</content>
    <link rel="http://opds-spec.org/acquisition"
          href="<?= htmlspecialchars($basis) ?>/buecher/<?= rawurlencode($name) ?>"
          type="application/epub+zip"/>
  </entry>
<?php endforeach; ?>
</feed>
PHP

cat > "$KAT/buecher/.htaccess" <<'HT'
Options -Indexes
HT

chmod 755 "$KAT" "$KAT/buecher"
chmod 644 "$KAT/index.php"
echo "--- angelegt:"
ls -la "$KAT"
OUTER
scp -q /tmp/nc_opds.sh netcup:/tmp/opds.sh
ssh -o BatchMode=yes netcup 'bash /tmp/opds.sh' 2>&1 | tail -12
