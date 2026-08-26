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
Dev.6 baut unmittelbar auf dev.5 auf. Neu ist `paper_engine.py`. Die Engine hält ein eigenes persistentes Paper-Konto, Positionen, Trades, Entscheidungen und Snapshots. Sie verwendet nur Allowlist-Symbole und `live_prices`. Ohne aktiven Analyse-/Paper-Schalter oder ohne Livepreis wird kein simulierter Trade ausgeführt. Gebühren, Slippage und Positionslimit sind App-Optionen. Der reale Kraken-Transport enthält weiterhin keine Ordermethode.

## Stand 0.1.0-dev.7
Die fehlende praktische Automatisierung aus dev.6 wurde geschlossen. Einstellungen sind vollständig in der Ingress-GUI sichtbar und werden in `settings` gespeichert. Allowlist-Symbole werden an den öffentlichen WebSocket übergeben. `refresh_allowed_prices()` aktualisiert sie vor jedem Lauf zusätzlich über REST. `paper_scheduler()` führt `run_paper_cycle()` im konfigurierten Intervall aus. Der manuelle Knopf verwendet exakt dieselbe Pipeline. BUY wird weiterhin nur bei erfülltem Signal ausgeführt.

## Stand 0.1.0-dev.8
Neu ist `scanner.py` mit persistenten Tabellen `ohlc_cache`, `scanner_results` und `scanner_runs`. Die Seite **Scanner** analysiert die freigegebenen Produkte auf abgeschlossenen 1-Stunden-Kerzen. Der Scanner ist absichtlich noch nicht direkt mit Paper-Trades gekoppelt; die Ergebnisse sollen zuerst praktisch geprüft und später gebenchmarkt werden.


## Stand 0.1.0-dev.13
Der globale Nachrichtenindex GDELT wird mit EZB-, Federal-Reserve- und Kraken-Feeds kombiniert. Quellenklassen und Gewichte bleiben nachvollziehbar. Nachrichten werden deterministisch taxonomiert und nur für die Vorfilterung verwendet. Jeder Vorfilterlauf erzeugt eine Watchlist-Version; valide Detailanalysen erzeugen 24h- und 168h-Prognosesnapshots, die später gegen reale Preise bewertet werden. Modellgewichte ändern sich nicht automatisch.


## Stand 0.1.0-dev.14
Dev.14 ist ein gezielter Start-Hotfix auf Basis von dev.13. Ursache des Exit-Codes war die fehlende SQLite-Migration der in dev.13 erweiterten Nachrichtentabellen. Fehlende Spalten werden nun beim Start idempotent ergänzt; Quellen und Nachrichten werden mit expliziten Spaltenlisten geschrieben. Bestehende Nachrichten bleiben erhalten.

## Stand 0.1.0-dev.15
Die fehleranfällige breite GDELT-Global-Abfrage wurde stillgelegt. GDELT Wirtschaft und GDELT Geopolitik verwenden kleinere Abfragen; Google News Wirtschaft AT und Google News Geopolitik AT ergänzen sie als RSS-Aggregatoren. Abrufe verwenden einen gesetzten User-Agent, bis zu drei begrenzte Versuche und persistieren HTTP-Status, Detailfehler, Fehlerzähler sowie letzten Erfolg. In den Einstellungen kann ein eigener automatischer Research-Zeitplan aktiviert werden.

## Stand 0.1.0-dev.16
Dev.16 erweitert das Universum auf Kraken-Aktien/xStocks der Assetklasse `tokenized_asset` und akzeptiert EUR- sowie USD-Paare im öffentlichen Stream. USD-Produkte werden für das Paper-Portfolio über EUR/USD in EUR bewertet. Der neue PortfolioAllocator berechnet Zielgewichte aus Scanner-Score, Volatilität, Portfolioobergrenze und No-Trade-Band. Schwächere Positionen dürfen eine bessere Gelegenheit nur finanzieren, wenn der konfigurierte Konfidenzabstand die geschätzten Rundlaufkosten übersteigt. Dynamischer Paper-Hebel nutzt ausschließlich Kraken-Metadaten und das Benutzermaximum. Realausführung bleibt hart deaktiviert; ein separater Adapter validiert lediglich zukünftige Pläne.

## Stand 0.1.0-dev.18
Ursache der leeren xStocks-Watchlist war die harte Bindung der Kandidatenauswahl an einen im gemeinsamen Vorfilterabruf erfolgreich zugeordneten Ticker. Dev.18 fragt xStocks explizit am internationalen Ausführungsplatz ab, routet Ticker nach Assetklasse, fällt bei Batchfehlern auf Einzelabrufe zurück und übernimmt weiterhin von Kraken gemeldete Märkte als `PENDING_TICKER`. Diese Kandidaten werden geprüft, dürfen ohne valide Detailanalyse aber nicht gehandelt werden.

## Stand 0.1.0-dev.20
Der Mehrklassenlauf scheiterte beim Prognose-Snapshot, weil `research_forecasts` zwölf Spalten hatte, der positionsabhängige Insert aber nur elf Gesamtwerte lieferte. Der Insert benennt jetzt alle elf Nicht-ID-Spalten explizit. Zusätzlich wurde das gesamte Repository auf echtes UTF-8 normalisiert und mit Regressionstests gegen beschädigte Umlaute abgesichert.

## Stand 0.1.0-dev.20
Dev.20 basiert ausschließlich auf dem vom Benutzer gelieferten dev.19-Snapshot. Die konkrete UNIQUE-Ursache liegt in der bisherigen SQL-Abfrage: `DISTINCT` umfasste auch `m.category`; ein hebelfähiger xStock erschien daher einmal als `xstocks` und nochmals als `leveraged_spot`. Die Mehrfachmitgliedschaft bleibt im Universum erhalten, während der Vorfilter pro Symbol eine kanonische Kategorie auswählt. Zusätzlich schützen eine Schleifen-Deduplizierung und `ON CONFLICT(run_id,symbol) DO UPDATE` die Persistenz. Sämtliche ausgelieferten Texte und sichtbaren GUI-Strings wurden erneut auf echtes UTF-8 repariert.

## Stand 0.1.0-dev.24
Das Umlautproblem wird nicht mehr nur in den Dateien behandelt. `text_encoding.py` repariert beim ersten Start auch bereits persistierte Anzeigetexte in SQLite und markiert die Migration danach als abgeschlossen. `.editorconfig` und `.gitattributes` erzwingen UTF-8/LF für zukünftige Änderungen. HTTP-Antworten behalten ein explizites UTF-8-Charset und erhalten `X-Content-Type-Options: nosniff`.

## Stand 0.1.0-dev.24
Dev.22 basiert ausschließlich auf dem übergebenen dev.21-Snapshot. Alle Mojibake-Folgen wurden direkt aus Quelltexten, Tests und Dokumentation entfernt. Die Datenbankmigration verwendet eine neue v2-Markierung und läuft deshalb auch dann einmalig, wenn dev.21 bereits `utf8_data_migration_v1=done` gespeichert hatte. Die UNIQUE-Absicherung des Vorfilters bleibt erhalten und wird zusammen mit der UTF-8-Reparatur getestet.

## Stand 0.1.0-dev.24
Aktien/xStocks sind jetzt durchgängig integriert: `tokenized_asset`-Universum, Ticker, OHLC, eigenes Scoreprofil `xstocks-v1`, Watchliststatus ANALYZED, BUY-Gate, dynamische Zielallokation, USD/EUR-Umrechnung und simulierte Ausführung. Paper-Käufe werden abgelehnt, wenn Kraken-Metadaten zu `ordermin` oder `costmin` nicht erfüllt sind. Realhandel bleibt weiterhin technisch deaktiviert.

## Stand 0.1.0-dev.24
Der reale Detailscore-0-Fehler bei Aktien wurde auf einen API-Vertragsfehler zurückgeführt. Ticker und OHLC senden nun `asset_class=tokenized_asset`; OHLC verwendet primär den von Kraken gelieferten `source_key`. Ein Fehler wird mit Typ und gekürzter Meldung im Scannergrund gespeichert.

## Stand 0.1.0-dev.25
Der neue Tab **Lernfreigaben** zeigt die neun aktiven xStock-Parameter, einen berechneten Kandidaten und die zulässigen Grenzen. Ab fünf ausgewerteten xStock-Prognosen kann ein begrenzter Vorschlag erzeugt werden. Er verändert nichts automatisch. Der Button **Alle neun Parameter mit einem Klick bestätigen** aktiviert die Werte atomar als neue Version und protokolliert die Freigabe im Audit.

## Stand 0.1.0-dev.27
Dev.27 baut ausschließlich auf dem übergebenen v26-Snapshot auf. Die EUR/USD-Auswahl verwendet vollständige erwartete Kosten und hält Alternativpaare als Metadaten. Forex wird ohne nicht dokumentierten AssetPairs-Parameter aus Fiat-zu-Fiat-Paaren abgeleitet. USD-Paper-Trades weisen FX-Spread, FX-Gebühr, Produktspread, Slippage und Handelsgebühr getrennt aus. Mindesthaltedauer, Cooldown, Bestätigungen, Hysterese, Tageslimit sowie Gewinn-/Verlust- und Steuereffekt schützen vor unnötigen Umschichtungen. Realhandel bleibt hart deaktiviert.



## Stand 0.1.0-dev.28
Dev.28 setzt die priorisierte Forex-Datenabsicherung um. Der neue Tab Datenqualität zeigt pro Paar Tickerstatus, Bid/Ask, Volumen, OHLC-Status, Zahl abgeschlossener Kerzen und konkrete Fehler. Der persistente OHLCVT-Speicher kann Kraken-kompatible CSV-Zeilen aufnehmen. Der neue Backtest-Tab vergleicht im zeitlich getrennten Walk-forward-Test eine einfache SMA-Strategie mit Keine Position und Buy-and-Hold und speichert Kostenannahme, Anlageklasse, Rendite, Drawdown und Umschichtungen. Realhandel bleibt hart deaktiviert.

## Stand 0.1.0-dev.29
Dev.29 ergänzt kontospezifische Gebühren über den read-only TradeVolume-Endpunkt. Maker- und Taker-Sätze werden pro Paar mit Quelle und Abrufzeitpunkt gespeichert und im neuen Tab Gebühren angezeigt. Paper-Ausführung und Kostenschätzung verwenden den paarbezogenen Taker-Satz. Bei fehlender Berechtigung oder API-Fehler bleibt der konfigurierte konservative Wert aktiv. Realhandel bleibt hart deaktiviert.

## Stand 0.1.0-dev.30
Dev.30 führt forex-v2 ausschließlich im Schattenmodus ein. Relative Währungsstärke, Safe-Haven-Regime, paarbezogene Nachrichten sowie kurze und mittlere Horizonte werden versioniert gespeichert und gegen forex-v1 verglichen. Noch nicht angebundene Makrodaten bleiben ausdrücklich null. Scanner- und Paper-Ergebnisse werden nicht verändert.

## Stand 0.1.0-dev.31
Dev.31 macht kanonische Produkte vollständig sichtbar und ergänzt eine einheitliche Umschichtungsmatrix. Die GUI zeigt Identität, gewähltes Paar, Alternativen, EUR-/USD-Kosten, Wahlzeitpunkt, Auswahlgrund und zugeordnete Position. Jede Umschichtung speichert sieben Einzelregeln; die erste fehlgeschlagene Regel wird als konkreter Blockierungsgrund angezeigt.

## Stand 0.1.0-dev.32
Dev.32 vervollständigt den kontrollierten Lernprozess für Forex, xStocks und Krypto. Kandidaten werden nur im Schattenmodus bewertet, benötigen Mindeststichprobe sowie Mindestverbesserung und zeigen ein Wilson-Konfidenzintervall. Aktivierung, Ablehnung und vollständiger Rollback erfolgen ausdrücklich über die GUI. Es gibt keine automatische oder direkte KI-Aktivierung.




## Stand 0.1.0-dev.36
Das kontrollierte Lernen ist konsolidiert. Alle drei Produktfamilien besitzen neun versionierte Parameter und der Scanner liest ausschließlich die aktive Familienversion. Prognosen enthalten Familie, Parameterversion, vollständige Parameter und strukturierte Features. Ein Kandidat darf nur freigegeben werden, solange seine Basisversion noch aktiv ist. Der frühere xStock-Sonderweg bleibt nur migrationsbedingt im Repository und ist nicht mehr in der Hauptnavigation verlinkt.

### Nächste Schritte
1. Historische Feature-Snapshots für Rendite nach Kosten, Abdeckung und Drawdown erweitern.
2. Lernmetriken nach 24- und 168-Stunden-Horizont getrennt ausweisen.
3. Legacy-Tab nach bestätigter Bestandsmigration vollständig entfernen.
4. Gesamte ältere Testsuite auf die aktuellen Verträge bereinigen.

## Stand 0.1.0-dev.34
Die dev.33-Lernintegration bleibt vollständig erhalten. Zusätzlich ist die gesamte Testsuite wieder grün. Scanner-Batches sind begrenzt, rotierend und über einen nicht blockierenden Lock geschützt. Forecasts tolerieren ältere Scanner-Schemata. UTF-8 ist in Quellen, Dokumentation und GUI bereinigt. Nächster fachlicher Schritt bleibt dev.35: kosten- und abdeckungsbewusster Offline-Schattenvergleich mit getrennten Metriken je Familie und Horizont.

## Stand 0.1.0-dev.36
Der Offline-Schattenvergleich wendet aktive und vorgeschlagene Familienparameter auf dieselben gespeicherten Features an. Für 24 und 168 Stunden werden Stichprobe, Entscheidungen, Abdeckung, Rendite nach geschätzten Kosten und maximaler Drawdown getrennt persistiert und in der GUI angezeigt. HOLD beziehungsweise keine Entscheidung gilt nicht automatisch als falsche Richtung. Die Aktivierung bleibt ausschließlich eine ausdrückliche Benutzeraktion. Die vollständige Suite umfasst 105 erfolgreiche Tests.

### Nächste Schritte
1. Freigabegates zusätzlich auf Mindestabdeckung, positive Nettorenditeverbesserung und Drawdown-Grenze erweitern.
2. Kosten-Snapshots um kontospezifische Gebührenquelle und tatsächliche FX-Spreads ergänzen.
3. Kandidatenvergleich über mehrere aufeinanderfolgende Walk-forward-Fenster stabilisieren.
4. Legacy-Lernmodul nach bestätigter Datenmigration entfernen.




## Stand 0.1.0-dev.36
Dev.36 übernimmt den vollständigen dev.35-Snapshot ohne Entfernung bestehender Funktionen. Der Release zentralisiert die Laufzeitversion in `app/version.py`, synchronisiert Health, GUI, HTTP-User-Agents, Add-on-Metadaten und Projektunterlagen und normalisiert alle ausgelieferten Texte auf echtes UTF-8. Die Handelsstrategie und Lernfreigabelogik bleiben unverändert. Realhandel bleibt hart deaktiviert.

### Verifikation
Die vollständige Testsuite wurde mit installierten Abhängigkeiten ausgeführt: 109 Tests erfolgreich. Zusätzlich prüfen vier dev.36-Tests Versionskonsistenz, Add-on-Metadaten, UTF-8 und die deaktivierte Real-Execution-Grenze.

### Nächster empfohlener Schritt
Dev.37 soll die Freigabe kontrollierter Lernkandidaten um konfigurierbare Mindestabdeckung, positive Nettorenditeverbesserung, Drawdown-Grenze und eine transaktionale erneute Gate-Prüfung bei der Benutzerfreigabe erweitern.

## Stand 0.1.0-dev.37
Dev.37 baut vollständig auf dev.36 auf und entfernt keine Funktionen. Kontrollierte Lernkandidaten müssen jetzt für jeden erforderlichen Horizont alle konfigurierten Risiko- und Qualitätsgates erfüllen. Policy und Einzelergebnisse werden am Kandidaten gespeichert und im Audit protokolliert. Eine ausdrückliche Benutzerfreigabe wiederholt die Prüfung direkt vor der atomaren Aktivierung; bei einem Fehler bleibt die aktive Version unverändert.

### Standard-Gates
- erforderliche Horizonte: 24 und 168 Stunden
- mindestens 5 Beobachtungen je Horizont
- mindestens 50 Prozent Kandidatenabdeckung
- mindestens 0,01 Prozentpunkte Nettorenditeverbesserung je Horizont
- Kandidaten-Drawdown nicht schlechter als -25 Prozent
- Drawdown höchstens 2 Prozentpunkte schlechter als die aktive Version

### Verifikation
Die vollständige Testsuite wurde ausgeführt: 115 Tests erfolgreich. Realhandel und automatische Parameteraktivierung bleiben ausgeschlossen.

### Nächster empfohlener Schritt
Dev.38 soll Prognosen am exakten historischen Zielzeitpunkt auswerten und Ein-, Ausstiegs- sowie Roundtrip-Kosten eindeutig und quellenbezogen speichern.

## Stand 0.1.0-dev.38
Dev.38 baut vollständig auf dev.37 auf. Prognoseauswertungen verwenden keine verspäteten Livepreise mehr, sondern die erste abgeschlossene lokale OHLC-Kerze am oder nach dem exakten Zielzeitpunkt. Ohne passende Historie bleibt die Prognose offen. Auswertungen speichern Zielzeit, Preisquelle, Kerzenzeit und Zeitabweichung. Feature-Snapshots trennen Einstiegs-, Ausstiegs- und Roundtrip-Kosten und dokumentieren die Gebührenherkunft.

### Verifikation
119 automatisierte Tests erfolgreich. YAML, Python, UTF-8 und Archivintegrität wurden zusätzlich geprüft. Realhandel bleibt hart deaktiviert.

### Nächster empfohlener Schritt
Dev.39 sollte eine echte zeitlich getrennte Walk-forward-Validierung für Lernkandidaten mit stabilen Teilfenster-Gates ergänzen.
