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

## Stand 0.1.0-dev.9
Dev.9 wurde unmittelbar aus dem bereitgestellten vollständigen dev.8-Snapshot rekonstruiert. `run_paper_cycle()` aktualisiert Livepreise, AssetPairs-Regeln und Scanner, bevor die PaperEngine entscheidet. Standardmäßig ist `scanner_required=true`: Nur ein valides Scanner-Ergebnis darf eine automatische Paper-Order auslösen. Die Engine prüft zusätzlich Paarstatus, Mindestmenge, Mindestwert und Mengenpräzision und verwendet die öffentliche Taker-Gebühr aus AssetPairs. Alle dev.8-Funktionen bleiben erhalten; Realhandel ist weiterhin nicht implementiert.

## Stand 0.1.0-dev.10
Die Einstellungen enthalten keine Einzelprodukte mehr. `market_universe.py` synchronisiert die vollständigen Kraken-Märkte für die Klassen `currency`, `tokenized_asset` und Forex und ordnet sie über eine überlappende Mitgliedschaft Kategorien zu. Der aktuell sichere Analyse- und Paper-Pfad verwendet daraus Online-Märkte mit EUR als Quotierungswährung. Texte und Dokumente wurden als UTF-8 normalisiert.

## Stand 0.1.0-dev.11
Umlaute wurden nicht nur dateiseitig, sondern zusätzlich über explizite UTF-8-Responseheader abgesichert. Der Scanner verarbeitet das vollständige kategoriebasierte Marktuniversum nicht mehr in einem synchronen Lauf. Ein persistenter Cursor wählt standardmäßig zehn Märkte, OHLC-Aufrufe werden verzögert, manuelle Läufe starten im Hintergrund und ein Lock verhindert Überlappungen. Preisabruf und öffentlicher Stream werden auf den aktuellen Teil-Lauf begrenzt.
