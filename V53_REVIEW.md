# Review Version 53

## Lernprozesse
Die Parametersuche des kontrollierten Lernens sieht nur Ã¤ltere Trainingsdaten. Alle Gates und angezeigten Trefferquoten werden auf dem jÃ¼ngeren, ungesehenen Holdout berechnet. Ist dieser zu klein, entsteht kein freigabefÃ¤higer Kandidat.

Das Nachrichtenlernen behÃ¤lt seine zeitliche Aufteilung und Walk-forward-PrÃ¼fung. Beide Kandidatensuchen werden weiterhin automatisch durch die Research-Pipeline angestoÃŸen. Die Aktivierung bleibt bewusst atomar und manuell.

## Realhandel
Market-Orders benÃ¶tigen eine eigene explizite Option und sind standardmÃ¤ÃŸig gesperrt. ZusÃ¤tzlich begrenzt `real_max_orders_per_day` die Zahl erfolgreich Ã¼bermittelter Live-AuftrÃ¤ge pro UTC-Tag.

## Restrisiko
Statistische Validierung verhindert keine Verluste. Live-Betrieb zuerst ausschlieÃŸlich mit Kraken-Validierung und kleinsten Limits prÃ¼fen.
