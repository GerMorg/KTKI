# Kraken Trader 0.1.0-dev.40

## Dauerhafte UTF-8-Strategie
1. Alle Repository-Texte sind UTF-8 mit LF.
2. `.editorconfig` und `.gitattributes` verhindern abweichende neue Dateien.
3. HTML, JSON, CSV und Text werden mit UTF-8-Charset ausgeliefert.
4. Beim ersten Start repariert eine idempotente Migration bekannte Altfehler in gespeicherten Anzeigetexten.
5. Automatische Tests prüfen typische Fehlerbilder und das gesamte Repository.

Die Migration verändert einen Wert nur, wenn die Rückwandlung die Anzahl bekannter Beschädigungsmarker reduziert. Das Ergebnis wird im Audit als `UTF8_DATA_MIGRATION` protokolliert.




## dev.28 Datenqualität und Backtest
Ticker- und OHLC-Status werden getrennt persistiert. Die letzte, noch laufende REST-OHLC-Kerze wird nicht als abgeschlossen gewertet. Der lokale OHLCVT-Speicher ist die Grundlage für reproduzierbare Walk-forward-Benchmarks.


## dev.40
Die Lern-GUI zeigt alle drei aktiven Parameterfamilien parallel und erklärt PENDING als einzige Freigabestufe. Google AI Studio/Gemini ist als optionaler kostenloser Schattenprovider integriert. Externe Themen und betroffene Assets werden mit der lokalen Taxonomie verglichen; Abweichungen sind nur Kalibrierhinweise und ändern nichts automatisch. Vollständige Regression: 123 Tests erfolgreich.
