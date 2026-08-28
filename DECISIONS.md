# Decisions Ã¢â‚¬â€ append-only

## 2026-08-23 D001
Version 0.1 startet read-only; Realhandel ist serverseitig nicht vorhanden.

## 2026-08-23 D002
Geldwerte werden als Dezimalstrings gespeichert.

## 2026-08-23 D003
Keine externen GUI-CDNs.

## 2026-08-23 D004
Alle internen URLs werden mit Flask `url_for` erzeugt. `X-Ingress-Path` wird als WSGI `SCRIPT_NAME` gesetzt, damit Navigation und Redirects innerhalb des HA-Ingress bleiben.
- 2026-08-23 REST bleibt kanonisch fuer Snapshots und Reconciliation; WebSocket v2 wird ergaenzend eingefuehrt.
- 2026-08-23 Historische Nullpositionen werden aus Ledger-Assets materialisiert.
- 2026-08-23 Public Spot WebSocket v2 liefert Live-Ticker nur fuer aktuell gehaltene EUR-Assets; REST bleibt kanonische Reconciliation-Quelle.
- 2026-08-23 Private WebSocket-Kanaele und Ordertransport bleiben in dev.4 ausgeschlossen.
- 2026-08-23 Private WebSocket-v2-Kanaele werden ausschliesslich read-only fuer balances und executions verwendet; Ordermethoden bleiben ausgeschlossen.
- 2026-08-23 Sequenzluecken fuehren zu DEGRADED, Audit und Reconnect mit frischem Snapshot.

## 2026-08-23 D007
Der erste Paper-Broker verwendet ausschlieÃƒÅ¸lich freigegebene Produkte und Live-Marktdaten. Eine Entscheidung darf nur simuliert ausgefÃƒÂ¼hrt werden, wenn die Analyse-/Paper-Automatik aktiv ist.

## 2026-08-23 D008
GebÃƒÂ¼hren und Slippage werden getrennt berechnet, gespeichert und in der GUI gezeigt. Standardwerte sind konservative, konfigurierbare Simulationen und keine Behauptung ÃƒÂ¼ber die individuelle Kraken-GebÃƒÂ¼hrenstufe.

## 2026-08-23 D009
Die Baseline ist absichtlich deterministisch und einfach, damit jede Entscheidung reproduzierbar bleibt. Sie ist Ausgangspunkt fÃƒÂ¼r spÃƒÂ¤tere Benchmarks und kein KI-Modell.

## 2026-08-23 D010
Paper-Parameter werden zusÃƒÂ¤tzlich direkt in der Ingress-GUI verwaltet und in SQLite gespeichert. Ãƒâ€žnderungen gelten ohne App-Neustart.

## 2026-08-23 D011
Alle Paper-Allowlist-Produkte werden WebSocket-seitig beobachtet. Vor jedem Strategielauf dient der ÃƒÂ¶ffentliche REST-Ticker als zusÃƒÂ¤tzlicher Preis-Fallback.

## 2026-08-23 D012
Ein Hintergrund-Scheduler fÃƒÂ¼hrt dieselbe Paper-Pipeline wie der manuelle Knopf aus. Es wird dennoch kein Kauf erzwungen, wenn das reproduzierbare Signal die Schwelle nicht erreicht.

## 2026-08-23 D013
Der Scanner verwendet ausschlieÃƒÅ¸lich abgeschlossene OHLC-Kerzen. Die laut Kraken stets enthaltene aktuelle, noch nicht abgeschlossene Kerze wird aus der Berechnung entfernt.

## 2026-08-23 D014
Scanner-Ergebnisse werden zunÃƒÂ¤chst getrennt von der Paper-AusfÃƒÂ¼hrung gefÃƒÂ¼hrt. Eine Kopplung erfolgt erst nach praktischer PrÃƒÂ¼fung und Backtest, um keine ungeprÃƒÂ¼fte Strategie automatisch handeln zu lassen.


## 2026-08-25 D023
FÃƒÂ¼r breite allgemeine Nachrichtenerkennung wird GDELT als offener Aggregator mit geringerem Quellengewicht eingesetzt und durch EZB, Federal Reserve und Kraken als PrimÃƒÂ¤r- beziehungsweise Emittentenquellen ergÃƒÂ¤nzt. Reuters bleibt ein optionaler zukÃƒÂ¼nftiger lizenzierter Adapter.

## 2026-08-25 D024
Watchlists und Prognosen sind unverÃƒÂ¤nderlich versioniert. Auswertungen verÃƒÂ¤ndern Modellgewichte nicht automatisch; neue Gewichte benÃƒÂ¶tigen eine eigene Version und kontrollierte Freigabe.


## 2026-08-25 D025
Datenbankschema-Erweiterungen werden ab dev.14 explizit und idempotent migriert. `CREATE TABLE IF NOT EXISTS` allein gilt nicht als Migration bestehender Tabellen.

## 2026-08-25 D026
Die einzelne breite GDELT-Abfrage wird durch kleine unabhÃƒÂ¤ngige Abfragen fÃƒÂ¼r Wirtschaft und Geopolitik ersetzt. Google-News-RSS dient als ergÃƒÂ¤nzender Fallback, nicht als alleinige Quelle.

## 2026-08-25 D027
Research erhÃƒÂ¤lt einen eigenen optionalen Scheduler. Laufende AuftrÃƒÂ¤ge werden weiterhin durch den Pipeline-Lock vor ÃƒÅ“berlappung geschÃƒÂ¼tzt; Paper-Automatik und Research-Zeitplan bleiben getrennt.

## 2026-08-25 D028
Aktien/xStocks werden ÃƒÂ¼ber Krakens Assetklasse `tokenized_asset` sowie ihre tatsÃƒÂ¤chlich gemeldeten USD- oder EUR-Paare erfasst. Der ÃƒÂ¶ffentliche Stream ist nicht lÃƒÂ¤nger auf EUR-Symbole beschrÃƒÂ¤nkt.

## 2026-08-25 D029
Dynamischer Hebel wird in dev.16 ausschlieÃƒÅ¸lich simuliert. Er darf nur aus den je Markt von Kraken gemeldeten `leverage_buy`-Stufen gewÃƒÂ¤hlt werden. Eine spÃƒÂ¤tere reale AusfÃƒÂ¼hrung besitzt eine getrennte, weiterhin hart deaktivierte Adaptergrenze.

## 2026-08-25 D030
Portfolio-Umschichtungen benÃƒÂ¶tigen einen Mindest-Konfidenzvorteil, mÃƒÂ¼ssen geschÃƒÂ¤tzte Verkaufs-, Kauf-, Spread- und Slippagekosten ÃƒÂ¼bertreffen und unterliegen einem No-Trade-Mindestbetrag.

## 2026-08-25 D033
Ein vorÃƒÂ¼bergehend fehlender Ticker darf einen von Kraken gemeldeten und aktivierten Markt nicht aus der Research-Watchlist entfernen. Der Markt bleibt als `PENDING_TICKER` Kandidat; eine Paper-AusfÃƒÂ¼hrung bleibt ohne valide Detailanalyse weiterhin ausgeschlossen.

## 2026-08-25 D034
Persistente Inserts verwenden bei weiterentwickelten Tabellen immer explizite Spaltenlisten. Dadurch bleiben sie gegenÃƒÂ¼ber vorhandenen und zukÃƒÂ¼nftig ergÃƒÂ¤nzten Spalten robust.

## 2026-08-25 D035
Alle ausgelieferten Textdateien und sichtbaren GUI-Texte sind echtes UTF-8. Typische Mojibake-Marker werden durch einen automatisierten Repository-Test ausgeschlossen.

## 2026-08-25 D036
Die angehÃƒÂ¤ngte Repository-Snapshot-Version ist ab sofort immer die alleinige Entwicklungsbasis. Ein Markt darf mehreren aktivierten Gruppen angehÃƒÂ¶ren, wird in `prefilter_results` wegen des PrimÃƒÂ¤rschlÃƒÂ¼ssels `(run_id,symbol)` aber vor Bewertung kanonisch auf genau einen Datensatz reduziert.

## 2026-08-25 D037
UTF-8 wird ab dev.21 auf vier Ebenen abgesichert: UTF-8-Quelltexte, Git-/Editor-Regeln, explizite HTTP-Charsets und eine idempotente Startmigration fÃƒÂ¼r bereits beschÃƒÂ¤digte SQLite-Anzeigetexte.

## 2026-08-25 D038
Dev.22 verwendet eine neue UTF-8-Datenmigrationskennung. Eine bereits gesetzte dev.21-Markierung darf die Reparatur noch beschÃƒÂ¤digter Bestandsdaten nicht ÃƒÂ¼berspringen. Repository-Quellen und sichtbare GUI-Texte mÃƒÂ¼ssen selbst korrektes UTF-8 enthalten; Laufzeitreparatur ist nur ein Upgrade-Sicherheitsnetz.

## 2026-08-25 D039
Aktien/xStocks erhalten ab dev.23 ein eigenes deterministisches Bewertungsprofil `xstocks-v1`. Nur ein valider Detailscan mit BUY-Signal darf eine Paper-Allokation erzeugen. USD-Preise werden vor der Paper-AusfÃƒÂ¼hrung ÃƒÂ¼ber EUR/USD in EUR umgerechnet; Kraken-Mindestmenge und Mindestkosten werden fail-closed geprÃƒÂ¼ft.

## 2026-08-25 D040
Nicht-kryptografische Marktdaten verwenden bei Kraken ausschlieÃƒÅ¸lich den dokumentierten Parameter `asset_class`; `aclass_base` ist dafÃƒÂ¼r unzulÃƒÂ¤ssig. FÃƒÂ¼r xStocks wird der originale `source_key` aus AssetPairs als primÃƒÂ¤re Pair-ID fÃƒÂ¼r OHLC verwendet, mit sichtbarer Fehlerdiagnose statt eines unbegrÃƒÂ¼ndeten Scores 0.

## 2026-08-26 D041
Der Lernprozess verÃƒÂ¤ndert niemals automatisch aktive Strategieparameter. Aus ausgewerteten xStock-Prognosen darf nur ein begrenzter Vorschlag fÃƒÂ¼r exakt neun Parameter entstehen. Alle neun Werte werden gemeinsam versioniert und ausschlieÃƒÅ¸lich nach ausdrÃƒÂ¼cklicher Ein-Klick-Freigabe aktiviert.

## 2026-08-26 D042
Produkte werden nach Anlageklasse und Basiswert kanonisiert. Watchlist, Scanner und Portfolio verwenden genau ein kostenoptimal gewÃƒÂ¤hltes AusfÃƒÂ¼hrungspaar; Alternativen bleiben als Metadaten erhalten.
## 2026-08-26 D043
USD-Paper-AusfÃƒÂ¼hrungen bilden EUR-USD-Konvertierung, FX-Spread, FX-GebÃƒÂ¼hr, Produktspread und HandelsgebÃƒÂ¼hr getrennt ab.
## 2026-08-26 D044
Forex verwendet asset_class=forex und ein eigenes deterministisches forex-v1-Profil. Umschichtungen benÃƒÂ¶tigen Mindesthaltedauer, Cooldown, MehrfachbestÃƒÂ¤tigung, positive Verbesserung nach Kosten und ein Tageslimit.

## 2026-08-26 D045
AssetPairs verwendet den dokumentierten Parameter `aclass_base`. Das Forex-Universum wird reproduzierbar aus Fiat-zu-Fiat-Paaren der Currency-Antwort abgeleitet; Ticker und OHLC bleiben fÃƒÂ¼r Forex im Currency-Routing.
## 2026-08-26 D046
Die Auswahl zwischen EUR- und USD-AusfÃƒÂ¼hrungspaar erfolgt ausschlieÃƒÅ¸lich nach vollstÃƒÂ¤ndigen erwarteten AusfÃƒÂ¼hrungskosten; LiquiditÃƒÂ¤t und danach EUR dienen als Gleichstandsregeln.
## 2026-08-26 D047
Paper-Umschichtungen berÃƒÂ¼cksichtigen Produkspread, Slippage, HandelsgebÃƒÂ¼hr, FX-Spread, FX-GebÃƒÂ¼hr, realisierten Gewinn/Verlust und eine konfigurierbare Steuersimulation.



## 2026-08-26 D048
Forex-DatenqualitÃƒÂ¤t wird je Paar getrennt fÃƒÂ¼r Ticker, Bid/Ask, Volumen, OHLC und Fehlergrund persistiert. Die aktuelle, noch nicht abgeschlossene OHLC-Kerze gilt nicht als Historie.
## 2026-08-26 D049
Backtests verwenden ausschlieÃƒÅ¸lich lokal persistierte abgeschlossene OHLCVT-Daten und weisen Kostenannahmen, Anlageklasse und Benchmarks gemeinsam aus. Reale Orders bleiben ausgeschlossen.

## 2026-08-26 D050
Kontospezifische HandelsgebÃƒÂ¼hren werden ausschlieÃƒÅ¸lich read-only ÃƒÂ¼ber TradeVolume bezogen. Maker und Taker werden je Paar mit Quelle und Zeitpunkt gespeichert. Fehlen Daten oder Berechtigungen, gilt der konservative konfigurierte Taker-Wert.

## 2026-08-26 D051
forex-v2 lÃƒÂ¤uft ausschlieÃƒÅ¸lich im Schattenmodus und darf weder Scanner-Ergebnisse ÃƒÂ¼berschreiben noch Paper-Entscheidungen beeinflussen. Nicht verfÃƒÂ¼gbare Makrofaktoren werden als null und fehlend gespeichert, niemals geschÃƒÂ¤tzt.

## 2026-08-26 D052
Kanonische ProduktidentitÃƒÂ¤t, AusfÃƒÂ¼hrungspaar, Alternativen, EUR-/USD-Kosten und Positionszuordnung werden gemeinsam sichtbar gemacht.
## 2026-08-26 D053
Umschichtungen werden ÃƒÂ¼ber sieben einzeln auditierte Regeln bewertet. Die erste nicht erfÃƒÂ¼llte Regel ist der verbindliche sichtbare Blockierungsgrund.

## 2026-08-26 D054
Parameterfamilien fÃƒÂ¼r Forex, xStocks und Krypto werden getrennt versioniert. Kandidaten benÃƒÂ¶tigen Schattenvergleich, Mindeststichprobe, Mindestverbesserung und Konfidenzintervall. Aktivierung und Rollback erfolgen ausschlieÃƒÅ¸lich nach Benutzeraktion.



## 2026-08-26 D055
Ab dev.33 existiert genau ein kontrolliertes Lernsystem. Forex, xStocks und Krypto besitzen je neun getrennte Parameter. Nur die aktive, ausdrÃƒÂ¼cklich freigegebene Familienversion darf den Scanner steuern. Prognosen speichern die zugehÃƒÂ¶rige Version und den vollstÃƒÂ¤ndigen Snapshot. Kandidaten auf einer nicht mehr aktiven Basisversion werden als STALE abgewiesen.

## 2026-08-26 D056
Die vollstÃƒÂ¤ndige Regressionstestsuite ist ab dev.34 ein hartes Release-Gate. Veraltete Tests werden auf aktuelle, dokumentierte VertrÃƒÂ¤ge migriert, statt produktive Sicherheitsfunktionen fÃƒÂ¼r historische Testannahmen zurÃƒÂ¼ckzubauen.

## 2026-08-26 D057
Lernkandidaten werden ab dev.35 auf denselben historischen Feature-Snapshots wie die aktive Version bewertet. Metriken werden je Prognosehorizont getrennt und nach geschÃƒÂ¤tzten Roundtrip-Kosten ausgewiesen. Abdeckung und Drawdown sind Freigabeinformationen; eine automatische Aktivierung bleibt ausgeschlossen.




## 2026-08-26 D058
Ab dev.36 stammen Laufzeitversion und HTTP-User-Agent aus einer einzigen zentralen Versionsquelle. Statische Add-on-Metadaten und Projektunterlagen werden durch Regressionstests auf denselben Releasewert geprÃƒÂ¼ft.

## 2026-08-26 D059
Dev.36 ist ein reines Konsistenz- und Vertrauensrelease. Strategieparameter, Freigabelogik und die hart deaktivierte Real-Execution-Grenze bleiben funktional unverÃƒÂ¤ndert.

## 2026-08-26 D060
Ab dev.37 wird ein Lernkandidat nur PENDING, wenn fÃƒÂ¼r alle konfigurierten Horizonte Mindeststichprobe, Mindestabdeckung, positive Nettorenditeverbesserung, absoluter Drawdown und Drawdown-Verschlechterung sowie die bisherige Trefferquotenverbesserung erfÃƒÂ¼llt sind.

## 2026-08-26 D061
Die Gate-Policy und jedes Gate-Ergebnis werden am Kandidaten gespeichert. Eine Benutzerfreigabe wiederholt die vollstÃƒÂ¤ndige PrÃƒÂ¼fung mit der aktuellen Policy direkt vor der atomaren Aktivierung. Bei Abweichung wird REJECTED_RECHECK gesetzt und keine Parameterfamilie verÃƒÂ¤ndert.

## 2026-08-26 D062
Ab dev.38 wird eine fÃƒÂ¤llige Prognose ausschlieÃƒÅ¸lich mit der ersten vollstÃƒÂ¤ndig abgeschlossenen lokalen OHLC-Kerze am oder nach ihrem exakten Zielzeitpunkt bewertet. Fehlt eine solche Kerze, bleibt die Prognose OPEN; ein aktueller Livepreis ist kein historischer Ersatz.

## 2026-08-26 D063
Forecast-Kosten werden als getrennte Einstiegs-, Ausstiegs- und Roundtrip-Werte gespeichert. GebÃƒÂ¼hrenquelle und GÃƒÂ¼ltigkeitszeitpunkt sowie FX-Erfordernis sind Bestandteil des unverÃƒÂ¤nderlichen Feature-Snapshots.

## 2026-08-27 D064
GebÃƒÂ¼hrenpaare werden vor TradeVolume aus der kanonischen MarktidentitÃƒÂ¤t gegen Kraken-QuellschlÃƒÂ¼ssel und Aliasse aufgelÃƒÂ¶st. Ein ungÃƒÂ¼ltiges Paar darf gÃƒÂ¼ltige GebÃƒÂ¼hrenprofile nicht verwerfen; nicht unterstÃƒÂ¼tzte Assetklassen bleiben beim konservativen Konfigurationswert.
## 2026-08-27 D065
Die Ingress-GUI erhÃƒÂ¤lt eine durchgÃƒÂ¤ngige responsive Navigation, eine gefÃƒÂ¼hrte Startseite und verstÃƒÂ¤ndliche Sicherheits- und Freigabehinweise. Bestehende Funktionen bleiben erhalten.


## 2026-08-28 D064
Die externe Nachrichten-AI darf lokale Nachrichtenparameter nur als Vergleichsinstanz anregen. Automatische Vergleiche sind zulÃƒÂ¤ssig; die Aktivierung bleibt eine ausdrÃƒÂ¼ckliche Benutzeraktion mit erneuter PrÃƒÂ¼fung und atomarer Versionierung.

## 2026-08-28 D066
Nachrichtenparameter dÃƒÂ¼rfen nur auf ÃƒÂ¤lteren Beobachtungen optimiert werden. Freigabemetriken stammen ausschlieÃƒÅ¸lich aus einem spÃƒÂ¤teren, disjunkten Validierungsfenster. Jede Freigabe wiederholt Fingerprint und Gates; verÃƒÂ¤nderte Daten blockieren die Aktivierung.

## 2026-08-28 D067
Ein Nachrichtenkandidat benÃƒÂ¶tigt neben dem finalen Validierungsfenster stabile Ergebnisse ÃƒÂ¼ber mehrere chronologische Walk-forward-Teilfenster. StandardmÃƒÂ¤ÃƒÅ¸ig mÃƒÂ¼ssen mindestens zwei von drei Fenstern alle Verlust- und RichtungsÃƒÂ¼bereinstimmungs-Gates erfÃƒÂ¼llen. Unzureichende Historie blockiert fail-closed.

## 2026-08-28 D067
Dashboard-VerfÃƒÂ¼gbarkeit wird aus tatsÃƒÂ¤chlich vorhandenen Daten abgeleitet. WebSocket-ZustÃƒÂ¤nde bleiben separat sichtbar und ÃƒÂ¼berschreiben erfolgreiche REST- oder Portfolio-Daten nicht.
## 2026-08-28 D068
Gemini wird als zusÃƒÂ¤tzlicher externer Nachrichten-AI-Anbieter ÃƒÂ¼ber den offiziellen generateContent-REST-Vertrag unterstÃƒÂ¼tzt. AI-Ergebnisse bleiben Vergleichsdaten ohne automatische Handels- oder Aktivierungswirkung.



## 2026-08-28 D045 - Familienbezogene Lernansicht
Die ÃƒÅ“bersicht zeigt alle aktiven Familienversionen. Detaildaten werden ausschlieÃƒÅ¸lich fÃƒÂ¼r die ausgewÃƒÂ¤hlte Familie geladen, um Fehlinterpretationen zu vermeiden.

## 2026-08-28 D046 - Lernfamilienstatus in der ÃƒÅ“bersicht
Die FamilienÃƒÂ¼bersicht zeigt nur kompakte, abgeleitete Statuswerte. Detaildaten und Aktionen bleiben auf die bewusst ausgewÃƒÂ¤hlte gÃƒÂ¼ltige Familie beschrÃƒÂ¤nkt.

## 2026-08-28 D047 - Nachrichtenvergleich bleibt datenbasiert
Die Mindeststichprobe wird nicht abgesenkt und es werden keine synthetischen Ergebnisse erzeugt. Stattdessen zeigt die GUI die Datenbereitschaft und ermÃƒÂ¶glicht die vorgelagerte AI-Auswertung.

## 2026-08-28 D051
Dev.48 ist ein IntegritÃƒÂ¤ts- und Konsistenzrelease. Historische Funktionen bleiben erhalten; Realhandel und automatische Parameteraktivierung bleiben hart deaktiviert.

## 2026-08-28 D067
Dev.49 modularisiert Monitoring als Blueprint. Audit-Exporte werden vor Ausgabe schlÃƒÂ¼sselbasiert redigiert; Realhandel und automatische Parameteraktivierung bleiben ausgeschlossen.
## 2026-08-28 D069
Dev.50 trennt Paper-Steuerinformationen strikt von realen VorgÃƒÂ¤ngen und befÃƒÂ¼llt keine Formular-Kennzahlen automatisch.
## 2026-08-28 D070
Realhandel verwendet eigene Tabellen und niemals Paper-Konten. Live-AuftrÃ¤ge benÃ¶tigen Konfigurationsfreigabe, kurzzeitiges Token und ein positives Auftragslimit.
