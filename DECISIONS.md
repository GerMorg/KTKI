# Decisions ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â append-only

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
Der erste Paper-Broker verwendet ausschlieÃƒÆ’Ã…Â¸lich freigegebene Produkte und Live-Marktdaten. Eine Entscheidung darf nur simuliert ausgefÃƒÆ’Ã‚Â¼hrt werden, wenn die Analyse-/Paper-Automatik aktiv ist.

## 2026-08-23 D008
GebÃƒÆ’Ã‚Â¼hren und Slippage werden getrennt berechnet, gespeichert und in der GUI gezeigt. Standardwerte sind konservative, konfigurierbare Simulationen und keine Behauptung ÃƒÆ’Ã‚Â¼ber die individuelle Kraken-GebÃƒÆ’Ã‚Â¼hrenstufe.

## 2026-08-23 D009
Die Baseline ist absichtlich deterministisch und einfach, damit jede Entscheidung reproduzierbar bleibt. Sie ist Ausgangspunkt fÃƒÆ’Ã‚Â¼r spÃƒÆ’Ã‚Â¤tere Benchmarks und kein KI-Modell.

## 2026-08-23 D010
Paper-Parameter werden zusÃƒÆ’Ã‚Â¤tzlich direkt in der Ingress-GUI verwaltet und in SQLite gespeichert. ÃƒÆ’Ã¢â‚¬Å¾nderungen gelten ohne App-Neustart.

## 2026-08-23 D011
Alle Paper-Allowlist-Produkte werden WebSocket-seitig beobachtet. Vor jedem Strategielauf dient der ÃƒÆ’Ã‚Â¶ffentliche REST-Ticker als zusÃƒÆ’Ã‚Â¤tzlicher Preis-Fallback.

## 2026-08-23 D012
Ein Hintergrund-Scheduler fÃƒÆ’Ã‚Â¼hrt dieselbe Paper-Pipeline wie der manuelle Knopf aus. Es wird dennoch kein Kauf erzwungen, wenn das reproduzierbare Signal die Schwelle nicht erreicht.

## 2026-08-23 D013
Der Scanner verwendet ausschlieÃƒÆ’Ã…Â¸lich abgeschlossene OHLC-Kerzen. Die laut Kraken stets enthaltene aktuelle, noch nicht abgeschlossene Kerze wird aus der Berechnung entfernt.

## 2026-08-23 D014
Scanner-Ergebnisse werden zunÃƒÆ’Ã‚Â¤chst getrennt von der Paper-AusfÃƒÆ’Ã‚Â¼hrung gefÃƒÆ’Ã‚Â¼hrt. Eine Kopplung erfolgt erst nach praktischer PrÃƒÆ’Ã‚Â¼fung und Backtest, um keine ungeprÃƒÆ’Ã‚Â¼fte Strategie automatisch handeln zu lassen.


## 2026-08-25 D023
FÃƒÆ’Ã‚Â¼r breite allgemeine Nachrichtenerkennung wird GDELT als offener Aggregator mit geringerem Quellengewicht eingesetzt und durch EZB, Federal Reserve und Kraken als PrimÃƒÆ’Ã‚Â¤r- beziehungsweise Emittentenquellen ergÃƒÆ’Ã‚Â¤nzt. Reuters bleibt ein optionaler zukÃƒÆ’Ã‚Â¼nftiger lizenzierter Adapter.

## 2026-08-25 D024
Watchlists und Prognosen sind unverÃƒÆ’Ã‚Â¤nderlich versioniert. Auswertungen verÃƒÆ’Ã‚Â¤ndern Modellgewichte nicht automatisch; neue Gewichte benÃƒÆ’Ã‚Â¶tigen eine eigene Version und kontrollierte Freigabe.


## 2026-08-25 D025
Datenbankschema-Erweiterungen werden ab dev.14 explizit und idempotent migriert. `CREATE TABLE IF NOT EXISTS` allein gilt nicht als Migration bestehender Tabellen.

## 2026-08-25 D026
Die einzelne breite GDELT-Abfrage wird durch kleine unabhÃƒÆ’Ã‚Â¤ngige Abfragen fÃƒÆ’Ã‚Â¼r Wirtschaft und Geopolitik ersetzt. Google-News-RSS dient als ergÃƒÆ’Ã‚Â¤nzender Fallback, nicht als alleinige Quelle.

## 2026-08-25 D027
Research erhÃƒÆ’Ã‚Â¤lt einen eigenen optionalen Scheduler. Laufende AuftrÃƒÆ’Ã‚Â¤ge werden weiterhin durch den Pipeline-Lock vor ÃƒÆ’Ã…â€œberlappung geschÃƒÆ’Ã‚Â¼tzt; Paper-Automatik und Research-Zeitplan bleiben getrennt.

## 2026-08-25 D028
Aktien/xStocks werden ÃƒÆ’Ã‚Â¼ber Krakens Assetklasse `tokenized_asset` sowie ihre tatsÃƒÆ’Ã‚Â¤chlich gemeldeten USD- oder EUR-Paare erfasst. Der ÃƒÆ’Ã‚Â¶ffentliche Stream ist nicht lÃƒÆ’Ã‚Â¤nger auf EUR-Symbole beschrÃƒÆ’Ã‚Â¤nkt.

## 2026-08-25 D029
Dynamischer Hebel wird in dev.16 ausschlieÃƒÆ’Ã…Â¸lich simuliert. Er darf nur aus den je Markt von Kraken gemeldeten `leverage_buy`-Stufen gewÃƒÆ’Ã‚Â¤hlt werden. Eine spÃƒÆ’Ã‚Â¤tere reale AusfÃƒÆ’Ã‚Â¼hrung besitzt eine getrennte, weiterhin hart deaktivierte Adaptergrenze.

## 2026-08-25 D030
Portfolio-Umschichtungen benÃƒÆ’Ã‚Â¶tigen einen Mindest-Konfidenzvorteil, mÃƒÆ’Ã‚Â¼ssen geschÃƒÆ’Ã‚Â¤tzte Verkaufs-, Kauf-, Spread- und Slippagekosten ÃƒÆ’Ã‚Â¼bertreffen und unterliegen einem No-Trade-Mindestbetrag.

## 2026-08-25 D033
Ein vorÃƒÆ’Ã‚Â¼bergehend fehlender Ticker darf einen von Kraken gemeldeten und aktivierten Markt nicht aus der Research-Watchlist entfernen. Der Markt bleibt als `PENDING_TICKER` Kandidat; eine Paper-AusfÃƒÆ’Ã‚Â¼hrung bleibt ohne valide Detailanalyse weiterhin ausgeschlossen.

## 2026-08-25 D034
Persistente Inserts verwenden bei weiterentwickelten Tabellen immer explizite Spaltenlisten. Dadurch bleiben sie gegenÃƒÆ’Ã‚Â¼ber vorhandenen und zukÃƒÆ’Ã‚Â¼nftig ergÃƒÆ’Ã‚Â¤nzten Spalten robust.

## 2026-08-25 D035
Alle ausgelieferten Textdateien und sichtbaren GUI-Texte sind echtes UTF-8. Typische Mojibake-Marker werden durch einen automatisierten Repository-Test ausgeschlossen.

## 2026-08-25 D036
Die angehÃƒÆ’Ã‚Â¤ngte Repository-Snapshot-Version ist ab sofort immer die alleinige Entwicklungsbasis. Ein Markt darf mehreren aktivierten Gruppen angehÃƒÆ’Ã‚Â¶ren, wird in `prefilter_results` wegen des PrimÃƒÆ’Ã‚Â¤rschlÃƒÆ’Ã‚Â¼ssels `(run_id,symbol)` aber vor Bewertung kanonisch auf genau einen Datensatz reduziert.

## 2026-08-25 D037
UTF-8 wird ab dev.21 auf vier Ebenen abgesichert: UTF-8-Quelltexte, Git-/Editor-Regeln, explizite HTTP-Charsets und eine idempotente Startmigration fÃƒÆ’Ã‚Â¼r bereits beschÃƒÆ’Ã‚Â¤digte SQLite-Anzeigetexte.

## 2026-08-25 D038
Dev.22 verwendet eine neue UTF-8-Datenmigrationskennung. Eine bereits gesetzte dev.21-Markierung darf die Reparatur noch beschÃƒÆ’Ã‚Â¤digter Bestandsdaten nicht ÃƒÆ’Ã‚Â¼berspringen. Repository-Quellen und sichtbare GUI-Texte mÃƒÆ’Ã‚Â¼ssen selbst korrektes UTF-8 enthalten; Laufzeitreparatur ist nur ein Upgrade-Sicherheitsnetz.

## 2026-08-25 D039
Aktien/xStocks erhalten ab dev.23 ein eigenes deterministisches Bewertungsprofil `xstocks-v1`. Nur ein valider Detailscan mit BUY-Signal darf eine Paper-Allokation erzeugen. USD-Preise werden vor der Paper-AusfÃƒÆ’Ã‚Â¼hrung ÃƒÆ’Ã‚Â¼ber EUR/USD in EUR umgerechnet; Kraken-Mindestmenge und Mindestkosten werden fail-closed geprÃƒÆ’Ã‚Â¼ft.

## 2026-08-25 D040
Nicht-kryptografische Marktdaten verwenden bei Kraken ausschlieÃƒÆ’Ã…Â¸lich den dokumentierten Parameter `asset_class`; `aclass_base` ist dafÃƒÆ’Ã‚Â¼r unzulÃƒÆ’Ã‚Â¤ssig. FÃƒÆ’Ã‚Â¼r xStocks wird der originale `source_key` aus AssetPairs als primÃƒÆ’Ã‚Â¤re Pair-ID fÃƒÆ’Ã‚Â¼r OHLC verwendet, mit sichtbarer Fehlerdiagnose statt eines unbegrÃƒÆ’Ã‚Â¼ndeten Scores 0.

## 2026-08-26 D041
Der Lernprozess verÃƒÆ’Ã‚Â¤ndert niemals automatisch aktive Strategieparameter. Aus ausgewerteten xStock-Prognosen darf nur ein begrenzter Vorschlag fÃƒÆ’Ã‚Â¼r exakt neun Parameter entstehen. Alle neun Werte werden gemeinsam versioniert und ausschlieÃƒÆ’Ã…Â¸lich nach ausdrÃƒÆ’Ã‚Â¼cklicher Ein-Klick-Freigabe aktiviert.

## 2026-08-26 D042
Produkte werden nach Anlageklasse und Basiswert kanonisiert. Watchlist, Scanner und Portfolio verwenden genau ein kostenoptimal gewÃƒÆ’Ã‚Â¤hltes AusfÃƒÆ’Ã‚Â¼hrungspaar; Alternativen bleiben als Metadaten erhalten.
## 2026-08-26 D043
USD-Paper-AusfÃƒÆ’Ã‚Â¼hrungen bilden EUR-USD-Konvertierung, FX-Spread, FX-GebÃƒÆ’Ã‚Â¼hr, Produktspread und HandelsgebÃƒÆ’Ã‚Â¼hr getrennt ab.
## 2026-08-26 D044
Forex verwendet asset_class=forex und ein eigenes deterministisches forex-v1-Profil. Umschichtungen benÃƒÆ’Ã‚Â¶tigen Mindesthaltedauer, Cooldown, MehrfachbestÃƒÆ’Ã‚Â¤tigung, positive Verbesserung nach Kosten und ein Tageslimit.

## 2026-08-26 D045
AssetPairs verwendet den dokumentierten Parameter `aclass_base`. Das Forex-Universum wird reproduzierbar aus Fiat-zu-Fiat-Paaren der Currency-Antwort abgeleitet; Ticker und OHLC bleiben fÃƒÆ’Ã‚Â¼r Forex im Currency-Routing.
## 2026-08-26 D046
Die Auswahl zwischen EUR- und USD-AusfÃƒÆ’Ã‚Â¼hrungspaar erfolgt ausschlieÃƒÆ’Ã…Â¸lich nach vollstÃƒÆ’Ã‚Â¤ndigen erwarteten AusfÃƒÆ’Ã‚Â¼hrungskosten; LiquiditÃƒÆ’Ã‚Â¤t und danach EUR dienen als Gleichstandsregeln.
## 2026-08-26 D047
Paper-Umschichtungen berÃƒÆ’Ã‚Â¼cksichtigen Produkspread, Slippage, HandelsgebÃƒÆ’Ã‚Â¼hr, FX-Spread, FX-GebÃƒÆ’Ã‚Â¼hr, realisierten Gewinn/Verlust und eine konfigurierbare Steuersimulation.



## 2026-08-26 D048
Forex-DatenqualitÃƒÆ’Ã‚Â¤t wird je Paar getrennt fÃƒÆ’Ã‚Â¼r Ticker, Bid/Ask, Volumen, OHLC und Fehlergrund persistiert. Die aktuelle, noch nicht abgeschlossene OHLC-Kerze gilt nicht als Historie.
## 2026-08-26 D049
Backtests verwenden ausschlieÃƒÆ’Ã…Â¸lich lokal persistierte abgeschlossene OHLCVT-Daten und weisen Kostenannahmen, Anlageklasse und Benchmarks gemeinsam aus. Reale Orders bleiben ausgeschlossen.

## 2026-08-26 D050
Kontospezifische HandelsgebÃƒÆ’Ã‚Â¼hren werden ausschlieÃƒÆ’Ã…Â¸lich read-only ÃƒÆ’Ã‚Â¼ber TradeVolume bezogen. Maker und Taker werden je Paar mit Quelle und Zeitpunkt gespeichert. Fehlen Daten oder Berechtigungen, gilt der konservative konfigurierte Taker-Wert.

## 2026-08-26 D051
forex-v2 lÃƒÆ’Ã‚Â¤uft ausschlieÃƒÆ’Ã…Â¸lich im Schattenmodus und darf weder Scanner-Ergebnisse ÃƒÆ’Ã‚Â¼berschreiben noch Paper-Entscheidungen beeinflussen. Nicht verfÃƒÆ’Ã‚Â¼gbare Makrofaktoren werden als null und fehlend gespeichert, niemals geschÃƒÆ’Ã‚Â¤tzt.

## 2026-08-26 D052
Kanonische ProduktidentitÃƒÆ’Ã‚Â¤t, AusfÃƒÆ’Ã‚Â¼hrungspaar, Alternativen, EUR-/USD-Kosten und Positionszuordnung werden gemeinsam sichtbar gemacht.
## 2026-08-26 D053
Umschichtungen werden ÃƒÆ’Ã‚Â¼ber sieben einzeln auditierte Regeln bewertet. Die erste nicht erfÃƒÆ’Ã‚Â¼llte Regel ist der verbindliche sichtbare Blockierungsgrund.

## 2026-08-26 D054
Parameterfamilien fÃƒÆ’Ã‚Â¼r Forex, xStocks und Krypto werden getrennt versioniert. Kandidaten benÃƒÆ’Ã‚Â¶tigen Schattenvergleich, Mindeststichprobe, Mindestverbesserung und Konfidenzintervall. Aktivierung und Rollback erfolgen ausschlieÃƒÆ’Ã…Â¸lich nach Benutzeraktion.



## 2026-08-26 D055
Ab dev.33 existiert genau ein kontrolliertes Lernsystem. Forex, xStocks und Krypto besitzen je neun getrennte Parameter. Nur die aktive, ausdrÃƒÆ’Ã‚Â¼cklich freigegebene Familienversion darf den Scanner steuern. Prognosen speichern die zugehÃƒÆ’Ã‚Â¶rige Version und den vollstÃƒÆ’Ã‚Â¤ndigen Snapshot. Kandidaten auf einer nicht mehr aktiven Basisversion werden als STALE abgewiesen.

## 2026-08-26 D056
Die vollstÃƒÆ’Ã‚Â¤ndige Regressionstestsuite ist ab dev.34 ein hartes Release-Gate. Veraltete Tests werden auf aktuelle, dokumentierte VertrÃƒÆ’Ã‚Â¤ge migriert, statt produktive Sicherheitsfunktionen fÃƒÆ’Ã‚Â¼r historische Testannahmen zurÃƒÆ’Ã‚Â¼ckzubauen.

## 2026-08-26 D057
Lernkandidaten werden ab dev.35 auf denselben historischen Feature-Snapshots wie die aktive Version bewertet. Metriken werden je Prognosehorizont getrennt und nach geschÃƒÆ’Ã‚Â¤tzten Roundtrip-Kosten ausgewiesen. Abdeckung und Drawdown sind Freigabeinformationen; eine automatische Aktivierung bleibt ausgeschlossen.




## 2026-08-26 D058
Ab dev.36 stammen Laufzeitversion und HTTP-User-Agent aus einer einzigen zentralen Versionsquelle. Statische Add-on-Metadaten und Projektunterlagen werden durch Regressionstests auf denselben Releasewert geprÃƒÆ’Ã‚Â¼ft.

## 2026-08-26 D059
Dev.36 ist ein reines Konsistenz- und Vertrauensrelease. Strategieparameter, Freigabelogik und die hart deaktivierte Real-Execution-Grenze bleiben funktional unverÃƒÆ’Ã‚Â¤ndert.

## 2026-08-26 D060
Ab dev.37 wird ein Lernkandidat nur PENDING, wenn fÃƒÆ’Ã‚Â¼r alle konfigurierten Horizonte Mindeststichprobe, Mindestabdeckung, positive Nettorenditeverbesserung, absoluter Drawdown und Drawdown-Verschlechterung sowie die bisherige Trefferquotenverbesserung erfÃƒÆ’Ã‚Â¼llt sind.

## 2026-08-26 D061
Die Gate-Policy und jedes Gate-Ergebnis werden am Kandidaten gespeichert. Eine Benutzerfreigabe wiederholt die vollstÃƒÆ’Ã‚Â¤ndige PrÃƒÆ’Ã‚Â¼fung mit der aktuellen Policy direkt vor der atomaren Aktivierung. Bei Abweichung wird REJECTED_RECHECK gesetzt und keine Parameterfamilie verÃƒÆ’Ã‚Â¤ndert.

## 2026-08-26 D062
Ab dev.38 wird eine fÃƒÆ’Ã‚Â¤llige Prognose ausschlieÃƒÆ’Ã…Â¸lich mit der ersten vollstÃƒÆ’Ã‚Â¤ndig abgeschlossenen lokalen OHLC-Kerze am oder nach ihrem exakten Zielzeitpunkt bewertet. Fehlt eine solche Kerze, bleibt die Prognose OPEN; ein aktueller Livepreis ist kein historischer Ersatz.

## 2026-08-26 D063
Forecast-Kosten werden als getrennte Einstiegs-, Ausstiegs- und Roundtrip-Werte gespeichert. GebÃƒÆ’Ã‚Â¼hrenquelle und GÃƒÆ’Ã‚Â¼ltigkeitszeitpunkt sowie FX-Erfordernis sind Bestandteil des unverÃƒÆ’Ã‚Â¤nderlichen Feature-Snapshots.

## 2026-08-27 D064
GebÃƒÆ’Ã‚Â¼hrenpaare werden vor TradeVolume aus der kanonischen MarktidentitÃƒÆ’Ã‚Â¤t gegen Kraken-QuellschlÃƒÆ’Ã‚Â¼ssel und Aliasse aufgelÃƒÆ’Ã‚Â¶st. Ein ungÃƒÆ’Ã‚Â¼ltiges Paar darf gÃƒÆ’Ã‚Â¼ltige GebÃƒÆ’Ã‚Â¼hrenprofile nicht verwerfen; nicht unterstÃƒÆ’Ã‚Â¼tzte Assetklassen bleiben beim konservativen Konfigurationswert.
## 2026-08-27 D065
Die Ingress-GUI erhÃƒÆ’Ã‚Â¤lt eine durchgÃƒÆ’Ã‚Â¤ngige responsive Navigation, eine gefÃƒÆ’Ã‚Â¼hrte Startseite und verstÃƒÆ’Ã‚Â¤ndliche Sicherheits- und Freigabehinweise. Bestehende Funktionen bleiben erhalten.


## 2026-08-28 D064
Die externe Nachrichten-AI darf lokale Nachrichtenparameter nur als Vergleichsinstanz anregen. Automatische Vergleiche sind zulÃƒÆ’Ã‚Â¤ssig; die Aktivierung bleibt eine ausdrÃƒÆ’Ã‚Â¼ckliche Benutzeraktion mit erneuter PrÃƒÆ’Ã‚Â¼fung und atomarer Versionierung.

## 2026-08-28 D066
Nachrichtenparameter dÃƒÆ’Ã‚Â¼rfen nur auf ÃƒÆ’Ã‚Â¤lteren Beobachtungen optimiert werden. Freigabemetriken stammen ausschlieÃƒÆ’Ã…Â¸lich aus einem spÃƒÆ’Ã‚Â¤teren, disjunkten Validierungsfenster. Jede Freigabe wiederholt Fingerprint und Gates; verÃƒÆ’Ã‚Â¤nderte Daten blockieren die Aktivierung.

## 2026-08-28 D067
Ein Nachrichtenkandidat benÃƒÆ’Ã‚Â¶tigt neben dem finalen Validierungsfenster stabile Ergebnisse ÃƒÆ’Ã‚Â¼ber mehrere chronologische Walk-forward-Teilfenster. StandardmÃƒÆ’Ã‚Â¤ÃƒÆ’Ã…Â¸ig mÃƒÆ’Ã‚Â¼ssen mindestens zwei von drei Fenstern alle Verlust- und RichtungsÃƒÆ’Ã‚Â¼bereinstimmungs-Gates erfÃƒÆ’Ã‚Â¼llen. Unzureichende Historie blockiert fail-closed.

## 2026-08-28 D067
Dashboard-VerfÃƒÆ’Ã‚Â¼gbarkeit wird aus tatsÃƒÆ’Ã‚Â¤chlich vorhandenen Daten abgeleitet. WebSocket-ZustÃƒÆ’Ã‚Â¤nde bleiben separat sichtbar und ÃƒÆ’Ã‚Â¼berschreiben erfolgreiche REST- oder Portfolio-Daten nicht.
## 2026-08-28 D068
Gemini wird als zusÃƒÆ’Ã‚Â¤tzlicher externer Nachrichten-AI-Anbieter ÃƒÆ’Ã‚Â¼ber den offiziellen generateContent-REST-Vertrag unterstÃƒÆ’Ã‚Â¼tzt. AI-Ergebnisse bleiben Vergleichsdaten ohne automatische Handels- oder Aktivierungswirkung.



## 2026-08-28 D045 - Familienbezogene Lernansicht
Die ÃƒÆ’Ã…â€œbersicht zeigt alle aktiven Familienversionen. Detaildaten werden ausschlieÃƒÆ’Ã…Â¸lich fÃƒÆ’Ã‚Â¼r die ausgewÃƒÆ’Ã‚Â¤hlte Familie geladen, um Fehlinterpretationen zu vermeiden.

## 2026-08-28 D046 - Lernfamilienstatus in der ÃƒÆ’Ã…â€œbersicht
Die FamilienÃƒÆ’Ã‚Â¼bersicht zeigt nur kompakte, abgeleitete Statuswerte. Detaildaten und Aktionen bleiben auf die bewusst ausgewÃƒÆ’Ã‚Â¤hlte gÃƒÆ’Ã‚Â¼ltige Familie beschrÃƒÆ’Ã‚Â¤nkt.

## 2026-08-28 D047 - Nachrichtenvergleich bleibt datenbasiert
Die Mindeststichprobe wird nicht abgesenkt und es werden keine synthetischen Ergebnisse erzeugt. Stattdessen zeigt die GUI die Datenbereitschaft und ermÃƒÆ’Ã‚Â¶glicht die vorgelagerte AI-Auswertung.

## 2026-08-28 D051
Dev.48 ist ein IntegritÃƒÆ’Ã‚Â¤ts- und Konsistenzrelease. Historische Funktionen bleiben erhalten; Realhandel und automatische Parameteraktivierung bleiben hart deaktiviert.

## 2026-08-28 D067
Dev.49 modularisiert Monitoring als Blueprint. Audit-Exporte werden vor Ausgabe schlÃƒÆ’Ã‚Â¼sselbasiert redigiert; Realhandel und automatische Parameteraktivierung bleiben ausgeschlossen.
## 2026-08-28 D069
Dev.50 trennt Paper-Steuerinformationen strikt von realen VorgÃƒÆ’Ã‚Â¤ngen und befÃƒÆ’Ã‚Â¼llt keine Formular-Kennzahlen automatisch.
## 2026-08-28 D070
Realhandel verwendet eigene Tabellen und niemals Paper-Konten. Live-AuftrÃƒÂ¤ge benÃƒÂ¶tigen Konfigurationsfreigabe, kurzzeitiges Token und ein positives Auftragslimit.
