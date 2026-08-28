# HA Kraken Trader Projektuebergabe

Stand: 0.1.0-dev.5

## Erhalten
Alle Funktionen aus dev.4 bleiben erhalten: komplette Ingress-GUI, REST-Portfolio, Ledger-Pagination, Nullpositionen, Snapshots, Paper-Wallet, Audit, Exporte, Einstellungen, Kill-Switch, Allowlist und oeffentlicher WebSocket-v2-Ticker. Realhandel und manuelle Orders sind weiterhin nicht implementiert.

## Neu
- Privater authentifizierter Kraken WebSocket v2 auf dem read-only Endpoint.
- Subscription auf balances mit initialem Snapshot und nachfolgenden Ledger-/Balance-Aenderungen.
- Subscription auf executions mit offenen Orders, letzten Ausfuehrungen und Statusaenderungen.
- Frischer Token bei jeder neuen Verbindung; Token wird nicht gespeichert, angezeigt oder protokolliert.
- Getrennte Sequenznummern fuer balances und executions.
- Eine Sequenzluecke erzeugt Audit, DEGRADED-Status, Verbindungsabbruch und Reconnect; der neue Snapshot baut den Zustand neu auf.
- Ereignisse werden idempotent gespeichert.
- Keine WebSocket-Ordermethoden im Code.

## Hinweis zu dev.4
Der sichtbare Ticker-Zeitstempel aendert sich nur bei einem gespeicherten Tickerereignis. Heartbeats aktualisieren intern die Verbindungsfrische, erzeugen aber keine sichtbare neue Preiszeile.

## HA-OS-Test dev.5
1. App aktualisieren und starten.
2. API-Seite oeffnen.
3. Privater Stream soll CONNECTED zeigen.
4. Live-Balances sollen erscheinen; Execution-Liste kann bei fehlender aktueller Aktivitaet leer sein.
5. App neu starten und pruefen, ob Balances erneut als Snapshot geladen werden.
6. Im Audit darf kein Token erscheinen.

## Naechster Schritt
Nachvollziehbare Kostenbasis sowie realisierte/unrealisierte Ergebnisse aus Kraken-Ledger und Execution-Daten; weiterhin ohne echte Orders.

## Stand 0.1.0-dev.6
Dev.6 baut unmittelbar auf dev.5 auf. Neu ist `paper_engine.py`. Die Engine hÃ¤lt ein eigenes persistentes Paper-Konto, Positionen, Trades, Entscheidungen und Snapshots. Sie verwendet nur Allowlist-Symbole und `live_prices`. Ohne aktiven Analyse-/Paper-Schalter oder ohne Livepreis wird kein simulierter Trade ausgefÃ¼hrt. GebÃ¼hren, Slippage und Positionslimit sind App-Optionen. Der reale Kraken-Transport enthÃ¤lt weiterhin keine Ordermethode.

## Stand 0.1.0-dev.7
Die fehlende praktische Automatisierung aus dev.6 wurde geschlossen. Einstellungen sind vollstÃ¤ndig in der Ingress-GUI sichtbar und werden in `settings` gespeichert. Allowlist-Symbole werden an den Ã¶ffentlichen WebSocket Ã¼bergeben. `refresh_allowed_prices()` aktualisiert sie vor jedem Lauf zusÃ¤tzlich Ã¼ber REST. `paper_scheduler()` fÃ¼hrt `run_paper_cycle()` im konfigurierten Intervall aus. Der manuelle Knopf verwendet exakt dieselbe Pipeline. BUY wird weiterhin nur bei erfÃ¼lltem Signal ausgefÃ¼hrt.

## Stand 0.1.0-dev.8
Neu ist `scanner.py` mit persistenten Tabellen `ohlc_cache`, `scanner_results` und `scanner_runs`. Die Seite **Scanner** analysiert die freigegebenen Produkte auf abgeschlossenen 1-Stunden-Kerzen. Der Scanner ist absichtlich noch nicht direkt mit Paper-Trades gekoppelt; die Ergebnisse sollen zuerst praktisch geprÃ¼ft und spÃ¤ter gebenchmarkt werden.


## Stand 0.1.0-dev.13
Der globale Nachrichtenindex GDELT wird mit EZB-, Federal-Reserve- und Kraken-Feeds kombiniert. Quellenklassen und Gewichte bleiben nachvollziehbar. Nachrichten werden deterministisch taxonomiert und nur fÃ¼r die Vorfilterung verwendet. Jeder Vorfilterlauf erzeugt eine Watchlist-Version; valide Detailanalysen erzeugen 24h- und 168h-Prognosesnapshots, die spÃ¤ter gegen reale Preise bewertet werden. Modellgewichte Ã¤ndern sich nicht automatisch.


## Stand 0.1.0-dev.14
Dev.14 ist ein gezielter Start-Hotfix auf Basis von dev.13. Ursache des Exit-Codes war die fehlende SQLite-Migration der in dev.13 erweiterten Nachrichtentabellen. Fehlende Spalten werden nun beim Start idempotent ergÃ¤nzt; Quellen und Nachrichten werden mit expliziten Spaltenlisten geschrieben. Bestehende Nachrichten bleiben erhalten.

## Stand 0.1.0-dev.15
Die fehleranfÃ¤llige breite GDELT-Global-Abfrage wurde stillgelegt. GDELT Wirtschaft und GDELT Geopolitik verwenden kleinere Abfragen; Google News Wirtschaft AT und Google News Geopolitik AT ergÃ¤nzen sie als RSS-Aggregatoren. Abrufe verwenden einen gesetzten User-Agent, bis zu drei begrenzte Versuche und persistieren HTTP-Status, Detailfehler, FehlerzÃ¤hler sowie letzten Erfolg. In den Einstellungen kann ein eigener automatischer Research-Zeitplan aktiviert werden.

## Stand 0.1.0-dev.16
Dev.16 erweitert das Universum auf Kraken-Aktien/xStocks der Assetklasse `tokenized_asset` und akzeptiert EUR- sowie USD-Paare im Ã¶ffentlichen Stream. USD-Produkte werden fÃ¼r das Paper-Portfolio Ã¼ber EUR/USD in EUR bewertet. Der neue PortfolioAllocator berechnet Zielgewichte aus Scanner-Score, VolatilitÃ¤t, Portfolioobergrenze und No-Trade-Band. SchwÃ¤chere Positionen dÃ¼rfen eine bessere Gelegenheit nur finanzieren, wenn der konfigurierte Konfidenzabstand die geschÃ¤tzten Rundlaufkosten Ã¼bersteigt. Dynamischer Paper-Hebel nutzt ausschlieÃŸlich Kraken-Metadaten und das Benutzermaximum. RealausfÃ¼hrung bleibt hart deaktiviert; ein separater Adapter validiert lediglich zukÃ¼nftige PlÃ¤ne.

## Stand 0.1.0-dev.18
Ursache der leeren xStocks-Watchlist war die harte Bindung der Kandidatenauswahl an einen im gemeinsamen Vorfilterabruf erfolgreich zugeordneten Ticker. Dev.18 fragt xStocks explizit am internationalen AusfÃ¼hrungsplatz ab, routet Ticker nach Assetklasse, fÃ¤llt bei Batchfehlern auf Einzelabrufe zurÃ¼ck und Ã¼bernimmt weiterhin von Kraken gemeldete MÃ¤rkte als `PENDING_TICKER`. Diese Kandidaten werden geprÃ¼ft, dÃ¼rfen ohne valide Detailanalyse aber nicht gehandelt werden.

## Stand 0.1.0-dev.20
Der Mehrklassenlauf scheiterte beim Prognose-Snapshot, weil `research_forecasts` zwÃ¶lf Spalten hatte, der positionsabhÃ¤ngige Insert aber nur elf Gesamtwerte lieferte. Der Insert benennt jetzt alle elf Nicht-ID-Spalten explizit. ZusÃ¤tzlich wurde das gesamte Repository auf echtes UTF-8 normalisiert und mit Regressionstests gegen beschÃ¤digte Umlaute abgesichert.

## Stand 0.1.0-dev.20
Dev.20 basiert ausschlieÃŸlich auf dem vom Benutzer gelieferten dev.19-Snapshot. Die konkrete UNIQUE-Ursache liegt in der bisherigen SQL-Abfrage: `DISTINCT` umfasste auch `m.category`; ein hebelfÃ¤higer xStock erschien daher einmal als `xstocks` und nochmals als `leveraged_spot`. Die Mehrfachmitgliedschaft bleibt im Universum erhalten, wÃ¤hrend der Vorfilter pro Symbol eine kanonische Kategorie auswÃ¤hlt. ZusÃ¤tzlich schÃ¼tzen eine Schleifen-Deduplizierung und `ON CONFLICT(run_id,symbol) DO UPDATE` die Persistenz. SÃ¤mtliche ausgelieferten Texte und sichtbaren GUI-Strings wurden erneut auf echtes UTF-8 repariert.

## Stand 0.1.0-dev.24
Das Umlautproblem wird nicht mehr nur in den Dateien behandelt. `text_encoding.py` repariert beim ersten Start auch bereits persistierte Anzeigetexte in SQLite und markiert die Migration danach als abgeschlossen. `.editorconfig` und `.gitattributes` erzwingen UTF-8/LF fÃ¼r zukÃ¼nftige Ã„nderungen. HTTP-Antworten behalten ein explizites UTF-8-Charset und erhalten `X-Content-Type-Options: nosniff`.

## Stand 0.1.0-dev.24
Dev.22 basiert ausschlieÃŸlich auf dem Ã¼bergebenen dev.21-Snapshot. Alle Mojibake-Folgen wurden direkt aus Quelltexten, Tests und Dokumentation entfernt. Die Datenbankmigration verwendet eine neue v2-Markierung und lÃ¤uft deshalb auch dann einmalig, wenn dev.21 bereits `utf8_data_migration_v1=done` gespeichert hatte. Die UNIQUE-Absicherung des Vorfilters bleibt erhalten und wird zusammen mit der UTF-8-Reparatur getestet.

## Stand 0.1.0-dev.24
Aktien/xStocks sind jetzt durchgÃ¤ngig integriert: `tokenized_asset`-Universum, Ticker, OHLC, eigenes Scoreprofil `xstocks-v1`, Watchliststatus ANALYZED, BUY-Gate, dynamische Zielallokation, USD/EUR-Umrechnung und simulierte AusfÃ¼hrung. Paper-KÃ¤ufe werden abgelehnt, wenn Kraken-Metadaten zu `ordermin` oder `costmin` nicht erfÃ¼llt sind. Realhandel bleibt weiterhin technisch deaktiviert.

## Stand 0.1.0-dev.24
Der reale Detailscore-0-Fehler bei Aktien wurde auf einen API-Vertragsfehler zurÃ¼ckgefÃ¼hrt. Ticker und OHLC senden nun `asset_class=tokenized_asset`; OHLC verwendet primÃ¤r den von Kraken gelieferten `source_key`. Ein Fehler wird mit Typ und gekÃ¼rzter Meldung im Scannergrund gespeichert.

## Stand 0.1.0-dev.25
Der neue Tab **Lernfreigaben** zeigt die neun aktiven xStock-Parameter, einen berechneten Kandidaten und die zulÃ¤ssigen Grenzen. Ab fÃ¼nf ausgewerteten xStock-Prognosen kann ein begrenzter Vorschlag erzeugt werden. Er verÃ¤ndert nichts automatisch. Der Button **Alle neun Parameter mit einem Klick bestÃ¤tigen** aktiviert die Werte atomar als neue Version und protokolliert die Freigabe im Audit.

## Stand 0.1.0-dev.27
Dev.27 baut ausschlieÃŸlich auf dem Ã¼bergebenen v26-Snapshot auf. Die EUR/USD-Auswahl verwendet vollstÃ¤ndige erwartete Kosten und hÃ¤lt Alternativpaare als Metadaten. Forex wird ohne nicht dokumentierten AssetPairs-Parameter aus Fiat-zu-Fiat-Paaren abgeleitet. USD-Paper-Trades weisen FX-Spread, FX-GebÃ¼hr, Produktspread, Slippage und HandelsgebÃ¼hr getrennt aus. Mindesthaltedauer, Cooldown, BestÃ¤tigungen, Hysterese, Tageslimit sowie Gewinn-/Verlust- und Steuereffekt schÃ¼tzen vor unnÃ¶tigen Umschichtungen. Realhandel bleibt hart deaktiviert.



## Stand 0.1.0-dev.28
Dev.28 setzt die priorisierte Forex-Datenabsicherung um. Der neue Tab DatenqualitÃ¤t zeigt pro Paar Tickerstatus, Bid/Ask, Volumen, OHLC-Status, Zahl abgeschlossener Kerzen und konkrete Fehler. Der persistente OHLCVT-Speicher kann Kraken-kompatible CSV-Zeilen aufnehmen. Der neue Backtest-Tab vergleicht im zeitlich getrennten Walk-forward-Test eine einfache SMA-Strategie mit Keine Position und Buy-and-Hold und speichert Kostenannahme, Anlageklasse, Rendite, Drawdown und Umschichtungen. Realhandel bleibt hart deaktiviert.

## Stand 0.1.0-dev.29
Dev.29 ergÃ¤nzt kontospezifische GebÃ¼hren Ã¼ber den read-only TradeVolume-Endpunkt. Maker- und Taker-SÃ¤tze werden pro Paar mit Quelle und Abrufzeitpunkt gespeichert und im neuen Tab GebÃ¼hren angezeigt. Paper-AusfÃ¼hrung und KostenschÃ¤tzung verwenden den paarbezogenen Taker-Satz. Bei fehlender Berechtigung oder API-Fehler bleibt der konfigurierte konservative Wert aktiv. Realhandel bleibt hart deaktiviert.

## Stand 0.1.0-dev.30
Dev.30 fÃ¼hrt forex-v2 ausschlieÃŸlich im Schattenmodus ein. Relative WÃ¤hrungsstÃ¤rke, Safe-Haven-Regime, paarbezogene Nachrichten sowie kurze und mittlere Horizonte werden versioniert gespeichert und gegen forex-v1 verglichen. Noch nicht angebundene Makrodaten bleiben ausdrÃ¼cklich null. Scanner- und Paper-Ergebnisse werden nicht verÃ¤ndert.

## Stand 0.1.0-dev.31
Dev.31 macht kanonische Produkte vollstÃ¤ndig sichtbar und ergÃ¤nzt eine einheitliche Umschichtungsmatrix. Die GUI zeigt IdentitÃ¤t, gewÃ¤hltes Paar, Alternativen, EUR-/USD-Kosten, Wahlzeitpunkt, Auswahlgrund und zugeordnete Position. Jede Umschichtung speichert sieben Einzelregeln; die erste fehlgeschlagene Regel wird als konkreter Blockierungsgrund angezeigt.

## Stand 0.1.0-dev.32
Dev.32 vervollstÃ¤ndigt den kontrollierten Lernprozess fÃ¼r Forex, xStocks und Krypto. Kandidaten werden nur im Schattenmodus bewertet, benÃ¶tigen Mindeststichprobe sowie Mindestverbesserung und zeigen ein Wilson-Konfidenzintervall. Aktivierung, Ablehnung und vollstÃ¤ndiger Rollback erfolgen ausdrÃ¼cklich Ã¼ber die GUI. Es gibt keine automatische oder direkte KI-Aktivierung.




## Stand 0.1.0-dev.36
Das kontrollierte Lernen ist konsolidiert. Alle drei Produktfamilien besitzen neun versionierte Parameter und der Scanner liest ausschlieÃŸlich die aktive Familienversion. Prognosen enthalten Familie, Parameterversion, vollstÃ¤ndige Parameter und strukturierte Features. Ein Kandidat darf nur freigegeben werden, solange seine Basisversion noch aktiv ist. Der frÃ¼here xStock-Sonderweg bleibt nur migrationsbedingt im Repository und ist nicht mehr in der Hauptnavigation verlinkt.

### NÃ¤chste Schritte
1. Historische Feature-Snapshots fÃ¼r Rendite nach Kosten, Abdeckung und Drawdown erweitern.
2. Lernmetriken nach 24- und 168-Stunden-Horizont getrennt ausweisen.
3. Legacy-Tab nach bestÃ¤tigter Bestandsmigration vollstÃ¤ndig entfernen.
4. Gesamte Ã¤ltere Testsuite auf die aktuellen VertrÃ¤ge bereinigen.

## Stand 0.1.0-dev.34
Die dev.33-Lernintegration bleibt vollstÃ¤ndig erhalten. ZusÃ¤tzlich ist die gesamte Testsuite wieder grÃ¼n. Scanner-Batches sind begrenzt, rotierend und Ã¼ber einen nicht blockierenden Lock geschÃ¼tzt. Forecasts tolerieren Ã¤ltere Scanner-Schemata. UTF-8 ist in Quellen, Dokumentation und GUI bereinigt. NÃ¤chster fachlicher Schritt bleibt dev.35: kosten- und abdeckungsbewusster Offline-Schattenvergleich mit getrennten Metriken je Familie und Horizont.

## Stand 0.1.0-dev.36
Der Offline-Schattenvergleich wendet aktive und vorgeschlagene Familienparameter auf dieselben gespeicherten Features an. FÃ¼r 24 und 168 Stunden werden Stichprobe, Entscheidungen, Abdeckung, Rendite nach geschÃ¤tzten Kosten und maximaler Drawdown getrennt persistiert und in der GUI angezeigt. HOLD beziehungsweise keine Entscheidung gilt nicht automatisch als falsche Richtung. Die Aktivierung bleibt ausschlieÃŸlich eine ausdrÃ¼ckliche Benutzeraktion. Die vollstÃ¤ndige Suite umfasst 105 erfolgreiche Tests.

### NÃ¤chste Schritte
1. Freigabegates zusÃ¤tzlich auf Mindestabdeckung, positive Nettorenditeverbesserung und Drawdown-Grenze erweitern.
2. Kosten-Snapshots um kontospezifische GebÃ¼hrenquelle und tatsÃ¤chliche FX-Spreads ergÃ¤nzen.
3. Kandidatenvergleich Ã¼ber mehrere aufeinanderfolgende Walk-forward-Fenster stabilisieren.
4. Legacy-Lernmodul nach bestÃ¤tigter Datenmigration entfernen.




## Stand 0.1.0-dev.36
Dev.36 Ã¼bernimmt den vollstÃ¤ndigen dev.35-Snapshot ohne Entfernung bestehender Funktionen. Der Release zentralisiert die Laufzeitversion in `app/version.py`, synchronisiert Health, GUI, HTTP-User-Agents, Add-on-Metadaten und Projektunterlagen und normalisiert alle ausgelieferten Texte auf echtes UTF-8. Die Handelsstrategie und Lernfreigabelogik bleiben unverÃ¤ndert. Realhandel bleibt hart deaktiviert.

### Verifikation
Die vollstÃ¤ndige Testsuite wurde mit installierten AbhÃ¤ngigkeiten ausgefÃ¼hrt: 109 Tests erfolgreich. ZusÃ¤tzlich prÃ¼fen vier dev.36-Tests Versionskonsistenz, Add-on-Metadaten, UTF-8 und die deaktivierte Real-Execution-Grenze.

### NÃ¤chster empfohlener Schritt
Dev.37 soll die Freigabe kontrollierter Lernkandidaten um konfigurierbare Mindestabdeckung, positive Nettorenditeverbesserung, Drawdown-Grenze und eine transaktionale erneute Gate-PrÃ¼fung bei der Benutzerfreigabe erweitern.

## Stand 0.1.0-dev.37
Dev.37 baut vollstÃ¤ndig auf dev.36 auf und entfernt keine Funktionen. Kontrollierte Lernkandidaten mÃ¼ssen jetzt fÃ¼r jeden erforderlichen Horizont alle konfigurierten Risiko- und QualitÃ¤tsgates erfÃ¼llen. Policy und Einzelergebnisse werden am Kandidaten gespeichert und im Audit protokolliert. Eine ausdrÃ¼ckliche Benutzerfreigabe wiederholt die PrÃ¼fung direkt vor der atomaren Aktivierung; bei einem Fehler bleibt die aktive Version unverÃ¤ndert.

### Standard-Gates
- erforderliche Horizonte: 24 und 168 Stunden
- mindestens 5 Beobachtungen je Horizont
- mindestens 50 Prozent Kandidatenabdeckung
- mindestens 0,01 Prozentpunkte Nettorenditeverbesserung je Horizont
- Kandidaten-Drawdown nicht schlechter als -25 Prozent
- Drawdown hÃ¶chstens 2 Prozentpunkte schlechter als die aktive Version

### Verifikation
Die vollstÃ¤ndige Testsuite wurde ausgefÃ¼hrt: 115 Tests erfolgreich. Realhandel und automatische Parameteraktivierung bleiben ausgeschlossen.

### NÃ¤chster empfohlener Schritt
Dev.38 soll Prognosen am exakten historischen Zielzeitpunkt auswerten und Ein-, Ausstiegs- sowie Roundtrip-Kosten eindeutig und quellenbezogen speichern.

## Stand 0.1.0-dev.38
Dev.38 baut vollstÃ¤ndig auf dev.37 auf. Prognoseauswertungen verwenden keine verspÃ¤teten Livepreise mehr, sondern die erste abgeschlossene lokale OHLC-Kerze am oder nach dem exakten Zielzeitpunkt. Ohne passende Historie bleibt die Prognose offen. Auswertungen speichern Zielzeit, Preisquelle, Kerzenzeit und Zeitabweichung. Feature-Snapshots trennen Einstiegs-, Ausstiegs- und Roundtrip-Kosten und dokumentieren die GebÃ¼hrenherkunft.

### Verifikation
119 automatisierte Tests erfolgreich. YAML, Python, UTF-8 und ArchivintegritÃ¤t wurden zusÃ¤tzlich geprÃ¼ft. Realhandel bleibt hart deaktiviert.

### NÃ¤chster empfohlener Schritt
Dev.39 sollte eine echte zeitlich getrennte Walk-forward-Validierung fÃ¼r Lernkandidaten mit stabilen Teilfenster-Gates ergÃ¤nzen.

## Stand 0.1.0-dev.43
Dev.39 basiert ausschlieÃŸlich auf dem gelieferten dev.38-Snapshot. Alle erkannten UTF-8-SchÃ¤den wurden repariert. Der GebÃ¼hrenabruf verwendet nun kanonische Kraken-PaaridentitÃ¤ten, lÃ¤sst nicht unterstÃ¼tzte Assetklassen beim sicheren Konfigurations-Fallback und isoliert ungÃ¼ltige Paare. Die GUI besitzt eine neue responsive Navigation, eine gefÃ¼hrte Ãœbersicht sowie eine verstÃ¤ndliche kontrollierte Lernfreigabe mit aktiver Version, Parametervergleich und Gate-Details. Die vollstÃ¤ndige Regression umfasst 124 erfolgreiche Tests. Realhandel bleibt hart deaktiviert.

### NÃ¤chster Schritt
Praktischer Home-Assistant-OS-Test des GebÃ¼hrenabrufs mit dem realen Marktuniversum sowie schrittweise Modularisierung der groÃŸen main.py in Blueprints ohne Funktionsverlust.


## Stand 0.1.0-dev.43
Die externe Nachrichten-AI kann nun automatisch mit der aktiven lokalen Nachrichtenbewertung verglichen werden. Ein begrenzter lokaler Kandidat wird nur bei geringerem Fehler und mindestens gleich guter RichtungsÃ¼bereinstimmung PENDING. Aktivierung erfolgt ausschlieÃŸlich manuell, nach erneuter PrÃ¼fung und als vollstÃ¤ndige neue Version.

### NÃ¤chster Schritt
Zeitlich getrennte Trainings- und Validierungsfenster fÃ¼r Nachrichtenkandidaten sowie eine spÃ¤tere PrÃ¼fung gegen tatsÃ¤chlich eingetretene Marktrenditen statt ausschlieÃŸlich gegen AI-Lehrergebnisse.

## Stand 0.1.0-dev.43
Dev.41 baut vollstÃ¤ndig auf dev.40 auf und entfernt keine Funktionen. Nachrichtenkandidaten werden auf dem Ã¤lteren Teil der chronologisch sortierten AI-Vergleiche optimiert. Nur der spÃ¤tere, disjunkte Teil entscheidet Ã¼ber Verlustverbesserung und RichtungsÃ¼bereinstimmung. Fenstergrenzen, Anzahlen und Policy werden gespeichert. Vor einer manuellen Aktivierung werden Datenfingerprint und Validierung erneut geprÃ¼ft. Realhandel bleibt hart deaktiviert.

### NÃ¤chster empfohlener Schritt
Mehrere aufeinanderfolgende Walk-forward-Teilfenster einfÃ¼hren und StabilitÃ¤tsgates je Teilfenster ergÃ¤nzen.

## Stand 0.1.0-dev.43
Dev.42 erweitert die zeitlich getrennte Validierung aus dev.41 um mehrere aufeinanderfolgende Walk-forward-Fenster. StandardmÃ¤ÃŸig werden drei disjunkte Validierungsabschnitte gegen ein jeweils wachsendes Trainingsfenster geprÃ¼ft; mindestens zwei mÃ¼ssen stabil bestehen. Die vollstÃ¤ndigen Fenstermetriken werden gespeichert und bei der manuellen Freigabe erneut geprÃ¼ft. Bestehende Funktionen bleiben erhalten. Realhandel bleibt hart deaktiviert.

### NÃ¤chster empfohlener Schritt
Walk-forward-StabilitÃ¤tsgates auf das kontrollierte Lernen der Produktfamilien Ã¼bertragen und anschlieÃŸend main.py schrittweise in Blueprints modularisieren.

## Ãœbergabe 0.1.0-dev.43
Die StartÃ¼bersicht unterscheidet nun DatenverfÃ¼gbarkeit vom Zustand der optionalen WebSocket-KanÃ¤le. Gemini kann als Nachrichten-AI-Provider konfiguriert werden. Der externe AI-Pfad bleibt ohne direkte Handelswirkung.

## Dev.44
Die Seite Kontrolliertes Lernen zeigt nun die aktiven Versionen aller unterstützten Parameterfamilien. Die gewählte Familie steuert weiterhin Kandidatenberechnung und Parameterdetails.
