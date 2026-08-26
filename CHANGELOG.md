# Changelog
## 0.1.0-dev.38
- fällige Prognosen werden mit der ersten vollständig abgeschlossenen historischen OHLC-Kerze am oder nach dem Zielzeitpunkt bewertet
- Livepreise werden nicht mehr als Ersatz für historische Zielpreise verwendet
- Zielzeit, Preisquelle, Kerzenzeit und Zeitabweichung werden persistent gespeichert
- Kosten werden getrennt als Einstieg, Ausstieg und Roundtrip gespeichert
- Gebührenquelle, Gebührenzeitpunkt und FX-Erfordernis werden im Feature-Snapshot nachgewiesen
- Feature-Schema auf Version 3 angehoben und Alt-Schema migrationssicher erweitert
- vollständige Regression: 119 Tests erfolgreich
- Realhandel bleibt hart deaktiviert
## 0.1.0-dev.37
- robuste Freigabe-Gates je erforderlichem Prognosehorizont
- Mindeststichprobe, Mindestabdeckung und positive Nettorenditeverbesserung sind harte Gates
- absoluter maximaler Drawdown und maximale Drawdown-Verschlechterung sind harte Gates
- Gate-Policy und Einzelergebnisse werden je Kandidat unveränderlich gespeichert und auditiert
- Freigabe prüft alle Gates unmittelbar vor der atomaren Aktivierung erneut
- Gate-Schwellen sind über Add-on-Optionen konfigurierbar und in der GUI sichtbar
- migrationssichere Erweiterung vorhandener Kandidatentabellen
- vollständige Regression: 115 Tests erfolgreich
- keine automatische Aktivierung; Realhandel bleibt hart deaktiviert
## 0.1.0-dev.36
- zentrale Versionsquelle für Anwendung, Health-Endpunkt und HTTP-User-Agent
- alle ausgelieferten Textdateien und GUI-Texte als echtes UTF-8 normalisiert
- widersprüchlichen UTF-8-Regressionstest korrigiert
- Add-on-Metadaten, README, DOCS, Verträge und Projektunterlagen synchronisiert
- vollständige Regression: 109 Tests erfolgreich
- keine Änderung der Handelsstrategie; Realhandel bleibt hart deaktiviert
## 0.1.0-dev.35
- Offline-Schattenvergleich verwendet dieselben historischen Feature-Snapshots für aktive und vorgeschlagene Parameter
- Lernmetriken werden getrennt für 24- und 168-Stunden-Horizonte gespeichert
- Nettorendite berücksichtigt geschätzte Roundtrip-Kosten aus Spread, Handelsgebühr, Slippage und optionaler FX-Gebühr
- Abdeckung, Entscheidungsanzahl und maximaler Drawdown werden je Horizont ausgewiesen
- HOLD und fehlende Entscheidung werden nicht mehr pauschal als falsche Prognose gewertet
- GUI zeigt Horizontmetriken jedes Lernkandidaten
- keine automatische Parameteraktivierung; Realhandel bleibt hart deaktiviert
- vollständige Regression: 105 Tests erfolgreich
## 0.1.0-dev.34
- vollständige Legacy-Testsuite wiederhergestellt: 103 Tests erfolgreich
- Repository- und GUI-Texte vollständig als echtes UTF-8 normalisiert
- Scanner-Lock, BUSY-Status und rotierende begrenzte Batches wiederhergestellt
- Datenbank- und Forecast-Kompatibilität für ältere Schemas abgesichert
- External-News-AI-Vertrag und hart deaktivierte Real-Execution-Grenze wiederhergestellt
- Produktklassenprofile bleiben getrennt und steuern den Scanner weiterhin wirksam
- veraltete Tests auf aktuelle Parameter-, Gebühren- und Allokationsverträge migriert
- Build-Prüfung installiert Abhängigkeiten reproduzierbar aus requirements.txt
## 0.1.0-dev.33
- ein einziges kontrolliertes Lernsystem für Forex, xStocks und Krypto
- neun vollständig versionierte Parameter je Produktklasse
- aktive Familienversionen steuern den Scanner tatsächlich
- Prognosen speichern Familie, Parameterversion, Parameter- und Feature-Snapshot
- paarweiser Schattenvergleich auf denselben Beobachtungen
- veraltete Kandidaten werden als STALE blockiert
- vorhandene xStock-Parameter werden migrationssicher übernommen
- neue Integrations- und Sicherheitsprüfungen
## 0.1.0-dev.32
- getrennte kontrollierte Parameterfamilien für Forex, xStocks und Krypto
- Schattenvergleich jedes Kandidaten gegen die aktive Version
- Mindeststichprobe und Mindestverbesserung als harte Freigabegates
- Wilson-Konfidenzintervall statt bloßer Trefferquote
- ausdrückliche Freigabe, Ablehnung und vollständiger versionierter Rollback
- keine automatische Aktivierung und keine direkte KI-Aktivierung
- neuer GUI-Tab Kontrolliertes Lernen
## 0.1.0-dev.31
- sichtbare kanonische Produktidentitäten mit gewähltem und alternativen Ausführungspaaren
- direkter EUR-/USD-Kostenvergleich, Zeitpunkt und Auswahlgrund
- Zuordnung bestehender Paper-Positionen zum kanonischen Produkt
- einheitliche Umschichtungsmatrix mit sieben einzeln persistierten Regeln
- exakter Blockierungsgrund für abgelehnte Entscheidungen
- neue GUI-Tabs Produkte und Regelmatrix
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







