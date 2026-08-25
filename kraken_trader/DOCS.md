# Kraken Trader 0.1.0-dev.18

## Scanner-Hotfix
Hebelfähige xStocks gehören gleichzeitig zu `xstocks` und `leveraged_spot`. Der Vorfilter erzeugt dennoch genau eine Ergebniszeile pro Symbol und Lauf. Dadurch kann der Primärschlüssel `(run_id, symbol)` nicht mehr mit derselben Aktie kollidieren.

## USD-Aktien und xStocks
USD-Paare bleiben zugelassen. Vorfilter und Detailscanner rufen `tokenized_asset` getrennt von `currency` und `forex` ab. Für Paper-Zielwerte wird ein aktueller EUR/USD-Preis benötigt. Fehlt er, wird nicht simuliert gehandelt.
