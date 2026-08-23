# Changelog
## 0.1.0-dev.5
- Authenticated read-only WebSocket v2 balances and executions streams.
- Fresh token per connection; token never persisted or displayed.
- Per-channel sequence tracking, gap audit, DEGRADED state and reconnect snapshots.
- No WebSocket order methods and no real-order transport.
## 0.1.0-dev.5
- Public Kraken WebSocket v2 ticker stream for held EUR assets.
- Persistent live prices, connection state, status, heartbeat freshness and reconnect backoff.
- REST remains canonical for portfolio snapshots and reconciliation.
- No private stream and no order transport.
## 0.1.0-dev.5
- Persistente historische Kraken-Portfolio-Snapshots mit EUR-Bewertung.
- Ehemals gehaltene Assets bleiben als Nullpositionen sichtbar.
- Vollständige Ledger-Pagination.
- Sicherer Test der privaten WebSocket-Berechtigung ohne Tokenspeicherung.
- Realhandel bleibt nicht implementiert.

## 0.1.0-dev.5
- HA-Ingress-Navigation für alle Tabs repariert
- API-Diagnoseseite und Verbindungstest
- Portfolio-Abruf und sichtbare Fehlerdiagnose
- Exportlinks ingress-kompatibel
- Regressionstests erweitert

## 0.1.0-dev.1
- Ingress-GUI, SQLite, Kraken read-only, Paper-Wallet, Audit und Exporte
