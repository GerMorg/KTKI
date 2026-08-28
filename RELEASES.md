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

## 0.1.0-dev.16 â€” 2026-08-25
Aktien/xStocks mit USD-Streaming, GDELT-TLS-Cooldown, dynamische Paper-Allokation, kostenbewusste Umschichtungen und marktgebundener dynamischer Paper-Hebel.

## 0.1.0-dev.18 â€” 2026-08-25
xStocks-Scanner-Hotfix: robuste Assetklassenabfragen, Einzel-Fallback und nichtleere Research-Watchlist trotz vorÃ¼bergehend fehlendem Ticker.

## 0.1.0-dev.20 â€” 2026-08-25
Hotfix fÃ¼r Prognose-Inserts bei Mehrklassen-Scans und vollstÃ¤ndige UTF-8-Bereinigung. Dev.18-Kandidatenkorrekturen und dev.17-KI-Analyse bleiben erhalten.

## 0.1.0-dev.20 â€” 2026-08-25
Vorfilter-Deduplizierung fÃ¼r Mehrfachkategorien, konfliktfeste Persistenz und vollstÃ¤ndige UTF-8-Reparatur auf Basis des vom Benutzer Ã¼bergebenen dev.19-Letztstands.

## 0.1.0-dev.24 â€” 2026-08-25
EndgÃ¼ltige UTF-8-Absicherung mit QuelltextprÃ¼fung, Git-/Editor-Regeln, HTTP-Charset und einmaliger Migration bestehender SQLite-Anzeigetexte.

## 0.1.0-dev.24 â€” 2026-08-25
Direkte UTF-8-Reparatur sÃ¤mtlicher ausgelieferter Quellen und Dokumente, erneute idempotente Bestandsdatenmigration sowie kombinierter Regressionstest gegen Mojibake und den Vorfilter-UNIQUE-Fehler.

## 0.1.0-dev.24 â€” 2026-08-25
DurchgÃ¤ngiger xStocks-Pfad vom Kraken-Universum Ã¼ber Aktien-Detailscore und EUR-Umrechnung bis zur kostenbehafteten Paper-AusfÃ¼hrung, einschlieÃŸlich fail-closed MindestorderprÃ¼fung.

## 0.1.0-dev.24 â€” 2026-08-25
Hotfix fÃ¼r reale xStock-Detailscores: dokumentierter `asset_class`-Parameter, `assetVersion=1`, Kraken-`source_key` fÃ¼r OHLC und aussagekrÃ¤ftige Fehlerdiagnose.

## 0.1.0-dev.25 â€” 2026-08-26
Kontrollierter xStock-Lernprozess mit neun begrenzten Parametern, Ã¼bersichtlicher GegenÃ¼berstellung und Ein-Klick-Gesamtfreigabe. Keine automatische ParameterÃ¤nderung.

## 0.1.0-dev.26 - 2026-08-26
Kanonische Produkte, kostenoptimale EUR/USD-Paarwahl, vollstÃ¤ndige FX-Kostensimulation, repariertes Forex-Universum mit forex-v1 und Schutz vor hÃ¤ufigen Umschichtungen. Alle bisherigen Funktionen bleiben erhalten.

## 0.1.0-dev.27 - 2026-08-26
Konsolidierte Weiterentwicklung von v26 mit dokumentationskonformem Forex-Universum, kanonischer kostenbasierter Paarwahl, vollstÃ¤ndiger Paper-Kostenkette, stabilen Umschichtungsregeln und echter UTF-8-Migration.



## 0.1.0-dev.28
Forex-DatenqualitÃ¤t, persistente abgeschlossene OHLCVT-Historie und erste reproduzierbare Walk-forward-Benchmarks.

## 0.1.0-dev.29
Kontospezifische Maker-/Taker-GebÃ¼hren mit Herkunft, Zeitpunkt und konservativem Fallback.

## 0.1.0-dev.30
Versioniertes forex-v2 im strikt wirkungslosen Schattenmodus mit Vergleich gegen forex-v1.

## 0.1.0-dev.31
Kanonische Produktansicht und auditierbare Umschichtungsmatrix mit exaktem Blockierungsgrund.

## 0.1.0-dev.32
Kontrollierter Lernprozess fÃ¼r alle Anlageklassen mit Schattenmodus, Konfidenzintervall und Rollback.



## 0.1.0-dev.34
- Regression und UTF-8 bereinigt
- 103 Tests erfolgreich
- Scanner-Resilienz und Legacy-SchemakompatibilitÃ¤t wiederhergestellt
- getrennte aktive Produktklassenprofile beibehalten

## 0.1.0-dev.36
- kostenbewusster Offline-Schattenvergleich
- getrennte 24h- und 168h-Metriken
- Abdeckung, Nettorendite und maximaler Drawdown
- 105 Tests erfolgreich




## 0.1.0-dev.36 â€” 2026-08-26
Konsistenz- und Vertrauensrelease mit zentraler Laufzeitversion, synchronisierten Metadaten, vollstÃ¤ndig repariertem UTF-8 und korrigiertem Regressionstest. 109 automatisierte Tests erfolgreich. Strategie unverÃ¤ndert; Realhandel bleibt hart deaktiviert.

## 0.1.0-dev.37 â€” 2026-08-26
Robuste kontrollierte Lernfreigabe mit Horizontpflicht, Mindeststichprobe, Mindestabdeckung, positiver Nettorenditeverbesserung und Drawdown-Grenzen. Policy und Gate-Ergebnisse sind persistent und auditierbar; vor Aktivierung erfolgt eine erneute atomare PrÃ¼fung. 115 automatisierte Tests erfolgreich.

## 0.1.0-dev.38 â€” 2026-08-26
Zielzeitgenaue Prognoseauswertung aus der ersten abgeschlossenen historischen OHLC-Kerze am oder nach dem Zielzeitpunkt. Kosten-Snapshots trennen Einstieg, Ausstieg und Roundtrip und dokumentieren ihre GebÃ¼hrenquelle. 119 automatisierte Tests erfolgreich.

## 0.1.0-dev.43 â€” 2026-08-27
Stabilisierung, robuster kanonischer GebÃ¼hrenabruf, isolierte Paarfehler und vollstÃ¤ndig Ã¼berarbeitete gefÃ¼hrte Ingress-GUI. 124 Tests erfolgreich; Realhandel hart deaktiviert.


## 0.1.0-dev.43 - 2026-08-28
Kontrolliertes Nachrichten-Lernen mit externer AI als Lehrer, automatischem Schattenvergleich und ausschlieÃŸlich manueller lokaler Aktivierung. Realhandel bleibt hart deaktiviert.

## 0.1.0-dev.43 - 2026-08-28
Zeitlich getrennte Trainings- und Validierungsfenster fÃ¼r kontrolliertes Nachrichten-Lernen mit persistenter Provenienz und fail-closed FreigabeprÃ¼fung. Realhandel bleibt hart deaktiviert.

## 0.1.0-dev.43 - 2026-08-28
Mehrfenster-Walk-forward-StabilitÃ¤tsprÃ¼fung fÃ¼r Nachrichtenkandidaten mit persistierten Teilfenster-Metriken und erneuter PrÃ¼fung bei manueller Freigabe.

## 0.1.0-dev.44 - 2026-08-28
Vollständige Übersicht der aktiven Lernversionen für Forex, xStocks und Krypto Spot. Realhandel bleibt hart deaktiviert.
