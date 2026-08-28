# Issues ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â append-only

## 2026-08-23 I001
Assetcodes und EUR-Bewertung noch offen.

## 2026-08-23 I002 ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â gelÃƒÆ’Ã‚Â¶st in 0.1.0-dev.2
Tabs fÃƒÆ’Ã‚Â¼hrten wegen fehlendem Ingress-PrÃƒÆ’Ã‚Â¤fix zu 404; Dashboard-Link verlieÃƒÆ’Ã…Â¸ die App. GelÃƒÆ’Ã‚Â¶st durch X-Ingress-Path-Middleware und konsequentes `url_for`.
- 2026-08-23 Direkte EUR-Bewertung deckt noch nicht jedes Asset ab; unbewertete Positionen markieren den Snapshot als INCOMPLETE.
- 2026-08-23 Assets ohne direkten EUR-Markt erhalten in dev.4 keinen Live-Stream; Cross-Rate-Bewertung folgt spaeter.
- 2026-08-23 Execution-Historie des Streams ist begrenzt; der REST-Ledger bleibt fuer vollstaendige Historie und Steuerdaten massgeblich.

## 2026-08-23 I003 ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â offen
Paper-GebÃƒÆ’Ã‚Â¼hren sind noch konfigurierbare Basispunkte und nicht die kontospezifische Kraken-GebÃƒÆ’Ã‚Â¼hrenstufe.

## 2026-08-23 I004 ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â offen
InstrumentabhÃƒÆ’Ã‚Â¤ngige MindestordergrÃƒÆ’Ã‚Â¶ÃƒÆ’Ã…Â¸e und Mindestkosten aus AssetPairs werden noch nicht im Paper-Broker validiert.

## 2026-08-23 I005 ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â gelÃƒÆ’Ã‚Â¶st in 0.1.0-dev.7
Paper-Konfiguration war in der Ingress-GUI nicht vollstÃƒÆ’Ã‚Â¤ndig sichtbar. GelÃƒÆ’Ã‚Â¶st durch eigene Konfigurationskarten im Tab Einstellungen.

## 2026-08-23 I006 ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â gelÃƒÆ’Ã‚Â¶st in 0.1.0-dev.7
Allowlist-Produkte erhielten nicht zuverlÃƒÆ’Ã‚Â¤ssig Livepreise, da primÃƒÆ’Ã‚Â¤r Echtportfolio-Symbole abonniert wurden. GelÃƒÆ’Ã‚Â¶st durch Allowlist-Abonnement plus REST-Ticker-Fallback.

## 2026-08-23 I007 ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â gelÃƒÆ’Ã‚Â¶st in 0.1.0-dev.7
Paper-Strategie lief nicht periodisch. GelÃƒÆ’Ã‚Â¶st durch konfigurierbaren Hintergrund-Scheduler.

## 2026-08-23 I008 ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â offen
Scanner und Paper-Orderentscheidung sind bewusst noch nicht gekoppelt; zunÃƒÆ’Ã‚Â¤chst ist die statistische Baseline praktisch zu validieren.


## 2026-08-25 I016 ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â gelÃƒÆ’Ã‚Â¶st in 0.1.0-dev.13
Die Nachrichtenabdeckung war zu schmal und ohne allgemeine Ereignistaxonomie. Dev.13 kombiniert globale Abdeckung mit PrimÃƒÆ’Ã‚Â¤rfeeds und speichert Themen sowie Ereignistypen.

## 2026-08-25 I017 ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â gelÃƒÆ’Ã‚Â¶st in 0.1.0-dev.13
Watchlists und Prognosen waren nicht historisch vergleichbar. Versionen, Horizonte, Ausgangspreise und spÃƒÆ’Ã‚Â¤tere Ergebnisbewertungen werden nun persistent gespeichert.


## 2026-08-25 I018 ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â gelÃƒÆ’Ã‚Â¶st in 0.1.0-dev.14
Dev.13 erweiterte `news_sources` und `news_items`, migrierte bestehende Tabellen aus dev.12 jedoch nicht. Beim Anwendungsstart trafen neue Inserts auf alte Spaltenzahlen; der Gunicorn-Worker konnte deshalb nicht booten. Dev.14 ergÃƒÆ’Ã‚Â¤nzt fehlende Spalten idempotent, verwendet explizite Spaltenlisten und bewahrt bestehende Daten.

## 2026-08-25 I019 ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â gelÃƒÆ’Ã‚Â¶st in 0.1.0-dev.15
Die breite Quelle "GDELT Global" lieferte wiederholt einen unspezifischen URL-Fehler. Sie wird deaktiviert und durch zwei kleinere GDELT-Abfragen ersetzt. Abrufe besitzen nun User-Agent, begrenzte Wiederholungen sowie nachvollziehbare HTTP- und Fehlerdiagnose.

## 2026-08-25 I020 ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â gelÃƒÆ’Ã‚Â¶st in 0.1.0-dev.16
Der ÃƒÆ’Ã‚Â¶ffentliche Stream und Vorfilter waren auf EUR-Paare beschrÃƒÆ’Ã‚Â¤nkt; dadurch fehlten USD-notierte Aktien/xStocks. Dev.16 unterstÃƒÆ’Ã‚Â¼tzt EUR- und USD-Paare, Assetklassenrouting und EUR-Umrechnung ÃƒÆ’Ã‚Â¼ber EUR/USD.

## 2026-08-25 I021 ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â gelÃƒÆ’Ã‚Â¶st in 0.1.0-dev.16
GDELT-TLS-Handshake-Timeouts erzeugten bei jedem Lauf neue Wartezeiten. Nach einem erkannten Handshake-Timeout wird die Quelle sechs Stunden auf DEGRADED/Cooldown gesetzt.

## 2026-08-25 I024 ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â gelÃƒÆ’Ã‚Â¶st in 0.1.0-dev.18
Bei ausschlieÃƒÆ’Ã…Â¸lich aktivierten Aktien/xStocks konnte ein fehlgeschlagener gemeinsamer Tickerabruf alle MÃƒÆ’Ã‚Â¤rkte als `NO_TICKER` markieren. Da nur `VALID` ausgewÃƒÆ’Ã‚Â¤hlt wurde, entstanden null Kandidaten. Dev.18 gruppiert korrekt nach Assetklasse, versucht fehlgeschlagene Batches einzeln und erhÃƒÆ’Ã‚Â¤lt gemeldete MÃƒÆ’Ã‚Â¤rkte als `PENDING_TICKER` Kandidaten.

## 2026-08-25 I025 ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â gelÃƒÆ’Ã‚Â¶st in 0.1.0-dev.20
`research_forecasts` besitzt einschlieÃƒÆ’Ã…Â¸lich `id` zwÃƒÆ’Ã‚Â¶lf Spalten. Der Snapshot-Insert verwendete jedoch eine positionsabhÃƒÆ’Ã‚Â¤ngige Werteliste mit nur elf Gesamtwerten. Dev.19 verwendet eine explizite Liste der elf befÃƒÆ’Ã‚Â¼llten Nicht-ID-Spalten und lÃƒÆ’Ã‚Â¤sst SQLite die ID erzeugen.

## 2026-08-25 I026 ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â gelÃƒÆ’Ã‚Â¶st in 0.1.0-dev.20
Mehrfach falsch dekodierte UTF-8-Texte verursachten beschÃƒÆ’Ã‚Â¤digte Umlaute. Alle Textdateien wurden als UTF-8 normalisiert; sichtbare deutsche Texte und typische Fehlerkennungen werden getestet.

## 2026-08-25 I027 ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â gelÃƒÆ’Ã‚Â¶st in 0.1.0-dev.20
Der dev.19-Vorfilter verwendete `DISTINCT` ÃƒÆ’Ã‚Â¼ber Symbol und Kategorie. HebelfÃƒÆ’Ã‚Â¤hige xStocks blieben dadurch trotz `DISTINCT` doppelt vorhanden und verletzten `(run_id,symbol)`. Dev.20 dedupliziert vor Bewertung nach Symbol, verhindert doppelte Zeilen nochmals unmittelbar in der Schleife und verwendet einen konfliktfesten Insert mit expliziten Spalten.

## 2026-08-25 I028 ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â gelÃƒÆ’Ã‚Â¶st in 0.1.0-dev.20
Der ÃƒÆ’Ã‚Â¼bergebene dev.19-Snapshot enthielt weiterhin sichtbare Mojibake-Folgen. Alle Repository-Texte wurden erneut als UTF-8 repariert und ein vollstÃƒÆ’Ã‚Â¤ndiger Test ÃƒÆ’Ã‚Â¼ber Quelltexte, Dokumentation und GUI-Texte ergÃƒÆ’Ã‚Â¤nzt.

## 2026-08-25 I029 ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â gelÃƒÆ’Ã‚Â¶st in 0.1.0-dev.24
Eine reine Quelltextkorrektur reparierte keine bereits beschÃƒÆ’Ã‚Â¤digt in SQLite gespeicherten Texte. Dev.21 fÃƒÆ’Ã‚Â¼hrt beim ersten Start eine konservative, idempotente Datenmigration aus und repariert nur Werte, deren bekannte Mojibake-Marker durch eine CP1252-zu-UTF-8-RÃƒÆ’Ã‚Â¼ckwandlung tatsÃƒÆ’Ã‚Â¤chlich abnehmen.

## 2026-08-25 I030 ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â gelÃƒÆ’Ã‚Â¶st in 0.1.0-dev.24
Der ÃƒÆ’Ã‚Â¼bergebene dev.21-Snapshot enthielt weiterhin Mojibake direkt in Quelltexten und Dokumentation. Zudem konnte die bereits gesetzte Migrationsmarke `utf8_data_migration_v1` weitere Reparaturen verhindern. Dev.22 repariert alle ausgelieferten Texte direkt, verwendet `utf8_data_migration_v2` und testet Quelltexte, Bestandsdaten sowie den Mehrfachkategorien-Vorfilter gemeinsam.

## 2026-08-25 I031 ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â gelÃƒÆ’Ã‚Â¶st in 0.1.0-dev.24
Aktien waren zwar im Universum und Vorfilter enthalten, aber der vollstÃƒÆ’Ã‚Â¤ndige Pfad Assetklasse ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬â„¢ OHLC ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬â„¢ Aktien-Score ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬â„¢ EUR-Bewertung ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬â„¢ Paper-Trade war nicht gemeinsam abgesichert. Dev.23 routet Ticker und OHLC ausdrÃƒÆ’Ã‚Â¼cklich ÃƒÆ’Ã‚Â¼ber `tokenized_asset`, nutzt ein Aktienprofil, koppelt ausschlieÃƒÆ’Ã…Â¸lich valide BUY-Ergebnisse an die Allokation und validiert `ordermin` sowie `costmin` vor einem simulierten Kauf.

## 2026-08-25 I032 ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â gelÃƒÆ’Ã‚Â¶st in 0.1.0-dev.24
Reale xStock-Scans ergaben Detailscore 0, weil Ticker und OHLC den falschen Parameter `aclass_base` statt `asset_class=tokenized_asset` sendeten. ZusÃƒÆ’Ã‚Â¤tzlich wurde OHLC primÃƒÆ’Ã‚Â¤r mit dem Anzeigesymbol statt dem Kraken-`source_key` angefragt. Dev.24 korrigiert beide API-VertrÃƒÆ’Ã‚Â¤ge und speichert konkrete Fehlertexte in den ScannergrÃƒÆ’Ã‚Â¼nden.

## 2026-08-26 I033 ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â gelÃƒÆ’Ã‚Â¶st in 0.1.0-dev.25
FÃƒÆ’Ã‚Â¼r die kontrollierte Kalibrierung fehlten eine FreigabeÃƒÆ’Ã‚Â¼bersicht, feste Parametergrenzen und eine atomare Aktivierung. Dev.25 zeigt aktuelle und vorgeschlagene Werte fÃƒÆ’Ã‚Â¼r neun xStock-Parameter, blockiert VorschlÃƒÆ’Ã‚Â¤ge bei weniger als fÃƒÆ’Ã‚Â¼nf Auswertungen und aktiviert alle Werte erst nach Benutzerfreigabe als gemeinsame Version.



## 2026-08-26 I034 - gelÃƒÆ’Ã‚Â¶st in 0.1.0-dev.29
Konfigurierbare Basispunkte bildeten die kontospezifische Kraken-GebÃƒÆ’Ã‚Â¼hrenstufe nicht ab. Dev.29 ergÃƒÆ’Ã‚Â¤nzt einen read-only TradeVolume-Abruf, persistiert Maker/Taker und verwendet bei Fehlern weiterhin den konservativen Konfigurationswert.



## 2026-08-26 I036 - gelÃƒÆ’Ã‚Â¶st in 0.1.0-dev.34
Der dev.33-Stand enthielt Testdrift, verbliebene Mojibake-Texte, fehlende KompatibilitÃƒÆ’Ã‚Â¤tsgrenzen und eine im PrÃƒÆ’Ã‚Â¼fcontainer nicht installierte Flask-Laufzeit. Dev.34 normalisiert UTF-8, stellt die AbhÃƒÆ’Ã‚Â¤ngigkeitsinstallation her, migriert alte Tests auf aktuelle VertrÃƒÆ’Ã‚Â¤ge und erreicht 103 erfolgreiche Tests.

## 2026-08-26 I037 - gelÃƒÆ’Ã‚Â¶st in 0.1.0-dev.35
Der frÃƒÆ’Ã‚Â¼here Schattenvergleich behandelte Nichtentscheidungen wie Fehler und verglich keine kostenbereinigten Renditen je Horizont. Dev.35 bewertet aktive und vorgeschlagene Parameter auf identischen Feature-Snapshots und speichert Abdeckung, Nettorendite sowie Drawdown getrennt fÃƒÆ’Ã‚Â¼r 24 und 168 Stunden.




## 2026-08-26 I038 - gelÃƒÆ’Ã‚Â¶st in 0.1.0-dev.36
Der ÃƒÆ’Ã‚Â¼bergebene dev.35-Snapshot enthielt widersprÃƒÆ’Ã‚Â¼chliche Versionsangaben und weiterhin Mojibake in Quelltexten, GUI und Dokumentation. Dev.36 zentralisiert die Laufzeitversion, synchronisiert statische Metadaten und repariert sÃƒÆ’Ã‚Â¤mtliche ausgelieferten UTF-8-Texte.

## 2026-08-26 I039 - gelÃƒÆ’Ã‚Â¶st in 0.1.0-dev.37
Dev.35 zeigte Abdeckung, Nettorendite und Drawdown nur als Information; ein Kandidat konnte trotz riskanter Horizontmetriken PENDING werden und bei der Freigabe wurden diese Werte nicht erneut geprÃƒÆ’Ã‚Â¼ft. Dev.37 macht alle Metriken zu konfigurierbaren harten Gates und wiederholt die PrÃƒÆ’Ã‚Â¼fung atomar vor jeder Aktivierung.

## 2026-08-26 I040 - gelÃƒÆ’Ã‚Â¶st in 0.1.0-dev.38
FÃƒÆ’Ã‚Â¤llige Prognosen wurden zuvor mit dem beim Auswertungslauf aktuellen Livepreis bewertet und die als Roundtrip bezeichneten Kosten trennten Einstieg und Ausstieg nicht eindeutig. Dev.38 verwendet historische Zielkerzen und persistiert eine quellenbezogene Entry-/Exit-Kostenkette.

## 2026-08-27 I041 - gelÃƒÆ’Ã‚Â¶st in 0.1.0-dev.42
Der GebÃƒÆ’Ã‚Â¼hrenabruf ÃƒÆ’Ã‚Â¼bergab interne Anzeige- und nicht unterstÃƒÆ’Ã‚Â¼tzte Produktpaare gemeinsam an TradeVolume. Ein unbekanntes Paar erzeugte EQuery:Unknown asset pair und verhinderte den gesamten Abruf. Dev.39 lÃƒÆ’Ã‚Â¶st Currency-Paare kanonisch auf, trennt nicht unterstÃƒÆ’Ã‚Â¼tzte Assetklassen und isoliert Teilfehler.
## 2026-08-27 I042 - gelÃƒÆ’Ã‚Â¶st in 0.1.0-dev.42
Der ÃƒÆ’Ã‚Â¼bergebene dev.38-Snapshot enthielt erneut Mojibake in Quelltexten, GUI und Dokumentation. Dev.39 repariert die Texte und bestÃƒÆ’Ã‚Â¤tigt die UTF-8-Gates in der vollstÃƒÆ’Ã‚Â¤ndigen Regression.


## 2026-08-28 I043 - gelÃƒÆ’Ã‚Â¶st in 0.1.0-dev.42
AI-Nachrichtenergebnisse konnten bisher gespeichert, aber nicht kontrolliert gegen die lokale Auswertung verglichen und als freigabepflichtige lokale Modellversion ÃƒÆ’Ã‚Â¼bernommen werden. Dev.40 ergÃƒÆ’Ã‚Â¤nzt den automatischen Schattenvergleich und eine manuelle atomare Freigabe.

## 2026-08-28 I044 - gelÃƒÆ’Ã‚Â¶st in 0.1.0-dev.42
Nachrichtenkandidaten wurden in dev.40 auf derselben Stichprobe optimiert und bewertet. Dev.41 trennt Training und Validierung zeitlich, persistiert die Fensterprovenienz und prÃƒÆ’Ã‚Â¼ft sie vor der manuellen Aktivierung erneut.

## 2026-08-28 I045 - gelÃƒÆ’Ã‚Â¶st in 0.1.0-dev.42
Ein einzelnes Validierungsfenster konnte zeitabschnittsspezifische Ergebnisse ÃƒÆ’Ã‚Â¼berbewerten. Dev.42 ergÃƒÆ’Ã‚Â¤nzt drei aufeinanderfolgende Walk-forward-Fenster und verlangt StabilitÃƒÆ’Ã‚Â¤t in mindestens zwei Fenstern.

## 2026-08-28 I045 - gelÃƒÆ’Ã‚Â¶st in 0.1.0-dev.43
Die ÃƒÆ’Ã…â€œbersicht zeigte WebSocket-Fehler als allgemeinen Markt- oder Kontodatenfehler, obwohl REST- beziehungsweise Portfoliodaten verfÃƒÆ’Ã‚Â¼gbar waren. Dev.43 trennt DatenverfÃƒÆ’Ã‚Â¼gbarkeit und Kanalzustand.
## 2026-08-28 I046 - gelÃƒÆ’Ã‚Â¶st in 0.1.0-dev.43
Gemini fehlte in der Add-on-Konfiguration und im Nachrichten-AI-Transport. Dev.43 ergÃƒÆ’Ã‚Â¤nzt Provider, REST-Anfrage und Antwortnormalisierung.



## 2026-08-28 I047 - gelÃƒÆ’Ã‚Â¶st in 0.1.0-dev.45
Die Lernseite zeigte nur Forex als aktuelle Version und mischte Kandidaten, Historien und Metriken aller Familien. Dev.45 zeigt alle Familienversionen und filtert die Detailbereiche konsistent.

## 2026-08-28 I048 - gelÃƒÆ’Ã‚Â¶st in 0.1.0-dev.46
Die FamilienÃƒÆ’Ã‚Â¼bersicht zeigte Versionen, aber nicht offene Freigaben oder den letzten Kandidatenstatus. AuÃƒÆ’Ã…Â¸erdem war ein unbekannter Familienparameter nicht explizit abgesichert. Dev.46 ergÃƒÆ’Ã‚Â¤nzt ÃƒÆ’Ã…â€œbersicht und Fail-closed-Auswahl.

## 2026-08-28 I049 - gelÃƒÆ’Ã‚Â¶st in 0.1.0-dev.47
Die Seite Kontrolliertes Lernen referenzierte FAMILIES ohne Import und konnte daher nicht geÃƒÆ’Ã‚Â¶ffnet werden. Dev.47 importiert die zentrale Familienquelle.

## 2026-08-28 I050 - gelÃƒÆ’Ã‚Â¶st in 0.1.0-dev.47
Nachrichten-Lernen meldete nur INSUFFICIENT_DATA ohne Datenpfad. Dev.47 zeigt Nachrichtenzahl, AI-Status, fehlende Stichprobe und bietet die AI-Auswertung als getrennte Aktion an.

## 2026-08-28 I051 - gelÃƒÆ’Ã‚Â¶st in 0.1.0-dev.51
Der Snapshot enthielt direkt gespeicherte Mojibake-Texte in Code, Tests und Dokumentation. Alle Textquellen wurden repariert und repositoryweit geprÃƒÆ’Ã‚Â¼ft.
## 2026-08-28 I052 - gelÃƒÆ’Ã‚Â¶st in 0.1.0-dev.51
Add-on-Metadaten und ein Konsistenztest verwiesen noch auf dev.42. Alle aktiven Versionsquellen sind auf dev.48 synchronisiert.
## 2026-08-28 I053 - gelÃƒÆ’Ã‚Â¶st in 0.1.0-dev.51
Der ÃƒÆ’Ã‚Â¶ffentliche WebSocket filterte USD-notierte MÃƒÆ’Ã‚Â¤rkte trotz vorhandener USD-UnterstÃƒÆ’Ã‚Â¼tzung aus. ZulÃƒÆ’Ã‚Â¤ssig sind nun EUR- und USD-Quote-WÃƒÆ’Ã‚Â¤hrungen.

## 2026-08-28 I049 - gelÃƒÆ’Ã‚Â¶st in 0.1.0-dev.51
Der Snapshot enthielt erneut sichtbare Mojibake-Texte. Dev.49 normalisiert alle ausgelieferten Texte und ergÃƒÆ’Ã‚Â¤nzt eine isolierbare Startgrenze fÃƒÆ’Ã‚Â¼r WebSockets.
## 2026-08-28 I054 - gelÃƒÆ’Ã‚Â¶st in 0.1.0-dev.51
Fehlende Steuerinfo durch auditierbaren Paper-Jahresbericht mit gleitendem Durchschnitt und CSV behoben.
## 2026-08-28 I055 - gelÃƒÂ¶st in 0.1.0-dev.51
Realhandelsbasis fehlte. Validierung und abgesicherte Live-Pipeline wurden getrennt ergÃƒÂ¤nzt.
