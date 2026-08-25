# Kraken Trader 0.1.0-dev.12

## Mehrstufige Research-Pipeline

1. Das aktivierte Kraken-Marktuniversum wird synchronisiert.
2. Nachrichten werden gesammelt, dedupliziert und Märkten beziehungsweise Kategorien zugeordnet.
3. Ein günstiger Vorfilter bewertet Liquidität, Spread, 24-Stunden-Veränderung und Nachrichtenrelevanz.
4. Nur die besten Kandidaten jeder Kategorie gelangen auf die Research-Watchlist.
5. Nur diese Watchlist erhält die aufwändige OHLC-Detailanalyse.
6. Die Paper-Strategie verwendet ausschließlich vollständig analysierte Watchlist-Einträge.

Nachrichten dienen nur der Research-Priorisierung. Sie können keine Paper- oder Realorder auslösen. Wenn Nachrichtenquellen ausfallen, bleibt der Nachrichtenscore neutral und der Fehler wird sichtbar gespeichert.

Der Scanner zeigt Auftragsstatus, Stufe, Fortschritt, Quellenstatus, Vorfilter und Watchlist. Ein neuer Lauf wird im Hintergrund ausgeführt.
