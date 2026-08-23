# HA Kraken Trader Projektuebergabe

Stand: 0.1.0-dev.4

## Zielbild
Home-Assistant-App fuer Kraken-Realportfolio, lokales Paper-Trading, nachvollziehbare automatische Bewertung, spaeter streng kontrollierten Realhandel und oesterreichische Steueraufbereitung.

## Erhaltene Funktionen
Ingress-Navigation, alle GUI-Tabs, signierte Kraken-REST-Abfragen, vollstaendige Ledger-Pagination, Portfoliohistorie samt Nullpositionen, Paper-Wallet, Einstellungen, Kill-Switch, Allowlist, Audit und CSV-Exporte. Realhandel ist nicht implementiert.

## Neue Entwicklungsstufe
- Oeffentlicher Kraken Spot WebSocket v2 zum Streamen von Tickerpreisen aktuell gehaltener Assets mit direktem EUR-Markt.
- Persistenz von Last, Bid, Ask, Prozentveraenderung und Empfangszeit.
- Automatischer Statuskanal und Heartbeat-Auswertung.
- STALE-Zustand, wenn 30 Sekunden keine Nachricht eintrifft; konfigurierbar von 10 bis 300 Sekunden.
- Reconnect mit wachsender Wartezeit bis maximal 30 Sekunden und erneuter Subscription.
- Streamsymbole werden nach jedem REST-Portfoliosync abgeglichen.
- REST bleibt kanonisch fuer Portfolio-Snapshots, Vollstaendigkeit und Wiederabgleich.
- Privater WebSocket-Zugriff wird weiterhin nur als Berechtigung getestet; keine privaten Streams und keine Ordertransporte.

## HA-OS-Test
1. App aktualisieren und starten.
2. Portfolio vollstaendig synchronisieren.
3. API-Seite oeffnen: Stream muss fuer gehaltene EUR-Assets CONNECTED und spaeter nicht STALE zeigen.
4. Last/Bid/Ask und Empfangszeit beobachten.
5. App neu starten und pruefen, ob Subscription anhand persistierter Positionen wieder aufgebaut wird.

## Naechster Schritt
Privater read-only WebSocket-v2-Stream fuer Balances und Executions mit Sequenzkontrolle und REST-Reconciliation. Noch keine Orders.
