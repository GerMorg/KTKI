# HA Kraken Trader Projektübergabe

Stand: 0.1.0-dev.3

## Zielbild
Home-Assistant-App für Kraken-Realportfolio, lokales Paper-Trading, nachvollziehbare automatische Bewertung, später streng kontrollierten Realhandel und österreichische Steueraufbereitung.

## Diese Version
- REST-Hybrid bleibt aktiv; Portfolio, Ledger, Assets, Paare und Ticker werden über Kraken REST synchronisiert.
- Private WebSocket-Berechtigung kann über GetWebSocketsToken geprüft werden; der Token wird weder angezeigt noch gespeichert.
- Alle Ledger-Seiten werden importiert. Assets aus der Historie bleiben mit Menge 0 als HISTORICAL_ZERO sichtbar.
- Jeder Sync erzeugt einen unveränderlichen Portfolio-Snapshot mit EUR-Gesamtwert und Qualitätsstatus.
- Fehlende EUR-Kurse führen zu INCOMPLETE statt erfundener Bewertung.
- Realhandel ist weiterhin serverseitig nicht implementiert.

## Nächster sinnvoller Schritt
Persistenter öffentlicher WebSocket-v2-Kursstream mit Reconnect, Heartbeat, Stale-Data-Erkennung und REST-Reconciliation; private Streams erst danach.
