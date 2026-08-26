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

## 0.1.0-dev.16 — 2026-08-25
Aktien/xStocks mit USD-Streaming, GDELT-TLS-Cooldown, dynamische Paper-Allokation, kostenbewusste Umschichtungen und marktgebundener dynamischer Paper-Hebel.

## 0.1.0-dev.18 — 2026-08-25
xStocks-Scanner-Hotfix: robuste Assetklassenabfragen, Einzel-Fallback und nichtleere Research-Watchlist trotz vorübergehend fehlendem Ticker.

## 0.1.0-dev.20 — 2026-08-25
Hotfix für Prognose-Inserts bei Mehrklassen-Scans und vollständige UTF-8-Bereinigung. Dev.18-Kandidatenkorrekturen und dev.17-KI-Analyse bleiben erhalten.

## 0.1.0-dev.20 — 2026-08-25
Vorfilter-Deduplizierung für Mehrfachkategorien, konfliktfeste Persistenz und vollständige UTF-8-Reparatur auf Basis des vom Benutzer übergebenen dev.19-Letztstands.

## 0.1.0-dev.24 — 2026-08-25
Endgültige UTF-8-Absicherung mit Quelltextprüfung, Git-/Editor-Regeln, HTTP-Charset und einmaliger Migration bestehender SQLite-Anzeigetexte.

## 0.1.0-dev.24 — 2026-08-25
Direkte UTF-8-Reparatur sämtlicher ausgelieferter Quellen und Dokumente, erneute idempotente Bestandsdatenmigration sowie kombinierter Regressionstest gegen Mojibake und den Vorfilter-UNIQUE-Fehler.

## 0.1.0-dev.24 — 2026-08-25
Durchgängiger xStocks-Pfad vom Kraken-Universum über Aktien-Detailscore und EUR-Umrechnung bis zur kostenbehafteten Paper-Ausführung, einschließlich fail-closed Mindestorderprüfung.

## 0.1.0-dev.24 — 2026-08-25
Hotfix für reale xStock-Detailscores: dokumentierter `asset_class`-Parameter, `assetVersion=1`, Kraken-`source_key` für OHLC und aussagekräftige Fehlerdiagnose.

## 0.1.0-dev.25 — 2026-08-26
Kontrollierter xStock-Lernprozess mit neun begrenzten Parametern, übersichtlicher Gegenüberstellung und Ein-Klick-Gesamtfreigabe. Keine automatische Parameteränderung.

## 0.1.0-dev.26 - 2026-08-26
Kanonische Produkte, kostenoptimale EUR/USD-Paarwahl, vollständige FX-Kostensimulation, repariertes Forex-Universum mit forex-v1 und Schutz vor häufigen Umschichtungen. Alle bisherigen Funktionen bleiben erhalten.

## 0.1.0-dev.27 - 2026-08-26
Konsolidierte Weiterentwicklung von v26 mit dokumentationskonformem Forex-Universum, kanonischer kostenbasierter Paarwahl, vollständiger Paper-Kostenkette, stabilen Umschichtungsregeln und echter UTF-8-Migration.



## 0.1.0-dev.28
Forex-Datenqualität, persistente abgeschlossene OHLCVT-Historie und erste reproduzierbare Walk-forward-Benchmarks.

## 0.1.0-dev.29
Kontospezifische Maker-/Taker-Gebühren mit Herkunft, Zeitpunkt und konservativem Fallback.

## 0.1.0-dev.30
Versioniertes forex-v2 im strikt wirkungslosen Schattenmodus mit Vergleich gegen forex-v1.

## 0.1.0-dev.31
Kanonische Produktansicht und auditierbare Umschichtungsmatrix mit exaktem Blockierungsgrund.

## 0.1.0-dev.32
Kontrollierter Lernprozess für alle Anlageklassen mit Schattenmodus, Konfidenzintervall und Rollback.



## 0.1.0-dev.34
- Regression und UTF-8 bereinigt
- 103 Tests erfolgreich
- Scanner-Resilienz und Legacy-Schemakompatibilität wiederhergestellt
- getrennte aktive Produktklassenprofile beibehalten

## 0.1.0-dev.36
- kostenbewusster Offline-Schattenvergleich
- getrennte 24h- und 168h-Metriken
- Abdeckung, Nettorendite und maximaler Drawdown
- 105 Tests erfolgreich




## 0.1.0-dev.36 — 2026-08-26
Konsistenz- und Vertrauensrelease mit zentraler Laufzeitversion, synchronisierten Metadaten, vollständig repariertem UTF-8 und korrigiertem Regressionstest. 109 automatisierte Tests erfolgreich. Strategie unverändert; Realhandel bleibt hart deaktiviert.

## 0.1.0-dev.37 — 2026-08-26
Robuste kontrollierte Lernfreigabe mit Horizontpflicht, Mindeststichprobe, Mindestabdeckung, positiver Nettorenditeverbesserung und Drawdown-Grenzen. Policy und Gate-Ergebnisse sind persistent und auditierbar; vor Aktivierung erfolgt eine erneute atomare Prüfung. 115 automatisierte Tests erfolgreich.

## 0.1.0-dev.38 — 2026-08-26
Zielzeitgenaue Prognoseauswertung aus der ersten abgeschlossenen historischen OHLC-Kerze am oder nach dem Zielzeitpunkt. Kosten-Snapshots trennen Einstieg, Ausstieg und Roundtrip und dokumentieren ihre Gebührenquelle. 119 automatisierte Tests erfolgreich.
