# Changelog
## 0.1.0-dev.19
- Prognose-Snapshot repariert: explizite Spaltenliste statt positionsabhängigem `VALUES`
- Regressionstest für das bestehende 12-Spalten-Schema
- Regressionstest für eine zukünftige zusätzliche Tabellenspalte
- vollständige UTF-8-Bereinigung der Repository-Texte und sichtbaren GUI-Texte
- automatischer Test gegen typische Mojibake-Marker
- xStocks- und Mehrklassen-Kandidatenkorrekturen aus dev.18 erhalten
- externe KI-Nachrichtenanalyse aus dev.17 erhalten

## 0.1.0-dev.18
- xStocks-Kandidatenfehler behoben
- `execution_venue=international` bei xStocks-Universumsabfrage
- Tickerabrufe nach Assetklasse gruppiert
- bei fehlerhaftem Batch automatische Einzelabfragen
- von Kraken gemeldete Märkte bleiben als `PENDING_TICKER` Research-Kandidaten erhalten
- ein Ticker-Ausfall leert die Watchlist nicht mehr
- externe KI-Nachrichtenanalyse aus dev.17 erhalten


## 0.1.0-dev.16
- Aktien/xStocks über `tokenized_asset`
- EUR- und USD-Märkte in Universum und öffentlichem Stream
- EUR-Bewertung von USD-Produkten über EUR/USD
- GDELT-TLS-Cooldown
- dynamische Paper-Zielgewichte und Transfergrößen
- kostenbewusste Umschichtung mit No-Trade-Band
- dynamischer Paper-Hebel aus Kraken-Metadaten
- simulierte Finanzierungsschuld und Eigenkapitalberechnung
- Realausführungsadapter vorbereitet, aber hart deaktiviert

## 0.1.0-dev.15
- Robuste Nachrichtenquellen und automatischer Research-Scheduler
