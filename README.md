# HA Kraken Trader 0.1.0-dev.77

Home-Assistant-Add-on für auditierbare Kraken-Analyse, Portfolioansicht, lokales Paper-Trading, kontrolliertes Lernen und eine österreichische Einkommensteuer-Prüfhilfe.

## Einstieg

- Dokumentation: [`docs/README.md`](docs/README.md)
- Add-on: [`kraken_trader/`](kraken_trader/)
- Projektverträge: `FEATURE_CONTRACT.yaml`, `TEST_MATRIX.yaml`, `PROJECT_MEMORY.yaml`
- Übergabe: `PROJECT_HANDOVER.md`

## Runtime-Struktur

`kraken_trader/` ist die einzige aktive Home-Assistant-Add-on-Struktur. Die App startet ausschließlich `v77_main:app`. Die früheren versionierten Runtime-Wrapper und die doppelte Root-App wurden entfernt, damit kein paralleler Lern- oder Automationspfad mehr existiert.

## Lernen

Die Lernoberfläche unter `/lernen` zeigt aktive Parameter, erzeugte Kandidaten, Training/Holdout, Gate-Ergebnisse, automatische Ablehnungsgründe und Freigabehistorie für Strategie- und Nachrichten-Lernen.

## Einkommensteuer Österreich

Die Seite `Einkommensteuer AT` ist direkt in der Hauptnavigation verfügbar. Sie nutzt die bestehende taxonomische Arbeits- und Prüfhilfe für Realhandel, Paper-Handel oder beide Quellen.

Realhandel ist standardmäßig deaktiviert. Sicherheitsgrenzen und Freigaben dürfen nicht umgangen werden.
