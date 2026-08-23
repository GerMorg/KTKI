# Project Handover

## Zielbild
Home-Assistant-App für Kraken-Realportfolio, lokales Paper-Trading, automatische daten- und nachrichtenbasierte Bewertung, kontrollierten Realhandel und österreichische Steuerdaten. Keine manuellen Orders.

## Stand 0.1.0-dev.2
Die ursprünglichen Funktionen bleiben erhalten. Neu ist eine Ingress-präfixfähige Navigation; alle Tabs funktionieren über `url_for`. Der neue API-Tab testet öffentliche und private Kraken-Aufrufe, zeigt Diagnoseinformationen und lädt Balance sowie Ledger in SQLite. Realhandel ist weiterhin technisch nicht vorhanden.

## Betrieb
App-Optionen werden beim Prozessstart aus `/data/options.json` gelesen. Nach Änderung von API-Key oder Private Key App neu starten. Danach im API-Tab `Verbindung testen und Portfolio laden` wählen.

## Weiterentwicklung
Zuerst alle Memory-/Contract-/Test-/Ledger-Dateien lesen. Keine Funktion entfernen. Version in `config.yaml`, `/health`, Dokumentation und Release-Ledger gleichzeitig erhöhen.
