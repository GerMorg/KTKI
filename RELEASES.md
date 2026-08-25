# Releases â€” append-only

## 0.1.0-dev.1 â€” 2026-08-23
Erster installierbarer Read-only-Stand.

## 0.1.0-dev.2 â€” 2026-08-23
Ingress-Navigation repariert; API-Diagnoseseite ergÃ¤nzt; alle GUI-Tabs und prÃ¤fixfÃ¤hige Exporte implementiert; bestehende Funktionen erhalten.
- 2026-08-23 0.1.0-dev.3 Portfoliohistorie, Nullpositionen, Ledger-Pagination und WebSocket-Berechtigungstest.
- 2026-08-23 0.1.0-dev.4 oeffentlicher WebSocket-v2-Ticker, persistente Live-Preise, Heartbeat/Stale-Erkennung und Reconnect.
- 2026-08-23 0.1.0-dev.5 private read-only WebSocket-v2-Balances und Executions mit Sequenzkontrolle.

## 0.1.0-dev.6 â€” 2026-08-23
Erster persistenter Paper-Broker mit Positionen, Trades, Snapshots, GebÃ¼hren, Slippage, Positionslimit und begrÃ¼ndeter Momentum-Baseline. Alle read-only Kraken- und WebSocket-Funktionen aus dev.5 bleiben erhalten; Realhandel bleibt ausgeschlossen.

## 0.1.0-dev.7 â€” 2026-08-23
Sichtbare Paper-Konfiguration, persistente Laufparameter, Allowlist-WebSocket-Abonnement, REST-Preis-Fallback und periodischer Paper-Scheduler. Kein erzwungener Kauf; Signalgates und alle Sicherheitsgrenzen bleiben erhalten.

## 0.1.0-dev.8 â€” 2026-08-23
Statistischer Markt-Scanner mit OHLC-Cache, Momentum, SMA-Trend, VolatilitÃ¤t, Spread, Volumen, reproduzierbarem Score, DatenqualitÃ¤t und begrÃ¼ndeten BUY/HOLD/AVOID-Signalen.


## 0.1.0-dev.13 â€” 2026-08-25
Erweiterte Nachrichtenarchitektur, Themen- und Ereignistaxonomie, versionierte Watchlists sowie kontrollierte Prognoseauswertung.


## 0.1.0-dev.14 â€” 2026-08-25
Startreparatur fÃ¼r Upgrades: migrationssichere Nachrichtentabellen, explizite Inserts und Regressionstest mit simuliertem dev.12-Datenbestand.

## 0.1.0-dev.15 â€” 2026-08-25
Robuste Nachrichtenbeschaffung mit kleineren GDELT-Abfragen, Google-News-RSS-Fallbacks, Quellendiagnose und optional automatischer Research-Pipeline.

## 0.1.0-dev.16 — 2026-08-25
Aktien/xStocks mit USD-Streaming, GDELT-TLS-Cooldown, dynamische Paper-Allokation, kostenbewusste Umschichtungen und marktgebundener dynamischer Paper-Hebel.
