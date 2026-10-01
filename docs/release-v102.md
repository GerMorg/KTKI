# Release v102 · 2026-10-01

v102 reduziert die GUI auf den tatsächlichen Kraken-Trading-Prozess und korrigiert die öffentliche Kraken-Marktdatenanbindung.

## Aktive GUI

Die Hauptnavigation besteht nur noch aus:

- Übersicht
- Markt & Daten
- Analyse
- Portfolio
- Handel
- Lernen
- Realhandel
- System

Die österreichische Steuer-/Einkommensteuerhilfe bleibt als Fachroute `/steuerinfo-at` erreichbar, ist aber nicht Teil der Hauptnavigation. Alte GUI-URLs werden auf die aktuellen Prozessseiten weitergeleitet.

## Public Market

`market_feed_v102.py` ist die einzige öffentliche Market-Schnittstelle. Sie verwendet REST für einen sofortigen Snapshot und den Kraken Public WebSocket für Live-Ticker. Private API-Schlüssel sind dafür nicht erforderlich.

Kraken-Paarbezeichnungen aus REST-Antworten werden vor dem Matching normalisiert, einschließlich klassischer Bezeichner wie `XXBTZEUR`.

## End-to-End

Der aktuelle Ablauf ist Market → News → Analyse → Lernen → Canonical Plan → Paper/Real Execution → Nachweis. Paper und Real verwenden weiterhin dieselbe Plan-/Execution-Logik.

## Regressionen

v102 testet den App-Import, die aktuellen GUI-Routen, Legacy-Weiterleitungen, Public-Market-Paarauflösung und den gemeinsamen Market-Refresh-Pfad.
