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

## 2026-08-23 D015
Ab dev.9 ist das valide Scanner-Ergebnis standardmäßig ein zwingendes Gate für automatische Paper-Orders. Fehlende oder ungültige Scanner-Daten blockieren fail-closed.

## 2026-08-23 D016
Der Paper-Broker synchronisiert öffentliche AssetPairs-Metadaten und prüft Paarstatus, Mindestmenge, Mindestwert und Mengenpräzision. Die öffentliche erste Taker-Gebührenstufe wird verwendet, solange keine kontospezifische TradeVolume-Auswertung aktiviert ist.

## 2026-08-23 D017
Produktfreigaben erfolgen ab dev.10 ausschließlich über Kategorien. Innerhalb aktivierter Kategorien wird das vollständige von Kraken gemeldete Online-Marktuniversum dynamisch bereitgestellt; Einzelprodukt-Allowlisten sind kein Benutzerkonzept mehr.

## 2026-08-23 D018
Produktkategorien dürfen sich überschneiden. Ein hebelfähiger Kryptomarkt gehört sowohl zu Kryptowährungen (Spot) als auch zu hebelfähigen Spot-Produkten.

## 2026-08-23 D019
Das vollständige Marktuniversum bleibt verfügbar, wird aber ressourcenschonend in persistent rotierenden Teil-Läufen verarbeitet. Marktverfügbarkeit und gleichzeitige Verarbeitung werden getrennt behandelt.

## 2026-08-23 D020
Öffentliche OHLC-Aufrufe werden standardmäßig auf höchstens ungefähr einen Aufruf pro Sekunde begrenzt; überlappende Scannerläufe werden verworfen und auditiert.


## 2026-08-25 D021
Die Marktvorfilterung kombiniert günstige Kraken-Tickerdaten mit deterministisch zugeordneten Nachrichten. Nachrichten beeinflussen ausschließlich die Research-Priorisierung und sind kein Handelssignal.

## 2026-08-25 D022
Die Paper-Automatik ist von laufenden Research-Aufträgen entkoppelt. Sie nutzt nur Watchlist-Einträge mit abgeschlossener valider Detailanalyse.
