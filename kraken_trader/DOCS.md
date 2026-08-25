# Kraken Trader 0.1.0-dev.15

## Nachrichtenquellen

Die alte Quelle **GDELT Global** wird automatisch deaktiviert. Sie wurde ersetzt durch:

- GDELT Wirtschaft
- GDELT Geopolitik
- Google News Wirtschaft AT
- Google News Geopolitik AT
- EZB Presse
- Federal Reserve
- Kraken Blog

GDELT-Abrufe verwenden kleinere Einzelabfragen, einen User-Agent und begrenzte Wiederholungen. Die Scannerseite zeigt HTTP-Status und konkrete Fehlerdetails. Der Ausfall einer Aggregatorquelle stoppt die übrigen Quellen nicht.

## Automatischer Research-Scanner

Unter **Einstellungen → Research** kann die automatische Research-Pipeline aktiviert und ein Intervall von 5 bis 1.440 Minuten gesetzt werden. Paper-Automatik und Research-Scheduler bleiben getrennt. Ein bereits laufender Research-Auftrag verhindert einen zweiten parallelen Lauf.
