# Changelog

## 0.1.0-dev.5
- Privater read-only Kraken WebSocket v2 fuer Balances und Executions.
- Frischer Token je Verbindung ohne Speicherung oder Anzeige.
- Sequenzkontrolle, Gap-Audit, DEGRADED-Zustand und automatischer Snapshot-Neuaufbau.
- Keine WebSocket-Ordermethoden und keine echten Orders.


## 0.1.0-dev.4
- Oeffentlicher Kraken Spot WebSocket v2 fuer Live-Ticker aktuell gehaltener EUR-Assets.
- Persistente Live-Preise, Verbindungs- und Kraken-Systemstatus.
- Heartbeat-Frische, STALE-Erkennung und automatischer Reconnect.
- REST-Reconciliation sowie alle bestehenden Funktionen bleiben erhalten.
- Keine privaten Streams und keine echten Orders.


## 0.1.0-dev.3
- Kraken-Realportfolio mit EUR-Bewertung und historischen Snapshots.
- Historische Nullpositionen aus der Ledger-Historie.
- Vollständige Ledger-Pagination und Portfolio-CSV.
- WebSocket-Token-Berechtigungstest; Token wird nie gespeichert.
- Alle bisherigen GUI-Seiten und Schutzgrenzen bleiben erhalten.
