# Review Version 52

## Befunde
- Die bisherige kontrollierte Lernlogik erzeugte nur einen heuristischen Nachbarn und wertete HOLD bei kleinen Bewegungen als korrekten Treffer. Das konnte bei Forex eine irreführende 100-%-Anzeige begünstigen.
- News-Learning optimierte jeden Parameter nur in einem Durchlauf.
- Ein Real-Order-Pfad war vorhanden, doch Add-on-Optionen und der ältere Adapter waren nicht vollständig konsolidiert.

## Lösung
- Mehrpassige automatische Koordinatensuche in beiden Lernloops.
- Automatischer Start nach jedem Research-Lauf, manuelle atomare Ein-Klick-Freigabe bleibt erhalten.
- Trefferquote als konservative 95-%-Wilson-Untergrenze nur für BUY/AVOID. HOLD gilt als Enthaltung.
- Realhandel mit Validierungsmodus, Default-Aus, Kill-Switch, Allowlist, Limits, Freigabephrase und Einmal-Token.

## Grenze
Keine Gewinn- oder Modellgütegarantie. Vor Live-Nutzung zuerst Kraken-Validierung, Paper-Handel und kleinste Limits verwenden.
