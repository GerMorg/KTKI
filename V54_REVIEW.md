# Review Version 54

## Informations- und Orderpfad
Die neue GUI-Seite â€žAblauf & Systemeâ€œ dokumentiert den tatsÃ¤chlich verdrahteten Ablauf. Marktuniversum, Prefilter, Scanner, aktive Strategieprofile, Kostenbewertung, Lernvalidierung und RealTradeEngine bilden beziehungsweise beeinflussen den Kernpfad. Die Parameteraktivierung und jede Live-Freigabe bleiben bewusst manuell.

## Werden alle Systeme verwendet?
Nicht jedes entwickelte Modul ist ein direkter Eingang der Live-Order. Paper Engine, Backtests, Prognoseauswertung, Audit, Monitoring und Steuerinfo arbeiten als Simulation, QualitÃ¤tssicherung oder Nachweis. Portfolio Allocator und Decision Matrix sind noch nicht automatisch an das Live-Auftragsformular gekoppelt. V54 zeigt diese Abgrenzung ausdrÃ¼cklich, anstatt eine Vollintegration vorzutÃ¤uschen.

## Anzeige
Persistierte Rechenwerte bleiben unverÃ¤ndert. Nur die Darstellung wird zentral begrenzt: Werte ab 1 mit hÃ¶chstens zwei, Werte unter 1 mit hÃ¶chstens vier und sehr kleine Werte mit hÃ¶chstens acht Nachkommastellen. Dadurch bleiben kleine Kryptovolumina sichtbar.

## Realhandel
Die vorhandenen Sicherungen aus V53 bleiben unverÃ¤ndert: Default-Aus, Kill-Switch, Allowlist, Limits, optional gesperrte Market-Orders, Tageslimit, zeitlich begrenztes Arming und Einmal-Token.
