# Issues — append-only

## 2026-08-23 I001
Assetcodes und EUR-Bewertung noch offen.

## 2026-08-23 I002 — gelöst in 0.1.0-dev.2
Tabs führten wegen fehlendem Ingress-Präfix zu 404; Dashboard-Link verließ die App. Gelöst durch X-Ingress-Path-Middleware und konsequentes `url_for`.
- 2026-08-23 Direkte EUR-Bewertung deckt noch nicht jedes Asset ab; unbewertete Positionen markieren den Snapshot als INCOMPLETE.
- 2026-08-23 Assets ohne direkten EUR-Markt erhalten in dev.4 keinen Live-Stream; Cross-Rate-Bewertung folgt spaeter.
- 2026-08-23 Execution-Historie des Streams ist begrenzt; der REST-Ledger bleibt fuer vollstaendige Historie und Steuerdaten massgeblich.

## 2026-08-23 I003 — offen
Paper-Gebühren sind noch konfigurierbare Basispunkte und nicht die kontospezifische Kraken-Gebührenstufe.

## 2026-08-23 I004 — offen
Instrumentabhängige Mindestordergröße und Mindestkosten aus AssetPairs werden noch nicht im Paper-Broker validiert.

## 2026-08-23 I005 — gelöst in 0.1.0-dev.7
Paper-Konfiguration war in der Ingress-GUI nicht vollständig sichtbar. Gelöst durch eigene Konfigurationskarten im Tab Einstellungen.

## 2026-08-23 I006 — gelöst in 0.1.0-dev.7
Allowlist-Produkte erhielten nicht zuverlässig Livepreise, da primär Echtportfolio-Symbole abonniert wurden. Gelöst durch Allowlist-Abonnement plus REST-Ticker-Fallback.

## 2026-08-23 I007 — gelöst in 0.1.0-dev.7
Paper-Strategie lief nicht periodisch. Gelöst durch konfigurierbaren Hintergrund-Scheduler.

## 2026-08-23 I008 — offen
Scanner und Paper-Orderentscheidung sind bewusst noch nicht gekoppelt; zunächst ist die statistische Baseline praktisch zu validieren.


## 2026-08-25 I016 — gelöst in 0.1.0-dev.13
Die Nachrichtenabdeckung war zu schmal und ohne allgemeine Ereignistaxonomie. Dev.13 kombiniert globale Abdeckung mit Primärfeeds und speichert Themen sowie Ereignistypen.

## 2026-08-25 I017 — gelöst in 0.1.0-dev.13
Watchlists und Prognosen waren nicht historisch vergleichbar. Versionen, Horizonte, Ausgangspreise und spätere Ergebnisbewertungen werden nun persistent gespeichert.


## 2026-08-25 I018 — gelöst in 0.1.0-dev.14
Dev.13 erweiterte `news_sources` und `news_items`, migrierte bestehende Tabellen aus dev.12 jedoch nicht. Beim Anwendungsstart trafen neue Inserts auf alte Spaltenzahlen; der Gunicorn-Worker konnte deshalb nicht booten. Dev.14 ergänzt fehlende Spalten idempotent, verwendet explizite Spaltenlisten und bewahrt bestehende Daten.

## 2026-08-25 I019 — gelöst in 0.1.0-dev.15
Die breite Quelle „GDELT Global“ lieferte wiederholt einen unspezifischen URL-Fehler. Sie wird deaktiviert und durch zwei kleinere GDELT-Abfragen ersetzt. Abrufe besitzen nun User-Agent, begrenzte Wiederholungen sowie nachvollziehbare HTTP- und Fehlerdiagnose.

## 2026-08-25 I020 â€” gelÃ¶st in 0.1.0-dev.16
Der Ã¶ffentliche Stream und Vorfilter waren auf EUR-Paare beschrÃ¤nkt; dadurch fehlten USD-notierte Aktien/xStocks. Dev.16 unterstÃ¼tzt EUR- und USD-Paare, Assetklassenrouting und EUR-Umrechnung Ã¼ber EUR/USD.

## 2026-08-25 I021 â€” gelÃ¶st in 0.1.0-dev.16
GDELT-TLS-Handshake-Timeouts erzeugten bei jedem Lauf neue Wartezeiten. Nach einem erkannten Handshake-Timeout wird die Quelle sechs Stunden auf DEGRADED/Cooldown gesetzt.

## 2026-08-25 I022 — gelöst in 0.1.0-dev.17
Im dev.16-Snapshot fehlten die referenzierten Module `portfolio_allocator.py` und `real_execution_adapter.py`. Beide wurden wiederhergestellt und getestet.

## 2026-08-25 I023 — gelöst in 0.1.0-dev.17
Eine optionale externe KI-Analyse ergänzt strukturierte inhaltliche Nachrichtenmerkmale mit strikter Validierung und begrenztem Einfluss.
