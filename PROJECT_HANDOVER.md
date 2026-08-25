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
Dev.6 baut unmittelbar auf dev.5 auf. Neu ist `paper_engine.py`. Die Engine hÃƒÂ¤lt ein eigenes persistentes Paper-Konto, Positionen, Trades, Entscheidungen und Snapshots. Sie verwendet nur Allowlist-Symbole und `live_prices`. Ohne aktiven Analyse-/Paper-Schalter oder ohne Livepreis wird kein simulierter Trade ausgefÃƒÂ¼hrt. GebÃƒÂ¼hren, Slippage und Positionslimit sind App-Optionen. Der reale Kraken-Transport enthÃƒÂ¤lt weiterhin keine Ordermethode.

## Stand 0.1.0-dev.7
Die fehlende praktische Automatisierung aus dev.6 wurde geschlossen. Einstellungen sind vollstÃƒÂ¤ndig in der Ingress-GUI sichtbar und werden in `settings` gespeichert. Allowlist-Symbole werden an den ÃƒÂ¶ffentlichen WebSocket ÃƒÂ¼bergeben. `refresh_allowed_prices()` aktualisiert sie vor jedem Lauf zusÃƒÂ¤tzlich ÃƒÂ¼ber REST. `paper_scheduler()` fÃƒÂ¼hrt `run_paper_cycle()` im konfigurierten Intervall aus. Der manuelle Knopf verwendet exakt dieselbe Pipeline. BUY wird weiterhin nur bei erfÃƒÂ¼lltem Signal ausgefÃƒÂ¼hrt.

## Stand 0.1.0-dev.8
Neu ist `scanner.py` mit persistenten Tabellen `ohlc_cache`, `scanner_results` und `scanner_runs`. Die Seite **Scanner** analysiert die freigegebenen Produkte auf abgeschlossenen 1-Stunden-Kerzen. Der Scanner ist absichtlich noch nicht direkt mit Paper-Trades gekoppelt; die Ergebnisse sollen zuerst praktisch geprÃƒÂ¼ft und spÃƒÂ¤ter gebenchmarkt werden.


## Stand 0.1.0-dev.13
Der globale Nachrichtenindex GDELT wird mit EZB-, Federal-Reserve- und Kraken-Feeds kombiniert. Quellenklassen und Gewichte bleiben nachvollziehbar. Nachrichten werden deterministisch taxonomiert und nur fÃƒÂ¼r die Vorfilterung verwendet. Jeder Vorfilterlauf erzeugt eine Watchlist-Version; valide Detailanalysen erzeugen 24h- und 168h-Prognosesnapshots, die spÃƒÂ¤ter gegen reale Preise bewertet werden. Modellgewichte ÃƒÂ¤ndern sich nicht automatisch.


## Stand 0.1.0-dev.14
Dev.14 ist ein gezielter Start-Hotfix auf Basis von dev.13. Ursache des Exit-Codes war die fehlende SQLite-Migration der in dev.13 erweiterten Nachrichtentabellen. Fehlende Spalten werden nun beim Start idempotent ergÃƒÂ¤nzt; Quellen und Nachrichten werden mit expliziten Spaltenlisten geschrieben. Bestehende Nachrichten bleiben erhalten.

## Stand 0.1.0-dev.15
Die fehleranfÃƒÂ¤llige breite GDELT-Global-Abfrage wurde stillgelegt. GDELT Wirtschaft und GDELT Geopolitik verwenden kleinere Abfragen; Google News Wirtschaft AT und Google News Geopolitik AT ergÃƒÂ¤nzen sie als RSS-Aggregatoren. Abrufe verwenden einen gesetzten User-Agent, bis zu drei begrenzte Versuche und persistieren HTTP-Status, Detailfehler, FehlerzÃƒÂ¤hler sowie letzten Erfolg. In den Einstellungen kann ein eigener automatischer Research-Zeitplan aktiviert werden.

## Stand 0.1.0-dev.16
Dev.16 erweitert das Universum auf Kraken-Aktien/xStocks der Assetklasse `tokenized_asset` und akzeptiert EUR- sowie USD-Paare im Ã¶ffentlichen Stream. USD-Produkte werden fÃ¼r das Paper-Portfolio Ã¼ber EUR/USD in EUR bewertet. Der neue PortfolioAllocator berechnet Zielgewichte aus Scanner-Score, VolatilitÃ¤t, Portfolioobergrenze und No-Trade-Band. SchwÃ¤chere Positionen dÃ¼rfen eine bessere Gelegenheit nur finanzieren, wenn der konfigurierte Konfidenzabstand die geschÃ¤tzten Rundlaufkosten Ã¼bersteigt. Dynamischer Paper-Hebel nutzt ausschlieÃŸlich Kraken-Metadaten und das Benutzermaximum. RealausfÃ¼hrung bleibt hart deaktiviert; ein separater Adapter validiert lediglich zukÃ¼nftige PlÃ¤ne.

## Stand 0.1.0-dev.18
Dev.17 behebt den UNIQUE-Fehler aus dev.16. Ursache war nicht ein doppelter Kraken-Markt, sondern die gewünschte Mehrfachmitgliedschaft eines hebelfähigen xStocks in `xstocks` und `leveraged_spot`. Vorfilterergebnisse bleiben bewusst symbolbezogen und werden deshalb kanonisch dedupliziert. USD-xStocks bleiben vollständig zugelassen. Vorfilter und Detailscanner gruppieren Tickerabrufe nach Kraken-Assetklasse, damit `tokenized_asset` nicht versehentlich über den Currency-Standard abgefragt wird.
