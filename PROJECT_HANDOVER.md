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
