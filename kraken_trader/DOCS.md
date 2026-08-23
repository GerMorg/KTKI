# Kraken Trader 0.1.0-dev.7

## Konfiguration
Im Tab **Einstellungen** befinden sich jetzt:
- Analyse-/Paper-Automatik
- Ausführungsintervall in Minuten
- Paper-Orderwert in EUR
- maximale Positionsgröße in Prozent
- simulierte Gebühr und Slippage in Basispunkten
- Produktfreigaben

Mindestens ein Produkt anhaken, Automatik aktivieren und speichern. Danach holt jeder Lauf zunächst öffentliche Preise. Entscheidungen entstehen automatisch im gewählten Intervall und können zusätzlich über **Musterdepot → Paper-Strategie jetzt ausführen** sofort ausgelöst werden.

Ein simulierter Kauf findet nur statt, wenn das Produkt freigegeben ist, ein aktueller Preis vorliegt, die Automatik aktiv ist, das Positionslimit frei ist und die 24-Stunden-Veränderung mindestens +1 % beträgt. Das Ausbleiben eines Kaufs kann daher eine korrekte HOLD-Entscheidung sein. Realhandel ist nicht implementiert.
