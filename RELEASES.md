# Releases — append-only

## 0.1.0-dev.1 — 2026-08-23
Erster installierbarer Read-only-Stand.

## 0.1.0-dev.2 — 2026-08-23
Ingress-Navigation repariert; API-Diagnoseseite ergänzt; alle GUI-Tabs und präfixfähige Exporte implementiert; bestehende Funktionen erhalten.
- 2026-08-23 0.1.0-dev.3 Portfoliohistorie, Nullpositionen, Ledger-Pagination und WebSocket-Berechtigungstest.
- 2026-08-23 0.1.0-dev.4 oeffentlicher WebSocket-v2-Ticker, persistente Live-Preise, Heartbeat/Stale-Erkennung und Reconnect.
- 2026-08-23 0.1.0-dev.5 private read-only WebSocket-v2-Balances und Executions mit Sequenzkontrolle.

## 0.1.0-dev.6 — 2026-08-23
Erster persistenter Paper-Broker mit Positionen, Trades, Snapshots, Gebühren, Slippage, Positionslimit und begründeter Momentum-Baseline. Alle read-only Kraken- und WebSocket-Funktionen aus dev.5 bleiben erhalten; Realhandel bleibt ausgeschlossen.

## 0.1.0-dev.7 — 2026-08-23
Sichtbare Paper-Konfiguration, persistente Laufparameter, Allowlist-WebSocket-Abonnement, REST-Preis-Fallback und periodischer Paper-Scheduler. Kein erzwungener Kauf; Signalgates und alle Sicherheitsgrenzen bleiben erhalten.

## 0.1.0-dev.8 — 2026-08-23
Statistischer Markt-Scanner mit OHLC-Cache, Momentum, SMA-Trend, Volatilität, Spread, Volumen, reproduzierbarem Score, Datenqualität und begründeten BUY/HOLD/AVOID-Signalen.


## 0.1.0-dev.13 — 2026-08-25
Erweiterte Nachrichtenarchitektur, Themen- und Ereignistaxonomie, versionierte Watchlists sowie kontrollierte Prognoseauswertung.


## 0.1.0-dev.14 — 2026-08-25
Startreparatur für Upgrades: migrationssichere Nachrichtentabellen, explizite Inserts und Regressionstest mit simuliertem dev.12-Datenbestand.

## 0.1.0-dev.15 — 2026-08-25
Robuste Nachrichtenbeschaffung mit kleineren GDELT-Abfragen, Google-News-RSS-Fallbacks, Quellendiagnose und optional automatischer Research-Pipeline.
