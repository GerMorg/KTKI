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
Aktien/xStocks werden Ã¼ber Krakens Assetklasse `tokenized_asset` sowie ihre tatsÃ¤chlich gemeldeten USD- oder EUR-Paare erfasst. Der Ã¶ffentliche Stream ist nicht lÃ¤nger auf EUR-Symbole beschrÃ¤nkt.

## 2026-08-25 D029
Dynamischer Hebel wird in dev.16 ausschlieÃŸlich simuliert. Er darf nur aus den je Markt von Kraken gemeldeten `leverage_buy`-Stufen gewÃ¤hlt werden. Eine spÃ¤tere reale AusfÃ¼hrung besitzt eine getrennte, weiterhin hart deaktivierte Adaptergrenze.

## 2026-08-25 D030
Portfolio-Umschichtungen benÃ¶tigen einen Mindest-Konfidenzvorteil, mÃ¼ssen geschÃ¤tzte Verkaufs-, Kauf-, Spread- und Slippagekosten Ã¼bertreffen und unterliegen einem No-Trade-Mindestbetrag.

## 2026-08-25 D031
Ein Markt darf mehreren Produktgruppen angehören, besitzt im Vorfilterlauf aber genau eine kanonische Ergebniszeile. Die Gruppenfreigabe bleibt erhalten; für Persistenz und Watchlist gilt die Priorität xStocks, Forex, Crypto-Spot, Hebelgruppe.
