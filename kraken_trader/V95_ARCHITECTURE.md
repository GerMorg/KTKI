# KTKI v95 – End-to-End Contract

## Daten
Kraken Public WebSocket/REST liefern Ticker; abgeschlossene OHLC-Kerzen bilden die Marktmerkmale. Datenqualität und Frische sind vor jeder Entscheidung sichtbar.

## Nachrichten
News werden gesammelt, klassifiziert und lokal/extern bewertet. Marktverknüpfungen verwenden nur frisch geholte Nachrichten aus einem begrenzten 48-Stunden-Fenster mit Altersabschlag. Der News-Score ist ein Scoring-Feature, kein unkalibrierter Prozent-Return.

## Lernen
Strategy Learning bleibt Long/Flat: BUY ist eine mögliche Position, AVOID bedeutet keine Long-Position. Downside/SHORT-Evidenz wird separat über DOWN-Forecasts kalibriert. Kandidaten werden zeitlich mit Holdout geprüft; Lernmetriken sind pro Entscheidung normalisiert und nicht als Portfolio-Equity interpretiert.

## Decision Engine
DecisionEngineV95 erzeugt für Paper und Real dieselben:
- Richtung
- Regime-Faktor
- Model-Quality-Faktor
- Volatilitätsanpassung
- erwartete Brutto-Edge
- vollständige Entry+Exit-Routekosten
- Expected Edge nach Kosten
- Target Exposure
- Rebalance Delta

Eine neue Position benötigt messbare positive Edge nach Kosten und ausreichende Evidenz. HOLD hält die bestehende Zielposition. AVOID reduziert eine bestehende Long-Position auf null. SHORT ist nur mit expliziter Margin-Short-Freigabe zulässig.

## Portfolio
Die Summe der absoluten Ziel-Exposures wird nach individueller Positionsobergrenze zusätzlich auf das verfügbare Investitionsbudget nach Cash-Reserve normalisiert.

## Ausführung
Paper und Real benutzen denselben Decision-Output. Der einzige Unterschied ist die letzte Adapterstufe:
- Paper simuliert Fill, Gebühr, Slippage und ggf. Paper-Hebel.
- Real verwendet das konkrete Kraken-Ausführungspaar, prüft Kraken-/Kontolimits und reicht die Order ein.

Bei Margin wird das Ziel als Notional verstanden. Paper verwendet dafür nur das benötigte Collateral; Real übergibt das Notional mit dem gewählten Leverage.

## Diagnose
Model Health zeigt Forecast-Qualität, nicht Depot-Rendite. Die Steuerinfo bleibt vollständig getrennt von der Handelsentscheidung und ist als eigene Oberfläche direkt erreichbar.
