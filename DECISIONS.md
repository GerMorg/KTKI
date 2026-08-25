# Decisions â€” append-only

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
Der erste Paper-Broker verwendet ausschlieÃŸlich freigegebene Produkte und Live-Marktdaten. Eine Entscheidung darf nur simuliert ausgefÃ¼hrt werden, wenn die Analyse-/Paper-Automatik aktiv ist.

## 2026-08-23 D008
GebÃ¼hren und Slippage werden getrennt berechnet, gespeichert und in der GUI gezeigt. Standardwerte sind konservative, konfigurierbare Simulationen und keine Behauptung Ã¼ber die individuelle Kraken-GebÃ¼hrenstufe.

## 2026-08-23 D009
Die Baseline ist absichtlich deterministisch und einfach, damit jede Entscheidung reproduzierbar bleibt. Sie ist Ausgangspunkt fÃ¼r spÃ¤tere Benchmarks und kein KI-Modell.

## 2026-08-23 D010
Paper-Parameter werden zusÃ¤tzlich direkt in der Ingress-GUI verwaltet und in SQLite gespeichert. Ã„nderungen gelten ohne App-Neustart.

## 2026-08-23 D011
Alle Paper-Allowlist-Produkte werden WebSocket-seitig beobachtet. Vor jedem Strategielauf dient der Ã¶ffentliche REST-Ticker als zusÃ¤tzlicher Preis-Fallback.

## 2026-08-23 D012
Ein Hintergrund-Scheduler fÃ¼hrt dieselbe Paper-Pipeline wie der manuelle Knopf aus. Es wird dennoch kein Kauf erzwungen, wenn das reproduzierbare Signal die Schwelle nicht erreicht.

## 2026-08-23 D013
Der Scanner verwendet ausschlieÃŸlich abgeschlossene OHLC-Kerzen. Die laut Kraken stets enthaltene aktuelle, noch nicht abgeschlossene Kerze wird aus der Berechnung entfernt.

## 2026-08-23 D014
Scanner-Ergebnisse werden zunÃ¤chst getrennt von der Paper-AusfÃ¼hrung gefÃ¼hrt. Eine Kopplung erfolgt erst nach praktischer PrÃ¼fung und Backtest, um keine ungeprÃ¼fte Strategie automatisch handeln zu lassen.


## 2026-08-25 D023
FÃ¼r breite allgemeine Nachrichtenerkennung wird GDELT als offener Aggregator mit geringerem Quellengewicht eingesetzt und durch EZB, Federal Reserve und Kraken als PrimÃ¤r- beziehungsweise Emittentenquellen ergÃ¤nzt. Reuters bleibt ein optionaler zukÃ¼nftiger lizenzierter Adapter.

## 2026-08-25 D024
Watchlists und Prognosen sind unverÃ¤nderlich versioniert. Auswertungen verÃ¤ndern Modellgewichte nicht automatisch; neue Gewichte benÃ¶tigen eine eigene Version und kontrollierte Freigabe.


## 2026-08-25 D025
Datenbankschema-Erweiterungen werden ab dev.14 explizit und idempotent migriert. `CREATE TABLE IF NOT EXISTS` allein gilt nicht als Migration bestehender Tabellen.

## 2026-08-25 D026
Die einzelne breite GDELT-Abfrage wird durch kleine unabhÃ¤ngige Abfragen fÃ¼r Wirtschaft und Geopolitik ersetzt. Google-News-RSS dient als ergÃ¤nzender Fallback, nicht als alleinige Quelle.

## 2026-08-25 D027
Research erhÃ¤lt einen eigenen optionalen Scheduler. Laufende AuftrÃ¤ge werden weiterhin durch den Pipeline-Lock vor Ãœberlappung geschÃ¼tzt; Paper-Automatik und Research-Zeitplan bleiben getrennt.

## 2026-08-25 D028
Aktien/xStocks werden über Krakens Assetklasse `tokenized_asset` sowie ihre tatsächlich gemeldeten USD- oder EUR-Paare erfasst. Der öffentliche Stream ist nicht länger auf EUR-Symbole beschränkt.

## 2026-08-25 D029
Dynamischer Hebel wird in dev.16 ausschließlich simuliert. Er darf nur aus den je Markt von Kraken gemeldeten `leverage_buy`-Stufen gewählt werden. Eine spätere reale Ausführung besitzt eine getrennte, weiterhin hart deaktivierte Adaptergrenze.

## 2026-08-25 D030
Portfolio-Umschichtungen benötigen einen Mindest-Konfidenzvorteil, müssen geschätzte Verkaufs-, Kauf-, Spread- und Slippagekosten übertreffen und unterliegen einem No-Trade-Mindestbetrag.
