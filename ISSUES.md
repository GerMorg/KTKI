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


## 2026-08-25 I016 â€” gelÃ¶st in 0.1.0-dev.13
Die Nachrichtenabdeckung war zu schmal und ohne allgemeine Ereignistaxonomie. Dev.13 kombiniert globale Abdeckung mit PrimÃ¤rfeeds und speichert Themen sowie Ereignistypen.

## 2026-08-25 I017 â€” gelÃ¶st in 0.1.0-dev.13
Watchlists und Prognosen waren nicht historisch vergleichbar. Versionen, Horizonte, Ausgangspreise und spÃ¤tere Ergebnisbewertungen werden nun persistent gespeichert.


## 2026-08-25 I018 â€” gelÃ¶st in 0.1.0-dev.14
Dev.13 erweiterte `news_sources` und `news_items`, migrierte bestehende Tabellen aus dev.12 jedoch nicht. Beim Anwendungsstart trafen neue Inserts auf alte Spaltenzahlen; der Gunicorn-Worker konnte deshalb nicht booten. Dev.14 ergÃ¤nzt fehlende Spalten idempotent, verwendet explizite Spaltenlisten und bewahrt bestehende Daten.

## 2026-08-25 I019 â€” gelÃ¶st in 0.1.0-dev.15
Die breite Quelle "GDELT Global" lieferte wiederholt einen unspezifischen URL-Fehler. Sie wird deaktiviert und durch zwei kleinere GDELT-Abfragen ersetzt. Abrufe besitzen nun User-Agent, begrenzte Wiederholungen sowie nachvollziehbare HTTP- und Fehlerdiagnose.

## 2026-08-25 I020 â€” gelÃ¶st in 0.1.0-dev.16
Der Ã¶ffentliche Stream und Vorfilter waren auf EUR-Paare beschrÃ¤nkt; dadurch fehlten USD-notierte Aktien/xStocks. Dev.16 unterstÃ¼tzt EUR- und USD-Paare, Assetklassenrouting und EUR-Umrechnung Ã¼ber EUR/USD.

## 2026-08-25 I021 â€” gelÃ¶st in 0.1.0-dev.16
GDELT-TLS-Handshake-Timeouts erzeugten bei jedem Lauf neue Wartezeiten. Nach einem erkannten Handshake-Timeout wird die Quelle sechs Stunden auf DEGRADED/Cooldown gesetzt.

## 2026-08-25 I024 â€” gelÃ¶st in 0.1.0-dev.18
Bei ausschlieÃŸlich aktivierten Aktien/xStocks konnte ein fehlgeschlagener gemeinsamer Tickerabruf alle MÃ¤rkte als `NO_TICKER` markieren. Da nur `VALID` ausgewÃ¤hlt wurde, entstanden null Kandidaten. Dev.18 gruppiert korrekt nach Assetklasse, versucht fehlgeschlagene Batches einzeln und erhÃ¤lt gemeldete MÃ¤rkte als `PENDING_TICKER` Kandidaten.

## 2026-08-25 I025 â€” gelÃ¶st in 0.1.0-dev.20
`research_forecasts` besitzt einschlieÃŸlich `id` zwÃ¶lf Spalten. Der Snapshot-Insert verwendete jedoch eine positionsabhÃ¤ngige Werteliste mit nur elf Gesamtwerten. Dev.19 verwendet eine explizite Liste der elf befÃ¼llten Nicht-ID-Spalten und lÃ¤sst SQLite die ID erzeugen.

## 2026-08-25 I026 â€” gelÃ¶st in 0.1.0-dev.20
Mehrfach falsch dekodierte UTF-8-Texte verursachten beschÃ¤digte Umlaute. Alle Textdateien wurden als UTF-8 normalisiert; sichtbare deutsche Texte und typische Fehlerkennungen werden getestet.

## 2026-08-25 I027 â€” gelÃ¶st in 0.1.0-dev.20
Der dev.19-Vorfilter verwendete `DISTINCT` Ã¼ber Symbol und Kategorie. HebelfÃ¤hige xStocks blieben dadurch trotz `DISTINCT` doppelt vorhanden und verletzten `(run_id,symbol)`. Dev.20 dedupliziert vor Bewertung nach Symbol, verhindert doppelte Zeilen nochmals unmittelbar in der Schleife und verwendet einen konfliktfesten Insert mit expliziten Spalten.

## 2026-08-25 I028 â€” gelÃ¶st in 0.1.0-dev.20
Der Ã¼bergebene dev.19-Snapshot enthielt weiterhin sichtbare Mojibake-Folgen. Alle Repository-Texte wurden erneut als UTF-8 repariert und ein vollstÃ¤ndiger Test Ã¼ber Quelltexte, Dokumentation und GUI-Texte ergÃ¤nzt.

## 2026-08-25 I029 â€” gelÃ¶st in 0.1.0-dev.24
Eine reine Quelltextkorrektur reparierte keine bereits beschÃ¤digt in SQLite gespeicherten Texte. Dev.21 fÃ¼hrt beim ersten Start eine konservative, idempotente Datenmigration aus und repariert nur Werte, deren bekannte Mojibake-Marker durch eine CP1252-zu-UTF-8-RÃ¼ckwandlung tatsÃ¤chlich abnehmen.

## 2026-08-25 I030 â€” gelÃ¶st in 0.1.0-dev.24
Der Ã¼bergebene dev.21-Snapshot enthielt weiterhin Mojibake direkt in Quelltexten und Dokumentation. Zudem konnte die bereits gesetzte Migrationsmarke `utf8_data_migration_v1` weitere Reparaturen verhindern. Dev.22 repariert alle ausgelieferten Texte direkt, verwendet `utf8_data_migration_v2` und testet Quelltexte, Bestandsdaten sowie den Mehrfachkategorien-Vorfilter gemeinsam.

## 2026-08-25 I031 â€” gelÃ¶st in 0.1.0-dev.24
Aktien waren zwar im Universum und Vorfilter enthalten, aber der vollstÃ¤ndige Pfad Assetklasse â†’ OHLC â†’ Aktien-Score â†’ EUR-Bewertung â†’ Paper-Trade war nicht gemeinsam abgesichert. Dev.23 routet Ticker und OHLC ausdrÃ¼cklich Ã¼ber `tokenized_asset`, nutzt ein Aktienprofil, koppelt ausschlieÃŸlich valide BUY-Ergebnisse an die Allokation und validiert `ordermin` sowie `costmin` vor einem simulierten Kauf.

## 2026-08-25 I032 â€” gelÃ¶st in 0.1.0-dev.24
Reale xStock-Scans ergaben Detailscore 0, weil Ticker und OHLC den falschen Parameter `aclass_base` statt `asset_class=tokenized_asset` sendeten. ZusÃ¤tzlich wurde OHLC primÃ¤r mit dem Anzeigesymbol statt dem Kraken-`source_key` angefragt. Dev.24 korrigiert beide API-VertrÃ¤ge und speichert konkrete Fehlertexte in den ScannergrÃ¼nden.

## 2026-08-26 I033 â€” gelÃ¶st in 0.1.0-dev.25
FÃ¼r die kontrollierte Kalibrierung fehlten eine FreigabeÃ¼bersicht, feste Parametergrenzen und eine atomare Aktivierung. Dev.25 zeigt aktuelle und vorgeschlagene Werte fÃ¼r neun xStock-Parameter, blockiert VorschlÃ¤ge bei weniger als fÃ¼nf Auswertungen und aktiviert alle Werte erst nach Benutzerfreigabe als gemeinsame Version.



## 2026-08-26 I034 - gelÃ¶st in 0.1.0-dev.29
Konfigurierbare Basispunkte bildeten die kontospezifische Kraken-GebÃ¼hrenstufe nicht ab. Dev.29 ergÃ¤nzt einen read-only TradeVolume-Abruf, persistiert Maker/Taker und verwendet bei Fehlern weiterhin den konservativen Konfigurationswert.



## 2026-08-26 I036 - gelÃ¶st in 0.1.0-dev.34
Der dev.33-Stand enthielt Testdrift, verbliebene Mojibake-Texte, fehlende KompatibilitÃ¤tsgrenzen und eine im PrÃ¼fcontainer nicht installierte Flask-Laufzeit. Dev.34 normalisiert UTF-8, stellt die AbhÃ¤ngigkeitsinstallation her, migriert alte Tests auf aktuelle VertrÃ¤ge und erreicht 103 erfolgreiche Tests.

## 2026-08-26 I037 - gelÃ¶st in 0.1.0-dev.35
Der frÃ¼here Schattenvergleich behandelte Nichtentscheidungen wie Fehler und verglich keine kostenbereinigten Renditen je Horizont. Dev.35 bewertet aktive und vorgeschlagene Parameter auf identischen Feature-Snapshots und speichert Abdeckung, Nettorendite sowie Drawdown getrennt fÃ¼r 24 und 168 Stunden.




## 2026-08-26 I038 - gelÃ¶st in 0.1.0-dev.36
Der Ã¼bergebene dev.35-Snapshot enthielt widersprÃ¼chliche Versionsangaben und weiterhin Mojibake in Quelltexten, GUI und Dokumentation. Dev.36 zentralisiert die Laufzeitversion, synchronisiert statische Metadaten und repariert sÃ¤mtliche ausgelieferten UTF-8-Texte.

## 2026-08-26 I039 - gelÃ¶st in 0.1.0-dev.37
Dev.35 zeigte Abdeckung, Nettorendite und Drawdown nur als Information; ein Kandidat konnte trotz riskanter Horizontmetriken PENDING werden und bei der Freigabe wurden diese Werte nicht erneut geprÃ¼ft. Dev.37 macht alle Metriken zu konfigurierbaren harten Gates und wiederholt die PrÃ¼fung atomar vor jeder Aktivierung.

## 2026-08-26 I040 - gelÃ¶st in 0.1.0-dev.38
FÃ¤llige Prognosen wurden zuvor mit dem beim Auswertungslauf aktuellen Livepreis bewertet und die als Roundtrip bezeichneten Kosten trennten Einstieg und Ausstieg nicht eindeutig. Dev.38 verwendet historische Zielkerzen und persistiert eine quellenbezogene Entry-/Exit-Kostenkette.

## 2026-08-27 I041 - gelÃ¶st in 0.1.0-dev.42
Der GebÃ¼hrenabruf Ã¼bergab interne Anzeige- und nicht unterstÃ¼tzte Produktpaare gemeinsam an TradeVolume. Ein unbekanntes Paar erzeugte EQuery:Unknown asset pair und verhinderte den gesamten Abruf. Dev.39 lÃ¶st Currency-Paare kanonisch auf, trennt nicht unterstÃ¼tzte Assetklassen und isoliert Teilfehler.
## 2026-08-27 I042 - gelÃ¶st in 0.1.0-dev.42
Der Ã¼bergebene dev.38-Snapshot enthielt erneut Mojibake in Quelltexten, GUI und Dokumentation. Dev.39 repariert die Texte und bestÃ¤tigt die UTF-8-Gates in der vollstÃ¤ndigen Regression.


## 2026-08-28 I043 - gelÃ¶st in 0.1.0-dev.42
AI-Nachrichtenergebnisse konnten bisher gespeichert, aber nicht kontrolliert gegen die lokale Auswertung verglichen und als freigabepflichtige lokale Modellversion Ã¼bernommen werden. Dev.40 ergÃ¤nzt den automatischen Schattenvergleich und eine manuelle atomare Freigabe.

## 2026-08-28 I044 - gelÃ¶st in 0.1.0-dev.42
Nachrichtenkandidaten wurden in dev.40 auf derselben Stichprobe optimiert und bewertet. Dev.41 trennt Training und Validierung zeitlich, persistiert die Fensterprovenienz und prÃ¼ft sie vor der manuellen Aktivierung erneut.

## 2026-08-28 I045 - gelÃ¶st in 0.1.0-dev.42
Ein einzelnes Validierungsfenster konnte zeitabschnittsspezifische Ergebnisse Ã¼berbewerten. Dev.42 ergÃ¤nzt drei aufeinanderfolgende Walk-forward-Fenster und verlangt StabilitÃ¤t in mindestens zwei Fenstern.

## 2026-08-28 I045 - gelÃ¶st in 0.1.0-dev.43
Die Ãœbersicht zeigte WebSocket-Fehler als allgemeinen Markt- oder Kontodatenfehler, obwohl REST- beziehungsweise Portfoliodaten verfÃ¼gbar waren. Dev.43 trennt DatenverfÃ¼gbarkeit und Kanalzustand.
## 2026-08-28 I046 - gelÃ¶st in 0.1.0-dev.43
Gemini fehlte in der Add-on-Konfiguration und im Nachrichten-AI-Transport. Dev.43 ergÃ¤nzt Provider, REST-Anfrage und Antwortnormalisierung.



## 2026-08-28 I047 - gelÃ¶st in 0.1.0-dev.45
Die Lernseite zeigte nur Forex als aktuelle Version und mischte Kandidaten, Historien und Metriken aller Familien. Dev.45 zeigt alle Familienversionen und filtert die Detailbereiche konsistent.

## 2026-08-28 I048 - gelÃ¶st in 0.1.0-dev.46
Die FamilienÃ¼bersicht zeigte Versionen, aber nicht offene Freigaben oder den letzten Kandidatenstatus. AuÃŸerdem war ein unbekannter Familienparameter nicht explizit abgesichert. Dev.46 ergÃ¤nzt Ãœbersicht und Fail-closed-Auswahl.

## 2026-08-28 I049 - gelÃ¶st in 0.1.0-dev.47
Die Seite Kontrolliertes Lernen referenzierte FAMILIES ohne Import und konnte daher nicht geÃ¶ffnet werden. Dev.47 importiert die zentrale Familienquelle.

## 2026-08-28 I050 - gelÃ¶st in 0.1.0-dev.47
Nachrichten-Lernen meldete nur INSUFFICIENT_DATA ohne Datenpfad. Dev.47 zeigt Nachrichtenzahl, AI-Status, fehlende Stichprobe und bietet die AI-Auswertung als getrennte Aktion an.

## 2026-08-28 I051 - gelÃ¶st in 0.1.0-dev.51
Der Snapshot enthielt direkt gespeicherte Mojibake-Texte in Code, Tests und Dokumentation. Alle Textquellen wurden repariert und repositoryweit geprÃ¼ft.
## 2026-08-28 I052 - gelÃ¶st in 0.1.0-dev.51
Add-on-Metadaten und ein Konsistenztest verwiesen noch auf dev.42. Alle aktiven Versionsquellen sind auf dev.48 synchronisiert.
## 2026-08-28 I053 - gelÃ¶st in 0.1.0-dev.51
Der Ã¶ffentliche WebSocket filterte USD-notierte MÃ¤rkte trotz vorhandener USD-UnterstÃ¼tzung aus. ZulÃ¤ssig sind nun EUR- und USD-Quote-WÃ¤hrungen.

## 2026-08-28 I049 - gelÃ¶st in 0.1.0-dev.51
Der Snapshot enthielt erneut sichtbare Mojibake-Texte. Dev.49 normalisiert alle ausgelieferten Texte und ergÃ¤nzt eine isolierbare Startgrenze fÃ¼r WebSockets.
## 2026-08-28 I054 - gelÃ¶st in 0.1.0-dev.51
Fehlende Steuerinfo durch auditierbaren Paper-Jahresbericht mit gleitendem Durchschnitt und CSV behoben.
## 2026-08-28 I055 - gelöst in 0.1.0-dev.51
Realhandelsbasis fehlte. Validierung und abgesicherte Live-Pipeline wurden getrennt ergänzt.
