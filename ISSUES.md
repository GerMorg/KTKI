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

## 2026-08-23 I003 — teilweise gelöst in 0.1.0-dev.9
Pauschale Paper-Gebühren werden bei vorhandenen AssetPairs-Metadaten durch die öffentliche erste Taker-Gebührenstufe ersetzt. Die kontospezifische TradeVolume-Gebühr bleibt offen.

## 2026-08-23 I004 — gelöst in 0.1.0-dev.9
Instrumentabhängige Mindestmenge, Mindestwert, Paarstatus und Mengenpräzision werden vor Paper-Käufen geprüft.

## 2026-08-23 I008 — gelöst in 0.1.0-dev.9
Scanner und Paper-Entscheidung sind kontrolliert gekoppelt; fehlende Scanner-Daten blockieren standardmäßig fail-closed.

## 2026-08-23 I009 — gelöst in 0.1.0-dev.10
Umlaute und Sonderzeichen waren teilweise als Mojibake dargestellt. Textquellen, Dokumentation und GUI wurden konsistent als UTF-8 normalisiert.

## 2026-08-23 I010 — gelöst in 0.1.0-dev.10
Einzelproduktfreigaben wurden durch dynamische Produktgruppen und ein vollständiges Kraken-Marktinventar ersetzt.

## 2026-08-23 I011 — gelöst in 0.1.0-dev.11
Mojibake wie „Ãœbersicht“ blieb in gemischten Quelltexten bestehen. Bekannte Fehlsequenzen wurden gezielt ersetzt und HTTP-Antworten deklarieren UTF-8 ausdrücklich.

## 2026-08-23 I012 — gelöst in 0.1.0-dev.11
Ein synchroner Scan des gesamten freigegebenen Marktes konnte Prozess und API überlasten. Der Scanner arbeitet nun asynchron, gesperrt, rate-aware und in rotierenden Teil-Läufen.


## 2026-08-25 I013 — gelöst in 0.1.0-dev.12
Automatik und manueller Paper-Lauf konnten durch vollständige Universums- und Scannerläufe blockiert werden. Der Paper-Pfad führt keine vollständige Research-Pipeline mehr synchron aus.

## 2026-08-25 I014 — gelöst in 0.1.0-dev.12
Der Scannerstart zeigte keinen belastbaren Fortschritt. Persistente Research-Aufträge speichern Status, Stufe, Fortschritt und Fehler.

## 2026-08-25 I015 — gelöst in 0.1.0-dev.12
Die Kraken-Client-Standardparameter behandelten normale Spot-Abfragen fälschlich als Forex. Asset-Class-Parameter werden nun nur für Forex und tokenisierte Assets gesendet.
