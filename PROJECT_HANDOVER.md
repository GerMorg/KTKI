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
Dev.16 erweitert das Universum auf Kraken-Aktien/xStocks der Assetklasse `tokenized_asset` und akzeptiert EUR- sowie USD-Paare im öffentlichen Stream. USD-Produkte werden für das Paper-Portfolio über EUR/USD in EUR bewertet. Der neue PortfolioAllocator berechnet Zielgewichte aus Scanner-Score, Volatilität, Portfolioobergrenze und No-Trade-Band. Schwächere Positionen dürfen eine bessere Gelegenheit nur finanzieren, wenn der konfigurierte Konfidenzabstand die geschätzten Rundlaufkosten übersteigt. Dynamischer Paper-Hebel nutzt ausschließlich Kraken-Metadaten und das Benutzermaximum. Realausführung bleibt hart deaktiviert; ein separater Adapter validiert lediglich zukünftige Pläne.

## Stand 0.1.0-dev.17
Dev.17 basiert auf dev.16. Fehlende Module wurden ergänzt. Optional analysiert OpenAI oder Azure OpenAI Feed-Titel und Kurztexte. Ergebnisse sind schema-, prompt-, modell- und provider-versioniert. Fehler führen zum deterministischen Fallback. Der KI-Einfluss ist gedeckelt und auf Research beschränkt.
