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


## 2026-08-25 I016 — gelöst in 0.1.0-dev.13
Die Nachrichtenabdeckung war zu schmal und ohne allgemeine Ereignistaxonomie. Dev.13 kombiniert globale Abdeckung mit Primärfeeds und speichert Themen sowie Ereignistypen.

## 2026-08-25 I017 — gelöst in 0.1.0-dev.13
Watchlists und Prognosen waren nicht historisch vergleichbar. Versionen, Horizonte, Ausgangspreise und spätere Ergebnisbewertungen werden nun persistent gespeichert.


## 2026-08-25 I018 — gelöst in 0.1.0-dev.14
Dev.13 erweiterte `news_sources` und `news_items`, migrierte bestehende Tabellen aus dev.12 jedoch nicht. Beim Anwendungsstart trafen neue Inserts auf alte Spaltenzahlen; der Gunicorn-Worker konnte deshalb nicht booten. Dev.14 ergänzt fehlende Spalten idempotent, verwendet explizite Spaltenlisten und bewahrt bestehende Daten.

## 2026-08-25 I019 — gelöst in 0.1.0-dev.15
Die breite Quelle "GDELT Global" lieferte wiederholt einen unspezifischen URL-Fehler. Sie wird deaktiviert und durch zwei kleinere GDELT-Abfragen ersetzt. Abrufe besitzen nun User-Agent, begrenzte Wiederholungen sowie nachvollziehbare HTTP- und Fehlerdiagnose.

## 2026-08-25 I020 — gelöst in 0.1.0-dev.16
Der öffentliche Stream und Vorfilter waren auf EUR-Paare beschränkt; dadurch fehlten USD-notierte Aktien/xStocks. Dev.16 unterstützt EUR- und USD-Paare, Assetklassenrouting und EUR-Umrechnung über EUR/USD.

## 2026-08-25 I021 — gelöst in 0.1.0-dev.16
GDELT-TLS-Handshake-Timeouts erzeugten bei jedem Lauf neue Wartezeiten. Nach einem erkannten Handshake-Timeout wird die Quelle sechs Stunden auf DEGRADED/Cooldown gesetzt.

## 2026-08-25 I024 — gelöst in 0.1.0-dev.18
Bei ausschließlich aktivierten Aktien/xStocks konnte ein fehlgeschlagener gemeinsamer Tickerabruf alle Märkte als `NO_TICKER` markieren. Da nur `VALID` ausgewählt wurde, entstanden null Kandidaten. Dev.18 gruppiert korrekt nach Assetklasse, versucht fehlgeschlagene Batches einzeln und erhält gemeldete Märkte als `PENDING_TICKER` Kandidaten.

## 2026-08-25 I025 — gelöst in 0.1.0-dev.20
`research_forecasts` besitzt einschließlich `id` zwölf Spalten. Der Snapshot-Insert verwendete jedoch eine positionsabhängige Werteliste mit nur elf Gesamtwerten. Dev.19 verwendet eine explizite Liste der elf befüllten Nicht-ID-Spalten und lässt SQLite die ID erzeugen.

## 2026-08-25 I026 — gelöst in 0.1.0-dev.20
Mehrfach falsch dekodierte UTF-8-Texte verursachten beschädigte Umlaute. Alle Textdateien wurden als UTF-8 normalisiert; sichtbare deutsche Texte und typische Fehlerkennungen werden getestet.

## 2026-08-25 I027 — gelöst in 0.1.0-dev.20
Der dev.19-Vorfilter verwendete `DISTINCT` über Symbol und Kategorie. Hebelfähige xStocks blieben dadurch trotz `DISTINCT` doppelt vorhanden und verletzten `(run_id,symbol)`. Dev.20 dedupliziert vor Bewertung nach Symbol, verhindert doppelte Zeilen nochmals unmittelbar in der Schleife und verwendet einen konfliktfesten Insert mit expliziten Spalten.

## 2026-08-25 I028 — gelöst in 0.1.0-dev.20
Der übergebene dev.19-Snapshot enthielt weiterhin sichtbare Mojibake-Folgen. Alle Repository-Texte wurden erneut als UTF-8 repariert und ein vollständiger Test über Quelltexte, Dokumentation und GUI-Texte ergänzt.

## 2026-08-25 I029 — gelöst in 0.1.0-dev.24
Eine reine Quelltextkorrektur reparierte keine bereits beschädigt in SQLite gespeicherten Texte. Dev.21 führt beim ersten Start eine konservative, idempotente Datenmigration aus und repariert nur Werte, deren bekannte Mojibake-Marker durch eine CP1252-zu-UTF-8-Rückwandlung tatsächlich abnehmen.

## 2026-08-25 I030 — gelöst in 0.1.0-dev.24
Der übergebene dev.21-Snapshot enthielt weiterhin Mojibake direkt in Quelltexten und Dokumentation. Zudem konnte die bereits gesetzte Migrationsmarke `utf8_data_migration_v1` weitere Reparaturen verhindern. Dev.22 repariert alle ausgelieferten Texte direkt, verwendet `utf8_data_migration_v2` und testet Quelltexte, Bestandsdaten sowie den Mehrfachkategorien-Vorfilter gemeinsam.

## 2026-08-25 I031 — gelöst in 0.1.0-dev.24
Aktien waren zwar im Universum und Vorfilter enthalten, aber der vollständige Pfad Assetklasse → OHLC → Aktien-Score → EUR-Bewertung → Paper-Trade war nicht gemeinsam abgesichert. Dev.23 routet Ticker und OHLC ausdrücklich über `tokenized_asset`, nutzt ein Aktienprofil, koppelt ausschließlich valide BUY-Ergebnisse an die Allokation und validiert `ordermin` sowie `costmin` vor einem simulierten Kauf.

## 2026-08-25 I032 — gelöst in 0.1.0-dev.24
Reale xStock-Scans ergaben Detailscore 0, weil Ticker und OHLC den falschen Parameter `aclass_base` statt `asset_class=tokenized_asset` sendeten. Zusätzlich wurde OHLC primär mit dem Anzeigesymbol statt dem Kraken-`source_key` angefragt. Dev.24 korrigiert beide API-Verträge und speichert konkrete Fehlertexte in den Scannergründen.

## 2026-08-26 I033 — gelöst in 0.1.0-dev.25
Für die kontrollierte Kalibrierung fehlten eine Freigabeübersicht, feste Parametergrenzen und eine atomare Aktivierung. Dev.25 zeigt aktuelle und vorgeschlagene Werte für neun xStock-Parameter, blockiert Vorschläge bei weniger als fünf Auswertungen und aktiviert alle Werte erst nach Benutzerfreigabe als gemeinsame Version.



## 2026-08-26 I034 - gelöst in 0.1.0-dev.29
Konfigurierbare Basispunkte bildeten die kontospezifische Kraken-Gebührenstufe nicht ab. Dev.29 ergänzt einen read-only TradeVolume-Abruf, persistiert Maker/Taker und verwendet bei Fehlern weiterhin den konservativen Konfigurationswert.



## 2026-08-26 I036 - gelöst in 0.1.0-dev.34
Der dev.33-Stand enthielt Testdrift, verbliebene Mojibake-Texte, fehlende Kompatibilitätsgrenzen und eine im Prüfcontainer nicht installierte Flask-Laufzeit. Dev.34 normalisiert UTF-8, stellt die Abhängigkeitsinstallation her, migriert alte Tests auf aktuelle Verträge und erreicht 103 erfolgreiche Tests.

## 2026-08-26 I037 - gelöst in 0.1.0-dev.35
Der frühere Schattenvergleich behandelte Nichtentscheidungen wie Fehler und verglich keine kostenbereinigten Renditen je Horizont. Dev.35 bewertet aktive und vorgeschlagene Parameter auf identischen Feature-Snapshots und speichert Abdeckung, Nettorendite sowie Drawdown getrennt für 24 und 168 Stunden.




## 2026-08-26 I038 - gelöst in 0.1.0-dev.36
Der übergebene dev.35-Snapshot enthielt widersprüchliche Versionsangaben und weiterhin Mojibake in Quelltexten, GUI und Dokumentation. Dev.36 zentralisiert die Laufzeitversion, synchronisiert statische Metadaten und repariert sämtliche ausgelieferten UTF-8-Texte.

## 2026-08-26 I039 - gelöst in 0.1.0-dev.37
Dev.35 zeigte Abdeckung, Nettorendite und Drawdown nur als Information; ein Kandidat konnte trotz riskanter Horizontmetriken PENDING werden und bei der Freigabe wurden diese Werte nicht erneut geprüft. Dev.37 macht alle Metriken zu konfigurierbaren harten Gates und wiederholt die Prüfung atomar vor jeder Aktivierung.

## 2026-08-26 I040 - gelöst in 0.1.0-dev.38
Fällige Prognosen wurden zuvor mit dem beim Auswertungslauf aktuellen Livepreis bewertet und die als Roundtrip bezeichneten Kosten trennten Einstieg und Ausstieg nicht eindeutig. Dev.38 verwendet historische Zielkerzen und persistiert eine quellenbezogene Entry-/Exit-Kostenkette.

## 2026-08-27 I041 - gelöst in 0.1.0-dev.41
Der Gebührenabruf übergab interne Anzeige- und nicht unterstützte Produktpaare gemeinsam an TradeVolume. Ein unbekanntes Paar erzeugte EQuery:Unknown asset pair und verhinderte den gesamten Abruf. Dev.39 löst Currency-Paare kanonisch auf, trennt nicht unterstützte Assetklassen und isoliert Teilfehler.
## 2026-08-27 I042 - gelöst in 0.1.0-dev.41
Der übergebene dev.38-Snapshot enthielt erneut Mojibake in Quelltexten, GUI und Dokumentation. Dev.39 repariert die Texte und bestätigt die UTF-8-Gates in der vollständigen Regression.


## 2026-08-28 I043 - gelöst in 0.1.0-dev.41
AI-Nachrichtenergebnisse konnten bisher gespeichert, aber nicht kontrolliert gegen die lokale Auswertung verglichen und als freigabepflichtige lokale Modellversion übernommen werden. Dev.40 ergänzt den automatischen Schattenvergleich und eine manuelle atomare Freigabe.

## 2026-08-28 I044 - gelöst in 0.1.0-dev.41
Nachrichtenkandidaten wurden in dev.40 auf derselben Stichprobe optimiert und bewertet. Dev.41 trennt Training und Validierung zeitlich, persistiert die Fensterprovenienz und prüft sie vor der manuellen Aktivierung erneut.
