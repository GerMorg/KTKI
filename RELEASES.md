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

## 0.1.0-dev.9 — 2026-08-23
Kontrollierte Scanner-Paper-Kopplung mit fail-closed Daten-Gate sowie persistente Kraken-AssetPairs-Regeln für Paarstatus, Mindestmenge, Mindestwert, Präzision und öffentliche Taker-Gebühr.
