# Review Version 53

## Lernprozesse
Die Parametersuche des kontrollierten Lernens sieht nur ältere Trainingsdaten. Alle Gates und angezeigten Trefferquoten werden auf dem jüngeren, ungesehenen Holdout berechnet. Ist dieser zu klein, entsteht kein freigabefähiger Kandidat.

Das Nachrichtenlernen behält seine zeitliche Aufteilung und Walk-forward-Prüfung. Beide Kandidatensuchen werden weiterhin automatisch durch die Research-Pipeline angestoßen. Die Aktivierung bleibt bewusst atomar und manuell.

## Realhandel
Market-Orders benötigen eine eigene explizite Option und sind standardmäßig gesperrt. Zusätzlich begrenzt `real_max_orders_per_day` die Zahl erfolgreich übermittelter Live-Aufträge pro UTC-Tag.

## Restrisiko
Statistische Validierung verhindert keine Verluste. Live-Betrieb zuerst ausschließlich mit Kraken-Validierung und kleinsten Limits prüfen.
