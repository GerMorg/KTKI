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

## 2026-08-23 D015
Ab dev.9 ist das valide Scanner-Ergebnis standardmäßig ein zwingendes Gate für automatische Paper-Orders. Fehlende oder ungültige Scanner-Daten blockieren fail-closed.

## 2026-08-23 D016
Der Paper-Broker synchronisiert öffentliche AssetPairs-Metadaten und prüft Paarstatus, Mindestmenge, Mindestwert und Mengenpräzision. Die öffentliche erste Taker-Gebührenstufe wird verwendet, solange keine kontospezifische TradeVolume-Auswertung aktiviert ist.

## 2026-08-23 D017
Produktfreigaben erfolgen ab dev.10 ausschließlich über Kategorien. Innerhalb aktivierter Kategorien wird das vollständige von Kraken gemeldete Online-Marktuniversum dynamisch bereitgestellt; Einzelprodukt-Allowlisten sind kein Benutzerkonzept mehr.

## 2026-08-23 D018
Produktkategorien dürfen sich überschneiden. Ein hebelfähiger Kryptomarkt gehört sowohl zu Kryptowährungen (Spot) als auch zu hebelfähigen Spot-Produkten.
