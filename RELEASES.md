# Releases Ã¢â‚¬â€ append-only

## 0.1.0-dev.1 Ã¢â‚¬â€ 2026-08-23
Erster installierbarer Read-only-Stand.

## 0.1.0-dev.2 Ã¢â‚¬â€ 2026-08-23
Ingress-Navigation repariert; API-Diagnoseseite ergÃƒÂ¤nzt; alle GUI-Tabs und prÃƒÂ¤fixfÃƒÂ¤hige Exporte implementiert; bestehende Funktionen erhalten.
- 2026-08-23 0.1.0-dev.3 Portfoliohistorie, Nullpositionen, Ledger-Pagination und WebSocket-Berechtigungstest.
- 2026-08-23 0.1.0-dev.4 oeffentlicher WebSocket-v2-Ticker, persistente Live-Preise, Heartbeat/Stale-Erkennung und Reconnect.
- 2026-08-23 0.1.0-dev.5 private read-only WebSocket-v2-Balances und Executions mit Sequenzkontrolle.

## 0.1.0-dev.6 Ã¢â‚¬â€ 2026-08-23
Erster persistenter Paper-Broker mit Positionen, Trades, Snapshots, GebÃƒÂ¼hren, Slippage, Positionslimit und begrÃƒÂ¼ndeter Momentum-Baseline. Alle read-only Kraken- und WebSocket-Funktionen aus dev.5 bleiben erhalten; Realhandel bleibt ausgeschlossen.

## 0.1.0-dev.7 Ã¢â‚¬â€ 2026-08-23
Sichtbare Paper-Konfiguration, persistente Laufparameter, Allowlist-WebSocket-Abonnement, REST-Preis-Fallback und periodischer Paper-Scheduler. Kein erzwungener Kauf; Signalgates und alle Sicherheitsgrenzen bleiben erhalten.

## 0.1.0-dev.8 Ã¢â‚¬â€ 2026-08-23
Statistischer Markt-Scanner mit OHLC-Cache, Momentum, SMA-Trend, VolatilitÃƒÂ¤t, Spread, Volumen, reproduzierbarem Score, DatenqualitÃƒÂ¤t und begrÃƒÂ¼ndeten BUY/HOLD/AVOID-Signalen.


## 0.1.0-dev.13 Ã¢â‚¬â€ 2026-08-25
Erweiterte Nachrichtenarchitektur, Themen- und Ereignistaxonomie, versionierte Watchlists sowie kontrollierte Prognoseauswertung.


## 0.1.0-dev.14 Ã¢â‚¬â€ 2026-08-25
Startreparatur fÃƒÂ¼r Upgrades: migrationssichere Nachrichtentabellen, explizite Inserts und Regressionstest mit simuliertem dev.12-Datenbestand.

## 0.1.0-dev.15 Ã¢â‚¬â€ 2026-08-25
Robuste Nachrichtenbeschaffung mit kleineren GDELT-Abfragen, Google-News-RSS-Fallbacks, Quellendiagnose und optional automatischer Research-Pipeline.

## 0.1.0-dev.16 Ã¢â‚¬â€ 2026-08-25
Aktien/xStocks mit USD-Streaming, GDELT-TLS-Cooldown, dynamische Paper-Allokation, kostenbewusste Umschichtungen und marktgebundener dynamischer Paper-Hebel.

## 0.1.0-dev.18 Ã¢â‚¬â€ 2026-08-25
xStocks-Scanner-Hotfix: robuste Assetklassenabfragen, Einzel-Fallback und nichtleere Research-Watchlist trotz vorÃƒÂ¼bergehend fehlendem Ticker.

## 0.1.0-dev.20 Ã¢â‚¬â€ 2026-08-25
Hotfix fÃƒÂ¼r Prognose-Inserts bei Mehrklassen-Scans und vollstÃƒÂ¤ndige UTF-8-Bereinigung. Dev.18-Kandidatenkorrekturen und dev.17-KI-Analyse bleiben erhalten.

## 0.1.0-dev.20 Ã¢â‚¬â€ 2026-08-25
Vorfilter-Deduplizierung fÃƒÂ¼r Mehrfachkategorien, konfliktfeste Persistenz und vollstÃƒÂ¤ndige UTF-8-Reparatur auf Basis des vom Benutzer ÃƒÂ¼bergebenen dev.19-Letztstands.

## 0.1.0-dev.24 Ã¢â‚¬â€ 2026-08-25
EndgÃƒÂ¼ltige UTF-8-Absicherung mit QuelltextprÃƒÂ¼fung, Git-/Editor-Regeln, HTTP-Charset und einmaliger Migration bestehender SQLite-Anzeigetexte.

## 0.1.0-dev.24 Ã¢â‚¬â€ 2026-08-25
Direkte UTF-8-Reparatur sÃƒÂ¤mtlicher ausgelieferter Quellen und Dokumente, erneute idempotente Bestandsdatenmigration sowie kombinierter Regressionstest gegen Mojibake und den Vorfilter-UNIQUE-Fehler.

## 0.1.0-dev.24 Ã¢â‚¬â€ 2026-08-25
DurchgÃƒÂ¤ngiger xStocks-Pfad vom Kraken-Universum ÃƒÂ¼ber Aktien-Detailscore und EUR-Umrechnung bis zur kostenbehafteten Paper-AusfÃƒÂ¼hrung, einschlieÃƒÅ¸lich fail-closed MindestorderprÃƒÂ¼fung.

## 0.1.0-dev.24 Ã¢â‚¬â€ 2026-08-25
Hotfix fÃƒÂ¼r reale xStock-Detailscores: dokumentierter `asset_class`-Parameter, `assetVersion=1`, Kraken-`source_key` fÃƒÂ¼r OHLC und aussagekrÃƒÂ¤ftige Fehlerdiagnose.

## 0.1.0-dev.25 Ã¢â‚¬â€ 2026-08-26
Kontrollierter xStock-Lernprozess mit neun begrenzten Parametern, ÃƒÂ¼bersichtlicher GegenÃƒÂ¼berstellung und Ein-Klick-Gesamtfreigabe. Keine automatische ParameterÃƒÂ¤nderung.

## 0.1.0-dev.26 - 2026-08-26
Kanonische Produkte, kostenoptimale EUR/USD-Paarwahl, vollstÃƒÂ¤ndige FX-Kostensimulation, repariertes Forex-Universum mit forex-v1 und Schutz vor hÃƒÂ¤ufigen Umschichtungen. Alle bisherigen Funktionen bleiben erhalten.

## 0.1.0-dev.27 - 2026-08-26
Konsolidierte Weiterentwicklung von v26 mit dokumentationskonformem Forex-Universum, kanonischer kostenbasierter Paarwahl, vollstÃƒÂ¤ndiger Paper-Kostenkette, stabilen Umschichtungsregeln und echter UTF-8-Migration.



## 0.1.0-dev.28
Forex-DatenqualitÃƒÂ¤t, persistente abgeschlossene OHLCVT-Historie und erste reproduzierbare Walk-forward-Benchmarks.

## 0.1.0-dev.29
Kontospezifische Maker-/Taker-GebÃƒÂ¼hren mit Herkunft, Zeitpunkt und konservativem Fallback.

## 0.1.0-dev.30
Versioniertes forex-v2 im strikt wirkungslosen Schattenmodus mit Vergleich gegen forex-v1.

## 0.1.0-dev.31
Kanonische Produktansicht und auditierbare Umschichtungsmatrix mit exaktem Blockierungsgrund.

## 0.1.0-dev.32
Kontrollierter Lernprozess fÃƒÂ¼r alle Anlageklassen mit Schattenmodus, Konfidenzintervall und Rollback.



## 0.1.0-dev.34
- Regression und UTF-8 bereinigt
- 103 Tests erfolgreich
- Scanner-Resilienz und Legacy-SchemakompatibilitÃƒÂ¤t wiederhergestellt
- getrennte aktive Produktklassenprofile beibehalten

## 0.1.0-dev.36
- kostenbewusster Offline-Schattenvergleich
- getrennte 24h- und 168h-Metriken
- Abdeckung, Nettorendite und maximaler Drawdown
- 105 Tests erfolgreich




## 0.1.0-dev.36 Ã¢â‚¬â€ 2026-08-26
Konsistenz- und Vertrauensrelease mit zentraler Laufzeitversion, synchronisierten Metadaten, vollstÃƒÂ¤ndig repariertem UTF-8 und korrigiertem Regressionstest. 109 automatisierte Tests erfolgreich. Strategie unverÃƒÂ¤ndert; Realhandel bleibt hart deaktiviert.

## 0.1.0-dev.37 Ã¢â‚¬â€ 2026-08-26
Robuste kontrollierte Lernfreigabe mit Horizontpflicht, Mindeststichprobe, Mindestabdeckung, positiver Nettorenditeverbesserung und Drawdown-Grenzen. Policy und Gate-Ergebnisse sind persistent und auditierbar; vor Aktivierung erfolgt eine erneute atomare PrÃƒÂ¼fung. 115 automatisierte Tests erfolgreich.

## 0.1.0-dev.38 Ã¢â‚¬â€ 2026-08-26
Zielzeitgenaue Prognoseauswertung aus der ersten abgeschlossenen historischen OHLC-Kerze am oder nach dem Zielzeitpunkt. Kosten-Snapshots trennen Einstieg, Ausstieg und Roundtrip und dokumentieren ihre GebÃƒÂ¼hrenquelle. 119 automatisierte Tests erfolgreich.

## 0.1.0-dev.43 Ã¢â‚¬â€ 2026-08-27
Stabilisierung, robuster kanonischer GebÃƒÂ¼hrenabruf, isolierte Paarfehler und vollstÃƒÂ¤ndig ÃƒÂ¼berarbeitete gefÃƒÂ¼hrte Ingress-GUI. 124 Tests erfolgreich; Realhandel hart deaktiviert.


## 0.1.0-dev.43 - 2026-08-28
Kontrolliertes Nachrichten-Lernen mit externer AI als Lehrer, automatischem Schattenvergleich und ausschlieÃƒÅ¸lich manueller lokaler Aktivierung. Realhandel bleibt hart deaktiviert.

## 0.1.0-dev.43 - 2026-08-28
Zeitlich getrennte Trainings- und Validierungsfenster fÃƒÂ¼r kontrolliertes Nachrichten-Lernen mit persistenter Provenienz und fail-closed FreigabeprÃƒÂ¼fung. Realhandel bleibt hart deaktiviert.

## 0.1.0-dev.43 - 2026-08-28
Mehrfenster-Walk-forward-StabilitÃƒÂ¤tsprÃƒÂ¼fung fÃƒÂ¼r Nachrichtenkandidaten mit persistierten Teilfenster-Metriken und erneuter PrÃƒÂ¼fung bei manueller Freigabe.



## 0.1.0-dev.45 - 2026-08-28
VollstÃƒÂ¤ndige LernversionsÃƒÂ¼bersicht mit familienbezogener Navigation und konsistent gefilterten Detaildaten.

## 0.1.0-dev.46 - 2026-08-28
Lernfamilien-Dashboard mit aktiver Version, offenen Kandidaten, letztem Status und abgesicherter Familienauswahl.

## 0.1.0-dev.47 - 2026-08-28
StabilitÃƒÂ¤tsrelease fÃƒÂ¼r kontrolliertes Lernen und Nachrichten-Lernen mit transparenten Datenstatus- und Wiederherstellungswegen.

## 0.1.0-dev.51 - 2026-08-28
IntegritÃƒÂ¤tsrelease: UTF-8-Quellen bereinigt, Versionsmetadaten synchronisiert, GUI-Bezeichnung konsistent und USD-WebSocket-Abdeckung repariert. Realhandel bleibt hart deaktiviert.

## 0.1.0-dev.51
Monitoring-Blueprint, Ereignis-Dashboard, redigierter Audit-Export und vollstÃƒÂ¤ndige UTF-8-Reparatur.
## 0.1.0-dev.51
Steuerinfo Ãƒâ€“sterreich; Realhandel bleibt hart deaktiviert.
## 0.1.0-dev.51
Abgesicherte Realhandels-Grundstufe mit standardmÃ¤ÃŸigem Validate-only-Modus.
