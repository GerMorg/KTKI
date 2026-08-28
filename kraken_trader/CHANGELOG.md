# Changelog
## 0.1.0-dev.46
- Statusübersicht und robuste Familienauswahl im kontrollierten Lernen ergänzt
- Realhandel bleibt hart deaktiviert
## 0.1.0-dev.45
- Lernfamilienübersicht und konsistente Familienfilterung ergänzt
- Realhandel bleibt hart deaktiviert
## 0.1.0-dev.42
- externe Nachrichten-AI dient als versionierte Vergleichsinstanz fÃ¼r die lokale Auswertung
- nach erfolgreichen AI-Auswertungen wird automatisch ein deduplizierter Schattenvergleich gestartet
- neun begrenzte lokale Nachrichtenparameter werden per deterministischer Koordinatensuche vorgeschlagen
- FehlermaÃŸ und RichtungsÃ¼bereinstimmung sind harte Vergleichsgates
- neue lokale Parameter werden niemals automatisch aktiviert, sondern nur nach ausdrÃ¼cklicher Freigabe
- Freigabe wiederholt den Vergleich und aktiviert alle Parameter atomar als neue Version
- aktive lokale Nachrichtenbewertung wird mit Modellversion persistent gespeichert und beeinflusst die Relevanzgewichtung
- neue Ingress-Seite â€žNachrichten-Lernenâ€œ mit Kandidaten, Vergleichswerten und Versionshistorie
- Realhandel bleibt hart deaktiviert
## 0.1.0-dev.42
- Repository und sichtbare GUI-Texte vollstÃ¤ndig als echtes UTF-8 repariert
- GebÃ¼hrenabruf lÃ¶st interne Symbole vor TradeVolume gegen Kraken-QuellschlÃ¼ssel und Aliasse auf
- nicht unterstÃ¼tzte Assetklassen werden mit dokumentiertem Konfigurations-Fallback Ã¼bersprungen
- fehlerhafte GebÃ¼hrenpaare werden isoliert; gÃ¼ltige Paare bleiben bei Teilfehlern erhalten
- neue Ã¼bersichtliche, responsive Hauptnavigation und gefÃ¼hrte Startseite
- kontrolliertes Lernen zeigt aktive Version, Parametervergleich, Gates und Aktivierungswirkung verstÃ¤ndlich an
- 124 automatische Regressionstests erfolgreich
- Realhandel bleibt hart deaktiviert
## 0.1.0-dev.38
- fÃ¤llige Prognosen werden mit der ersten vollstÃ¤ndig abgeschlossenen historischen OHLC-Kerze am oder nach dem Zielzeitpunkt bewertet
- Livepreise werden nicht mehr als Ersatz fÃ¼r historische Zielpreise verwendet
- Zielzeit, Preisquelle, Kerzenzeit und Zeitabweichung werden persistent gespeichert
- Kosten werden getrennt als Einstieg, Ausstieg und Roundtrip gespeichert
- GebÃ¼hrenquelle, GebÃ¼hrenzeitpunkt und FX-Erfordernis werden im Feature-Snapshot nachgewiesen
- Feature-Schema auf Version 3 angehoben und Alt-Schema migrationssicher erweitert
- vollstÃ¤ndige Regression: 119 Tests erfolgreich
- Realhandel bleibt hart deaktiviert
## 0.1.0-dev.37
- robuste Freigabe-Gates je erforderlichem Prognosehorizont
- Mindeststichprobe, Mindestabdeckung und positive Nettorenditeverbesserung sind harte Gates
- absoluter maximaler Drawdown und maximale Drawdown-Verschlechterung sind harte Gates
- Gate-Policy und Einzelergebnisse werden je Kandidat unverÃ¤nderlich gespeichert und auditiert
- Freigabe prÃ¼ft alle Gates unmittelbar vor der atomaren Aktivierung erneut
- Gate-Schwellen sind Ã¼ber Add-on-Optionen konfigurierbar und in der GUI sichtbar
- migrationssichere Erweiterung vorhandener Kandidatentabellen
- vollstÃ¤ndige Regression: 115 Tests erfolgreich
- keine automatische Aktivierung; Realhandel bleibt hart deaktiviert
## 0.1.0-dev.36
- zentrale Versionsquelle fÃ¼r Anwendung, Health-Endpunkt und HTTP-User-Agent
- alle ausgelieferten Textdateien und GUI-Texte als echtes UTF-8 normalisiert
- widersprÃ¼chlichen UTF-8-Regressionstest korrigiert
- Add-on-Metadaten, README, DOCS, VertrÃ¤ge und Projektunterlagen synchronisiert
- vollstÃ¤ndige Regression: 109 Tests erfolgreich
- keine Ã„nderung der Handelsstrategie; Realhandel bleibt hart deaktiviert
## 0.1.0-dev.35
- Offline-Schattenvergleich verwendet dieselben historischen Feature-Snapshots fÃ¼r aktive und vorgeschlagene Parameter
- Lernmetriken werden getrennt fÃ¼r 24- und 168-Stunden-Horizonte gespeichert
- Nettorendite berÃ¼cksichtigt geschÃ¤tzte Roundtrip-Kosten aus Spread, HandelsgebÃ¼hr, Slippage und optionaler FX-GebÃ¼hr
- Abdeckung, Entscheidungsanzahl und maximaler Drawdown werden je Horizont ausgewiesen
- HOLD und fehlende Entscheidung werden nicht mehr pauschal als falsche Prognose gewertet
- GUI zeigt Horizontmetriken jedes Lernkandidaten
- keine automatische Parameteraktivierung; Realhandel bleibt hart deaktiviert
- vollstÃ¤ndige Regression: 105 Tests erfolgreich
## 0.1.0-dev.34
- vollstÃ¤ndige Legacy-Testsuite wiederhergestellt: 103 Tests erfolgreich
- Repository- und GUI-Texte vollstÃ¤ndig als echtes UTF-8 normalisiert
- Scanner-Lock, BUSY-Status und rotierende begrenzte Batches wiederhergestellt
- Datenbank- und Forecast-KompatibilitÃ¤t fÃ¼r Ã¤ltere Schemas abgesichert
- External-News-AI-Vertrag und hart deaktivierte Real-Execution-Grenze wiederhergestellt
- Produktklassenprofile bleiben getrennt und steuern den Scanner weiterhin wirksam
- veraltete Tests auf aktuelle Parameter-, GebÃ¼hren- und AllokationsvertrÃ¤ge migriert
- Build-PrÃ¼fung installiert AbhÃ¤ngigkeiten reproduzierbar aus requirements.txt
## 0.1.0-dev.33
- ein einziges kontrolliertes Lernsystem fÃ¼r Forex, xStocks und Krypto
- neun vollstÃ¤ndig versionierte Parameter je Produktklasse
- aktive Familienversionen steuern den Scanner tatsÃ¤chlich
- Prognosen speichern Familie, Parameterversion, Parameter- und Feature-Snapshot
- paarweiser Schattenvergleich auf denselben Beobachtungen
- veraltete Kandidaten werden als STALE blockiert
- vorhandene xStock-Parameter werden migrationssicher Ã¼bernommen
- neue Integrations- und SicherheitsprÃ¼fungen
## 0.1.0-dev.32
- getrennte kontrollierte Parameterfamilien fÃ¼r Forex, xStocks und Krypto
- Schattenvergleich jedes Kandidaten gegen die aktive Version
- Mindeststichprobe und Mindestverbesserung als harte Freigabegates
- Wilson-Konfidenzintervall statt bloÃŸer Trefferquote
- ausdrÃ¼ckliche Freigabe, Ablehnung und vollstÃ¤ndiger versionierter Rollback
- keine automatische Aktivierung und keine direkte KI-Aktivierung
- neuer GUI-Tab Kontrolliertes Lernen
## 0.1.0-dev.31
- sichtbare kanonische ProduktidentitÃ¤ten mit gewÃ¤hltem und alternativen AusfÃ¼hrungspaaren
- direkter EUR-/USD-Kostenvergleich, Zeitpunkt und Auswahlgrund
- Zuordnung bestehender Paper-Positionen zum kanonischen Produkt
- einheitliche Umschichtungsmatrix mit sieben einzeln persistierten Regeln
- exakter Blockierungsgrund fÃ¼r abgelehnte Entscheidungen
- neue GUI-Tabs Produkte und Regelmatrix
## 0.1.0-dev.30
- forex-v2 als strikt wirkungsloser Schattenmodus
- relative StÃ¤rke beider WÃ¤hrungen und Risiko-/Safe-Haven-Regime
- getrennte kurzfristige und mittelfristige Horizonte
- paarbezogene Nachrichtenmerkmale und versionierte Eingangssnapshots
- fehlende Zins-, Inflations-, Wachstums- und Zentralbankdaten bleiben explizit null
- Vergleich mit forex-v1 samt Abweichungsprotokoll und neuem GUI-Tab
## 0.1.0-dev.29
- read-only TradeVolume-Abruf fÃ¼r kontospezifische 30-Tage-GebÃ¼hrenstufen
- Maker und Taker je Paar mit Quelle und Zeitpunkt persistent gespeichert
- konservativer konfigurierter Fallback bei fehlender Berechtigung oder API-Fehler
- Paper-AusfÃ¼hrung und KostenschÃ¤tzung verwenden das aktive paarbezogene Taker-Profil
- neuer Ingress-Tab GebÃ¼hren; Realhandel bleibt hart deaktiviert
## 0.1.0-dev.28
- Forex-Diagnose fÃ¼r Ticker, Bid/Ask, Volumen, OHLC und konkrete FehlergrÃ¼nde
- persistenter OHLCVT-Historienspeicher mit CSV-Importbasis und abgeschlossenen Kerzen
- Walk-forward-Backtest mit Benchmarks Keine Position, Buy-and-Hold und SMA-Trend
- getrennte Ergebnisse nach Anlageklasse sowie Kosten- und Drawdown-Kennzahlen
- neue Ingress-Tabs DatenqualitÃ¤t und Backtests; Realhandel bleibt hart deaktiviert
## 0.1.0-dev.27
- v26 als alleinige Entwicklungsbasis Ã¼bernommen und die Umsetzung konsolidiert
- kanonische Produkte Ã¼ber Anlageklasse und Basiswert
- kostenoptimale EUR/USD-Paarwahl mit Spread, LiquiditÃ¤t, Slippage, Handels- und FX-Kosten
- vollstÃ¤ndige USD-Paper-Kostenkette mit separatem Produkspread und FX-Kosten
- Forex-Universum aus dokumentierten Currency-Paaren abgeleitet und eigenes forex-v1 beibehalten
- xStocks und traditionelle Aktien strikt getrennt; Rohmetadaten auditierbar
- Mindesthaltedauer, Cooldown, BestÃ¤tigung, Hysterese, Tageslimit und Steuersimulation
- echte UTF-8-Quelltextbereinigung und idempotente SQLite-Migration v4
## 0.1.0-dev.26
- Kanonische ProduktidentitÃ¤t und kostenbasierte EUR/USD-AusfÃ¼hrungspaarwahl
- vollstÃ¤ndige FX-Kostenkette fÃ¼r USD-Paper-Trades
- Forex-Universum repariert und deterministisches forex-v1-Profil
- xStocks und traditionelle Aktien strikt getrennt; API-Metadaten auditierbar
- Mindesthaltedauer, Cooldown, MehrfachbestÃ¤tigung und tÃ¤gliches Umschichtungslimit
- vollstÃ¤ndige UTF-8-Bereinigung

## 0.1.0-dev.25
- neuer Ingress-Tab Lernfreigaben
- neun xStock-Bewertungsparameter zentral versioniert
- begrenzte VorschlÃ¤ge aus ausgewerteten Prognosen
- Mindeststichprobe von fÃ¼nf Auswertungen
- keine automatische Aktivierung
- Ein-Klick-Freigabe aller neun Parameter als gemeinsame Version
- vollstÃ¤ndige Audit-Protokollierung

## 0.1.0-dev.24
- realen xStock-Detailscore durch korrekten Kraken-API-Vertrag repariert

## 0.1.0-dev.42 - 2026-08-28
- Nachrichtenkandidaten werden ausschlieÃŸlich auf einem Ã¤lteren Trainingsfenster optimiert und auf einem spÃ¤teren, disjunkten Validierungsfenster geprÃ¼ft
- Fenstergrenzen, Stichprobenzahlen, Policy und Vergleichsmetriken werden persistent gespeichert und auditiert
- Freigaben prÃ¼fen Datenfingerprint und Validierung erneut; geÃ¤nderte Stichproben blockieren fail-closed
- idempotente Schemaerweiterung und neue Regressionstests
- keine automatische Aktivierung; Realhandel bleibt hart deaktiviert

## 0.1.0-dev.42 - 2026-08-28
- Nachrichtenkandidaten erhalten drei aufeinanderfolgende Walk-forward-Validierungsfenster
- mindestens zwei Fenster mÃ¼ssen Verlustverbesserung und unverÃ¤nderte oder bessere RichtungsÃ¼bereinstimmung erfÃ¼llen
- Ergebnisse jedes Teilfensters und die StabilitÃ¤tsanforderung werden persistent gespeichert und in der GUI angezeigt
- unzureichende Historie und instabile Kandidaten werden fail-closed blockiert
- Freigabe wiederholt auch die Walk-forward-StabilitÃ¤tsgates
- Realhandel und automatische Aktivierung bleiben hart deaktiviert

## 0.1.0-dev.43
- Ãœbersicht trennt verfÃ¼gbare REST-/Portfoliodaten vom Zustand der optionalen WebSocket-KanÃ¤le
- vorhandene Marktdaten und Portfolios werden nicht mehr pauschal als Fehler dargestellt
- Gemini ist als externer Nachrichten-AI-Anbieter konfigurierbar
- Gemini-REST-Transport unterstÃ¼tzt JSON-Ausgaben, API-Key-Header, Modell und Timeout
- AI-Verarbeitung erzwingt das konfigurierte Lauf-Limit
- Realhandel bleibt hart deaktiviert
