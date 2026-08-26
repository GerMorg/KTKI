# Changelog
## 0.1.0-dev.27
- v26 als alleinige Entwicklungsbasis übernommen und die Umsetzung konsolidiert
- kanonische Produkte über Anlageklasse und Basiswert
- kostenoptimale EUR/USD-Paarwahl mit Spread, Liquidität, Slippage, Handels- und FX-Kosten
- vollständige USD-Paper-Kostenkette mit separatem Produkspread und FX-Kosten
- Forex-Universum aus dokumentierten Currency-Paaren abgeleitet und eigenes forex-v1 beibehalten
- xStocks und traditionelle Aktien strikt getrennt; Rohmetadaten auditierbar
- Mindesthaltedauer, Cooldown, Bestätigung, Hysterese, Tageslimit und Steuersimulation
- echte UTF-8-Quelltextbereinigung und idempotente SQLite-Migration v4
## 0.1.0-dev.26
- Kanonische Produktidentität und kostenbasierte EUR/USD-Ausführungspaarwahl
- vollständige FX-Kostenkette für USD-Paper-Trades
- Forex-Universum repariert und deterministisches forex-v1-Profil
- xStocks und traditionelle Aktien strikt getrennt; API-Metadaten auditierbar
- Mindesthaltedauer, Cooldown, Mehrfachbestätigung und tägliches Umschichtungslimit
- vollständige UTF-8-Bereinigung

## 0.1.0-dev.25
- neuer Ingress-Tab Lernfreigaben
- neun xStock-Bewertungsparameter zentral versioniert
- begrenzte Vorschläge aus ausgewerteten Prognosen
- Mindeststichprobe von fünf Auswertungen
- keine automatische Aktivierung
- Ein-Klick-Freigabe aller neun Parameter als gemeinsame Version
- vollständige Audit-Protokollierung

## 0.1.0-dev.24
- realen xStock-Detailscore durch korrekten Kraken-API-Vertrag repariert
