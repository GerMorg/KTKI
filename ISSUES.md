# Issues â€” append-only

## 2026-08-23 I001
Assetcodes und EUR-Bewertung noch offen.

## 2026-08-23 I002 â€” gelÃ¶st in 0.1.0-dev.2
Tabs fÃ¼hrten wegen fehlendem Ingress-PrÃ¤fix zu 404; Dashboard-Link verlieÃŸ die App. GelÃ¶st durch X-Ingress-Path-Middleware und konsequentes `url_for`.
- 2026-08-23 Direkte EUR-Bewertung deckt noch nicht jedes Asset ab; unbewertete Positionen markieren den Snapshot als INCOMPLETE.
- 2026-08-23 Assets ohne direkten EUR-Markt erhalten in dev.4 keinen Live-Stream; Cross-Rate-Bewertung folgt spaeter.
- 2026-08-23 Execution-Historie des Streams ist begrenzt; der REST-Ledger bleibt fuer vollstaendige Historie und Steuerdaten massgeblich.

## 2026-08-23 I003 â€” offen
Paper-GebÃ¼hren sind noch konfigurierbare Basispunkte und nicht die kontospezifische Kraken-GebÃ¼hrenstufe.

## 2026-08-23 I004 â€” offen
InstrumentabhÃ¤ngige MindestordergrÃ¶ÃŸe und Mindestkosten aus AssetPairs werden noch nicht im Paper-Broker validiert.

## 2026-08-23 I005 â€” gelÃ¶st in 0.1.0-dev.7
Paper-Konfiguration war in der Ingress-GUI nicht vollstÃ¤ndig sichtbar. GelÃ¶st durch eigene Konfigurationskarten im Tab Einstellungen.

## 2026-08-23 I006 â€” gelÃ¶st in 0.1.0-dev.7
Allowlist-Produkte erhielten nicht zuverlÃ¤ssig Livepreise, da primÃ¤r Echtportfolio-Symbole abonniert wurden. GelÃ¶st durch Allowlist-Abonnement plus REST-Ticker-Fallback.

## 2026-08-23 I007 â€” gelÃ¶st in 0.1.0-dev.7
Paper-Strategie lief nicht periodisch. GelÃ¶st durch konfigurierbaren Hintergrund-Scheduler.

## 2026-08-23 I008 â€” offen
Scanner und Paper-Orderentscheidung sind bewusst noch nicht gekoppelt; zunÃ¤chst ist die statistische Baseline praktisch zu validieren.


## 2026-08-25 I016 â€” gelÃ¶st in 0.1.0-dev.13
Die Nachrichtenabdeckung war zu schmal und ohne allgemeine Ereignistaxonomie. Dev.13 kombiniert globale Abdeckung mit PrimÃ¤rfeeds und speichert Themen sowie Ereignistypen.

## 2026-08-25 I017 â€” gelÃ¶st in 0.1.0-dev.13
Watchlists und Prognosen waren nicht historisch vergleichbar. Versionen, Horizonte, Ausgangspreise und spÃ¤tere Ergebnisbewertungen werden nun persistent gespeichert.


## 2026-08-25 I018 â€” gelÃ¶st in 0.1.0-dev.14
Dev.13 erweiterte `news_sources` und `news_items`, migrierte bestehende Tabellen aus dev.12 jedoch nicht. Beim Anwendungsstart trafen neue Inserts auf alte Spaltenzahlen; der Gunicorn-Worker konnte deshalb nicht booten. Dev.14 ergÃ¤nzt fehlende Spalten idempotent, verwendet explizite Spaltenlisten und bewahrt bestehende Daten.

## 2026-08-25 I019 â€” gelÃ¶st in 0.1.0-dev.15
Die breite Quelle â€žGDELT Globalâ€œ lieferte wiederholt einen unspezifischen URL-Fehler. Sie wird deaktiviert und durch zwei kleinere GDELT-Abfragen ersetzt. Abrufe besitzen nun User-Agent, begrenzte Wiederholungen sowie nachvollziehbare HTTP- und Fehlerdiagnose.

## 2026-08-25 I020 — gelöst in 0.1.0-dev.16
Der öffentliche Stream und Vorfilter waren auf EUR-Paare beschränkt; dadurch fehlten USD-notierte Aktien/xStocks. Dev.16 unterstützt EUR- und USD-Paare, Assetklassenrouting und EUR-Umrechnung über EUR/USD.

## 2026-08-25 I021 — gelöst in 0.1.0-dev.16
GDELT-TLS-Handshake-Timeouts erzeugten bei jedem Lauf neue Wartezeiten. Nach einem erkannten Handshake-Timeout wird die Quelle sechs Stunden auf DEGRADED/Cooldown gesetzt.
