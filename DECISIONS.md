# Decisions — append-only

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
Der erste Paper-Broker verwendet ausschließlich freigegebene Produkte und Live-Marktdaten. Eine Entscheidung darf nur simuliert ausgeführt werden, wenn die Analyse-/Paper-Automatik aktiv ist.

## 2026-08-23 D008
Gebühren und Slippage werden getrennt berechnet, gespeichert und in der GUI gezeigt. Standardwerte sind konservative, konfigurierbare Simulationen und keine Behauptung über die individuelle Kraken-Gebührenstufe.

## 2026-08-23 D009
Die Baseline ist absichtlich deterministisch und einfach, damit jede Entscheidung reproduzierbar bleibt. Sie ist Ausgangspunkt für spätere Benchmarks und kein KI-Modell.

## 2026-08-23 D010
Paper-Parameter werden zusätzlich direkt in der Ingress-GUI verwaltet und in SQLite gespeichert. Änderungen gelten ohne App-Neustart.

## 2026-08-23 D011
Alle Paper-Allowlist-Produkte werden WebSocket-seitig beobachtet. Vor jedem Strategielauf dient der öffentliche REST-Ticker als zusätzlicher Preis-Fallback.

## 2026-08-23 D012
Ein Hintergrund-Scheduler führt dieselbe Paper-Pipeline wie der manuelle Knopf aus. Es wird dennoch kein Kauf erzwungen, wenn das reproduzierbare Signal die Schwelle nicht erreicht.

## 2026-08-23 D013
Der Scanner verwendet ausschließlich abgeschlossene OHLC-Kerzen. Die laut Kraken stets enthaltene aktuelle, noch nicht abgeschlossene Kerze wird aus der Berechnung entfernt.

## 2026-08-23 D014
Scanner-Ergebnisse werden zunächst getrennt von der Paper-Ausführung geführt. Eine Kopplung erfolgt erst nach praktischer Prüfung und Backtest, um keine ungeprüfte Strategie automatisch handeln zu lassen.


## 2026-08-25 D023
Für breite allgemeine Nachrichtenerkennung wird GDELT als offener Aggregator mit geringerem Quellengewicht eingesetzt und durch EZB, Federal Reserve und Kraken als Primär- beziehungsweise Emittentenquellen ergänzt. Reuters bleibt ein optionaler zukünftiger lizenzierter Adapter.

## 2026-08-25 D024
Watchlists und Prognosen sind unveränderlich versioniert. Auswertungen verändern Modellgewichte nicht automatisch; neue Gewichte benötigen eine eigene Version und kontrollierte Freigabe.


## 2026-08-25 D025
Datenbankschema-Erweiterungen werden ab dev.14 explizit und idempotent migriert. `CREATE TABLE IF NOT EXISTS` allein gilt nicht als Migration bestehender Tabellen.

## 2026-08-25 D026
Die einzelne breite GDELT-Abfrage wird durch kleine unabhängige Abfragen für Wirtschaft und Geopolitik ersetzt. Google-News-RSS dient als ergänzender Fallback, nicht als alleinige Quelle.

## 2026-08-25 D027
Research erhält einen eigenen optionalen Scheduler. Laufende Aufträge werden weiterhin durch den Pipeline-Lock vor Überlappung geschützt; Paper-Automatik und Research-Zeitplan bleiben getrennt.

## 2026-08-25 D028
Aktien/xStocks werden über Krakens Assetklasse `tokenized_asset` sowie ihre tatsächlich gemeldeten USD- oder EUR-Paare erfasst. Der öffentliche Stream ist nicht länger auf EUR-Symbole beschränkt.

## 2026-08-25 D029
Dynamischer Hebel wird in dev.16 ausschließlich simuliert. Er darf nur aus den je Markt von Kraken gemeldeten `leverage_buy`-Stufen gewählt werden. Eine spätere reale Ausführung besitzt eine getrennte, weiterhin hart deaktivierte Adaptergrenze.

## 2026-08-25 D030
Portfolio-Umschichtungen benötigen einen Mindest-Konfidenzvorteil, müssen geschätzte Verkaufs-, Kauf-, Spread- und Slippagekosten übertreffen und unterliegen einem No-Trade-Mindestbetrag.

## 2026-08-25 D033
Ein vorübergehend fehlender Ticker darf einen von Kraken gemeldeten und aktivierten Markt nicht aus der Research-Watchlist entfernen. Der Markt bleibt als `PENDING_TICKER` Kandidat; eine Paper-Ausführung bleibt ohne valide Detailanalyse weiterhin ausgeschlossen.

## 2026-08-25 D034
Persistente Inserts verwenden bei weiterentwickelten Tabellen immer explizite Spaltenlisten. Dadurch bleiben sie gegenüber vorhandenen und zukünftig ergänzten Spalten robust.

## 2026-08-25 D035
Alle ausgelieferten Textdateien und sichtbaren GUI-Texte sind echtes UTF-8. Typische Mojibake-Marker werden durch einen automatisierten Repository-Test ausgeschlossen.

## 2026-08-25 D036
Die angehängte Repository-Snapshot-Version ist ab sofort immer die alleinige Entwicklungsbasis. Ein Markt darf mehreren aktivierten Gruppen angehören, wird in `prefilter_results` wegen des Primärschlüssels `(run_id,symbol)` aber vor Bewertung kanonisch auf genau einen Datensatz reduziert.

## 2026-08-25 D037
UTF-8 wird ab dev.21 auf vier Ebenen abgesichert: UTF-8-Quelltexte, Git-/Editor-Regeln, explizite HTTP-Charsets und eine idempotente Startmigration für bereits beschädigte SQLite-Anzeigetexte.

## 2026-08-25 D038
Dev.22 verwendet eine neue UTF-8-Datenmigrationskennung. Eine bereits gesetzte dev.21-Markierung darf die Reparatur noch beschädigter Bestandsdaten nicht überspringen. Repository-Quellen und sichtbare GUI-Texte müssen selbst korrektes UTF-8 enthalten; Laufzeitreparatur ist nur ein Upgrade-Sicherheitsnetz.

## 2026-08-25 D039
Aktien/xStocks erhalten ab dev.23 ein eigenes deterministisches Bewertungsprofil `xstocks-v1`. Nur ein valider Detailscan mit BUY-Signal darf eine Paper-Allokation erzeugen. USD-Preise werden vor der Paper-Ausführung über EUR/USD in EUR umgerechnet; Kraken-Mindestmenge und Mindestkosten werden fail-closed geprüft.

## 2026-08-25 D040
Nicht-kryptografische Marktdaten verwenden bei Kraken ausschließlich den dokumentierten Parameter `asset_class`; `aclass_base` ist dafür unzulässig. Für xStocks wird der originale `source_key` aus AssetPairs als primäre Pair-ID für OHLC verwendet, mit sichtbarer Fehlerdiagnose statt eines unbegründeten Scores 0.

## 2026-08-26 D041
Der Lernprozess verändert niemals automatisch aktive Strategieparameter. Aus ausgewerteten xStock-Prognosen darf nur ein begrenzter Vorschlag für exakt neun Parameter entstehen. Alle neun Werte werden gemeinsam versioniert und ausschließlich nach ausdrücklicher Ein-Klick-Freigabe aktiviert.

## 2026-08-26 D042
Produkte werden nach Anlageklasse und Basiswert kanonisiert. Watchlist, Scanner und Portfolio verwenden genau ein kostenoptimal gewähltes Ausführungspaar; Alternativen bleiben als Metadaten erhalten.
## 2026-08-26 D043
USD-Paper-Ausführungen bilden EUR-USD-Konvertierung, FX-Spread, FX-Gebühr, Produktspread und Handelsgebühr getrennt ab.
## 2026-08-26 D044
Forex verwendet asset_class=forex und ein eigenes deterministisches forex-v1-Profil. Umschichtungen benötigen Mindesthaltedauer, Cooldown, Mehrfachbestätigung, positive Verbesserung nach Kosten und ein Tageslimit.

## 2026-08-26 D045
AssetPairs verwendet den dokumentierten Parameter `aclass_base`. Das Forex-Universum wird reproduzierbar aus Fiat-zu-Fiat-Paaren der Currency-Antwort abgeleitet; Ticker und OHLC bleiben für Forex im Currency-Routing.
## 2026-08-26 D046
Die Auswahl zwischen EUR- und USD-Ausführungspaar erfolgt ausschließlich nach vollständigen erwarteten Ausführungskosten; Liquidität und danach EUR dienen als Gleichstandsregeln.
## 2026-08-26 D047
Paper-Umschichtungen berücksichtigen Produkspread, Slippage, Handelsgebühr, FX-Spread, FX-Gebühr, realisierten Gewinn/Verlust und eine konfigurierbare Steuersimulation.



## 2026-08-26 D048
Forex-Datenqualität wird je Paar getrennt für Ticker, Bid/Ask, Volumen, OHLC und Fehlergrund persistiert. Die aktuelle, noch nicht abgeschlossene OHLC-Kerze gilt nicht als Historie.
## 2026-08-26 D049
Backtests verwenden ausschließlich lokal persistierte abgeschlossene OHLCVT-Daten und weisen Kostenannahmen, Anlageklasse und Benchmarks gemeinsam aus. Reale Orders bleiben ausgeschlossen.

## 2026-08-26 D050
Kontospezifische Handelsgebühren werden ausschließlich read-only über TradeVolume bezogen. Maker und Taker werden je Paar mit Quelle und Zeitpunkt gespeichert. Fehlen Daten oder Berechtigungen, gilt der konservative konfigurierte Taker-Wert.

## 2026-08-26 D051
forex-v2 läuft ausschließlich im Schattenmodus und darf weder Scanner-Ergebnisse überschreiben noch Paper-Entscheidungen beeinflussen. Nicht verfügbare Makrofaktoren werden als null und fehlend gespeichert, niemals geschätzt.

## 2026-08-26 D052
Kanonische Produktidentität, Ausführungspaar, Alternativen, EUR-/USD-Kosten und Positionszuordnung werden gemeinsam sichtbar gemacht.
## 2026-08-26 D053
Umschichtungen werden über sieben einzeln auditierte Regeln bewertet. Die erste nicht erfüllte Regel ist der verbindliche sichtbare Blockierungsgrund.

## 2026-08-26 D054
Parameterfamilien für Forex, xStocks und Krypto werden getrennt versioniert. Kandidaten benötigen Schattenvergleich, Mindeststichprobe, Mindestverbesserung und Konfidenzintervall. Aktivierung und Rollback erfolgen ausschließlich nach Benutzeraktion.



## 2026-08-26 D055
Ab dev.33 existiert genau ein kontrolliertes Lernsystem. Forex, xStocks und Krypto besitzen je neun getrennte Parameter. Nur die aktive, ausdrücklich freigegebene Familienversion darf den Scanner steuern. Prognosen speichern die zugehörige Version und den vollständigen Snapshot. Kandidaten auf einer nicht mehr aktiven Basisversion werden als STALE abgewiesen.

## 2026-08-26 D056
Die vollständige Regressionstestsuite ist ab dev.34 ein hartes Release-Gate. Veraltete Tests werden auf aktuelle, dokumentierte Verträge migriert, statt produktive Sicherheitsfunktionen für historische Testannahmen zurückzubauen.

## 2026-08-26 D057
Lernkandidaten werden ab dev.35 auf denselben historischen Feature-Snapshots wie die aktive Version bewertet. Metriken werden je Prognosehorizont getrennt und nach geschätzten Roundtrip-Kosten ausgewiesen. Abdeckung und Drawdown sind Freigabeinformationen; eine automatische Aktivierung bleibt ausgeschlossen.




## 2026-08-26 D058
Ab dev.36 stammen Laufzeitversion und HTTP-User-Agent aus einer einzigen zentralen Versionsquelle. Statische Add-on-Metadaten und Projektunterlagen werden durch Regressionstests auf denselben Releasewert geprüft.

## 2026-08-26 D059
Dev.36 ist ein reines Konsistenz- und Vertrauensrelease. Strategieparameter, Freigabelogik und die hart deaktivierte Real-Execution-Grenze bleiben funktional unverändert.

## 2026-08-26 D060
Ab dev.37 wird ein Lernkandidat nur PENDING, wenn für alle konfigurierten Horizonte Mindeststichprobe, Mindestabdeckung, positive Nettorenditeverbesserung, absoluter Drawdown und Drawdown-Verschlechterung sowie die bisherige Trefferquotenverbesserung erfüllt sind.

## 2026-08-26 D061
Die Gate-Policy und jedes Gate-Ergebnis werden am Kandidaten gespeichert. Eine Benutzerfreigabe wiederholt die vollständige Prüfung mit der aktuellen Policy direkt vor der atomaren Aktivierung. Bei Abweichung wird REJECTED_RECHECK gesetzt und keine Parameterfamilie verändert.

## 2026-08-26 D062
Ab dev.38 wird eine fällige Prognose ausschließlich mit der ersten vollständig abgeschlossenen lokalen OHLC-Kerze am oder nach ihrem exakten Zielzeitpunkt bewertet. Fehlt eine solche Kerze, bleibt die Prognose OPEN; ein aktueller Livepreis ist kein historischer Ersatz.

## 2026-08-26 D063
Forecast-Kosten werden als getrennte Einstiegs-, Ausstiegs- und Roundtrip-Werte gespeichert. Gebührenquelle und Gültigkeitszeitpunkt sowie FX-Erfordernis sind Bestandteil des unveränderlichen Feature-Snapshots.

## 2026-08-27 D064
Gebührenpaare werden vor TradeVolume aus der kanonischen Marktidentität gegen Kraken-Quellschlüssel und Aliasse aufgelöst. Ein ungültiges Paar darf gültige Gebührenprofile nicht verwerfen; nicht unterstützte Assetklassen bleiben beim konservativen Konfigurationswert.
## 2026-08-27 D065
Die Ingress-GUI erhält eine durchgängige responsive Navigation, eine geführte Startseite und verständliche Sicherheits- und Freigabehinweise. Bestehende Funktionen bleiben erhalten.


## 2026-08-28 D064
Die externe Nachrichten-AI darf lokale Nachrichtenparameter nur als Vergleichsinstanz anregen. Automatische Vergleiche sind zulässig; die Aktivierung bleibt eine ausdrückliche Benutzeraktion mit erneuter Prüfung und atomarer Versionierung.

## 2026-08-28 D066
Nachrichtenparameter dürfen nur auf älteren Beobachtungen optimiert werden. Freigabemetriken stammen ausschließlich aus einem späteren, disjunkten Validierungsfenster. Jede Freigabe wiederholt Fingerprint und Gates; veränderte Daten blockieren die Aktivierung.

## 2026-08-28 D067
Ein Nachrichtenkandidat benötigt neben dem finalen Validierungsfenster stabile Ergebnisse über mehrere chronologische Walk-forward-Teilfenster. Standardmäßig müssen mindestens zwei von drei Fenstern alle Verlust- und Richtungsübereinstimmungs-Gates erfüllen. Unzureichende Historie blockiert fail-closed.

## 2026-08-28 D067
Dashboard-Verfügbarkeit wird aus tatsächlich vorhandenen Daten abgeleitet. WebSocket-Zustände bleiben separat sichtbar und überschreiben erfolgreiche REST- oder Portfolio-Daten nicht.
## 2026-08-28 D068
Gemini wird als zusätzlicher externer Nachrichten-AI-Anbieter über den offiziellen generateContent-REST-Vertrag unterstützt. AI-Ergebnisse bleiben Vergleichsdaten ohne automatische Handels- oder Aktivierungswirkung.



## 2026-08-28 D045 - Familienbezogene Lernansicht
Die Übersicht zeigt alle aktiven Familienversionen. Detaildaten werden ausschließlich für die ausgewählte Familie geladen, um Fehlinterpretationen zu vermeiden.

## 2026-08-28 D046 - Lernfamilienstatus in der Übersicht
Die Familienübersicht zeigt nur kompakte, abgeleitete Statuswerte. Detaildaten und Aktionen bleiben auf die bewusst ausgewählte gültige Familie beschränkt.

## 2026-08-28 D047 - Nachrichtenvergleich bleibt datenbasiert
Die Mindeststichprobe wird nicht abgesenkt und es werden keine synthetischen Ergebnisse erzeugt. Stattdessen zeigt die GUI die Datenbereitschaft und ermöglicht die vorgelagerte AI-Auswertung.

## 2026-08-28 D051
Dev.48 ist ein Integritäts- und Konsistenzrelease. Historische Funktionen bleiben erhalten; Realhandel und automatische Parameteraktivierung bleiben hart deaktiviert.
