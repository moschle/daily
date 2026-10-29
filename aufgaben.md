# Aufgaben

*Letzte Aktualisierung: 28. Oktober 2026*

> Regel für den Morgenbrief: Einträge mit [x] sind erledigt. Bei Widersprüchen gilt der neueste STAND-Block.

## DAUERAUFGABE (seit 28.10.2026) — Tagungen, Preise, Vorträge
Immer in der Pipeline: monatlich Calls prüfen, in die Arbeit (stille stürme, Farzona-Korpus, Analyzer, Übersetzungen) einreichbar? 2025 eine passende Sommertagung verpasst.
- [ ] **SilkRoadNLP 2027 (2nd Workshop on NLP for the Iranian language family, EACL Athen 9.–14.03.2027) — Frist 15.12.2026** (direkte Einreichung). Shared Task: Transliteration Tadschikisch-Kyrillisch ↔ Perso-Arabisch. Passt für Analyzer/ʿarūż-Skansion + Farzona-Korpus. https://www.aclweb.org/portal/node/14605
- [ ] ECIS 11 (European Conference of Iranian Studies, alle 4 Jahre, zuletzt Leiden 2023) — CfP für 2027 erwartet ca. Nov. 2026 (ECIS 10: CfP Nov. 2022); SIE vergibt auch einen Ph.D. Thesis Award. https://www.societasiranologicaeu.org/conferences/
- [ ] Symposia Iranica (St Andrews, Nachwuchs) — V war April 2026, Abstract-Frist Ende Aug. 2025; nächste Runde beobachten
- [ ] DAVO-Kongress (jährlich Herbst, CfP meist Mai/Juni) — Call 2027 beobachten
- [ ] CESS Annual Conference + ESCAS Regional (Calls meist Winter/Frühjahr) — beobachten, centraleurasia.org
- [ ] Vortrag Rzehak/Werkstattgespräch, Vortrag Berlin (s. unten) — mit stille stürme verbinden

## STAND 28.10.2026 — wazan (vormals tajikpoemanalyzer) und stille stürme
- [x] Umbenennung (GitHub moschle/wazan), Dilorom-Korpus aus den Quelldateien neu (T 40, E 34, B 33), Review aller nicht erkannten Farzona-Gedichte + drei Stichprobenrunden (gesamt 89 %, frische Stichproben 85–100 %)
- [ ] Labels (data/validierung/review.jsonl, von Claude) selbst stichprobenartig prüfen oder von einem zweiten Modell gegenprüfen lassen
- [ ] stille stürme: Fußnote „Skansion von Hand“ + Farzona-Fußnote Druckgeschichte freigeben
- [x] 29.10. MTLD im Buch: alte Werte (~149/150/232) mit keinem Analyzer-Stand seit Feb. 2026 reproduzierbar; alle Fassungen ergeben 169/161/212 → im Buch ersetzt (B ein Viertel bis ein Drittel höher statt „fast 50 %“). Wortzahlen T (šab 24, sadoi 20, kase 16) bestätigt
- [x] 29.10. Projektskizze, Mails, Farzona-Kennzahlen auf validierte Zahlen gebracht (Paket_2026-10-29.zip)
- [ ] T: drei Gedichte, die der Analyzer anders zählt als die Handzählung (25/15 statt 28/12), mit eigener Liste abgleichen

## STAND 27.10.2026 — Futro als Heimserver (Home Assistant + lokale KI über Nacht)
Ziel: Futro wie ein „Pamir Lapis One“ — läuft rund um die Uhr, Home Assistant bleibt, dazu Agent und lokales Modell, das Aufgaben ohne Eile nachts abarbeitet.
- [ ] Hardware: 8-GB-Riegel einbauen (→ 12 GB), im BIOS „Power on after power loss“ einschalten
- [ ] mSATA-USB-Adapter besorgen; mSATA als einziges Laufwerk (USB-Stick + externe Festplatte fallen weg)
- [ ] Umbau auf Debian, Home Assistant darin weiter (Backup einspielen), Werbeblocker + Tailscale mitnehmen
- [ ] Lokales Modell (8–14B, quantisiert) + Whisper für Transkription; Nacht-Warteschlange: Ordner/Kurzbefehl rein, Ergebnis morgens raus
- [ ] Erste Nachtaufgaben: Persisch-Karten aus Preply-Notizen gegen das Deck abgleichen, Diktate/Aufnahmen transkribieren, Unterlagen in Verwaltung benennen + Fristen ziehen
- [ ] Danach: MemPalace auf den Futro (für Claude am Handy, mit Zugangsschutz), Anki-Sync-Server
- [ ] Pala Note (Waveshare ESP32-S3-ePaper-1.54) prüfen: Board-Version 8 MB Flash/8 MB PSRAM? Gehäuse drucken lassen, größerer Akku; Aufnahmen lokal über den Futro transkribieren statt OpenAI

## DFG-Sachbeihilfe (Entscheidung 26.10.2026: sofort angehen)
- Antragsteller formal Purnaqcheband (Promotion nötig), Moritz schreibt den Antrag; beantragt wird die eigene Doktorandenstelle + Reise-/Sachmittel; Laufzeit i. d. R. 36 Monate; keine feste Frist
- [ ] 03.11.2026 Purnaqcheband: Zusage als Antragsteller, Zeitplan, Rolle der Fakultät
- [ ] Forschungsförderung MLU (Drittmittelberatung) um Beratungstermin bitten — Antragsformulare, Kalkulation Personalmittel, interne Abläufe
- [ ] Exposé bis 15.12. so anlegen, dass es Kern der DFG-Projektbeschreibung wird (Stand der Forschung, eigene Vorarbeiten: MA/Monografie De Gruyter, Tajikpoemanalyzer, Feldforschung 2025; Arbeitsprogramm, Zeitplan)
- [x] 26.10.2026 Erster Entwurf Projektbeschreibung: ~/Documents/Promotion/DFG_Antrag/ (ZIP, Prüfliste)
- [ ] bis 30.11.2026 vollständiger Entwurf (Belege, Korpusumfang, Kalkulation)
- [ ] 1.–15.12.2026 Gegenlesen Purnaqcheband + interne Prüfung MLU
- [ ] vor Weihnachten 2026 einreichen (über elan); Januar: Grafög + KAS aus dem DFG-Text kürzen

## ENTSCHEIDUNG 26.10.2026 — Fokus Promotion + Finanzierung
- Vollzeit-Bewerbungen ruhen (Deloitte, Ferropolis Zeitzeugen, Topographie, Grüne LSA, Görlitz, MDR KLASSIK zurückgestellt)
- Stellen-Monitor sucht nur noch Nebenjobs (bis ~20 h, Honorar, remote) sowie Promotionsstellen/Stipendien; Vollzeit max. 3/10
- Nachtdienst wird für jeden besseren Nebenjob sofort aufgegeben
- Offen als Nebenjob: Ferropolis Medienportal 50 % remote (Frist 04.11.) — prüfen, ob 20 h neben Promotion passen; BBK Künstlernachlässe Halle 20 h
- [ ] Dekanat Phil. Fak. I: Fakultätsfrist Landesgraduiertenförderung + Nebenverdienst/§ 7a GradFVO klären

## STAND 27.10.2026 — Stellen-Monitor
- [ ] **NEVA e.V. München (Netzwerk Erinnern, Verändern, Aufklären), Projektkoordination Modellprojekt „selbstbestimmt vernetzen erinnern und bilden“ — Frist 15.11.2026.** 20 h, E11, befristet, Home-Office teilweise; KI-Bewertung 7/10. Passt als Nebenjob neben der Promotion. Belege: Langenstein-Zwieberge-Band, Warte für Kultur (Förderanträge, Budget, Vereinsarbeit). Lücke: kein Bachelor in den genannten Fächern (Ausweg: vergleichbare Berufserfahrung), Türkisch nur erwünscht. Vorher klären: Präsenzanteil in München. https://muenchen-erinnern.de/2026/10/22/projektkoordination-gesucht/
- Verworfen: Orient-Institut Beirut WiMi (Promotion nötig), Schaufler Lab TU Dresden Doctoral Fellowship (Promotion in Dresden statt Halle), Zürich Cultural History of India
- [ ] Stellen-Monitor: Quelle stgs sachsen-anhalt ausgefallen (Muster `/Chancen/.+\.pdf$` findet 0 Treffer) — Muster/URL anpassen, danach `bash _netcup_deploy.sh`

## STAND 26.10.2026 (abends) — neue Stellen aus dem Monitor-Testlauf
- [ ] Ferropolis / Netzwerk Industriekultur Sachsen-Anhalt, Mitarbeiter/in Medienportal, 50 %, E11, remote + Gräfenhainichen, ab 01.01.2027, 2 J. — Frist 04.11.2026, bewerbung@ferropolis.de
- [ ] Ferropolis / Netzwerk Industriekultur Sachsen-Anhalt, Mitarbeiter/in Zeitzeug:innenarbeit, Vollzeit, E11, remote + Gräfenhainichen, ab 01.01.2027, 2 J. — Frist 04.11.2026, bewerbung@ferropolis.de (Master ODER Berufserfahrung)
- [ ] Topographie des Terrors / Dokumentationszentrum NS-Zwangsarbeit Berlin, Koordination im Bildungsbereich, Vollzeit, E9a, 2 J., ab 15.02.2027 — Frist 24.11.2026, Bewerbung über Kenjo-Portal (Erfahrung Vermittlung an NS-Erinnerungsorten gefordert)
- [ ] MDR KLASSIK Leipzig Musikvermittlung 30h — Frist 06.11.2026 (prüfen)
- [ ] BBK Sachsen-Anhalt Halle Künstlernachlässe 20h ab 01.01.2027 — keine Frist
- Verworfen: Uni Würzburg Lektorat Französisch (Französisch als Muttersprache Pflicht), Zürich MINARET (Ethnologie, anthropologisch), Botschaft Doha (Ortskraft)
- [x] Stellen-Monitor läuft auf netcup mit KI-Bewertung; Rückstand ~1.550 Stellen wird über ~10 Tage abgearbeitet; Rauschfilter eingebaut

## STAND 26.10.2026 — FÖRDERFAHRPLAN PROMOTION (ersetzt die Einzelnotizen vom 26.10.)
Projektordner mit allen Ausschreibungen, Formularen, Sachstand und Mails: ~/Projects/foerderungen (00_uebersicht/SACHSTAND.md)
Neu 27.10.: Studienstiftung Call 01.–14.02.2027 per POST (Ahrstr. 41, 53175 Bonn), Auswahl ca. Sept. 2027, Beginn frühestens 01.10.2027; braucht Erstgutachter-Fragebogen von Purnaqcheband; berufsbegleitende Promotion nicht förderbar (Nachtdienst klären). KAS-Gutachter müssen habilitiert/promotionsberechtigt sein (Rzehak prüfen). Böll braucht Nachweis Zulassung zur Promotion.
Ziele: schnelle Forschungsreise · max. 2 Jahre Promotion · keine Geldsorgen · keine Lehre · Vernetzung · Oxford langfristig.
Grundsatz: überall bewerben, beste Zusage annehmen; nur eine Lebensunterhalts-Förderung gleichzeitig, jede Nebenförderung (DÜF, Literaturprojekt, Arbeit) bei der Hauptförderung anmelden und Anrechnung schriftlich bestätigen lassen.

### Bausteine
- Landesstipendium MLU (Grafög): 1.400 €/Monat + einmalig 1.100 € Sach-/Reisekosten, 3 J., keine Lehre. Start 01.04.2027. Antrag über Dekanat, Fakultätsfrist erfragen, Weiterleitung bis 31.01.2027. Unterlagen: Erstantrag, beglaubigtes Zeugnis, Arbeitsplan, 2 Gutachten, Lebenslauf, Einkommensnachweis § 7a GradFVO. Voraussetzung: Annahme als Doktorand (HalDoc-ID 6740). Ausland >30 Tage: 8 Wochen vorher Ref. 1.3. Kontakt Heike Schmidt, 0345/55-21315.
- KAS (15.01.2027), Studienstiftung (01.–14.02.2027), Böll (01.03.2027): bei Zusage Wechsel, Landesstipendium endet. KAS bevorzugt (Auslandsförderung, Begleitprogramm). Bei KAS klären: Umgang mit laufendem Landesstipendium, Starttermin.
- DFG-Sachbeihilfe mit Doktorandenstelle: Antragsteller Purnaqcheband, Moritz schreibt. Jederzeit einreichbar, Entscheidung nach Monaten → Start frühestens Ende 2027. Abgabe der Diss. nach 2 J. möglich, Stelle läuft bis Projektende (3. Jahr für Publikationen/Postdoc-Antrag). Oxford als Projektkosten budgetieren. Parallel zu den Stipendien einreichen.
- DAAD: Forschungsstipendium für Doktorand:innen (nach formaler Annahme; 1–12 Monate) — allein möglich; mit Landesstipendium nur Aufstockung; mit Begabtenförderwerk ausgeschlossen; mit Stelle nur mit Freistellung. Risikoländerliste (Tadschikistan/GBAO) prüfen.
- DÜF-Reisestipendium (landeskundliche Reise): beantragt zur Frist 15.09.2026, Reise 01.–21.03.2027, Jury-Entscheidung etwa Mitte November 2026. Reise liegt vor Start Landesstipendium — keine Doppelförderung; Promotionsrecherche in Duschanbe mitnehmen.
- Literaturprojekt / Übersetzung: DÜF Initiativstipendium (2.000 €, ohne Verlagsvertrag; Frist 30.11. verifizieren); DÜF Arbeitsstipendium nur mit Verlagsvertrag (Runden 15.01./15.05./15.09.).
- Nach der Promotion: DFG Eigene Stelle / Walter-Benjamin-Programm (Ausland, z. B. Oxford) prüfen.

### Fristen und Termine
- [x] 27.10.2026 Antwort Dekanat (Mandy Wehse, 0345/552-4207): FRIST 11.01.2027
- [ ] 03.11.2026 Purnaqcheband: DFG-Antrag besprechen, Dienstende klären (muss 3 J. Projektlaufzeit abdecken, sonst Prof. Meier als Mitantragstellerin)
- [ ] 10.11.2026 Drittmittelservice MLU (Abt. 6): Beratung Sachbeihilfe, Kalkulation (Stelle, Reisemittel Duschanbe, Oxford); dazu klären: Ahrary als Programmierer – Code-Review/Weiterentwicklung Tajikpoemanalyzer als Auftrag an Dritte (Mittel für Sonstiges, ab 10.000 € Angebot nötig) oder als Personal (je nach Qualifikation); Vergaberegeln MLU
- [ ] Vor 10.11.2026 Ahrary um Angebot bitten: Umfang Code-Review und Härtung Tajikpoemanalyzer (Stunden, Satz) für DFG-Kalkulation
- [ ] 02.11.2026 14:00 Infoveranstaltung FAIR Data Fellowships (dt.; engl. 03.11. 14:00), Link in Ausschreibung_2027_dt.pdf auf 4memory.de
- [ ] 18.11.2026 FRIST NFDI4Memory FAIR Data Fellowship 2027 (1.500 €, 1 Monat remote, Feb–Dez 2027): Datenset aus der MA (Dilorom-Korpus, Merkmalsdatensatz) publikationsfähig machen. Unterlagen in einem PDF an fairdatafellowships.4memory.ifg@hu-berlin.de: Motivation inkl. Beratungsbedarf und Passung zur Einrichtung (max. 2000 Zeichen), Beschreibung Datenset (max. 2000 Zeichen), tabellarischer CV (max. 2 S.). Einrichtung wählen (DCH Köln: Software/Editionen/Datenbanken hosten; HAB: digitale Editionen) und vorher kontaktieren
- [ ] 27.10.2026 Projektskizze fertig machen (Korpusumfang ergänzen; ~/Projects/foerderungen/00_uebersicht/Projektskizze_Kein_Blick_auf_Berge.docx) und an die Gutachter-Mails (Purnaqcheband, Rzehak) hängen
- [ ] 27.10.2026 Mail an Ahrary schicken (unverbindliche Anfrage Code-Review Tajikpoemanalyzer, Entwurf im Chat 27.10.)
- [ ] Rzehak fragen, worauf sich der Begriff Samisdat stützt (Bände ohne Druckgenehmigung belegbar?)
- [ ] bis 06.11.2026 Data Center for the Humanities Köln kontaktieren (info-dch@uni-koeln.de): Passung Datenset, ob bezahlte Prüfung des Exportcodes durch Programmierer zulässig
- [ ] bis 06.11.2026 Historisches Datenzentrum Sachsen-Anhalt (MLU, NFDI4Memory-Co-Antragstellerin) kontaktieren: FDM für DFG-Antrag, Incubator Funds 2028
- [ ] bis 15.11.2026 Fellowship-Bewerbung fertig (Datensatz: Farzonas Werk, 22 Bände als Digitalisate; Entwurf ~/Projects/foerderungen/09_4memory/) + tabellarischer CV (max. 2 S.) als ein PDF
- [x] Texterkennung Farzona abgeschlossen 27.10.2026: 14 Bände 1994–2019, 3975 S., Zierrahmen-Bände (Найсон, Муҳри гули мино) nachbeschnitten; 5337 Gedichte, 70459 Verse im Korpus (lokal), features_public.json erzeugt (nicht gepusht). Kennzahlen: foerderungen/09_4memory/Farzona_Baende_Kennzahlen.md. Fellowship-Text auf 14 Bände korrigiert.
- [ ] 28.10.2026 Mails verschicken (Entwürfe foerderungen/00_uebersicht/mails_2026-10-28.md): Absage Stephan, Purnaqcheband (Pläne, Gutachten, DFG), Rzehak (Gutachten); Adressen eintragen
- [ ] FAIR Data Fellowship abschicken: foerderungen/09_4memory/FAIR_Data_Fellowship_Schlenstedt.pdf an fairdatafellowships.4memory.ifg@hu-berlin.de (Frist 18.11.); vorher ggf. Infoveranstaltung 02.11. 14:00 / Rücksprache DCH (info-dch@uni-koeln.de)
- [ ] Analyzer: Freivers-Erkennung validieren (Stichprobe 28.10.: ~1/3 falsch positiv durch treppenartig gesetzte gebundene Verse und Rubāʿī); Metrum jetzt persische Muster (Commit 9dc4862)
- [x] Analyzer: Metrum-Erkennung für Farzona unbrauchbar (Kāmil/Wāfir dominieren, Ramal als Mutaqārib) – vor Veröffentlichung prüfen; Fellowship-Thema Zuverlässigkeit
- [x] Farzona: Gedichttrennung über Inhaltsverzeichnisse und 56 Stichproben verbessert; 2647 verschiedene Gedichte, 39344 Verse, 4814 Abdrucke (2170 Nachdrucke verknüpft); 341 Übersetzungen getrennt (Найсон ab S. 213, Себарга ab S. 236). Kennzahlen: foerderungen/09_4memory/Farzona_Baende_Kennzahlen.md
- [x] Farzona: alle 14 Bände seitenweise geprüft (27.10.2026), Verzeichnisse am Bild abgeschrieben (toc_hand), ~500 Korrekturen + Regeln; Sammelausgabe Ҳама гул (2 Bde.) als Beleg drin, 420 nur dort belegte Gedichte markiert (erstbeleg_sammelausgabe). Korpus: 12 Bände + Sammelausgabe, 2390 Gedichte, ~36.800 Verse, 4655 Abdrucke; ocr_tesseract.py erkennt Doppelseiten; 362 Übersetzungen getrennt (Себарга bis Bandende S. 424, laut Inhaltsverzeichnis geklärt). Fellowship-Text angepasst, Korpusprojekt Tadschikisch ergänzt.
- [ ] Entscheiden: tajikpoemanalyzer-Commits pushen und features_public.json mit Farzona veröffentlichen?
- [ ] Hodgkin, Kap. 20 Routledge Handbook (Persian Poetry in the Second-World Translation System) über Bibliothek besorgen, PDF in Bookends
- [ ] 01.06.2027 Ausschreibung NFDI4Memory Incubator Funds 2028 prüfen (mit Historischem Datenzentrum; Ahrary einplanen)
- [ ] Incubator Funds (bis 50.000 €, jährlich; Runde 2027 Frist war 27.07.2026 → nächste Runde Sommer 2027): MLU ist über das Historische Datenzentrum Sachsen-Anhalt Co-Antragstellerin von NFDI4Memory (Task Area Data Connectivity) → dort Kontakt aufnehmen, auch für FDM im DFG-Antrag; Ahrary darüber finanzierbar
- [ ] 15.11.2026 Oxford Recognised Student: Bewerbungsfrist Hilary Term 2028 recherchieren
- [ ] 25.11.2026 DÜF-Entscheidung Reisestipendium prüfen → Reise 01.–21.03.2027 buchen
- [ ] 27.10.2026 Gutachten JETZT anfragen: Purnaqcheband + Rzehak (Landesstipendium nach Gliederung A–G der MLU-Hinweise, dieselben Gutachter für KAS); Rückgabe bis 04.01.2027. Rzehak ist ordentlicher Hochschullehrer und habilitiert (erfüllt MLU, KAS, Böll); Stephan als Ersatz
- [ ] 01.12.2026 Exposé/Arbeitsplan an beide Gutachter (vorgezogen vom 15.12.)
- [ ] Einkommensnachweis § 7a: Stelle Pflegedienst ab 01.11.2026 (60 Std./Monat) angeben
- [ ] 20.11.2026 Dreiländer-Orientkolloquium, Villa Tillmanns Leipzig, 8:30–17:30
- [ ] 30.11.2026 DÜF Initiativstipendium (Frist verifizieren)
- [ ] 15.12.2026 Exposé/Arbeitsplan fertig (auf 2 Jahre angelegt, eine Feldphase); Al-Manhal-/Kezana-Recherche abschließen (Testzugang bis 31.12.)
- [ ] 04.01.2027 Endcheck Landesstipendium (Gutachten da? Digital-Fassung fertig?)
- [ ] 11.01.2027 FRIST Landesstipendium: Antrag komplett mit allen Anlagen im Dekanat Phil. Fak. I abgeben (Emil-Abderhalden-Str. 6) UND vorab digital senden; Dekanat prüft Vollständigkeit, Prorektorat braucht Daten digital. Formulare (Erstantrag ausfüllbar, Gutachten-Bearbeitungshinweise für Purnaqcheband/Stephan): wisswei.verwaltung.uni-halle.de/graduiertenfoerderung__exkursions/. Zeugnis-Original zur Beglaubigung mitnehmen. Danach Fakultät: Stellungnahme + Rangliste; Weiterleitung bis 31.01.2027. Annahme als Doktorand kann der Dekan in klaren Fällen ohne Sitzung bewilligen. Mit Purnaqcheband besprechen, dass die Fakultätsstellungnahme das Vorhaben stützt
- [ ] 15.01.2027 KAS
- [ ] 01.–14.02.2027 Studienstiftung
- [ ] vor Weihnachten 2026 DFG-Antrag über Purnaqcheband einreichen (Entwurf: ~/Projects/foerderungen/05_dfg/DFG_Antrag; vorher Prof. Meier + Drittmittelservice)
- [ ] 01.03.2027 Böll
- [ ] 01.–21.03.2027 Tadschikistan (DÜF, falls bewilligt)
- [ ] 01.04.2027 Beginn Landesstipendium (falls bewilligt) → DAAD-Aufstockung für weitere Feldphase beantragen (Fristen auf daad.de prüfen)
- [ ] Oxford Hilary Term 2028 (16.01.–11.03.2028): Bewerbungsfrist Recognised Student recherchieren; Finanzierung je nach Lage über KAS / DFG-Projekt / DAAD
- [ ] Anfang 2029 Abgabe Dissertation

### Weiteres aus den Aushängen
- [ ] Purnaqcheband, „Firdawsī und der autochthone Diskurs“ (HBO 52/25) vor dem Arbeitsplan lesen
- Beobachten: Imaginamics Bridge Jena (2026: Frist 11.06.); 4memory-Fellowships nur bei Datenbank-Variante

## STAND 25.10.2026 (spät) — kultweet-Vollanalyse: Vorschläge nach Frist
- [x] (verworfen 26.10.) KAS Berlin, Referent Bundeswehr und Gesellschaft — verlangt mehrjährige Berufserfahrung, wiss. Expertise Sicherheitspolitik, sehr gute Kenntnis der Bundeswehr-Führungskultur
- [~] (zurückgestellt 26.10., Vollzeit vor Ort) Grünen-Fraktion LSA Magdeburg, Referent*in Wiss./Kultur/Digitales — Frist 31.10.2026; Anschreiben fertig (~/Documents/Bewerbungen/gruene_lsa_wiss_kultur_digitales/), PDF per Mail
- [~] (zurückgestellt 26.10.) Görlitz (Meetingpoint Memory Messiaen), Projektassistenz Zwangsarbeit, 32h E9, ab 01/2027 — Frist 02.11.2026; Anschreiben fertig (~/Documents/Bewerbungen/goerlitz_zwangsarbeit_projektassistenz/), Mail an info@meetingpointmm.eu
- [x] (verworfen 26.10., zu erfahrungslastig) MDR Leipzig, Gehobene Redakteurin — Frist 04.11.2026
- [ ] KAS Berlin, Referent Hauptabteilung Politische Bildung (Bildungsforum Berlin) — Frist prüfen (KAS-Seite: 03.–05.11.2026)
- [ ] MDR KLASSIK Leipzig, Koordination Musikvermittlung, 30h — Frist 06.11.2026
- [ ] Deutsche Welle Bonn/Berlin, Editorial Coordinator — Frist 08.11.2026
- [ ] Literarische Gesellschaft Karlsruhe, wiss. Volontariat ab 01.02.2027 — Frist 15.11.2026 (info@literaturmuseum.de)
- [ ] BBK Sachsen-Anhalt Halle, Mitarbeiter*in Künstlernachlässe 20h ab 01.01.2027 — keine Frist genannt, bald bewerben
- Verworfen: GWZO Fachlektorat Leipzig (Master Kunstgeschichte Pflicht), KBB Kuratorische Redaktion (Frist 25.10. abgelaufen)
- [x] Scoring um neue Felder erweitert, weiche Trennstriche entfernt (Commit 323be13)

## STAND 25.10.2026 — Deloitte, neue kultweet-Stellen, Monitor-Lücke
- [ ] Deloitte Lektorat/Berichtswesen München: Anschreiben fertig (~/Documents/Bewerbungen/deloitte_lektorat/), als PDF über Online-Portal einreichen
- [ ] Silke Krüger: Rückfrage an Laura zu Benefit-Start (Anzeige vs. Mail vs. Merkblatt); Auszahlungstermin schriftlich; Arbeitsaufnahme ans Jobcenter melden
- [ ] Entscheiden: Kiel NdL WiMi/Promotion (Frist 13.11., Exposé NdL/AVL nötig) · Bielefeld GRK 2650 (Frist 30.11.) · Basel Literaturvermittlung Kinder (ab 01.05.2027) · Hannover Religionswiss. (Frist 03.11., eher auslassen)
- [x] (erledigt 25.10., f123474) Stellenmonitor: kultweet nur erste 46 Einträge (keine Paginierung) — mehr Seiten/Kategorien holen; Scoring ergänzen um Lektorat, Germanistik/Neuere deutsche Literatur, Literaturvermittlung, Religionswissenschaft, Zielrichtung Promotion (Deloitte bekam nur Score 1)

## STAND 24.10.2026 — Stellenscan hochschul-job.de
- Neue Quelle im Stellen-Monitor: hochschul-job.de (Endpunkt /jm-ajax/get_listings/, geistes-/sozialwiss. Kategorien), `fetch_hochschuljob` in stellen_quellen_extra.py, eingetragen in stellen_boot.py. Vollscan 24.10.: 2.758 Stellen, 8 über Min-Score.
- [ ] **DRINGEND: TIB Hannover, WiMi semantische Erschließung von KI-Trainingsdaten, Kennziffer 41/2026 — Frist Sa 31.10.2026.** DFG-Projekt COUGAR (annotiertes Korpus ~120.000 deutscher Forschungsberichte, mit Uni Marburg), E13 TV-L, 39,8 h (Teilzeit möglich), 2 Jahre, Beginn frühestens 01.02.2027. Aufgaben: Annotationsschemata und -richtlinien, Anleitung studentischer Hilfskräfte, Qualitätssicherung, Open Data, Publikationen. Pflicht: Master in Computerlinguistik/DH/Informatik/BIW „oder verwandtem Fachgebiet“, sehr gutes Deutsch, Erfahrung in Projektkoordination oder Anleitung von Hilfskräften. Wünschenswert: INCEpTION o. ä., Sacherschließung/kontrollierte Vokabulare, Dublin Core/TEI/XML, Cohens Kappa. Argumente: tajikpoemanalyzer (Korpusaufbau), GND-Abgleich, Leitung Warte für Kultur e.V.; Lücke: kein DH-/CL-Abschluss. Bewerbung: eine PDF an Bewerbung@tib.eu oder tib.eu/bewerbungsformular-41-2026, Kennziffer + Stellenbörse im Betreff, Gehaltsvorstellung erwünscht. Kontakt Dr. Diana Slawig, 0511 762-3424.
- [ ] **Bundestagsbüro Lamya Kaddor (Grüne), wiss. Mitarbeiter/in — Frist 15.11.2026.** Vollzeit 39 h, bis Ende der 21. Wahlperiode, Anlehnung TVöD Bund. Themen: Innenpolitik mit Religions-/Gesellschaftspolitik, Sicherheitspolitik (Islamismus), Außenpolitik (u. a. Arabische Halbinsel); Initiativen, Reden, Pressemitteilungen, Innenausschuss. Gefordert: Master (ideal Politik/Jura), einschlägige Erfahrung Innenpolitik. Eine PDF (Anschreiben, CV 2 S., Masterzeugnis, Arbeitszeugnisse der letzten drei Arbeitgeber) an lamya.kaddor.ma02@bundestag.de.
- [-] Göttingen Turkologie (Prof. Ruth Bartholomä, Frist 11.12.): verworfen — Pflicht sind Türkeitürkisch-Kenntnisse plus Quellenforschung in einer Turksprache, Schwerpunkt Soziolinguistik.
- [-] Nicht passend: MLU Romanistik 4-9370/26-H (Spanisch, Frist 04.11.), Zürich Oberassistenz Islamwiss. und FU Islamwiss. Postdoc (Promotion nötig), Wien Professuren Arabistik, Tübingen DaF-Leitung E14.

## STAND 23.10.2026 — Bewerbungen
- [x] VG Wort Fachkraft Meldewesen (32 h) abgeschickt (23.10.)
- [ ] **Dubnow-Institut Wiss. Redakteur — Frist Mi 28.10.**, eine PDF an bewerbung@dubnow.de; Entwurf: ~/Documents/Bewerbungen/03_laufend/2026_Dubnow_Redakteur/
- [ ] Mail an Frau Meier mit neuem Abgabetermin (Antrag auf Annahme, Dekanat Phil. Fak. I) + Termin über promotionsverfahren@philfak1.uni-halle.de
- [-] Buchenwald, Bergen-Belsen: Fristen verstrichen · Jena Imaginamics, CAU Kiel, FZ Jülich: nicht verfolgt · Jüdische Akademie: vermutlich besetzt

## STAND 13.10.2026
- [x] Futro S940n (J5005, 4 GB, 32 GB mSATA, inkl. Netzteil) für Home Assistant bestellt; USB-Tastatur organisiert (13.10.)
- [x] Mail-Datum-Skript (netcup-Zeitfehler 08.–11.10.) ausgeführt, Ticket an netcup geschickt (13.10.)
- [ ] Di 13.10. 11:30 Telefoninterview Demenz-WG; danach flaschenpost Mini (falls Nachtdienst als Midi) oder Midi (~12 h/Wo.) entscheiden; zweite Demenzstation zurückrufen
- [ ] Jobcenter: Rücknahme SGB-II-Antrag zum 01.10. (inkl. § 16b/16c/AVGS) abschicken; EKS September + Mitwirkung bis 26.10.
- [ ] Home Assistant auf Futro: feste IP 192.168.1.250, an Speedport-LAN; Generic Thermostat für Moritz' Zimmer, Shirins Zimmer, Kinderzimmer (dritter Sensor nötig); Apple-Zuhause nach Hermann-Liebmann zusammenlegen

## STAND 09.10.2026 — Nebenjob Nachtdienst
- [ ] **Di 13.10.2026 Telefoninterview Häusliche Krankenpflege Silke Krüger GmbH**, Nachtdienst Demenz-WGs (Herbstzauber Böhlitz-Ehrenberg / Elsterpassage Plagwitz), 60 h/Monat — Stand 09.10.: doch offen dafür (Routine). Falls schon abgesagt: Mo 12.10. anrufen und wieder zusagen. Im Gespräch klären: Bereitschafts- oder Wachnacht (darf man schlafen?), Anteil Wochenenden, Nacht-/Sonntags-/Feiertagszuschläge, Stundenlohn, Vertragsart, Kündigungsfrist, Einarbeitung
- [ ] **Achtung Stipendium**: 60 h/Monat passen NICHT zu KAS (max. 20 h/Monat Erwerbstätigkeit) und Studienstiftung (max. 5 h/Woche außerhalb Forschung/Lehre). Bis Förderbeginn (frühestens Sommer/Herbst 2027) unproblematisch, dann reduzieren oder kündigen — kurze Kündigungsfrist vereinbaren
- Elsa-Neumann-Stipendium (Berlin) entfällt — Promotion jetzt in Halle
- [ ] **19.10. in Halle: ULB ausleihen** — Pirzad „Sih kitāb“ (مثل همه عصرها + طعم گس خرمالو + یک روز مانده به عید پاک, Našr-i Markaz 2005, ULB Halle DE-3) vorher im ULB-Katalog vormerken; zusätzlich nach چراغ‌ها را من خاموش می‌کنم suchen. Majid-Glossar (Nišastan-i wāža dar qiṣṣa) per Fernleihe aus SUB Hamburg. Kauf aus USA (ketab.com) verworfen: 70 $ Versand
- [ ] **19.10. zusätzlich**: Landesgraduiertenförderung Sachsen-Anhalt (Vergabe 01.04.) — fakultätsinterne Frist bei Phil. Fak. I erfragen
- [ ] **Manja Stephan antworten — die Antwort schuldet Moritz ihr, nicht umgekehrt** (NICHT absagen): Entscheidung für literaturwissenschaftliche Promotion in Halle bei Purnaqcheband erklären; fragen, ob sie **Zweitgutachterin** wird und das **zweite KAS-Gutachten** schreibt. Alternative Zweitgutachter: Rzehak (Ruhestand — in der Promotionsordnung Phil. Fak. I prüfen, ob Emeriti/Pensionierte begutachten dürfen)
- [x] **Polizei-Bewerbungen ABGESCHICKT 09.10.2026** (LKA Berlin 155-26 + Bundespolizei OSINT BPOLD 11) (Pakete fertig 09.10.2026, je 10 S., 2,8 MB, ZIP im Ordner): LKA Berlin 155-26 → karriereportal-stellen.berlin.de (j69721), Datei `Bewerbung_Schlenstedt_LKA_155-26_v2.pdf`; Bundespolizei OSINT → komm-zur-bundespolizei.de, Datei `03_laufend/2026_BPol_OSINT_Berlin/Bewerbung_Schlenstedt_BPol_OSINT.pdf`. Rangfolge Stellen: Bundessprachenamt (E13) > LKA > BPol (beide gehobener Dienst, Berlin, Vollzeit)
- Stelle statt Stipendium: Bei Zusage einer Vollzeitstelle entfallen KAS/Studienstiftung (Doppelförderung/Nebentätigkeit) → berufsbegleitend promovieren; Oxford dann über Sonderurlaub ohne Entgelt (§ 28 TVöD, nur wenn dienstliche Verhältnisse es gestatten) — im Vorstellungsgespräch nicht als Bedingung stellen
- KAS-Grenze konkret: max. 20 h/Monat Erwerbstätigkeit = ca. 2 Nachtdienste à 10 h/Monat; Studienstiftung 5 h/Woche — ob monatlich gemittelt werden darf, bei der Stiftung erfragen

## STAND 06.10.2026
- [x] Fahrdienst angeschrieben, Hörstudie angemeldet, BAPersBw angerufen
- [ ] **ZEDAR Fair Wear**: Mitgliedschaft nicht möglich (Beiträge erst ab 30 Mio. € Umsatz, Fair Wear priorisiert große Marken) — Fair-Wear-Aussagen auf zedarsilk entfernen, Ziel jetzt: Textilbündnis + Sozialaudit bei FTS (BSCI/SMETA anfragen) + Grüner Knopf; Färberei Shenghong steht auf der bluesign-Partnerliste (01.08.2026). Rechtsform: gUG für den Handel nicht tragfähig — gemeinnützigen Teil separat klären
- [ ] **ZEDAR Website-Texte** schreiben (Claim: feinste Seide für faire Preise), danach Deploy

## STAND 05.10.2026 — neue Stellen und Nebenjobs
- [x] **BfV Initiativbewerbung Farsi/Dari** (karriere@bfv.bund.de) ABGESCHICKT 05.10.2026 — Antwort 08.10.2026: Aufnahme in den Talentpool angeboten (Kennziffer Z34 - FSM-0088, Speicherung 2 Jahre); Einverständnis erteilt
- Goethe Taschkent Praktikum: nicht verfolgt (05.10., kollidiert mit Forschungsreise). Goethe Kasachstan Honorarlehrkraft: nicht verfolgen.
- [ ] DAAD Lektorate/Lehrassistenz 2027/28: Herbst-Ausschreibung pruefen (Vorjahresfrist Lehrassistenz 25.11.), Entwuerfe Beijing/Belem/Alger liegen vor
- [ ] **FZ Jülich, Referent:in Internationale Forschungskooperationen / PGSBstrong (Palestinian-German Science Bridge)** — E13 TVöD Bund, 20–39 h, ortsflexibel nach Abstimmung, befristet bis 31.03.2031. Frist nicht angegeben → zügig. Beste Passung des Stapels (Arabisch, Nahost, Geisteswiss. zugelassen). Lücken: formales Projekt-/Qualitätsmanagement, palästinensische Partner. Belege: Warte für Kultur (Förderpraxis, Berichtswesen).
- [ ] **Jüdische Akademie Frankfurt (Zentralrat), Programmleitung Schwerpunkt Israel und Naher Osten** — angelehnt an TVöD E14, VZ 40 h, 1 Jahr befristet, Übernahme angestrebt. Frist nicht angegeben. Reach: Moderation/Veranstaltungen stark; Israel-Diskurse und jüdische Perspektive müssen im Anschreiben konkret belegt werden. Umzug Frankfurt.
- CAU Kiel, Referent*in des Präsidenten (E13 TV-L, bis 31.10.2032, Frist 23.10.2026) — nicht verfolgen (Hochschulverwaltung/Promotion gefordert).
- [x] **Nebenjob Fahrdienst/Haushaltshilfe Zentrum Ost** (dsble, 21.09.2026): älterer Herr, 80 J., PG 2; Arztfahrten 1–2x/Woche, Haushalt mittwochs ca. 1 h; Bezahlung über Verhinderungspflege/Entlastungsbetrag. Kontakt feliciter@gmx.de — sofort anschreiben.
- [x] **Hörstudie Uni Leipzig** (angemeldet 06.10.) (Talstraße 33): 4 Tage, 2+1+1+2 h, 10 €/h; Blöcke Mo–Do 13–17 Uhr oder Di–Fr 9–13 Uhr, Teilnahme in den nächsten 3 Wochen. Anmeldung paul.friedrich@uni-leipzig.de mit gewünschtem Block.
- [ ] Berlitz DaF freiberuflich (ohne BAMF-Zulassung) — nur als Online-Zubrot, kein Standort Leipzig (nächster Dresden). Nachrangig.
- dsble „Studentische Literatur- und Rechercheassistenz“ — nicht verfolgen (unseriös, für Studierende).

## STAND 03.10.2026
- [x] **Mo 05.10.: BAPersBw Bewerbungsmanagement ROA anrufen** (Fr. Gombert 02203 105 2407 / Hr. Dicks 02203 105 2418, AC-Bewerbung-ROA@bundeswehr.org, Ref-Nr. 13270-P00547648-1-S). Kernfrage: Gilt beim Master-Einstieg als Oberfähnrich (2 Jahre) auch die Regel des allgemeinen ROA-Infoblatts, dass 2 Jahre nur als Sicherungsoffizier gehen und spezialisierte Verwendungen 3 Jahre brauchen? Welche Verwendungen sind mit 2 bzw. 3 Jahren möglich? Weitere Punkte: Umstellung auf ROA i.d.W. / Offizier mit Master, 2 Jahre; Einstellungstermin 2027; Lehrgangsorte erstes Jahr; Dienstposten nahe Leipzig (Heimschläfer); fachliche Verwendung (MilNW, ZOpKomBw, Sprachen) schriftlich; Promotion nebenbei; Reisen Tadschikistan/SÜ; Nebentätigkeit ZEDAR; spätester Absagezeitpunkt.
- [ ] **ZEDAR Rechtsform**: GbR (Testphase, Haftung beider) oder direkt UG — vorher Jobcenter (Einstiegsgeld, Leistungsberechtigung) und Greta klären; Entscheidung erst nach Klärung ROA i.d.W.
- [x] **Lichtenburg Prettin — abgeschickt 03.10.2026**: Anschreiben neu (Stilvorlagen, ohne Promotion), Gesamt-PDF unter Bewerbungen/03_laufend/2026_Lichtenburg_Prettin/Bewerbung_Schlenstedt_Lichtenburg.pdf (3 MB). Mail-Entwurf in Apple Mail an personalstelle@erinnern.org (BCC personnalstelle@) — nur noch absenden.
- ReCentGlobe 126/2026: nicht verfolgt (Entscheidung 03.10.2026).
- [x] **Bundessprachenamt — ABGESCHICKT 05.10.2026** (Frist 06.10.): Anschreiben am 05.10. neu als Werdegang (Übersetzen → Sprachtechnologie für ressourcenarme Sprachen → Datenerschließung), MT/ASR/LLM und Linked Data explizit; CV korrigiert (Böll-Alumnus, Typisch-DDR-Titel, Praefectus, Technik ergänzt); Paket als ZIP im Ordner. Vorher: Anschreiben am 03.10. nach Ausschreibung neu (ohne private Werkzeuge), Lebenslauf um Sprachmodelle/GND/LaTeX ergänzt, Gesamt-PDF 11 S. — über bewerbung.bundeswehr-karriere.de hochladen.
- Literaturhaus Thurgau: nicht verfolgt (Entscheidung 03.10.2026).

## STAND 01.10.2026
- [x] **SenInnSport III 15/2026 aktualisiert eingereicht am 01.10.2026** (Karriereportal j69631, dieselbe Stelle wie am 07.09.): neues Anschreiben, Paket unter Bewerbungen/03_laufend/2026_SenInnSport_III-15/Bewerbung_Schlenstedt_III-15-2026.pdf; Hinweis, dass es die Fassung vom 07.09. ersetzt
- [x] Bewerbungsordner aufgeräumt: 03_laufend ein Ordner pro laufender Stelle, Erledigtes und Abgelaufenes in 04_abgeschlossen
- [x] Jurabrief: Lesetexte nur noch aus AG/LG (Zivilrecht) bzw. VG (Verwaltungsrecht), keine OLG/BGH/OVG-Entscheidungen mehr


- [x] Rechnung 1067 Atelier Thilo Krause (Pantanal, Zoo Zürich, 21.–29.09.2026) — verschickt 01.10.2026

**Standort: Leipzig** (zurück aus Zürich seit 30.09.2026).

## ERLEDIGT, abgeschickt (Stand 20.09.2026)

- [x] Jobcenter Leipzig, Mitwirkung — hochgeladen
- [x] GRK Bonn, Kennziffer 2026/333 — abgeschickt
- [x] Gropius Bau / KBB, Volontariat kuratorische Abteilung — abgeschickt
- [x] DÜF Reisestipendium, Herbstvergabe — abgeschickt
- Uni Leipzig 119/2026 — Frist am 15.09. verstrichen, bewusst gelassen

## DRINGEND (diese Woche)

- [x] **AOK PLUS, Service-Nr. 2002205498**: Antrag freiwillige Mitgliedschaft mit ergänztem Punkt 3 — abgeschickt (Stand 25.09.2026); Ummeldung nach Leipzig beim Bürgeramt erledigt (22.09.2026), Meldebestätigung nachgereicht (01.10.2026).

- [ ] **DÜF Initiativstipendium — Frist 30.11.2026**, am 15.09.2026 im Portal verifiziert (Bewerbungszeitraum „Herbst", Einreichungsfrist 30.11.), nicht 15.09. 2.000 €, ohne Verlagsvertrag möglich. Anlagen: 3 Normseiten Übersetzung, Projektbeschreibung inkl. erstem Exposé (ca. 1 S.), Kurzbiographie, Veröffentlichungsverzeichnis, Kopie der Originalstelle. Kurzbiographie, Veröffentlichungsverzeichnis und Originalseiten sind aus dem Reisestipendien-PDF übernehmbar; neu zu schreiben ist nur die Projektbeschreibung.
- [ ] **BAMF-2026-300, Entscheider Landesasylstelle Berlin** (Interamt, Beginn 04.01.2027, SÜ1, kein Anschreiben zulässig) — Hilfstexte für die Freitextfelder liegen vor
- [ ] **flaschenpost Leipzig**: Probearbeiten als Fahrer/Kurier steht an. Midijob-Vertrag statt Minijob prüfen.
- [x] **VERZICHTET (29.09.2026) — Gastdozenturen des DÜF — Frist 30.09.2026**: Sommersemester 2027, 10.000 € plus Reisekosten. **Unterlagen fertig (3 S., 16.09.2026): biografische Angaben, Sprachen, Publikationen und Lehrerfahrung, Seminaridee „Übersetzen ohne Tradition", Zielgruppe, drei Wunschuniversitäten (DLL Leipzig, MLU Halle, HU Berlin Zentralasien-Seminar).** Zwei Vorbehalte: Die Ausschreibung verlangt Übersetzer·innen, die ihre Einkünfte überwiegend aus literarischen Tätigkeiten erzielen; und wer für das SoSe 2027 ausgewählt wird, ist von der DÜF-Ausschreibung vom 15.01.2027 ausgeschlossen — kollidiert also mit einem Arbeitsstipendium, falls der Verlagsvertrag bis dahin steht.
- [x] **NICHT VERFOLGT (03.10.2026) — Uni Leipzig / ReCentGlobe, Mitarbeiter/-in Wissenschaftskommunikation und IT — Frist 05.10.2026**, Kennziffer 126/2026, E9b TV-L, 50 %, befristet bis 30.09.2031 (ERC-Projekt „Conspiracy Theorizing from South Asia"), Bewerbung über das Online-Bewerbungsportal, adressiert an Prof. Dr. Nadin Heé; inhaltliche Fragen an Antje Zettler (Geschäftsführerin ReCentGlobe). Dienstort Leipzig, lässt sich mit Promotion und ZEDAR vereinbaren. Anschreiben über Korpusaufbau (tajikpoemanalyzer, gndmatch), Scraping- und Workflow-Praxis (Stellenmonitor als GitHub Action, Morgenbrief-Pipeline), Python-Auswertung der Langenstein-Häftlingsdaten, Radio mephisto für Audio/Öffentlichkeitsarbeit; offen benennen: kein Ethnologie-Abschluss, kein ausgewiesener Südasien-Bezug, keine Videoproduktion.
- [x] **ABGESCHICKT 09.10.2026 — Bundespolizeidirektion 11, OSINT-Sachbearbeiter/-in Berlin — Frist 14.10.2026**, TVöD E 11 plus Stellenzulage 110 €, unbefristet, Dienstort Berlin; bei Verbeamteten extern nur bis A 11 BBesO. Zugang: Laufbahnbefähigung gehobener nichttechnischer Verwaltungsdienst **oder** Bachelor Politik-/Sozial-/Kriminalistik-/Informationswissenschaften plus 18 Monate einschlägige Berufserfahrung (laut Ausschreibung beim Arbeitgeber nachholbar). Gefordert: Analyse offener Quellen, phänomenologische Kenntnisse Terrorismus/Extremismus, Englisch B2, Französisch und/oder Arabisch, Bereitschaft zu mehrtägigen Dienstreisen; Sicherheitsüberprüfung. Bewerbung über komm-zur-bundespolizei.de. Gefunden über den bpb-Infodienst (#OSINTBer). **Am 09.10.2026 im Portal hochgeladen und abgeschickt.** Nicht zu verwechseln mit Polizei Berlin LKA 155-26, gleiche Frist, anderer Arbeitgeber.
- [x] **ABGESCHICKT 09.10.2026 — Polizei Berlin, LKA 5 und 7, OSINT-Analyst/in mit besonderen Ermittlungsaufgaben — Frist 14.10.2026**, Kennziffer 155-26, gehobener Dienst, unbefristet, Dienstort Berlin, Kontakt Frau Kohls +49 30/4664-791264. Bewerbung über karriereportal-stellen.berlin.de (j69721). Zugangsvoraussetzung ist ein Bachelor in Sozial- oder Politikwissenschaften **oder einem vergleichbaren Studiengang** — damit formal offen. Gefordert: OSINT-/SOCMINT-Methoden, Grundkenntnisse des Datenverkehrs (IP, Mail-Header), gezielte Rechercheanfragen; erwünscht Analyse-/Auswertesoftware. Passt zum bereits verfolgten Profil (AWV-038 OSINT, BfV, SenInnSport) und zu den eigenen Scraping- und Auswertungswerkzeugen. Korrigiert den früheren Vermerk, LKA Berlin nehme Quereinsteiger nur für IT/Cyber und Wirtschaft.

- [x] **ABGESCHICKT 03.10.2026 — Gedenkstätte KZ Lichtenburg Prettin, wiss. Mitarbeit im Forschungsprojekt — Frist 04.10.2026 (Posteingang!)**. Projekt „Bauliche und erinnerungskulturelle Strategieentwicklung für erhaltene NS-Tatorte mit komplexer Überlagerungsgeschichte am Beispiel des Schlosses Lichtenburg“ (Kooperation FH Aachen), E13 TV-L, 20 h, 15.12.2026–31.10.2029, unter Vorbehalt der Zuwendungsbewilligung. Mit Promotion vereinbar. PDF max. 5 MB an personalstelle@erinnern.org — Ausschreibung schreibt „personnalstelle“, Adresse prüfen; Rückfragen Melanie Engler 035386 60 99 76. Gespräche vsl. KW 45. Anschreiben fertig 29.09.2026, Versand offen (Belege: Python-Auswertung Langenstein, „Grab des unbekannten Häftlings“, Buchenwald-Bibliografie, „Typisch DDR“; Lücke Bauforschung offen benennen).

## Bewerbungspipeline (Stand 07.09.2026)

### Neu im Stellenscan 29.09.2026 (Rangfolge: Dubnow · Lichtenburg · Buchenwald · VG Wort · LiteraturBasel · BPol OSINT · Bergen-Belsen)
- [ ] **Dubnow-Institut Leipzig, Wissenschaftlicher Redakteur — Frist 28.10.2026**. Transferbereich Forschungslabor „Materialität jüdischer Kultur“, E13 TV-L, 40 h (Teilzeit möglich), 2 J. befristet, Entfristung vorgesehen, Beginn 01.01.2027. Eine PDF an bewerbung@dubnow.de; inhaltliche Rückfragen Dr. Petra Gamke-Breitschopf, Dr. Caroline Jessen. Beste Passung. Schwachstelle: mehrjährige Erfahrung mit wiss. Publikationsformaten.
- [ ] **Gedenkstätte Buchenwald, Bildungsreferent:in — Frist 18.10.2026**. Unbefristet, VZ 40 h, ab 01.03.2027. Nur online über buchenwald.de/jobs-praktika; Praxisnachweis inkl. Social-Media-Portfolio oder Referenz. Gespräche vsl. KW 47.
- [ ] **VG Wort München, Fachkraft Meldewesen (Abt. Audio/AV) — ohne Frist**. 53.200–58.800 €/J. (37 h), TZ ab 32 h, 2 Tage mobil. Plan: 32 h als Zwischenlösung, 2 Tage Leipzig / 2 Tage München. Mobile Tage bei TZ passen (geklärt 29.09.2026). Bewerbung mit Wochenarbeitszeit und frühestem Eintritt an vg-wort-jobs@m.personio.de.
- [ ] **LiteraturBasel, Programmkuration ab 2027** — noch nicht ausgeschrieben, wird erst ausgeschrieben; literaturhaus-basel.ch/de/ueber-uns/offene-stellen/ beobachten.
- [ ] **Gedenkstätte Bergen-Belsen, wiss. Volontariat „Neue Dauerausstellung“ — Frist 18.10.2026 (im Brief neben Buchenwald nennen)**, Kennziffer SnG 2026-4, 50 % E13, 2 J., ab 01.12.2026, bewerbung@stiftung-ng.de. Nachrangig.
- Langenstein-Zwieberge, Ko-Kuration Dauerausstellung (E13): war für 08/2026 ausgeschrieben, befristet bis 01/2027, Verlängerung bis 05/2028 möglich — bei der Gedenkstätte nach der Verlängerungsphase fragen.

### Anschreiben fertig, Versand offen (Stand 16.09.2026)
- [x] **FRIST ABGELAUFEN — Museum Ratingen, Wissenschaftliches Volontariat — Frist 25.09.2026**, Beginn 01.01.2027, 2 Jahre, halbes EG 13 Stufe 1 TVöD, 39 h. Über das Bewerbungsportal stadt-ratingen.de unter dem Kennwort „Wissenschaftliches Volontariat im Museum Ratingen". Fachlich Frau Siever 02102/550-4183. Der Master wird verlangt und liegt vor — die früher notierte „Master-Hürde" existiert nicht mehr.
- [x] **NICHT VERFOLGT (03.10.2026) — Literaturhaus Thurgau / Bodmanhaus, Programmleitung — Frist 30.09.2026**, ca. 30 %, 5 Jahre plus Option, Beginn 01.01.2027. Per Mail an sekretariat@bodmanhaus.ch, Rückfragen Lorenz Zubler +41 79 948 99 49. Einzige Stelle im Stapel, die sich mit einer Promotion verträgt. Anschreiben nutzt den Schweizbezug: Schweizer Eltern, Kenntnis der jüngeren Schweizer Literatur über die unabhängigen Lesereihen, Kontakt zu Mohammad Abbas Salhei, der aus dem Persischen exklusiv für den Schweizer Raum überträgt — **Schreibweise des Namens vor dem Absenden prüfen, nicht verifizierbar.**
- [x] **ABGESCHICKT 05.10.2026 — Bundessprachenamt Hürth, Referent sprachtechnologische Fachanwendungen — Frist 06.10.2026**, E13 TVöD unbefristet, Voll- oder Teilzeit, Homeoffice möglich. PDF-Druckversion über bewerbung.bundeswehr-karriere.de. Anschreiben argumentiert über die Masterarbeit als translationswissenschaftliche Arbeit plus die eigenen Werkzeuge (tajikpoemanalyzer, GND-Abgleich, Morgenbrief-Pipeline, Stellenscraper, Persisch-Englisch-Wörterbuch) und benennt die fehlende CAT-Praxis im Behördenbetrieb offen. Kollidiert als unbefristete Vollzeitstelle mit einer Promotion.
- [x] **FRIST ABGELAUFEN — ZLB Berlin, Kulturgutschutz und Sammlungsmanagement — Frist 30.09.2026**, E11 TV-L unbefristet, mind. 75 %, Kontakt Elisabeth Feß +49 30 90226-514. Kein Anschreiben gebaut — fachlicher Kern (präventive Konservierung, Materialkunde, Notfallmanagement) liegt neben dem Profil.
- Brücke-Museum Outreach und Bildung: Frist war 10.09.2026, abgelaufen.

### Promotionsfinanzierung — geprüft am 16.09.2026
- [x] **ENTFÄLLT (Promotion in Halle, nicht Berlin) — Elsa-Neumann-Stipendium des Landes Berlin (NaföG) — Bewerbungsrunde 16.09.–11.11.2026.** 1.350 €/Monat plus 100 € Sachkostenpauschale, zunächst bis zu zwei Jahre, Ende spätestens nach drei Jahren; Förderbeginn 1. April. Gefördert werden Promotionen an den vier Berliner Universitäten, Einschreibung und Betreuung dort nötig; zur Antragstellung genügt, dass der Zulassungsantrag eingereicht ist. Geschäftsstelle für die wissenschaftlichen Fächer über die Berliner Universitäten (FU/DRS-NaföG). **Konflikt: Das Gespräch mit Manja Stephan ist erst „ab November" verabredet — für diese Runde muss es in die erste Novemberwoche und der Zulassungsantrag unmittelbar danach raus. Sonst April-Runde 2027.**
- [ ] **Böll-Promotionsstipendium — Portal 15.01.–01.03.2027.** Voraussetzung: Zulassung zur Promotion an einer staatlichen Hochschule, erste Vorarbeiten abgeschlossen, überzeugendes Exposé. Als Alumnus starke Passung. Dieselbe Abhängigkeit von der Betreuungszusage wie Elsa-Neumann, nur mit vier Monaten mehr Luft.
- [ ] **Landesgraduiertenförderung MLU Halle** (Purnaqcheband-Rückfall): Vergabe jeweils zum 1. April, Antrag über die Fakultät, deren interne Frist deutlich früher liegen kann — bei der Philosophischen Fakultät I nach der Frist für den 01.04.2027 fragen. Betreuung durch eine/n nicht im Ruhestand befindliche/n MLU-Hochschullehrer/in erforderlich (Rzehak geht in Pension, scheidet aus).
- [ ] ASEEES-Vollmitgliedschaft läuft am 31.12.2026 aus — Verlängerung nötig für REECAS NW 2027 (Seattle, 15.–17.04.2027). CESS-Mitgliedschaftsentscheidung war auf November 2026 vertagt.
- Überholt: lyrikline-Aufnahmen waren für September 2026 in Tadschikistan geplant — Reise verschoben, Termin mit Heiko Strunk neu ansetzen. DAAD-Lehrassistenz: Zyklus 2027/28 ist das letzte sichere Fenster, Master darf bei Antritt keine zwei Jahre alt sein.

### Entwürfe liegen vor, Versand unklar (Stand 03.09.2026)
- BfV AWV-2026-062 (Referent Islamismus/islamistischer Terrorismus) — Anschreiben datiert 02.09.2026
- DFG GRK 3125 Bonn, Kennziffer 2026/333 — durch das neue Paket vom 07.09.2026 ersetzt
- Uni Leipzig Finanzen 119/2026 — Anschreiben datiert 02.09.2026
- BAMF-2026-300 — Interamt-Hilfstexte statt Anschreiben

### Eingereicht, wartend
- [x] **SenInnSport Berlin, Referent/in AG III C 1 — Strategische Steuerung der Bekämpfung des islamistischen Terrorismus, der Deradikalisierung und der Radikalisierungsprävention**, Kennziffer III 15/2026, E13/A13h, Dienstort Klosterstraße 47 Berlin, Vollzeit unbefristet — **eingereicht am 07.09.2026** über das Karriereportal Berlin (Gesamt-PDF, 8 S.: Anschreiben, Lebenslauf, MA-Urkunde/-Zeugnis, BA-Urkunde, Arabisch-Zertifikate)
- [x] BfV AWV-2026-022 (Auswertung Islamismus, Berlin) — eingereicht 13.04.2026. Zeugnisse nachreichbar über Personalgewinnung-AWV@bva.bund.de
- [x] BND AWV-2026-045 — abgeschickt
- [x] KSK-Antrag (Künstlersozialkasse) — eingereicht, Bescheid steht aus
- [x] Uni Hildesheim E13 50%, Kennziffer 2026/76 — eingereicht 15.05.2026

### Aktiv zu bewerben
- [ ] **SenInnSport Berlin III 15/2026** — bereits eingereicht am 07.09.2026. Der bpb-Infodienst führt die Stelle am 23.09.2026 weiterhin mit Frist 01.10.2026 (Karriereportal j69631) — prüfen, ob das dieselbe Ausschreibung ist; falls es eine zweite Runde ist, erneut bewerben.
- [ ] Tier 1 aus dem Mai-Stand, **Fristen vor Bearbeitung einzeln prüfen**: zenith Magazin Berlin, De Gruyter/Brill Volontariat, UniBw München Arabistik E14, GEI Braunschweig, sujet Verlag Bremen, Bundessprachenamt Hürth
- [ ] Tier 2 aus dem Mai-Stand, ebenfalls Fristen prüfen: Matthes & Seitz, Jena LfbA Persisch, GIZ Tadschikistan, Haus für Poesie, LfV NRW, FU Berlin Islamwissenschaft WiMi 50% (Frist unklar, service.bund.de prüfen)
- [ ] FU Berlin Arabisch-Lehrkraft (LfbA, 50%, E13, Mutterschutz) — Ausschreibungsstand prüfen
- [ ] AVP Düsseldorf 80% Projektleitung Prävention/De-Radikalisierung (rolling, bewerbung@a-v-p.org)
- [ ] MfD München Maghreb Circular Migration (Frist erfragen: joachim.scheurer@munichforum.org)
- [ ] AwareNet Hannover E13 Islamismusprävention (Deadline prüfen)

### Absagen
- Auswärtiger Dienst höherer Dienst: am Test vom 01.09.2026 nicht teilgenommen
- Deutsches Hygiene-Museum (Stand 26.08.2026)
- AIWG Frankfurt „Weiter Sprechen" (02.07.2026)
- BfV AWV-2026-020
- GIZ develoPPP
- Bayreuth Islam-in-Afrika E13 — eigene Absage 12.05.2026 (Pendelaufwand, kein Profilmatch)
- BfV Rechtsextremismus-Stelle — eigene Absage
- DAAD Regellektorat Nachausschreibung 2026/27 — Stellen vergeben

### Nicht verfolgen / verworfen
- Hanns-Seidel-Stiftung München, Projektkoordination Nordost-/Zentralasien, 19,5 h, E10, Frist 30.09.2026 — nachrangig, nicht verfolgen
- AWV-048, BND-IT, Aktion-Hunger, DaMOst AntiRaktiv, HKW Volontariat
- BKA-Direkteinstieg höherer Dienst nicht möglich. **Korrektur 16.09.2026: LKA Berlin schreibt auch OSINT-Stellen im gehobenen Dienst aus (Kennziffer 155-26), der Vermerk „nur IT/Cyber und Wirtschaft" war zu eng.** BfV bleibt daneben der sinnvollste Sicherheitsbehörden-Pfad für dieses Profil.
- BayLfV: Initiativbewerbungen nicht zulässig (Stand April 2026), lfv.bayern.de/karriere monatlich prüfen

### Vorbereitung Herbst-/Winterausschreibungen
- [ ] **DAAD-Lehrassistenz 2027/28** — seit 15.07.2026 ausgeschrieben, Bewerbungsschluss vermutlich Ende November 2026. **HAT VERFALLSDATUM** (MA max. 2 Jahre alt), letztes sicheres Fenster. Standorte priorisieren: Iran, Tadschikistan, Algerien, Tunesien, Jordanien, Libanon, Türkei, Italien.
- [ ] **DAAD-Lektorat Hauptausschreibung Oktober 2026** für 2027/28 — Materialien für Beijing CNU, Belém UFPA, Alger 2 (CV + Gutachtenentwurf als .md) liegen vor
- [ ] **Erasmus+ Praktikumsförderung** — bis ~März 2027 nutzbar, Priorität. Schweizer Praktika laut Leonardo-Büro Magdeburg nicht förderfähig; vor einem CH-Track Rückfrage bei Anna Kostov, MLU International Office, +49 345 55 21579. Favoriten: Droschl Graz, Verdier Lagrasse.
- [ ] Mercator-Kolleg — Frist ~15. Juni jährlich, erfordert bestehenden Arbeitsvertrag
- [ ] ZfA-BPLK: MA-Anerkennung („vergleichbar" zu Master DaF) klären, ZfA +49 22899 358-74209

## ZEDAR Silk — Entscheidungspunkt 06.10.2026

In zwei Wochen werden die Samples gesichtet und die Produktionsentscheidung getroffen. Bis dahin müssen die folgenden Punkte geklärt sein.

- [ ] **Importgewerbe anmelden** (Ausfüllhilfe: zedar_gewa1_ausfuellhilfe.md, 03.10.2026) (Leipzig, auf Moritz allein), Betriebsart Haupterwerb — Voraussetzung für alles Weitere; danach EORI-Nummer beantragen und Geschäftskonto eröffnen. Ablauf in zedar_gewerbeanmeldung.md.
- [ ] **Website zedarsilk.com weiterentwickeln**: Fotos und Blog vorbereiten, Produktdarstellung der Launch-Linie, Shop-Funktion für den Verkaufsstart 2026.
- [ ] **Import- und Zollfragen klären** (IHK Leipzig): Einfuhrabgaben und Zolltarifnummern für Seidenbekleidung, Einfuhrumsatzsteuer, Ursprungsnachweise, Textilkennzeichnung.
- [ ] **Vermarktungsfragen klären**: Preisfindung gegen den USD-Einkauf (Wechselkursrisiko liegt bei ZEDAR), Verkaufskanal, Versand- und Retourenabwicklung, Kommunikation der Fair-Wear-Position.
- [ ] **Rechtliches vor der Bestellung**: GbR-Innenvertrag mit Greta, UG-Gründung (Oktober 2026), Impressum/AGB/Widerruf auf die tatsächliche Rechtsform ziehen.
- [ ] **Finanzierung**: zweckgebundenes Darlehen 7.500 € (Eingang voraussichtlich Oktober). Antrag auf Einstiegsgeld § 16b, Leistungen § 16c und AVGS Gründungsberatung ist am 15.09.2026 beim Jobcenter Leipzig gestellt — offen sind die Unterlagen für die Tragfähigkeitsprüfung (Businessplan, Kapitalbedarfs- und Finanzierungsplan, Umsatz- und Rentabilitätsvorschau über drei Jahre).
- [ ] Erste Produktionscharge im November 2026 bestellen und bezahlen — hängt an der Entscheidung vom 06.10.

## Promotion

### Promotionsstipendien + Oxford — Plan (Stand 09.10.2026)
Entscheidung: Promotion in Halle (Phil. Fak. I, Purnaqcheband), Beginn 01.01.2027. Noch nirgends beworben. Reihenfolge **KAS → Studienstiftung → Böll**. Parallelbewerbungen erlaubt, aber nur ein Stipendium (keine Doppelförderung). Bei KAS und Studienstiftung **nur ein Versuch** — nach Ablehnung keine erneute Bewerbung.
- [ ] **19.10.2026 Termin Purnaqcheband**: Antrag auf Annahme unterschreiben lassen; nach nächster Sitzung des Promotionsausschusses Phil. Fak. I fragen (entscheidet, ob KAS 15.01. klappt); Gutachten für KAS (formlos) + Studienstiftung (Betreuerfragebogen) + Böll (Fachgutachten-Formular) ankündigen; Oxford-Plan und Unterstützungsbrief ansprechen; Zweitgutachter:in für KAS-Gutachten klären
- [ ] **Nebentätigkeit prüfen** vor jeder Bewerbung: Studienstiftung max. 5 h/Woche außerhalb Forschung/Lehre; KAS max. 20 h/Monat Erwerbstätigkeit. Gesang/Bildhauerei muss reinpassen
- [ ] **Exposé** 5–10 S. (KAS-Format: Motiv, Problemaufriss, Lösungsansatz, Methoden, Arbeits-/Zeitplan, Literaturverzeichnis; Erstbetreuer im 1. Absatz) — Basis für alle drei Bewerbungen; fertig bis Mitte Dezember
- [ ] **KAS — Frist 15.01.2027, 12:00 Uhr** (Portal campus.kas.de). Voraussetzung: Zulassung zur Promotion liegt vor, sonst **15.07.2027**. Unterlagen: ausformulierter Lebenslauf 3–5 S., tabellarischer CV, Abiturzeugnis, Masterzeugnis, Exposé, 2 Gutachten (eins vom Erstbetreuer, bei Frist max. 6 Monate alt). Auswahltagung ca. 4 Monate nach Frist (~Mai 2027). Werte-Nähe und Ehrenamt sind Pflichtkriterien (Warte für Kultur, Schöffenamt). 1.650 €/Monat + 100 € Forschungspauschale; Auslandsaufenthalte und Studiengebühren im Ausland auf Antrag bezuschussbar (6 Wochen vorher)
- [ ] **Studienstiftung — Call 01.–14.02.2027**, per Post (einseitig, ungeheftet) an Studienstiftung, Team Promotionsförderung, Ahrstr. 41, 53175 Bonn. Auswahlsitzung ~Sept 2027, Beginn frühestens 01.10.2027. Zulassung erst zum Förderbeginn nötig. Betreuerfragebogen vom Erstgutachter. Bereits bezogenes Promotionsstipendium wird zu 100 % auf die Förderdauer angerechnet. Weitere Calls: 01.–14.06.2027, 01.–14.10.2027
- [ ] **Böll — Frist 01.03.2027** (Portal öffnet ~6 Wochen vorher). Zulassung zur Promotion nötig; 2 Fachgutachten (Formular); Stufen: schriftlich → Gespräch Vertrauensdozent:in → digitales Auswahlgespräch. Nachrangig (Programm schwach, Ehrenamtsgutachten)
- [ ] **Oxford Recognised Student, Hilary Term 2028** (Full Term 16.01.–11.03.2028; ggf. + Trinity 23.04.–17.06.2028; max. 3 Terms). Gebühr AMES 2026/27 £15.940/Jahr ≈ £5.300/Term, keine Unterkunft; Alternative OSGA (Middle East / Russian & East European Studies) £2.000/Term + £50 Bewerbungsgebühr. Kein Oxford-Abschluss — im CV: „Recognised Student, Faculty of Asian and Middle Eastern Studies, University of Oxford“. Unter 6 Monate: Visitor-Route
  - [ ] Anfang 2027 (nach Annahme): Prof. Dominic Parviz Brookshaw (Soudavar Chair in Persian Studies; Dichterinnen der persischsprachigen Welt, moderne Lyrik) als Academic Advisor anfragen — Abstract, ANOR/De-Gruyter-Publikation, 2–3 Übersetzungen mitschicken; vorher Purnaqcheband einbinden
  - [ ] Unterlagen (OSGA-Liste als Richtschnur): Bewerbungsschreiben, Unterstützungsbrief Halle, Zeugnisse, Forschungsvorhaben 500–1.000 Wörter Englisch, 2 Referenzen, CV
  - [ ] Bewerbung spätestens **Mitte Oktober 2027** einreichen (≥3 Monate vor Ankunft; besser früher)
  - [ ] Finanzierung: KAS-Auslandszuschuss + Studiengebührenzuschuss beantragen (6 Wochen vor Reise); MLU International Office fragen, ob ein Erasmus+-Abkommen mit Oxford kommt (UK ab 2027/28 wieder dabei; Doktorandenmobilität 2–12 Monate)
  - Oxford Nizami Ganjavi Centre: Visiting Fellowship (£2.500/Monat, 3–9 Monate) erst **nach** der Promotion möglich (Doktorgrad + Heimatinstitution nötig) → Postdoc-Option merken
- [ ] **MLU InGrA** nach Annahme kontaktieren: Qualifizierungsprogramm, Förderberatung (funding4docs)

- [ ] **DRINGEND: Manja Stephan antworten — Moritz schuldet ihr die Antwort** (Stand 25.09.2026)
- Zweifel (25.09.2026): ob mit Stephan eine durchführbare und sinnvolle (anthropologische) Arbeit zustande kommt; Purnaqcheband würde ggf. flexibler betreuen. Wunsch: Übersetzen ins Zentrum stellen.
- [x] Betreuungsanfrage an Manja Stephan abgeschickt (28.07.2026)
- Antwort 31.07.2026: keine Zu-/Absage, inhaltlich offen. Forschungsfreisemester ab Mitte August, bis Ende Oktober nicht in Berlin — **Gespräch über mögliche Themen ab November**.
- Themenrichtung Stephan: „Alltagsleben" des freien Verses — wer schreibt für wen und warum, unter welchen Bedingungen; Verhältnis zur klassischen Dichtung; Migration/Diaspora, Geschlechterverhältnisse, Nation-Building, Social Media und KI
- Purnaqcheband (MLU Halle) als Zweitgutachter bzw. Halle als reibungsloser Rückfall
- [ ] GRK Heidelberg „Ambivalent Enmity"
- [ ] Uni Bayreuth Promotionsstelle Islamwissenschaft
- [ ] Exposé Dissertation (1 Seite Lentz/Draesner, 10–15 S. Böll)
- Studienstiftung und Böll: siehe Plan oben (Stand 09.10.2026)

## ANOR / MA-Publikation „stille stürme"

- MA am 10.06.2026 mit 1,0 bewertet; Aufnahme in die ANOR-Reihe (De Gruyter Brill) am 13.07.2026 zugesagt
- [x] (27.10.2026 erledigt: Zählung aufgegeben, Gruppen nach Jahrzehnten (1960er, 1980er/90er, nach dem Bürgerkrieg), Fußnote mit Belegen; Seiten Shafipour auf 57–74 korrigiert) Vor Drucklegung: „vierte Generation“ im Manuskript (body.tex Z. 297, 301, 311, 313) korrigieren — Quellen stützen die Zählung nicht (Shafipour Fomeni/Vafaei 2020: Gulruxsor = 5. Generation; Khodayar/Hooman 2023: Strömung „soziale Romantik“, keine Generationen). Neue Texte in Bookends (27.10.2026)
- Rzehak schreibt das Peer-Review-Gutachten (Anfrage 22.08.2026); Herausgeberinnen peilen die Ausgabe noch im Kalenderjahr 2026 an
- Entscheidung 22.08.2026: Pabst-Anmerkungen werden nicht eingearbeitet; stattdessen etwaige Anmerkungen aus Rzehaks Peer-Review abwarten
- [ ] Vortrags-/Werkstattgesprächstermine mit Rzehak Mitte Oktober nach Semesterbeginn besprechen

## Schreibprojekte / Persische Dichtung

- [ ] **hochroth Bielefeld, persophone Anthologie**: interne Beratung angekündigt, seit Juli keine Rückmeldung — nachfassen, laut Tillmann Severin hilft beharrliches Nachhaken. Verlagsvertrag schaltet DÜF-Arbeitsstipendium, Looren, LCB und VdÜ-Vollmitgliedschaft frei.
- [ ] **Weitere Verlagsadressen für die Anthologie** (Empfehlung Severin, 07.09.2026): **hochroth Berlin**, berlin@hochroth.eu, unter den Standorten auf Übersetzungen spezialisiert; **Klak Verlag Berlin**, Verleger Jörg Becken, info@klak-verlag.de, Paul-Lincke-Ufer 44a — hat Übersetzungen aus dem Persischen im Programm. Verlagshaus Berlin scheidet aus — inhaltlich nicht passend, Severin steigt im nächsten Jahr als Verleger aus. Entwürfe für alle drei Mails plus Antwort an Severin liegen vor (15.09.2026).
- [ ] Severin möchte mehr über das Anthologie-Projekt erfahren — Material schicken oder erzählen
- [ ] **Übersetzungen veröffentlichen — Tipps Peter Sipos (20.09.2026)**, dranbleiben:
  - [x] Peter hat Dagmara angeschrieben (Stand 25.09.2026)
  - [x] Übersetzungsmappe als PDF (Garamond, Transliteration auf h-Stand) erstellt (25.09.2026)
  - [ ] Edition Lyrik Kabinett bei Hanser anfragen (Hg. Michael Krüger, Piero Salabè, Holger Pils; zweisprachige Reihe)
  - [ ] Roughbooks anfragen
  - [ ] Yevgeniy Breyger, Michael Lentz, Kerstin Preiwuß ansprechen
  - [ ] Werkstätten und Netzwerke unter Übersetzer:innen suchen; kleine Bewerbungen für Standing und Netzwerk
  - [ ] Reiseberichte einbinden: eigenes Buch oder Nachwort zu den Übersetzungen
- [ ] Gafforova: Übersetzung des Farzona-Gedichts weiterhin offen
- [ ] lyrikline-Neuaufnahmen — hingen an der Tadschikistan-Reise, die auf unbestimmte Zeit verschoben ist. Alternative Aufnahmewege prüfen (Kontakt Heiko Strunk).
- [ ] MA-Original an Dilorom übergeben — ebenfalls verschoben mit der Reise
- [ ] Kommentierter Übersetzungsessay (Akzente / Sprache im technischen Zeitalter / Sinn und Form)
- [ ] Egon Schmandt Lyrik — Artikel aufarbeiten
- [ ] Westsahara-Artikel für dis:orient
- [ ] Yage-Projekt Exposé (Bogotá → Putumayo → Lima → Pucallpa, 2027, Kulturstiftung Sachsen Max Uhlig Reisestipendium)
- [ ] Musikpodcast (iranischer Jazz)
- [ ] Schreibkollektiv mit Maja Maj und Yara Moritz (Konzept: PROJEKT_maja-maj-yara-moritz.md)
- [ ] Texte platzieren (Lettre International u. a.) und Zeitungstexte schreiben
- [x] Morgenbrief: Leseübung zu schwer — umgebaut am 26.09.2026: Text aus dem Anki-Wortschatz (gelernte Karten, bekannt_fa.json), Prüfung auf mind. 95 % bekannte Wörter mit bis zu drei Versuchen, max. 5 neue Wörter pro Tag, glossiert, als .apkg im Mailanhang. Wortschatz auffrischen: `python3 bekannt_aktualisieren.py` am Mac, dann committen und deployen
- [ ] Morgenbrief Public Version (generisches Repo)
- [x] **Morgenbrief per Mail statt Kindle** — umgestellt am 26.09.2026: Versand an MORGENBRIEF_TO (in /automat/zugang.env auf netcup), Text im Mailtext, ePub im Anhang; ohne die Variable fällt er auf den Kindle zurück. Offen: FAZ-Ausgabe ebenfalls per Mail ausprobieren (faztokindle)

## Herbst 2026

- [ ] Afghanistan-Reise
- [ ] Arbeit auf dem Bau
- [ ] Vortrag in Berlin
- [ ] evtl. Workshops
- [ ] Promotion organisieren, weitere Artikel schreiben
- [ ] Marseille Anfang Oktober, ein paar Tage — Kammerchorprojekt von Lucas
- Tadschikistan: auf unbestimmte Zeit verschoben (Stand 22.08.2026), separat, bei weniger Hitze und mit mehr Zeit und Geld
- Marokko/Taghazout Oktober: abgesagt (Stand 31.08.2026)

## Stipendien & Förderungen (Zeitleiste ab September 2026)

### September
- [ ] DÜF Arbeitsstipendium Herbstvergabe — Frist 15.09. (nur mit Verlagsvertrag)
- [ ] DÜF Reisestipendium Herbstvergabe — Frist 15.09.
- [ ] DÜF Aufenthaltsstipendien Visby/Arles/Straelen — Frist 15.09.
- [ ] DÜF Looren Aufenthalt — Frist 01.09. (verstrichen, nächste Runde vormerken)
- [ ] GRK Bonn — 17.09.
- Gastdozenturen des DÜF — 30.09. — **verzichtet (29.09.2026)**: Einkommensvoraussetzung nicht erfüllt; hält die DÜF-Runde 15.01.2027 frei.

### Oktober / November
- [ ] DAAD-Lektorat Hauptausschreibung Oktober für 2027/28
- [ ] DAAD-Lehrassistenz Bewerbungsschluss vermutlich Ende November 2026
- [ ] DÜF Initiativstipendium — **Frist 30.11.2026** (verifiziert 15.09.2026), 2.000 €, ohne Vertrag möglich
- [ ] NRW Arbeits-/Recherchestipendien — Frist 30.11.
- [ ] Kunststiftung Sachsen-Anhalt Arbeitsstipendium — Frist November (1.500 €/Monat)
- [ ] Georges-Arthur-Goldschmidt-Programm (DE/FR/CH, Nachwuchs) — Frist 18.10.2026. Nur mit einem Projekt Französisch→Deutsch sinnvoll.

### 2027 und später
- [ ] DÜF Arbeits-, Reise- und Bode-Stipendium (Mentorat) — Frist 15.01.2027 (frei, weil Gastdozentur nicht beantragt)
- [ ] Paul Celan Fellowship (Übersetzung geistes-/sozialwiss. Werke) — Frist 16.01.2027
- [ ] Culture Moves Europe (Mobilität) — Frist 30.04.2027
- [ ] Stuttgarter Schriftstellerhaus, Aufenthalt für Autor·innen-Übersetzer·innen — Frist 31.08.2027
- [ ] Kulturstiftung Sachsen — Bewerbungsphase ab Mai, Frist 01.07. (Max Uhlig für Yage)
- [ ] Berliner Übersetzerwerkstatt — Frist 15.06.
- [ ] Wien Angewandte PhD in Art / Wien Akademie PhD in Practice — voraussichtlich Februar 2027
- [ ] DMG-Forschungspreis (5.000 €) — nächster DOT, voraussichtlich 2029

## Sprachen

- [ ] Tägliches Sprachtraining: Arabisch + Persisch (je 20–30 Min.)
  – GLOSS täglich (rotiert nach Tagesparität)
  – Pimsleur Arabic / Farsi, Glossika Persian
  – Harry Potter Persisch abends
  – *Once Upon a Time in Iran* (Khatoon) Hörverstehen
  – Preply: Lebanese 2x/Woche, Afghan Farsi 1x/Woche
- [ ] AVGS Persisch-Einzelcoaching (Berlitz) — Anfrage läuft
- [ ] Bildungsgutschein Französisch C1 (für Auswärtiges Amt)

## Mitgliedschaften & Vernetzung

- [ ] DMG (Deutsche Morgenländische Gesellschaft) — Mitgliedschaft beantragen
- [ ] VdÜ Kandidatenstatus beantragen (Vollmitglied nach Verlagsvertrag)
- [ ] GiG (Gesellschaft für interkulturelle Germanistik) prüfen
- [ ] SIE (Societas Iranologica Europaea) — langfristig, 2 Bürgen nötig
- [ ] H-Net + H-Soz-Kult für CfP-Alerts registrieren
- [x] ASEEES Vollmitglied seit Mai 2026 (Independent Scholar, Leipzig)

## Stellenmonitoring

- stellen_check.py v2.0 (Min-Score 3): H-Soz-Kult, kultweet, service.bund.de, arthist.net, jobs.ac.uk
- [x] **stellen_check.py überarbeitet → v2.3** (25.09.2026): ASPS-Feed neu, Fehlertexte und Ausfall-Mail, Dubletten zusammengeführt, Filter um OSINT/Sicherheit, Dari/Paschtu, Promotion/Forschung erweitert, „Sonntag“-Fehlalarm raus. Offen: bpb-Infodienst, H-Net, academics.de und interamt bieten keinen maschinenlesbaren Feed — weiter manuell prüfen.
- bpb-Infodienst Radikalisierungsprävention, Stellenangebote: bpb.de/themen/infodienst/304029/stellenangebote/
- Google und RapidJob geben veraltete Ausschreibungen fälschlich als neu aus (04.08.2026) — Datum immer gegenprüfen
- [ ] BfV-Stellenportal monatlich, lfv.bayern.de/karriere monatlich
- [ ] GIZ Praktika (jobs.giz.de): Naher Osten, Zentralasien, Klimaschutz
- [ ] SWP Berlin / DGAP / ZOiS Berlin / Goethe-Institut / Orient-Institut Beirut / zenith / Carlo-Schmid-Programm

## Plan B Landschaftspflege (mit Bruder besprechen)

- [ ] Mit Bruder über gemeinsame Highland-Cattle-Mutterkuhhaltung sprechen
- [ ] Standort: Bayern (Allgäu/Frankenalb auf Zürich-Achse) ODER Galgata/Umbrien
- [ ] Kontakte: Eble Osterzell (hochlandrinderzucht.de, Allgäu), Markus Wolf 91349 Egloffstein, Bichlerhof Oberbayern
- [ ] Variante Agri-PV mit Hühnern prüfen
- [ ] Schlachtplan-Doku: schlachtplan_weidehaltung.md

## Garten (Roitzsch)

- [ ] Zwischenbau planen und umsetzen
- [ ] Sanitärinstallation weiterführen
- [ ] Gartenhausdach: Sanierung / Überdeckung der Dachpappe
- [ ] Wasserführende Heizung (kleiner Holzofen + Handtuchheizkörper Thermosiphon)

## Wohnung

- [ ] Kachelofen-Sanierung: Zustand klären, Ofeneinsatz
- [ ] Küche: Gastro-Edelstahlmöbel, offene Entscheidungen

## Auto

- [ ] Peugeot 309: Werkstattermin Leuner Dresden vor nächstem Dresdenbesuch (Kraftstoffstutzen/Flansch Benzinpumpe), danach verkaufen
- [ ] VW Sportsvan von Oma kaufen (~8.000 €, Ratenzahlung)
- [ ] ERGO-Rechtsstreit (Az. KS0731 23075-0005, Anwältin Turan-Agdas)
- [ ] RCD330 Radio für Sportsvan klären

## Konsumiges

- [ ] Vivobarefoot Support: retroaktiver 40%-Rabattcode auf Bestellung DE000802538 (REV-015094)
- [ ] Cranston R9Max Faltrad — Farbwechsel-Anfrage offen

## Laufend

- [ ] **Umzug Websites zu netcup (04.10.2026)** — neue Fassungen von warte.org, moritzschlenstedt.de und zedarsilk (Spiegel der Vercel-Seite) liegen in ~/Projects/websites und in den httpdocs auf netcup. Offen: Inhalte prüfen, Impressum-Anschriften ergänzen, Let's-Encrypt-Zertifikate ausstellen, DNS von warte.org und moritzschlenstedt.de von Carrd auf netcup (46.38.249.87) umstellen, danach Carrd und Vercel kündigen
- [ ] **zedarsilk.com von Squarespace zu netcup transferieren** — Auth-Code über Greta; iCloud-Mail-Einträge (MX, TXT, DKIM) vorher sichern und bei netcup wieder eintragen
- [ ] **manitu kündigen**, sobald Shirins und hanarhupkas alte Mails ins netcup-Postfach umgezogen sind
- [x] Stellen-Monitor auf GitHub Actions deaktiviert (04.10.2026), läuft nur noch auf netcup
- [x] VG Wort Anmeldung (03.04.2026)

## Erledigt (Juni–August 2026)

- [x] MA-Note 1,0 (10.06.2026)
- [x] Aufnahme in die ANOR-Reihe zugesagt (13.07.2026)
- [x] Betreuungsanfrage an Manja Stephan (28.07.2026)
- [x] Artikel „Typisch DDR" für Berliner Debatte Initial, Heft 37(1) 2026 — Publikation bestätigt
- [x] Bürgergeld/Anlage EKS für 18.06.–31.07.2026 eingereicht; zum 31.07.2026 abgemeldet, Wechsel in die freiwillige Krankenversicherung
- [x] Camino Primitivo (Mai/Juni 2026), Ledro Trek (08.–13.06.2026), Chimaera Festival (14.–16.08.2026)

## Erledigt (Frühjahr 2026)

- [x] MA abgegeben (30.03.2026)
- [x] BfV AWV-2026-022 eingereicht (13.04.), BND AWV-2026-045 abgeschickt
- [x] Sechs GIZ-Praktikumsbewerbungen (Sahel, Ukraine, Bildung, develoPPP, Indien, Stabilisierung); GIZ-Gespräch Digitaldialog Indien am 14.05.2026
- [x] Böll-Stiftung Abschlussbericht (01.04.)
- [x] FAZ/FAS ePub-to-Kindle Automation
- [x] Persian-English Kindle Mega-Dictionary (~70k Einträge)
- [x] Tajik Poetry Analyzer (Streamlit, GitHub: tajikpoemanalyzer)
- [x] Langenstein-Kapitel Mitteldeutscher Verlag
- [x] Brodyer Nächte Termine 2 (21.05.) und 3 (18.06.)

- [ ] GUZU/Seide: Namensfavorit HOTPOT SILK (Claim: The rest is pleasure) – TMview hotpot prüfen (DE/EM/WO, Kl. 24/25/35), hotpotsilk.de/.com sichern, Greta abstimmen (23.10.2026)
- [ ] Seide: UG gründen (Musterprotokoll, 50/50, GF Moritz) – Firma festlegen, IHK-Firmierungscheck, Notartermin, GLS-Konto UG i.G., Stammkapital einzahlen (23.10.2026)
- [ ] Seide: DPMA-Gebühr HOTPOT 290 € zahlen bis ca. 23.01.2027 (Anmeldung 23.10.2026, Kl. 24/25), möglichst über UG-Konto

- Standortwünsche (26.10.): Schweiz, München; lieber Berlin/Köln; zur Not Frankfurt; Dresden/Leipzig/Halle ok; sonst nur ohne volle Präsenz
