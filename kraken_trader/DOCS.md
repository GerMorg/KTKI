# Kraken Trader 0.1

## Sicherer Start
Die App funktioniert ohne Zugangsdaten. Fuer das echte Portfolio einen separaten Kraken-Schluessel mit ausschliesslich benoetigten Leserechten verwenden. Keine Rechte fuer Orders, Einzahlungen oder Auszahlungen vergeben.

## Optionen
- `kraken_api_key`: optionaler Read-only-Key
- `kraken_api_secret`: optionales Secret
- `paper_start_eur`: einmaliger Startwert des Musterdepots
- `refresh_minutes`: fuer kuenftigen Scheduler vorbereitet

## Bedienung
`Synchronisieren` liest Systemstatus, Instrumente, Balance und aktuelle Ledger-Eintraege. Einstellungen verwalten globalen Automatikstopp und die erlaubte Produktliste. Diese Version erzeugt keine Orders.

## Datenschutz
Secret-Werte werden nicht in HTML, Auditdaten oder Exporte geschrieben. Sie liegen in den geschuetzten App-Optionen von Home Assistant.
