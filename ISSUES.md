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

## 2026-08-23 I003 — teilweise gelöst in 0.1.0-dev.9
Pauschale Paper-Gebühren werden bei vorhandenen AssetPairs-Metadaten durch die öffentliche erste Taker-Gebührenstufe ersetzt. Die kontospezifische TradeVolume-Gebühr bleibt offen.

## 2026-08-23 I004 — gelöst in 0.1.0-dev.9
Instrumentabhängige Mindestmenge, Mindestwert, Paarstatus und Mengenpräzision werden vor Paper-Käufen geprüft.

## 2026-08-23 I008 — gelöst in 0.1.0-dev.9
Scanner und Paper-Entscheidung sind kontrolliert gekoppelt; fehlende Scanner-Daten blockieren standardmäßig fail-closed.
