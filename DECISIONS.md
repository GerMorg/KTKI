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
