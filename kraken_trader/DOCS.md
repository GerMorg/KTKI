# Kraken Trader 0.1.0-dev.9

## Neuer Entscheidungsweg
Jeder automatische Paper-Lauf führt nacheinander aus:
1. Livepreise aktualisieren.
2. Kraken-AssetPairs-Regeln synchronisieren.
3. Scanner für freigegebene Produkte aktualisieren.
4. Nur valide Scanner-Ergebnisse bewerten.
5. Paarstatus, Mindestmenge, Mindestwert, Präzision, Gebühren und Positionslimit prüfen.
6. Entscheidung und gegebenenfalls simulierten Trade vollständig protokollieren.

Unter **Einstellungen** ist „Scanner-Signal zwingend verwenden“ standardmäßig aktiv. Ohne valides Scanner-Ergebnis wird keine Paper-Order ausgeführt. Realhandel bleibt ausgeschlossen.
