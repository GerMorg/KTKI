# Releases ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â append-only

## 0.1.0-dev.1 ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â 2026-08-23
Erster installierbarer Read-only-Stand.

## 0.1.0-dev.2 ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â 2026-08-23
Ingress-Navigation repariert; API-Diagnoseseite ergÃƒÆ’Ã‚Â¤nzt; alle GUI-Tabs und prÃƒÆ’Ã‚Â¤fixfÃƒÆ’Ã‚Â¤hige Exporte implementiert; bestehende Funktionen erhalten.
- 2026-08-23 0.1.0-dev.3 Portfoliohistorie, Nullpositionen, Ledger-Pagination und WebSocket-Berechtigungstest.
- 2026-08-23 0.1.0-dev.4 oeffentlicher WebSocket-v2-Ticker, persistente Live-Preise, Heartbeat/Stale-Erkennung und Reconnect.
- 2026-08-23 0.1.0-dev.5 private read-only WebSocket-v2-Balances und Executions mit Sequenzkontrolle.

## 0.1.0-dev.6 ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â 2026-08-23
Erster persistenter Paper-Broker mit Positionen, Trades, Snapshots, GebÃƒÆ’Ã‚Â¼hren, Slippage, Positionslimit und begrÃƒÆ’Ã‚Â¼ndeter Momentum-Baseline. Alle read-only Kraken- und WebSocket-Funktionen aus dev.5 bleiben erhalten; Realhandel bleibt ausgeschlossen.

## 0.1.0-dev.7 ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â 2026-08-23
Sichtbare Paper-Konfiguration, persistente Laufparameter, Allowlist-WebSocket-Abonnement, REST-Preis-Fallback und periodischer Paper-Scheduler. Kein erzwungener Kauf; Signalgates und alle Sicherheitsgrenzen bleiben erhalten.

## 0.1.0-dev.8 ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â 2026-08-23
Statistischer Markt-Scanner mit OHLC-Cache, Momentum, SMA-Trend, VolatilitÃƒÆ’Ã‚Â¤t, Spread, Volumen, reproduzierbarem Score, DatenqualitÃƒÆ’Ã‚Â¤t und begrÃƒÆ’Ã‚Â¼ndeten BUY/HOLD/AVOID-Signalen.


## 0.1.0-dev.13 ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â 2026-08-25
Erweiterte Nachrichtenarchitektur, Themen- und Ereignistaxonomie, versionierte Watchlists sowie kontrollierte Prognoseauswertung.


## 0.1.0-dev.14 ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â 2026-08-25
Startreparatur fÃƒÆ’Ã‚Â¼r Upgrades: migrationssichere Nachrichtentabellen, explizite Inserts und Regressionstest mit simuliertem dev.12-Datenbestand.

## 0.1.0-dev.15 ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â 2026-08-25
Robuste Nachrichtenbeschaffung mit kleineren GDELT-Abfragen, Google-News-RSS-Fallbacks, Quellendiagnose und optional automatischer Research-Pipeline.

## 0.1.0-dev.16 ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â 2026-08-25
Aktien/xStocks mit USD-Streaming, GDELT-TLS-Cooldown, dynamische Paper-Allokation, kostenbewusste Umschichtungen und marktgebundener dynamischer Paper-Hebel.

## 0.1.0-dev.18 ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â 2026-08-25
xStocks-Scanner-Hotfix: robuste Assetklassenabfragen, Einzel-Fallback und nichtleere Research-Watchlist trotz vorÃƒÆ’Ã‚Â¼bergehend fehlendem Ticker.

## 0.1.0-dev.20 ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â 2026-08-25
Hotfix fÃƒÆ’Ã‚Â¼r Prognose-Inserts bei Mehrklassen-Scans und vollstÃƒÆ’Ã‚Â¤ndige UTF-8-Bereinigung. Dev.18-Kandidatenkorrekturen und dev.17-KI-Analyse bleiben erhalten.

## 0.1.0-dev.20 ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â 2026-08-25
Vorfilter-Deduplizierung fÃƒÆ’Ã‚Â¼r Mehrfachkategorien, konfliktfeste Persistenz und vollstÃƒÆ’Ã‚Â¤ndige UTF-8-Reparatur auf Basis des vom Benutzer ÃƒÆ’Ã‚Â¼bergebenen dev.19-Letztstands.

## 0.1.0-dev.24 ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â 2026-08-25
EndgÃƒÆ’Ã‚Â¼ltige UTF-8-Absicherung mit QuelltextprÃƒÆ’Ã‚Â¼fung, Git-/Editor-Regeln, HTTP-Charset und einmaliger Migration bestehender SQLite-Anzeigetexte.

## 0.1.0-dev.24 ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â 2026-08-25
Direkte UTF-8-Reparatur sÃƒÆ’Ã‚Â¤mtlicher ausgelieferter Quellen und Dokumente, erneute idempotente Bestandsdatenmigration sowie kombinierter Regressionstest gegen Mojibake und den Vorfilter-UNIQUE-Fehler.

## 0.1.0-dev.24 ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â 2026-08-25
DurchgÃƒÆ’Ã‚Â¤ngiger xStocks-Pfad vom Kraken-Universum ÃƒÆ’Ã‚Â¼ber Aktien-Detailscore und EUR-Umrechnung bis zur kostenbehafteten Paper-AusfÃƒÆ’Ã‚Â¼hrung, einschlieÃƒÆ’Ã…Â¸lich fail-closed MindestorderprÃƒÆ’Ã‚Â¼fung.

## 0.1.0-dev.24 ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â 2026-08-25
Hotfix fÃƒÆ’Ã‚Â¼r reale xStock-Detailscores: dokumentierter `asset_class`-Parameter, `assetVersion=1`, Kraken-`source_key` fÃƒÆ’Ã‚Â¼r OHLC und aussagekrÃƒÆ’Ã‚Â¤ftige Fehlerdiagnose.

## 0.1.0-dev.25 ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â 2026-08-26
Kontrollierter xStock-Lernprozess mit neun begrenzten Parametern, ÃƒÆ’Ã‚Â¼bersichtlicher GegenÃƒÆ’Ã‚Â¼berstellung und Ein-Klick-Gesamtfreigabe. Keine automatische ParameterÃƒÆ’Ã‚Â¤nderung.

## 0.1.0-dev.26 - 2026-08-26
Kanonische Produkte, kostenoptimale EUR/USD-Paarwahl, vollstÃƒÆ’Ã‚Â¤ndige FX-Kostensimulation, repariertes Forex-Universum mit forex-v1 und Schutz vor hÃƒÆ’Ã‚Â¤ufigen Umschichtungen. Alle bisherigen Funktionen bleiben erhalten.

## 0.1.0-dev.27 - 2026-08-26
Konsolidierte Weiterentwicklung von v26 mit dokumentationskonformem Forex-Universum, kanonischer kostenbasierter Paarwahl, vollstÃƒÆ’Ã‚Â¤ndiger Paper-Kostenkette, stabilen Umschichtungsregeln und echter UTF-8-Migration.



## 0.1.0-dev.28
Forex-DatenqualitÃƒÆ’Ã‚Â¤t, persistente abgeschlossene OHLCVT-Historie und erste reproduzierbare Walk-forward-Benchmarks.

## 0.1.0-dev.29
Kontospezifische Maker-/Taker-GebÃƒÆ’Ã‚Â¼hren mit Herkunft, Zeitpunkt und konservativem Fallback.

## 0.1.0-dev.30
Versioniertes forex-v2 im strikt wirkungslosen Schattenmodus mit Vergleich gegen forex-v1.

## 0.1.0-dev.31
Kanonische Produktansicht und auditierbare Umschichtungsmatrix mit exaktem Blockierungsgrund.

## 0.1.0-dev.32
Kontrollierter Lernprozess fÃƒÆ’Ã‚Â¼r alle Anlageklassen mit Schattenmodus, Konfidenzintervall und Rollback.



## 0.1.0-dev.34
- Regression und UTF-8 bereinigt
- 103 Tests erfolgreich
- Scanner-Resilienz und Legacy-SchemakompatibilitÃƒÆ’Ã‚Â¤t wiederhergestellt
- getrennte aktive Produktklassenprofile beibehalten

## 0.1.0-dev.36
- kostenbewusster Offline-Schattenvergleich
- getrennte 24h- und 168h-Metriken
- Abdeckung, Nettorendite und maximaler Drawdown
- 105 Tests erfolgreich




## 0.1.0-dev.36 ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â 2026-08-26
Konsistenz- und Vertrauensrelease mit zentraler Laufzeitversion, synchronisierten Metadaten, vollstÃƒÆ’Ã‚Â¤ndig repariertem UTF-8 und korrigiertem Regressionstest. 109 automatisierte Tests erfolgreich. Strategie unverÃƒÆ’Ã‚Â¤ndert; Realhandel bleibt hart deaktiviert.

## 0.1.0-dev.37 ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â 2026-08-26
Robuste kontrollierte Lernfreigabe mit Horizontpflicht, Mindeststichprobe, Mindestabdeckung, positiver Nettorenditeverbesserung und Drawdown-Grenzen. Policy und Gate-Ergebnisse sind persistent und auditierbar; vor Aktivierung erfolgt eine erneute atomare PrÃƒÆ’Ã‚Â¼fung. 115 automatisierte Tests erfolgreich.

## 0.1.0-dev.38 ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â 2026-08-26
Zielzeitgenaue Prognoseauswertung aus der ersten abgeschlossenen historischen OHLC-Kerze am oder nach dem Zielzeitpunkt. Kosten-Snapshots trennen Einstieg, Ausstieg und Roundtrip und dokumentieren ihre GebÃƒÆ’Ã‚Â¼hrenquelle. 119 automatisierte Tests erfolgreich.

## 0.1.0-dev.43 ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â 2026-08-27
Stabilisierung, robuster kanonischer GebÃƒÆ’Ã‚Â¼hrenabruf, isolierte Paarfehler und vollstÃƒÆ’Ã‚Â¤ndig ÃƒÆ’Ã‚Â¼berarbeitete gefÃƒÆ’Ã‚Â¼hrte Ingress-GUI. 124 Tests erfolgreich; Realhandel hart deaktiviert.


## 0.1.0-dev.43 - 2026-08-28
Kontrolliertes Nachrichten-Lernen mit externer AI als Lehrer, automatischem Schattenvergleich und ausschlieÃƒÆ’Ã…Â¸lich manueller lokaler Aktivierung. Realhandel bleibt hart deaktiviert.

## 0.1.0-dev.43 - 2026-08-28
Zeitlich getrennte Trainings- und Validierungsfenster fÃƒÆ’Ã‚Â¼r kontrolliertes Nachrichten-Lernen mit persistenter Provenienz und fail-closed FreigabeprÃƒÆ’Ã‚Â¼fung. Realhandel bleibt hart deaktiviert.

## 0.1.0-dev.43 - 2026-08-28
Mehrfenster-Walk-forward-StabilitÃƒÆ’Ã‚Â¤tsprÃƒÆ’Ã‚Â¼fung fÃƒÆ’Ã‚Â¼r Nachrichtenkandidaten mit persistierten Teilfenster-Metriken und erneuter PrÃƒÆ’Ã‚Â¼fung bei manueller Freigabe.



## 0.1.0-dev.45 - 2026-08-28
VollstÃƒÆ’Ã‚Â¤ndige LernversionsÃƒÆ’Ã‚Â¼bersicht mit familienbezogener Navigation und konsistent gefilterten Detaildaten.

## 0.1.0-dev.46 - 2026-08-28
Lernfamilien-Dashboard mit aktiver Version, offenen Kandidaten, letztem Status und abgesicherter Familienauswahl.

## 0.1.0-dev.47 - 2026-08-28
StabilitÃƒÆ’Ã‚Â¤tsrelease fÃƒÆ’Ã‚Â¼r kontrolliertes Lernen und Nachrichten-Lernen mit transparenten Datenstatus- und Wiederherstellungswegen.

## 0.1.0-dev.51 - 2026-08-28
IntegritÃƒÆ’Ã‚Â¤tsrelease: UTF-8-Quellen bereinigt, Versionsmetadaten synchronisiert, GUI-Bezeichnung konsistent und USD-WebSocket-Abdeckung repariert. Realhandel bleibt hart deaktiviert.

## 0.1.0-dev.51
Monitoring-Blueprint, Ereignis-Dashboard, redigierter Audit-Export und vollstÃƒÆ’Ã‚Â¤ndige UTF-8-Reparatur.
## 0.1.0-dev.51
Steuerinfo ÃƒÆ’Ã¢â‚¬â€œsterreich; Realhandel bleibt hart deaktiviert.
## 0.1.0-dev.51
Abgesicherte Realhandels-Grundstufe mit standardmÃƒÂ¤ÃƒÅ¸igem Validate-only-Modus.
