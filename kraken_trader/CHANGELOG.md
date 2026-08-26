# Changelog
## 0.1.0-dev.30
- forex-v2 als strikt wirkungsloser Schattenmodus
- relative Stärke beider Währungen und Risiko-/Safe-Haven-Regime
- getrennte kurzfristige und mittelfristige Horizonte
- paarbezogene Nachrichtenmerkmale und versionierte Eingangssnapshots
- fehlende Zins-, Inflations-, Wachstums- und Zentralbankdaten bleiben explizit null
- Vergleich mit forex-v1 samt Abweichungsprotokoll und neuem GUI-Tab
## 0.1.0-dev.29
- read-only TradeVolume-Abruf für kontospezifische 30-Tage-Gebührenstufen
- Maker und Taker je Paar mit Quelle und Zeitpunkt persistent gespeichert
- konservativer konfigurierter Fallback bei fehlender Berechtigung oder API-Fehler
- Paper-Ausführung und Kostenschätzung verwenden das aktive paarbezogene Taker-Profil
- neuer Ingress-Tab Gebühren; Realhandel bleibt hart deaktiviert
## 0.1.0-dev.28
- Forex-Diagnose für Ticker, Bid/Ask, Volumen, OHLC und konkrete Fehlergründe
- persistenter OHLCVT-Historienspeicher mit CSV-Importbasis und abgeschlossenen Kerzen
- Walk-forward-Backtest mit Benchmarks Keine Position, Buy-and-Hold und SMA-Trend
- getrennte Ergebnisse nach Anlageklasse sowie Kosten- und Drawdown-Kennzahlen
- neue Ingress-Tabs Datenqualität und Backtests; Realhandel bleibt hart deaktiviert
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


