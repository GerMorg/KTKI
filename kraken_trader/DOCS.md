# Kraken Trader 0.1.0-dev.45

## Dauerhafte UTF-8-Strategie
1. Alle Repository-Texte sind UTF-8 mit LF.
2. `.editorconfig` und `.gitattributes` verhindern abweichende neue Dateien.
3. HTML, JSON, CSV und Text werden mit UTF-8-Charset ausgeliefert.
4. Beim ersten Start repariert eine idempotente Migration bekannte Altfehler in gespeicherten Anzeigetexten.
5. Automatische Tests prÃ¼fen typische Fehlerbilder und das gesamte Repository.

Die Migration verÃ¤ndert einen Wert nur, wenn die RÃ¼ckwandlung die Anzahl bekannter BeschÃ¤digungsmarker reduziert. Das Ergebnis wird im Audit als `UTF8_DATA_MIGRATION` protokolliert.




## dev.28 DatenqualitÃ¤t und Backtest
Ticker- und OHLC-Status werden getrennt persistiert. Die letzte, noch laufende REST-OHLC-Kerze wird nicht als abgeschlossen gewertet. Der lokale OHLCVT-Speicher ist die Grundlage fÃ¼r reproduzierbare Walk-forward-Benchmarks.


