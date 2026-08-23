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
