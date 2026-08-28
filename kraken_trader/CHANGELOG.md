## 0.1.0-dev.52
- Realhandel technisch aktivierbar, standardmäßig aus, mit Kill-Switch, Allowlist, Volumen- und Notional-Limits, Kraken-Validierung, Arming und Einmal-Token.
- Beide Lernloops durchsuchen Kandidaten automatisch per mehrpassiger Koordinatensuche.
- Nach jedem Research-Lauf startet die Kandidatensuche automatisch; nur die atomare Freigabe bleibt manuell.
- Forex-Trefferquote verwendet die konservative Wilson-Untergrenze auf BUY/AVOID; HOLD ist Enthaltung.
- Regressionstests für Lernmetrik und Realhandels-Sicherungen ergänzt.

# Changelog
## 0.1.0-dev.51
- sichtbare UTF-8-BeschÃƒÂ¤digungen in Quelltexten, Tests und Dokumentation vollstÃƒÂ¤ndig repariert
- Monitoring als erster Flask-Blueprint modularisiert
- neues filterbares Ereignis-Dashboard fÃƒÂ¼r Fehler, Warnungen und Benutzernachrichten
- Audit-Export als redigierte JSON- oder CSV-API ergÃƒÂ¤nzt
- WebSocket-Start fÃƒÂ¼r isolierte Tests explizit deaktivierbar gemacht
- neue Sicherheits- und Regressionstests; Realhandel bleibt hart deaktiviert
## 0.1.0-dev.51
- sichtbare Mojibake-Reste in Quelltexten, Tests und Projektdokumentation vollstÃƒÂ¤ndig repariert
- Laufzeit-, Add-on- und Repository-Version zentral auf dev.48 synchronisiert
- kontrolliertes Lernen bezeichnet aktive Versionen wieder konsistent
- ÃƒÂ¶ffentlicher Markt-WebSocket akzeptiert neben EUR auch USD-notierte MÃƒÂ¤rkte
- neue dev.48-IntegritÃƒÂ¤tsregressionen; Realhandel bleibt hart deaktiviert
## 0.1.0-dev.47
- Kontrolliertes Lernen repariert und Nachrichten-Lernen mit transparenter Datenbereitschaft stabilisiert
- Realhandel bleibt hart deaktiviert
## 0.1.0-dev.46
- StatusÃƒÂ¼bersicht und robuste Familienauswahl im kontrollierten Lernen ergÃƒÂ¤nzt
- Realhandel bleibt hart deaktiviert
## 0.1.0-dev.45
- LernfamilienÃƒÂ¼bersicht und konsistente Familienfilterung ergÃƒÂ¤nzt
- Realhandel bleibt hart deaktiviert
## 0.1.0-dev.40
- externe Nachrichten-AI dient als versionierte Vergleichsinstanz fÃƒÂ¼r die lokale Auswertung
- nach erfolgreichen AI-Auswertungen wird automatisch ein deduplizierter Schattenvergleich gestartet
- neun begrenzte lokale Nachrichtenparameter werden per deterministischer Koordinatensuche vorgeschlagen
- FehlermaÃƒÅ¸ und RichtungsÃƒÂ¼bereinstimmung sind harte Vergleichsgates
- neue lokale Parameter werden niemals automatisch aktiviert, sondern nur nach ausdrÃƒÂ¼cklicher Freigabe
- Freigabe wiederholt den Vergleich und aktiviert alle Parameter atomar als neue Version
- aktive lokale Nachrichtenbewertung wird mit Modellversion persistent gespeichert und beeinflusst die Relevanzgewichtung
- neue Ingress-Seite "Nachrichten-Lernen" mit Kandidaten, Vergleichswerten und Versionshistorie
- Realhandel bleibt hart deaktiviert
## 0.1.0-dev.39
- Repository und sichtbare GUI-Texte vollstÃƒÂ¤ndig als echtes UTF-8 repariert
- GebÃƒÂ¼hrenabruf lÃƒÂ¶st interne Symbole vor TradeVolume gegen Kraken-QuellschlÃƒÂ¼ssel und Aliasse auf
- nicht unterstÃƒÂ¼tzte Assetklassen werden mit dokumentiertem Konfigurations-Fallback ÃƒÂ¼bersprungen
- fehlerhafte GebÃƒÂ¼hrenpaare werden isoliert; gÃƒÂ¼ltige Paare bleiben bei Teilfehlern erhalten
- neue ÃƒÂ¼bersichtliche, responsive Hauptnavigation und gefÃƒÂ¼hrte Startseite
- kontrolliertes Lernen zeigt aktive Version, Parametervergleich, Gates und Aktivierungswirkung verstÃƒÂ¤ndlich an
- 124 automatische Regressionstests erfolgreich
- Realhandel bleibt hart deaktiviert
## 0.1.0-dev.38
- fÃƒÂ¤llige Prognosen werden mit der ersten vollstÃƒÂ¤ndig abgeschlossenen historischen OHLC-Kerze am oder nach dem Zielzeitpunkt bewertet
- Livepreise werden nicht mehr als Ersatz fÃƒÂ¼r historische Zielpreise verwendet
- Zielzeit, Preisquelle, Kerzenzeit und Zeitabweichung werden persistent gespeichert
- Kosten werden getrennt als Einstieg, Ausstieg und Roundtrip gespeichert
- GebÃƒÂ¼hrenquelle, GebÃƒÂ¼hrenzeitpunkt und FX-Erfordernis werden im Feature-Snapshot nachgewiesen
- Feature-Schema auf Version 3 angehoben und Alt-Schema migrationssicher erweitert
- vollstÃƒÂ¤ndige Regression: 119 Tests erfolgreich
- Realhandel bleibt hart deaktiviert
## 0.1.0-dev.37
- robuste Freigabe-Gates je erforderlichem Prognosehorizont
- Mindeststichprobe, Mindestabdeckung und positive Nettorenditeverbesserung sind harte Gates
- absoluter maximaler Drawdown und maximale Drawdown-Verschlechterung sind harte Gates
- Gate-Policy und Einzelergebnisse werden je Kandidat unverÃƒÂ¤nderlich gespeichert und auditiert
- Freigabe prÃƒÂ¼ft alle Gates unmittelbar vor der atomaren Aktivierung erneut
- Gate-Schwellen sind ÃƒÂ¼ber Add-on-Optionen konfigurierbar und in der GUI sichtbar
- migrationssichere Erweiterung vorhandener Kandidatentabellen
- vollstÃƒÂ¤ndige Regression: 115 Tests erfolgreich
- keine automatische Aktivierung; Realhandel bleibt hart deaktiviert
## 0.1.0-dev.36
- zentrale Versionsquelle fÃƒÂ¼r Anwendung, Health-Endpunkt und HTTP-User-Agent
- alle ausgelieferten Textdateien und GUI-Texte als echtes UTF-8 normalisiert
- widersprÃƒÂ¼chlichen UTF-8-Regressionstest korrigiert
- Add-on-Metadaten, README, DOCS, VertrÃƒÂ¤ge und Projektunterlagen synchronisiert
- vollstÃƒÂ¤ndige Regression: 109 Tests erfolgreich
- keine Ãƒâ€žnderung der Handelsstrategie; Realhandel bleibt hart deaktiviert
## 0.1.0-dev.35
- Offline-Schattenvergleich verwendet dieselben historischen Feature-Snapshots fÃƒÂ¼r aktive und vorgeschlagene Parameter
- Lernmetriken werden getrennt fÃƒÂ¼r 24- und 168-Stunden-Horizonte gespeichert
- Nettorendite berÃƒÂ¼cksichtigt geschÃƒÂ¤tzte Roundtrip-Kosten aus Spread, HandelsgebÃƒÂ¼hr, Slippage und optionaler FX-GebÃƒÂ¼hr
- Abdeckung, Entscheidungsanzahl und maximaler Drawdown werden je Horizont ausgewiesen
- HOLD und fehlende Entscheidung werden nicht mehr pauschal als falsche Prognose gewertet
- GUI zeigt Horizontmetriken jedes Lernkandidaten
- keine automatische Parameteraktivierung; Realhandel bleibt hart deaktiviert
- vollstÃƒÂ¤ndige Regression: 105 Tests erfolgreich
## 0.1.0-dev.34
- vollstÃƒÂ¤ndige Legacy-Testsuite wiederhergestellt: 103 Tests erfolgreich
- Repository- und GUI-Texte vollstÃƒÂ¤ndig als echtes UTF-8 normalisiert
- Scanner-Lock, BUSY-Status und rotierende begrenzte Batches wiederhergestellt
- Datenbank- und Forecast-KompatibilitÃƒÂ¤t fÃƒÂ¼r ÃƒÂ¤ltere Schemas abgesichert
- External-News-AI-Vertrag und hart deaktivierte Real-Execution-Grenze wiederhergestellt
- Produktklassenprofile bleiben getrennt und steuern den Scanner weiterhin wirksam
- veraltete Tests auf aktuelle Parameter-, GebÃƒÂ¼hren- und AllokationsvertrÃƒÂ¤ge migriert
- Build-PrÃƒÂ¼fung installiert AbhÃƒÂ¤ngigkeiten reproduzierbar aus requirements.txt
## 0.1.0-dev.33
- ein einziges kontrolliertes Lernsystem fÃƒÂ¼r Forex, xStocks und Krypto
- neun vollstÃƒÂ¤ndig versionierte Parameter je Produktklasse
- aktive Familienversionen steuern den Scanner tatsÃƒÂ¤chlich
- Prognosen speichern Familie, Parameterversion, Parameter- und Feature-Snapshot
- paarweiser Schattenvergleich auf denselben Beobachtungen
- veraltete Kandidaten werden als STALE blockiert
- vorhandene xStock-Parameter werden migrationssicher ÃƒÂ¼bernommen
- neue Integrations- und SicherheitsprÃƒÂ¼fungen
## 0.1.0-dev.32
- getrennte kontrollierte Parameterfamilien fÃƒÂ¼r Forex, xStocks und Krypto
- Schattenvergleich jedes Kandidaten gegen die aktive Version
- Mindeststichprobe und Mindestverbesserung als harte Freigabegates
- Wilson-Konfidenzintervall statt bloÃƒÅ¸er Trefferquote
- ausdrÃƒÂ¼ckliche Freigabe, Ablehnung und vollstÃƒÂ¤ndiger versionierter Rollback
- keine automatische Aktivierung und keine direkte KI-Aktivierung
- neuer GUI-Tab Kontrolliertes Lernen
## 0.1.0-dev.31
- sichtbare kanonische ProduktidentitÃƒÂ¤ten mit gewÃƒÂ¤hltem und alternativen AusfÃƒÂ¼hrungspaaren
- direkter EUR-/USD-Kostenvergleich, Zeitpunkt und Auswahlgrund
- Zuordnung bestehender Paper-Positionen zum kanonischen Produkt
- einheitliche Umschichtungsmatrix mit sieben einzeln persistierten Regeln
- exakter Blockierungsgrund fÃƒÂ¼r abgelehnte Entscheidungen
- neue GUI-Tabs Produkte und Regelmatrix
## 0.1.0-dev.30
- forex-v2 als strikt wirkungsloser Schattenmodus
- relative StÃƒÂ¤rke beider WÃƒÂ¤hrungen und Risiko-/Safe-Haven-Regime
- getrennte kurzfristige und mittelfristige Horizonte
- paarbezogene Nachrichtenmerkmale und versionierte Eingangssnapshots
- fehlende Zins-, Inflations-, Wachstums- und Zentralbankdaten bleiben explizit null
- Vergleich mit forex-v1 samt Abweichungsprotokoll und neuem GUI-Tab
## 0.1.0-dev.29
- read-only TradeVolume-Abruf fÃƒÂ¼r kontospezifische 30-Tage-GebÃƒÂ¼hrenstufen
- Maker und Taker je Paar mit Quelle und Zeitpunkt persistent gespeichert
- konservativer konfigurierter Fallback bei fehlender Berechtigung oder API-Fehler
- Paper-AusfÃƒÂ¼hrung und KostenschÃƒÂ¤tzung verwenden das aktive paarbezogene Taker-Profil
- neuer Ingress-Tab GebÃƒÂ¼hren; Realhandel bleibt hart deaktiviert
## 0.1.0-dev.28
- Forex-Diagnose fÃƒÂ¼r Ticker, Bid/Ask, Volumen, OHLC und konkrete FehlergrÃƒÂ¼nde
- persistenter OHLCVT-Historienspeicher mit CSV-Importbasis und abgeschlossenen Kerzen
- Walk-forward-Backtest mit Benchmarks Keine Position, Buy-and-Hold und SMA-Trend
- getrennte Ergebnisse nach Anlageklasse sowie Kosten- und Drawdown-Kennzahlen
- neue Ingress-Tabs DatenqualitÃƒÂ¤t und Backtests; Realhandel bleibt hart deaktiviert
## 0.1.0-dev.27
- v26 als alleinige Entwicklungsbasis ÃƒÂ¼bernommen und die Umsetzung konsolidiert
- kanonische Produkte ÃƒÂ¼ber Anlageklasse und Basiswert
- kostenoptimale EUR/USD-Paarwahl mit Spread, LiquiditÃƒÂ¤t, Slippage, Handels- und FX-Kosten
- vollstÃƒÂ¤ndige USD-Paper-Kostenkette mit separatem Produkspread und FX-Kosten
- Forex-Universum aus dokumentierten Currency-Paaren abgeleitet und eigenes forex-v1 beibehalten
- xStocks und traditionelle Aktien strikt getrennt; Rohmetadaten auditierbar
- Mindesthaltedauer, Cooldown, BestÃƒÂ¤tigung, Hysterese, Tageslimit und Steuersimulation
- echte UTF-8-Quelltextbereinigung und idempotente SQLite-Migration v4
## 0.1.0-dev.26
- Kanonische ProduktidentitÃƒÂ¤t und kostenbasierte EUR/USD-AusfÃƒÂ¼hrungspaarwahl
- vollstÃƒÂ¤ndige FX-Kostenkette fÃƒÂ¼r USD-Paper-Trades
- Forex-Universum repariert und deterministisches forex-v1-Profil
- xStocks und traditionelle Aktien strikt getrennt; API-Metadaten auditierbar
- Mindesthaltedauer, Cooldown, MehrfachbestÃƒÂ¤tigung und tÃƒÂ¤gliches Umschichtungslimit
- vollstÃƒÂ¤ndige UTF-8-Bereinigung

## 0.1.0-dev.25
- neuer Ingress-Tab Lernfreigaben
- neun xStock-Bewertungsparameter zentral versioniert
- begrenzte VorschlÃƒÂ¤ge aus ausgewerteten Prognosen
- Mindeststichprobe von fÃƒÂ¼nf Auswertungen
- keine automatische Aktivierung
- Ein-Klick-Freigabe aller neun Parameter als gemeinsame Version
- vollstÃƒÂ¤ndige Audit-Protokollierung

## 0.1.0-dev.24
- realen xStock-Detailscore durch korrekten Kraken-API-Vertrag repariert

## 0.1.0-dev.42 - 2026-08-28
- Nachrichtenkandidaten werden ausschlieÃƒÅ¸lich auf einem ÃƒÂ¤lteren Trainingsfenster optimiert und auf einem spÃƒÂ¤teren, disjunkten Validierungsfenster geprÃƒÂ¼ft
- Fenstergrenzen, Stichprobenzahlen, Policy und Vergleichsmetriken werden persistent gespeichert und auditiert
- Freigaben prÃƒÂ¼fen Datenfingerprint und Validierung erneut; geÃƒÂ¤nderte Stichproben blockieren fail-closed
- idempotente Schemaerweiterung und neue Regressionstests
- keine automatische Aktivierung; Realhandel bleibt hart deaktiviert

## 0.1.0-dev.42 - 2026-08-28
- Nachrichtenkandidaten erhalten drei aufeinanderfolgende Walk-forward-Validierungsfenster
- mindestens zwei Fenster mÃƒÂ¼ssen Verlustverbesserung und unverÃƒÂ¤nderte oder bessere RichtungsÃƒÂ¼bereinstimmung erfÃƒÂ¼llen
- Ergebnisse jedes Teilfensters und die StabilitÃƒÂ¤tsanforderung werden persistent gespeichert und in der GUI angezeigt
- unzureichende Historie und instabile Kandidaten werden fail-closed blockiert
- Freigabe wiederholt auch die Walk-forward-StabilitÃƒÂ¤tsgates
- Realhandel und automatische Aktivierung bleiben hart deaktiviert

## 0.1.0-dev.43
- ÃƒÅ“bersicht trennt verfÃƒÂ¼gbare REST-/Portfoliodaten vom Zustand der optionalen WebSocket-KanÃƒÂ¤le
- vorhandene Marktdaten und Portfolios werden nicht mehr pauschal als Fehler dargestellt
- Gemini ist als externer Nachrichten-AI-Anbieter konfigurierbar
- Gemini-REST-Transport unterstÃƒÂ¼tzt JSON-Ausgaben, API-Key-Header, Modell und Timeout
- AI-Verarbeitung erzwingt das konfigurierte Lauf-Limit
- Realhandel bleibt hart deaktiviert
