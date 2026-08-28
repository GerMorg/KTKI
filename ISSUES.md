# Issues Ã¢â‚¬â€ append-only

## 2026-08-23 I001
Assetcodes und EUR-Bewertung noch offen.

## 2026-08-23 I002 Ã¢â‚¬â€ gelÃƒÂ¶st in 0.1.0-dev.2
Tabs fÃƒÂ¼hrten wegen fehlendem Ingress-PrÃƒÂ¤fix zu 404; Dashboard-Link verlieÃƒÅ¸ die App. GelÃƒÂ¶st durch X-Ingress-Path-Middleware und konsequentes `url_for`.
- 2026-08-23 Direkte EUR-Bewertung deckt noch nicht jedes Asset ab; unbewertete Positionen markieren den Snapshot als INCOMPLETE.
- 2026-08-23 Assets ohne direkten EUR-Markt erhalten in dev.4 keinen Live-Stream; Cross-Rate-Bewertung folgt spaeter.
- 2026-08-23 Execution-Historie des Streams ist begrenzt; der REST-Ledger bleibt fuer vollstaendige Historie und Steuerdaten massgeblich.

## 2026-08-23 I003 Ã¢â‚¬â€ offen
Paper-GebÃƒÂ¼hren sind noch konfigurierbare Basispunkte und nicht die kontospezifische Kraken-GebÃƒÂ¼hrenstufe.

## 2026-08-23 I004 Ã¢â‚¬â€ offen
InstrumentabhÃƒÂ¤ngige MindestordergrÃƒÂ¶ÃƒÅ¸e und Mindestkosten aus AssetPairs werden noch nicht im Paper-Broker validiert.

## 2026-08-23 I005 Ã¢â‚¬â€ gelÃƒÂ¶st in 0.1.0-dev.7
Paper-Konfiguration war in der Ingress-GUI nicht vollstÃƒÂ¤ndig sichtbar. GelÃƒÂ¶st durch eigene Konfigurationskarten im Tab Einstellungen.

## 2026-08-23 I006 Ã¢â‚¬â€ gelÃƒÂ¶st in 0.1.0-dev.7
Allowlist-Produkte erhielten nicht zuverlÃƒÂ¤ssig Livepreise, da primÃƒÂ¤r Echtportfolio-Symbole abonniert wurden. GelÃƒÂ¶st durch Allowlist-Abonnement plus REST-Ticker-Fallback.

## 2026-08-23 I007 Ã¢â‚¬â€ gelÃƒÂ¶st in 0.1.0-dev.7
Paper-Strategie lief nicht periodisch. GelÃƒÂ¶st durch konfigurierbaren Hintergrund-Scheduler.

## 2026-08-23 I008 Ã¢â‚¬â€ offen
Scanner und Paper-Orderentscheidung sind bewusst noch nicht gekoppelt; zunÃƒÂ¤chst ist die statistische Baseline praktisch zu validieren.


## 2026-08-25 I016 Ã¢â‚¬â€ gelÃƒÂ¶st in 0.1.0-dev.13
Die Nachrichtenabdeckung war zu schmal und ohne allgemeine Ereignistaxonomie. Dev.13 kombiniert globale Abdeckung mit PrimÃƒÂ¤rfeeds und speichert Themen sowie Ereignistypen.

## 2026-08-25 I017 Ã¢â‚¬â€ gelÃƒÂ¶st in 0.1.0-dev.13
Watchlists und Prognosen waren nicht historisch vergleichbar. Versionen, Horizonte, Ausgangspreise und spÃƒÂ¤tere Ergebnisbewertungen werden nun persistent gespeichert.


## 2026-08-25 I018 Ã¢â‚¬â€ gelÃƒÂ¶st in 0.1.0-dev.14
Dev.13 erweiterte `news_sources` und `news_items`, migrierte bestehende Tabellen aus dev.12 jedoch nicht. Beim Anwendungsstart trafen neue Inserts auf alte Spaltenzahlen; der Gunicorn-Worker konnte deshalb nicht booten. Dev.14 ergÃƒÂ¤nzt fehlende Spalten idempotent, verwendet explizite Spaltenlisten und bewahrt bestehende Daten.

## 2026-08-25 I019 Ã¢â‚¬â€ gelÃƒÂ¶st in 0.1.0-dev.15
Die breite Quelle "GDELT Global" lieferte wiederholt einen unspezifischen URL-Fehler. Sie wird deaktiviert und durch zwei kleinere GDELT-Abfragen ersetzt. Abrufe besitzen nun User-Agent, begrenzte Wiederholungen sowie nachvollziehbare HTTP- und Fehlerdiagnose.

## 2026-08-25 I020 Ã¢â‚¬â€ gelÃƒÂ¶st in 0.1.0-dev.16
Der ÃƒÂ¶ffentliche Stream und Vorfilter waren auf EUR-Paare beschrÃƒÂ¤nkt; dadurch fehlten USD-notierte Aktien/xStocks. Dev.16 unterstÃƒÂ¼tzt EUR- und USD-Paare, Assetklassenrouting und EUR-Umrechnung ÃƒÂ¼ber EUR/USD.

## 2026-08-25 I021 Ã¢â‚¬â€ gelÃƒÂ¶st in 0.1.0-dev.16
GDELT-TLS-Handshake-Timeouts erzeugten bei jedem Lauf neue Wartezeiten. Nach einem erkannten Handshake-Timeout wird die Quelle sechs Stunden auf DEGRADED/Cooldown gesetzt.

## 2026-08-25 I024 Ã¢â‚¬â€ gelÃƒÂ¶st in 0.1.0-dev.18
Bei ausschlieÃƒÅ¸lich aktivierten Aktien/xStocks konnte ein fehlgeschlagener gemeinsamer Tickerabruf alle MÃƒÂ¤rkte als `NO_TICKER` markieren. Da nur `VALID` ausgewÃƒÂ¤hlt wurde, entstanden null Kandidaten. Dev.18 gruppiert korrekt nach Assetklasse, versucht fehlgeschlagene Batches einzeln und erhÃƒÂ¤lt gemeldete MÃƒÂ¤rkte als `PENDING_TICKER` Kandidaten.

## 2026-08-25 I025 Ã¢â‚¬â€ gelÃƒÂ¶st in 0.1.0-dev.20
`research_forecasts` besitzt einschlieÃƒÅ¸lich `id` zwÃƒÂ¶lf Spalten. Der Snapshot-Insert verwendete jedoch eine positionsabhÃƒÂ¤ngige Werteliste mit nur elf Gesamtwerten. Dev.19 verwendet eine explizite Liste der elf befÃƒÂ¼llten Nicht-ID-Spalten und lÃƒÂ¤sst SQLite die ID erzeugen.

## 2026-08-25 I026 Ã¢â‚¬â€ gelÃƒÂ¶st in 0.1.0-dev.20
Mehrfach falsch dekodierte UTF-8-Texte verursachten beschÃƒÂ¤digte Umlaute. Alle Textdateien wurden als UTF-8 normalisiert; sichtbare deutsche Texte und typische Fehlerkennungen werden getestet.

## 2026-08-25 I027 Ã¢â‚¬â€ gelÃƒÂ¶st in 0.1.0-dev.20
Der dev.19-Vorfilter verwendete `DISTINCT` ÃƒÂ¼ber Symbol und Kategorie. HebelfÃƒÂ¤hige xStocks blieben dadurch trotz `DISTINCT` doppelt vorhanden und verletzten `(run_id,symbol)`. Dev.20 dedupliziert vor Bewertung nach Symbol, verhindert doppelte Zeilen nochmals unmittelbar in der Schleife und verwendet einen konfliktfesten Insert mit expliziten Spalten.

## 2026-08-25 I028 Ã¢â‚¬â€ gelÃƒÂ¶st in 0.1.0-dev.20
Der ÃƒÂ¼bergebene dev.19-Snapshot enthielt weiterhin sichtbare Mojibake-Folgen. Alle Repository-Texte wurden erneut als UTF-8 repariert und ein vollstÃƒÂ¤ndiger Test ÃƒÂ¼ber Quelltexte, Dokumentation und GUI-Texte ergÃƒÂ¤nzt.

## 2026-08-25 I029 Ã¢â‚¬â€ gelÃƒÂ¶st in 0.1.0-dev.24
Eine reine Quelltextkorrektur reparierte keine bereits beschÃƒÂ¤digt in SQLite gespeicherten Texte. Dev.21 fÃƒÂ¼hrt beim ersten Start eine konservative, idempotente Datenmigration aus und repariert nur Werte, deren bekannte Mojibake-Marker durch eine CP1252-zu-UTF-8-RÃƒÂ¼ckwandlung tatsÃƒÂ¤chlich abnehmen.

## 2026-08-25 I030 Ã¢â‚¬â€ gelÃƒÂ¶st in 0.1.0-dev.24
Der ÃƒÂ¼bergebene dev.21-Snapshot enthielt weiterhin Mojibake direkt in Quelltexten und Dokumentation. Zudem konnte die bereits gesetzte Migrationsmarke `utf8_data_migration_v1` weitere Reparaturen verhindern. Dev.22 repariert alle ausgelieferten Texte direkt, verwendet `utf8_data_migration_v2` und testet Quelltexte, Bestandsdaten sowie den Mehrfachkategorien-Vorfilter gemeinsam.

## 2026-08-25 I031 Ã¢â‚¬â€ gelÃƒÂ¶st in 0.1.0-dev.24
Aktien waren zwar im Universum und Vorfilter enthalten, aber der vollstÃƒÂ¤ndige Pfad Assetklasse Ã¢â€ â€™ OHLC Ã¢â€ â€™ Aktien-Score Ã¢â€ â€™ EUR-Bewertung Ã¢â€ â€™ Paper-Trade war nicht gemeinsam abgesichert. Dev.23 routet Ticker und OHLC ausdrÃƒÂ¼cklich ÃƒÂ¼ber `tokenized_asset`, nutzt ein Aktienprofil, koppelt ausschlieÃƒÅ¸lich valide BUY-Ergebnisse an die Allokation und validiert `ordermin` sowie `costmin` vor einem simulierten Kauf.

## 2026-08-25 I032 Ã¢â‚¬â€ gelÃƒÂ¶st in 0.1.0-dev.24
Reale xStock-Scans ergaben Detailscore 0, weil Ticker und OHLC den falschen Parameter `aclass_base` statt `asset_class=tokenized_asset` sendeten. ZusÃƒÂ¤tzlich wurde OHLC primÃƒÂ¤r mit dem Anzeigesymbol statt dem Kraken-`source_key` angefragt. Dev.24 korrigiert beide API-VertrÃƒÂ¤ge und speichert konkrete Fehlertexte in den ScannergrÃƒÂ¼nden.

## 2026-08-26 I033 Ã¢â‚¬â€ gelÃƒÂ¶st in 0.1.0-dev.25
FÃƒÂ¼r die kontrollierte Kalibrierung fehlten eine FreigabeÃƒÂ¼bersicht, feste Parametergrenzen und eine atomare Aktivierung. Dev.25 zeigt aktuelle und vorgeschlagene Werte fÃƒÂ¼r neun xStock-Parameter, blockiert VorschlÃƒÂ¤ge bei weniger als fÃƒÂ¼nf Auswertungen und aktiviert alle Werte erst nach Benutzerfreigabe als gemeinsame Version.



## 2026-08-26 I034 - gelÃƒÂ¶st in 0.1.0-dev.29
Konfigurierbare Basispunkte bildeten die kontospezifische Kraken-GebÃƒÂ¼hrenstufe nicht ab. Dev.29 ergÃƒÂ¤nzt einen read-only TradeVolume-Abruf, persistiert Maker/Taker und verwendet bei Fehlern weiterhin den konservativen Konfigurationswert.



## 2026-08-26 I036 - gelÃƒÂ¶st in 0.1.0-dev.34
Der dev.33-Stand enthielt Testdrift, verbliebene Mojibake-Texte, fehlende KompatibilitÃƒÂ¤tsgrenzen und eine im PrÃƒÂ¼fcontainer nicht installierte Flask-Laufzeit. Dev.34 normalisiert UTF-8, stellt die AbhÃƒÂ¤ngigkeitsinstallation her, migriert alte Tests auf aktuelle VertrÃƒÂ¤ge und erreicht 103 erfolgreiche Tests.

## 2026-08-26 I037 - gelÃƒÂ¶st in 0.1.0-dev.35
Der frÃƒÂ¼here Schattenvergleich behandelte Nichtentscheidungen wie Fehler und verglich keine kostenbereinigten Renditen je Horizont. Dev.35 bewertet aktive und vorgeschlagene Parameter auf identischen Feature-Snapshots und speichert Abdeckung, Nettorendite sowie Drawdown getrennt fÃƒÂ¼r 24 und 168 Stunden.




## 2026-08-26 I038 - gelÃƒÂ¶st in 0.1.0-dev.36
Der ÃƒÂ¼bergebene dev.35-Snapshot enthielt widersprÃƒÂ¼chliche Versionsangaben und weiterhin Mojibake in Quelltexten, GUI und Dokumentation. Dev.36 zentralisiert die Laufzeitversion, synchronisiert statische Metadaten und repariert sÃƒÂ¤mtliche ausgelieferten UTF-8-Texte.

## 2026-08-26 I039 - gelÃƒÂ¶st in 0.1.0-dev.37
Dev.35 zeigte Abdeckung, Nettorendite und Drawdown nur als Information; ein Kandidat konnte trotz riskanter Horizontmetriken PENDING werden und bei der Freigabe wurden diese Werte nicht erneut geprÃƒÂ¼ft. Dev.37 macht alle Metriken zu konfigurierbaren harten Gates und wiederholt die PrÃƒÂ¼fung atomar vor jeder Aktivierung.

## 2026-08-26 I040 - gelÃƒÂ¶st in 0.1.0-dev.38
FÃƒÂ¤llige Prognosen wurden zuvor mit dem beim Auswertungslauf aktuellen Livepreis bewertet und die als Roundtrip bezeichneten Kosten trennten Einstieg und Ausstieg nicht eindeutig. Dev.38 verwendet historische Zielkerzen und persistiert eine quellenbezogene Entry-/Exit-Kostenkette.

## 2026-08-27 I041 - gelÃƒÂ¶st in 0.1.0-dev.42
Der GebÃƒÂ¼hrenabruf ÃƒÂ¼bergab interne Anzeige- und nicht unterstÃƒÂ¼tzte Produktpaare gemeinsam an TradeVolume. Ein unbekanntes Paar erzeugte EQuery:Unknown asset pair und verhinderte den gesamten Abruf. Dev.39 lÃƒÂ¶st Currency-Paare kanonisch auf, trennt nicht unterstÃƒÂ¼tzte Assetklassen und isoliert Teilfehler.
## 2026-08-27 I042 - gelÃƒÂ¶st in 0.1.0-dev.42
Der ÃƒÂ¼bergebene dev.38-Snapshot enthielt erneut Mojibake in Quelltexten, GUI und Dokumentation. Dev.39 repariert die Texte und bestÃƒÂ¤tigt die UTF-8-Gates in der vollstÃƒÂ¤ndigen Regression.


## 2026-08-28 I043 - gelÃƒÂ¶st in 0.1.0-dev.42
AI-Nachrichtenergebnisse konnten bisher gespeichert, aber nicht kontrolliert gegen die lokale Auswertung verglichen und als freigabepflichtige lokale Modellversion ÃƒÂ¼bernommen werden. Dev.40 ergÃƒÂ¤nzt den automatischen Schattenvergleich und eine manuelle atomare Freigabe.

## 2026-08-28 I044 - gelÃƒÂ¶st in 0.1.0-dev.42
Nachrichtenkandidaten wurden in dev.40 auf derselben Stichprobe optimiert und bewertet. Dev.41 trennt Training und Validierung zeitlich, persistiert die Fensterprovenienz und prÃƒÂ¼ft sie vor der manuellen Aktivierung erneut.

## 2026-08-28 I045 - gelÃƒÂ¶st in 0.1.0-dev.42
Ein einzelnes Validierungsfenster konnte zeitabschnittsspezifische Ergebnisse ÃƒÂ¼berbewerten. Dev.42 ergÃƒÂ¤nzt drei aufeinanderfolgende Walk-forward-Fenster und verlangt StabilitÃƒÂ¤t in mindestens zwei Fenstern.

## 2026-08-28 I045 - gelÃƒÂ¶st in 0.1.0-dev.43
Die ÃƒÅ“bersicht zeigte WebSocket-Fehler als allgemeinen Markt- oder Kontodatenfehler, obwohl REST- beziehungsweise Portfoliodaten verfÃƒÂ¼gbar waren. Dev.43 trennt DatenverfÃƒÂ¼gbarkeit und Kanalzustand.
## 2026-08-28 I046 - gelÃƒÂ¶st in 0.1.0-dev.43
Gemini fehlte in der Add-on-Konfiguration und im Nachrichten-AI-Transport. Dev.43 ergÃƒÂ¤nzt Provider, REST-Anfrage und Antwortnormalisierung.



## 2026-08-28 I047 - gelÃƒÂ¶st in 0.1.0-dev.45
Die Lernseite zeigte nur Forex als aktuelle Version und mischte Kandidaten, Historien und Metriken aller Familien. Dev.45 zeigt alle Familienversionen und filtert die Detailbereiche konsistent.

## 2026-08-28 I048 - gelÃƒÂ¶st in 0.1.0-dev.46
Die FamilienÃƒÂ¼bersicht zeigte Versionen, aber nicht offene Freigaben oder den letzten Kandidatenstatus. AuÃƒÅ¸erdem war ein unbekannter Familienparameter nicht explizit abgesichert. Dev.46 ergÃƒÂ¤nzt ÃƒÅ“bersicht und Fail-closed-Auswahl.

## 2026-08-28 I049 - gelÃƒÂ¶st in 0.1.0-dev.47
Die Seite Kontrolliertes Lernen referenzierte FAMILIES ohne Import und konnte daher nicht geÃƒÂ¶ffnet werden. Dev.47 importiert die zentrale Familienquelle.

## 2026-08-28 I050 - gelÃƒÂ¶st in 0.1.0-dev.47
Nachrichten-Lernen meldete nur INSUFFICIENT_DATA ohne Datenpfad. Dev.47 zeigt Nachrichtenzahl, AI-Status, fehlende Stichprobe und bietet die AI-Auswertung als getrennte Aktion an.

## 2026-08-28 I051 - gelÃƒÂ¶st in 0.1.0-dev.51
Der Snapshot enthielt direkt gespeicherte Mojibake-Texte in Code, Tests und Dokumentation. Alle Textquellen wurden repariert und repositoryweit geprÃƒÂ¼ft.
## 2026-08-28 I052 - gelÃƒÂ¶st in 0.1.0-dev.51
Add-on-Metadaten und ein Konsistenztest verwiesen noch auf dev.42. Alle aktiven Versionsquellen sind auf dev.48 synchronisiert.
## 2026-08-28 I053 - gelÃƒÂ¶st in 0.1.0-dev.51
Der ÃƒÂ¶ffentliche WebSocket filterte USD-notierte MÃƒÂ¤rkte trotz vorhandener USD-UnterstÃƒÂ¼tzung aus. ZulÃƒÂ¤ssig sind nun EUR- und USD-Quote-WÃƒÂ¤hrungen.

## 2026-08-28 I049 - gelÃƒÂ¶st in 0.1.0-dev.51
Der Snapshot enthielt erneut sichtbare Mojibake-Texte. Dev.49 normalisiert alle ausgelieferten Texte und ergÃƒÂ¤nzt eine isolierbare Startgrenze fÃƒÂ¼r WebSockets.
## 2026-08-28 I054 - gelÃƒÂ¶st in 0.1.0-dev.51
Fehlende Steuerinfo durch auditierbaren Paper-Jahresbericht mit gleitendem Durchschnitt und CSV behoben.
## 2026-08-28 I055 - gelÃ¶st in 0.1.0-dev.51
Realhandelsbasis fehlte. Validierung und abgesicherte Live-Pipeline wurden getrennt ergÃ¤nzt.
