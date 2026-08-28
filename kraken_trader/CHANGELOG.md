## 0.1.0-dev.54
- GUI zentral vereinheitlicht und Zahlen kontextschonend gerundet; keine unlesbaren endlosen Nachkommastellen mehr.
- Neue Seite â€žAblauf & Systemeâ€œ erklÃ¤rt den implementierten Weg von Information, Analyse und Lernen bis zur realen Order.
- Systemmatrix trennt Kernpfad, indirekte Lernwirkung, QualitÃ¤tssicherung, Live-AusfÃ¼hrung und Begleitsysteme.
- Health-Endpunkt zeigt den tatsÃ¤chlichen Realhandelszustand statt eines festen Wertes.
- Responsive Ablaufkarten, kompaktere Detailausgaben und besser lesbare Tabellen ergÃ¤nzt.
- Regressionstests fÃ¼r Zahlenformatierung und unverÃ¤nderte JSON-Rohdaten ergÃ¤nzt.

## 0.1.0-dev.52
- Realhandel technisch aktivierbar, standardmÃ¤ÃŸig aus, mit Kill-Switch, Allowlist, Volumen- und Notional-Limits, Kraken-Validierung, Arming und Einmal-Token.
- Beide Lernloops durchsuchen Kandidaten automatisch per mehrpassiger Koordinatensuche.
- Nach jedem Research-Lauf startet die Kandidatensuche automatisch; nur die atomare Freigabe bleibt manuell.
- Forex-Trefferquote verwendet die konservative Wilson-Untergrenze auf BUY/AVOID; HOLD ist Enthaltung.
- Regressionstests fÃ¼r Lernmetrik und Realhandels-Sicherungen ergÃ¤nzt.

# Changelog
## 0.1.0-dev.51
- sichtbare UTF-8-BeschÃƒÆ’Ã‚Â¤digungen in Quelltexten, Tests und Dokumentation vollstÃƒÆ’Ã‚Â¤ndig repariert
- Monitoring als erster Flask-Blueprint modularisiert
- neues filterbares Ereignis-Dashboard fÃƒÆ’Ã‚Â¼r Fehler, Warnungen und Benutzernachrichten
- Audit-Export als redigierte JSON- oder CSV-API ergÃƒÆ’Ã‚Â¤nzt
- WebSocket-Start fÃƒÆ’Ã‚Â¼r isolierte Tests explizit deaktivierbar gemacht
- neue Sicherheits- und Regressionstests; Realhandel bleibt hart deaktiviert
## 0.1.0-dev.51
- sichtbare Mojibake-Reste in Quelltexten, Tests und Projektdokumentation vollstÃƒÆ’Ã‚Â¤ndig repariert
- Laufzeit-, Add-on- und Repository-Version zentral auf dev.48 synchronisiert
- kontrolliertes Lernen bezeichnet aktive Versionen wieder konsistent
- ÃƒÆ’Ã‚Â¶ffentlicher Markt-WebSocket akzeptiert neben EUR auch USD-notierte MÃƒÆ’Ã‚Â¤rkte
- neue dev.48-IntegritÃƒÆ’Ã‚Â¤tsregressionen; Realhandel bleibt hart deaktiviert
## 0.1.0-dev.47
- Laufzeitfehler der Seite Kontrolliertes Lernen durch fehlenden FAMILIES-Import behoben
- Nachrichten-Lernen zeigt Datenbestand, gÃƒÆ’Ã‚Â¼ltige, ungÃƒÆ’Ã‚Â¼ltige und unverarbeitete AI-Auswertungen
- Vergleich bleibt bis zur erforderlichen gÃƒÆ’Ã‚Â¼ltigen Stichprobe gesperrt und erklÃƒÆ’Ã‚Â¤rt den konkreten Grund
- separate Aktion "AI auswerten" ergÃƒÆ’Ã‚Â¤nzt; keine automatische Parameteraktivierung
- neue Regressions- und Diagnosetests; Realhandel bleibt hart deaktiviert
## 0.1.0-dev.46
- LernfamilienÃƒÆ’Ã‚Â¼bersicht zeigt aktive Version, offene Kandidaten und letzten Kandidatenstatus je Familie
- Familiennavigation bleibt direkt auswÃƒÆ’Ã‚Â¤hlbar und Detaildaten bleiben gefiltert
- unbekannte Familienparameter fallen kontrolliert auf Forex zurÃƒÆ’Ã‚Â¼ck
- vier neue Regressionstests; Realhandel bleibt hart deaktiviert
## 0.1.0-dev.45
- Aktuelle Lernversionen zeigen Forex, xStocks und Krypto Spot gleichzeitig
- Familiennamen sind direkt auswÃƒÆ’Ã‚Â¤hlbar
- Kandidaten, Versionshistorie und Horizontmetriken werden auf die gewÃƒÆ’Ã‚Â¤hlte Familie gefiltert
- Regressionstests fÃƒÆ’Ã‚Â¼r FamilienÃƒÆ’Ã‚Â¼bersicht und Filterung ergÃƒÆ’Ã‚Â¤nzt
- Realhandel bleibt hart deaktiviert
## 0.1.0-dev.40
- externe Nachrichten-AI dient als versionierte Vergleichsinstanz fÃƒÆ’Ã‚Â¼r die lokale Auswertung
- nach erfolgreichen AI-Auswertungen wird automatisch ein deduplizierter Schattenvergleich gestartet
- neun begrenzte lokale Nachrichtenparameter werden per deterministischer Koordinatensuche vorgeschlagen
- FehlermaÃƒÆ’Ã…Â¸ und RichtungsÃƒÆ’Ã‚Â¼bereinstimmung sind harte Vergleichsgates
- neue lokale Parameter werden niemals automatisch aktiviert, sondern nur nach ausdrÃƒÆ’Ã‚Â¼cklicher Freigabe
- Freigabe wiederholt den Vergleich und aktiviert alle Parameter atomar als neue Version
- aktive lokale Nachrichtenbewertung wird mit Modellversion persistent gespeichert und beeinflusst die Relevanzgewichtung
- neue Ingress-Seite "Nachrichten-Lernen" mit Kandidaten, Vergleichswerten und Versionshistorie
- Realhandel bleibt hart deaktiviert
## 0.1.0-dev.39
- Repository und sichtbare GUI-Texte vollstÃƒÆ’Ã‚Â¤ndig als echtes UTF-8 repariert
- GebÃƒÆ’Ã‚Â¼hrenabruf lÃƒÆ’Ã‚Â¶st interne Symbole vor TradeVolume gegen Kraken-QuellschlÃƒÆ’Ã‚Â¼ssel und Aliasse auf
- nicht unterstÃƒÆ’Ã‚Â¼tzte Assetklassen werden mit dokumentiertem Konfigurations-Fallback ÃƒÆ’Ã‚Â¼bersprungen
- fehlerhafte GebÃƒÆ’Ã‚Â¼hrenpaare werden isoliert; gÃƒÆ’Ã‚Â¼ltige Paare bleiben bei Teilfehlern erhalten
- neue ÃƒÆ’Ã‚Â¼bersichtliche, responsive Hauptnavigation und gefÃƒÆ’Ã‚Â¼hrte Startseite
- kontrolliertes Lernen zeigt aktive Version, Parametervergleich, Gates und Aktivierungswirkung verstÃƒÆ’Ã‚Â¤ndlich an
- 124 automatische Regressionstests erfolgreich
- Realhandel bleibt hart deaktiviert
## 0.1.0-dev.38
- fÃƒÆ’Ã‚Â¤llige Prognosen werden mit der ersten vollstÃƒÆ’Ã‚Â¤ndig abgeschlossenen historischen OHLC-Kerze am oder nach dem Zielzeitpunkt bewertet
- Livepreise werden nicht mehr als Ersatz fÃƒÆ’Ã‚Â¼r historische Zielpreise verwendet
- Zielzeit, Preisquelle, Kerzenzeit und Zeitabweichung werden persistent gespeichert
- Kosten werden getrennt als Einstieg, Ausstieg und Roundtrip gespeichert
- GebÃƒÆ’Ã‚Â¼hrenquelle, GebÃƒÆ’Ã‚Â¼hrenzeitpunkt und FX-Erfordernis werden im Feature-Snapshot nachgewiesen
- Feature-Schema auf Version 3 angehoben und Alt-Schema migrationssicher erweitert
- vollstÃƒÆ’Ã‚Â¤ndige Regression: 119 Tests erfolgreich
- Realhandel bleibt hart deaktiviert
## 0.1.0-dev.37
- robuste Freigabe-Gates je erforderlichem Prognosehorizont
- Mindeststichprobe, Mindestabdeckung und positive Nettorenditeverbesserung sind harte Gates
- absoluter maximaler Drawdown und maximale Drawdown-Verschlechterung sind harte Gates
- Gate-Policy und Einzelergebnisse werden je Kandidat unverÃƒÆ’Ã‚Â¤nderlich gespeichert und auditiert
- Freigabe prÃƒÆ’Ã‚Â¼ft alle Gates unmittelbar vor der atomaren Aktivierung erneut
- Gate-Schwellen sind ÃƒÆ’Ã‚Â¼ber Add-on-Optionen konfigurierbar und in der GUI sichtbar
- migrationssichere Erweiterung vorhandener Kandidatentabellen
- vollstÃƒÆ’Ã‚Â¤ndige Regression: 115 Tests erfolgreich
- keine automatische Aktivierung; Realhandel bleibt hart deaktiviert
## 0.1.0-dev.36
- zentrale Versionsquelle fÃƒÆ’Ã‚Â¼r Anwendung, Health-Endpunkt und HTTP-User-Agent
- alle ausgelieferten Textdateien und GUI-Texte als echtes UTF-8 normalisiert
- widersprÃƒÆ’Ã‚Â¼chlichen UTF-8-Regressionstest korrigiert
- Add-on-Metadaten, README, DOCS, VertrÃƒÆ’Ã‚Â¤ge und Projektunterlagen synchronisiert
- vollstÃƒÆ’Ã‚Â¤ndige Regression: 109 Tests erfolgreich
- keine ÃƒÆ’Ã¢â‚¬Å¾nderung der Handelsstrategie; Realhandel bleibt hart deaktiviert
## 0.1.0-dev.35
- Offline-Schattenvergleich verwendet dieselben historischen Feature-Snapshots fÃƒÆ’Ã‚Â¼r aktive und vorgeschlagene Parameter
- Lernmetriken werden getrennt fÃƒÆ’Ã‚Â¼r 24- und 168-Stunden-Horizonte gespeichert
- Nettorendite berÃƒÆ’Ã‚Â¼cksichtigt geschÃƒÆ’Ã‚Â¤tzte Roundtrip-Kosten aus Spread, HandelsgebÃƒÆ’Ã‚Â¼hr, Slippage und optionaler FX-GebÃƒÆ’Ã‚Â¼hr
- Abdeckung, Entscheidungsanzahl und maximaler Drawdown werden je Horizont ausgewiesen
- HOLD und fehlende Entscheidung werden nicht mehr pauschal als falsche Prognose gewertet
- GUI zeigt Horizontmetriken jedes Lernkandidaten
- keine automatische Parameteraktivierung; Realhandel bleibt hart deaktiviert
- vollstÃƒÆ’Ã‚Â¤ndige Regression: 105 Tests erfolgreich
## 0.1.0-dev.34
- vollstÃƒÆ’Ã‚Â¤ndige Legacy-Testsuite wiederhergestellt: 103 Tests erfolgreich
- Repository- und GUI-Texte vollstÃƒÆ’Ã‚Â¤ndig als echtes UTF-8 normalisiert
- Scanner-Lock, BUSY-Status und rotierende begrenzte Batches wiederhergestellt
- Datenbank- und Forecast-KompatibilitÃƒÆ’Ã‚Â¤t fÃƒÆ’Ã‚Â¼r ÃƒÆ’Ã‚Â¤ltere Schemas abgesichert
- External-News-AI-Vertrag und hart deaktivierte Real-Execution-Grenze wiederhergestellt
- Produktklassenprofile bleiben getrennt und steuern den Scanner weiterhin wirksam
- veraltete Tests auf aktuelle Parameter-, GebÃƒÆ’Ã‚Â¼hren- und AllokationsvertrÃƒÆ’Ã‚Â¤ge migriert
- Build-PrÃƒÆ’Ã‚Â¼fung installiert AbhÃƒÆ’Ã‚Â¤ngigkeiten reproduzierbar aus requirements.txt
## 0.1.0-dev.33
- ein einziges kontrolliertes Lernsystem fÃƒÆ’Ã‚Â¼r Forex, xStocks und Krypto
- neun vollstÃƒÆ’Ã‚Â¤ndig versionierte Parameter je Produktklasse
- aktive Familienversionen steuern den Scanner tatsÃƒÆ’Ã‚Â¤chlich
- Prognosen speichern Familie, Parameterversion, Parameter- und Feature-Snapshot
- paarweiser Schattenvergleich auf denselben Beobachtungen
- veraltete Kandidaten werden als STALE blockiert
- vorhandene xStock-Parameter werden migrationssicher ÃƒÆ’Ã‚Â¼bernommen
- neue Integrations- und SicherheitsprÃƒÆ’Ã‚Â¼fungen
## 0.1.0-dev.32
- getrennte kontrollierte Parameterfamilien fÃƒÆ’Ã‚Â¼r Forex, xStocks und Krypto
- Schattenvergleich jedes Kandidaten gegen die aktive Version
- Mindeststichprobe und Mindestverbesserung als harte Freigabegates
- Wilson-Konfidenzintervall statt bloÃƒÆ’Ã…Â¸er Trefferquote
- ausdrÃƒÆ’Ã‚Â¼ckliche Freigabe, Ablehnung und vollstÃƒÆ’Ã‚Â¤ndiger versionierter Rollback
- keine automatische Aktivierung und keine direkte KI-Aktivierung
- neuer GUI-Tab Kontrolliertes Lernen
## 0.1.0-dev.31
- sichtbare kanonische ProduktidentitÃƒÆ’Ã‚Â¤ten mit gewÃƒÆ’Ã‚Â¤hltem und alternativen AusfÃƒÆ’Ã‚Â¼hrungspaaren
- direkter EUR-/USD-Kostenvergleich, Zeitpunkt und Auswahlgrund
- Zuordnung bestehender Paper-Positionen zum kanonischen Produkt
- einheitliche Umschichtungsmatrix mit sieben einzeln persistierten Regeln
- exakter Blockierungsgrund fÃƒÆ’Ã‚Â¼r abgelehnte Entscheidungen
- neue GUI-Tabs Produkte und Regelmatrix
## 0.1.0-dev.30
- forex-v2 als strikt wirkungsloser Schattenmodus
- relative StÃƒÆ’Ã‚Â¤rke beider WÃƒÆ’Ã‚Â¤hrungen und Risiko-/Safe-Haven-Regime
- getrennte kurzfristige und mittelfristige Horizonte
- paarbezogene Nachrichtenmerkmale und versionierte Eingangssnapshots
- fehlende Zins-, Inflations-, Wachstums- und Zentralbankdaten bleiben explizit null
- Vergleich mit forex-v1 samt Abweichungsprotokoll und neuem GUI-Tab
## 0.1.0-dev.29
- read-only TradeVolume-Abruf fÃƒÆ’Ã‚Â¼r kontospezifische 30-Tage-GebÃƒÆ’Ã‚Â¼hrenstufen
- Maker und Taker je Paar mit Quelle und Zeitpunkt persistent gespeichert
- konservativer konfigurierter Fallback bei fehlender Berechtigung oder API-Fehler
- Paper-AusfÃƒÆ’Ã‚Â¼hrung und KostenschÃƒÆ’Ã‚Â¤tzung verwenden das aktive paarbezogene Taker-Profil
- neuer Ingress-Tab GebÃƒÆ’Ã‚Â¼hren; Realhandel bleibt hart deaktiviert
## 0.1.0-dev.28
- Forex-Diagnose fÃƒÆ’Ã‚Â¼r Ticker, Bid/Ask, Volumen, OHLC und konkrete FehlergrÃƒÆ’Ã‚Â¼nde
- persistenter OHLCVT-Historienspeicher mit CSV-Importbasis und abgeschlossenen Kerzen
- Walk-forward-Backtest mit Benchmarks Keine Position, Buy-and-Hold und SMA-Trend
- getrennte Ergebnisse nach Anlageklasse sowie Kosten- und Drawdown-Kennzahlen
- neue Ingress-Tabs DatenqualitÃƒÆ’Ã‚Â¤t und Backtests; Realhandel bleibt hart deaktiviert
## 0.1.0-dev.27
- v26 als alleinige Entwicklungsbasis ÃƒÆ’Ã‚Â¼bernommen und die Umsetzung konsolidiert
- kanonische Produkte ÃƒÆ’Ã‚Â¼ber Anlageklasse und Basiswert
- kostenoptimale EUR/USD-Paarwahl mit Spread, LiquiditÃƒÆ’Ã‚Â¤t, Slippage, Handels- und FX-Kosten
- vollstÃƒÆ’Ã‚Â¤ndige USD-Paper-Kostenkette mit separatem Produkspread und FX-Kosten
- Forex-Universum aus dokumentierten Currency-Paaren abgeleitet und eigenes forex-v1 beibehalten
- xStocks und traditionelle Aktien strikt getrennt; Rohmetadaten auditierbar
- Mindesthaltedauer, Cooldown, BestÃƒÆ’Ã‚Â¤tigung, Hysterese, Tageslimit und Steuersimulation
- echte UTF-8-Quelltextbereinigung und idempotente SQLite-Migration v4
## 0.1.0-dev.26
- Kanonische ProduktidentitÃƒÆ’Ã‚Â¤t und kostenbasierte EUR/USD-AusfÃƒÆ’Ã‚Â¼hrungspaarwahl
- vollstÃƒÆ’Ã‚Â¤ndige FX-Kostenkette fÃƒÆ’Ã‚Â¼r USD-Paper-Trades
- Forex-Universum repariert und deterministisches forex-v1-Profil
- xStocks und traditionelle Aktien strikt getrennt; API-Metadaten auditierbar
- Mindesthaltedauer, Cooldown, MehrfachbestÃƒÆ’Ã‚Â¤tigung und tÃƒÆ’Ã‚Â¤gliches Umschichtungslimit
- vollstÃƒÆ’Ã‚Â¤ndige UTF-8-Bereinigung

## 0.1.0-dev.25
- neuer Ingress-Tab Lernfreigaben
- neun xStock-Bewertungsparameter zentral versioniert
- begrenzte VorschlÃƒÆ’Ã‚Â¤ge aus ausgewerteten Prognosen
- Mindeststichprobe von fÃƒÆ’Ã‚Â¼nf Auswertungen
- keine automatische Aktivierung
- Ein-Klick-Freigabe aller neun Parameter als gemeinsame Version
- vollstÃƒÆ’Ã‚Â¤ndige Audit-Protokollierung

## 0.1.0-dev.24
- realen xStock-Detailscore durch korrekten Kraken-API-Vertrag repariert

## 0.1.0-dev.42 - 2026-08-28
- Nachrichtenkandidaten werden ausschlieÃƒÆ’Ã…Â¸lich auf einem ÃƒÆ’Ã‚Â¤lteren Trainingsfenster optimiert und auf einem spÃƒÆ’Ã‚Â¤teren, disjunkten Validierungsfenster geprÃƒÆ’Ã‚Â¼ft
- Fenstergrenzen, Stichprobenzahlen, Policy und Vergleichsmetriken werden persistent gespeichert und auditiert
- Freigaben prÃƒÆ’Ã‚Â¼fen Datenfingerprint und Validierung erneut; geÃƒÆ’Ã‚Â¤nderte Stichproben blockieren fail-closed
- idempotente Schemaerweiterung und neue Regressionstests
- keine automatische Aktivierung; Realhandel bleibt hart deaktiviert

## 0.1.0-dev.42 - 2026-08-28
- Nachrichtenkandidaten erhalten drei aufeinanderfolgende Walk-forward-Validierungsfenster
- mindestens zwei Fenster mÃƒÆ’Ã‚Â¼ssen Verlustverbesserung und unverÃƒÆ’Ã‚Â¤nderte oder bessere RichtungsÃƒÆ’Ã‚Â¼bereinstimmung erfÃƒÆ’Ã‚Â¼llen
- Ergebnisse jedes Teilfensters und die StabilitÃƒÆ’Ã‚Â¤tsanforderung werden persistent gespeichert und in der GUI angezeigt
- unzureichende Historie und instabile Kandidaten werden fail-closed blockiert
- Freigabe wiederholt auch die Walk-forward-StabilitÃƒÆ’Ã‚Â¤tsgates
- Realhandel und automatische Aktivierung bleiben hart deaktiviert

## 0.1.0-dev.43
- ÃƒÆ’Ã…â€œbersicht trennt verfÃƒÆ’Ã‚Â¼gbare REST-/Portfoliodaten vom Zustand der optionalen WebSocket-KanÃƒÆ’Ã‚Â¤le
- vorhandene Marktdaten und Portfolios werden nicht mehr pauschal als Fehler dargestellt
- Gemini ist als externer Nachrichten-AI-Anbieter konfigurierbar
- Gemini-REST-Transport unterstÃƒÆ’Ã‚Â¼tzt JSON-Ausgaben, API-Key-Header, Modell und Timeout
- AI-Verarbeitung erzwingt das konfigurierte Lauf-Limit
- Realhandel bleibt hart deaktiviert
## 0.1.0-dev.51
- Steuerinfo ÃƒÆ’Ã¢â‚¬â€œsterreich mit Jahresbericht, CSV, Audit und Fail-closed-PrÃƒÆ’Ã‚Â¼fhinweisen
- UTF-8- und Versionskonsistenz korrigiert; Realhandel bleibt hart deaktiviert
## 0.1.0-dev.51
- Realhandel-Grundstufe strikt getrennt vom Paper-Handel
- Kraken-Validierungsmodus, kurzzeitige manuelle Aktivierung, Auftragslimit, Idempotenz und Audit
- Live-AusfÃƒÂ¼hrung bleibt standardmÃƒÂ¤ÃƒÅ¸ig deaktiviert und fail-closed

## 0.1.0-dev.53
- Kontrolliertes Lernen trennt Parametersuche und Bewertung jetzt strikt zeitlich in Training und ungesehenes Holdout.
- Freigabe-Gates und Trefferquote werden ausschlieÃŸlich auf dem Holdout berechnet.
- MindestgrÃ¶ÃŸe des Holdouts ist konfigurierbar und blockiert zu kleine Vergleiche transparent.
- Market-Orders sind im Realhandel separat und standardmÃ¤ÃŸig gesperrt.
- ZusÃ¤tzliches tÃ¤gliches Limit fÃ¼r tatsÃ¤chlich Ã¼bermittelte RealauftrÃ¤ge.

## 0.1.0-dev.56
- Real-Balancing kann über einen eigenen Scheduler vollständig automatisch laufen.
- Vorschlagserstellung und automatische Orderausführung sind getrennt aktivierbar; Dry-Run ist standardmäßig aktiv.
- Konfigurierbar: Intervall, Positionslimit, Cashreserve, Mindest-/Maximalbetrag, No-Trade-Band, Aktionen pro Lauf/Tag, Cooldown, Mindestscore, Allowlist und Limitpreisabstand.
- Automatische Live-Ausführung benötigt zusätzlich eine getrennte Automation-Berechtigung; UI-Arming-Tokens werden nicht wiederverwendet.
- Jeder Lauf und jede Aktion wird in eigenen REAL-Tabellen sowie im REAL-Audit gespeichert.
