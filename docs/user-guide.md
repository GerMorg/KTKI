# Benutzerhandbuch · v103

Die Hauptnavigation bildet weiterhin nur den tatsächlichen Prozess ab. Gerenderte Aktionen zeigen auf aktuelle Endpoints; historische URLs werden nur als Weiterleitungen vorgehalten.

## Paper-Handel

Ein SUBMITTED-Eintrag im Paperpfad bedeutet einen persistierten simulierten Fill. Nachgelagerte Snapshot- oder Guard-Buchhaltung wird separat als Warnung protokolliert und macht den vorhandenen Fill nicht zu einem FAILED-Trade.

## Realhandel

Die automatische Ausführung nutzt denselben Plan/Intent wie Paper. Für eine Liveübermittlung müssen Realhandel, Kill-Switch und die automatische Real-Ausführung über die Home-Assistant-Konfiguration freigegeben sein; anschließend werden Balance, Limits, Marktregeln und Kraken-Preflight erneut geprüft. Der manuelle Livepfad bleibt davon getrennt und benötigt das zeitlich begrenzte Freigabetoken.

## Österreichische Steuerhilfe

/steuerinfo-at enthält die österreichische Einkommensteuer-/KESt-Arbeitshilfe, offizielle BMF-Quellen, Prüffelder und die aktuellen ZIP-/CSV-Exporte. Die Darstellung ist ausdrücklich keine Steuer- oder Rechtsberatung.

# Benutzerhandbuch · v102

Die Hauptnavigation bildet nur noch den tatsächlichen Prozess ab. Legacy-GUI-URLs führen auf die jeweilige aktuelle Seite, damit alte Bookmarks nicht mehr in veralteten Oberflächen landen.

# Benutzerhandbuch · v101

Die Oberfläche ist über Home-Assistant-Ingress erreichbar. Die aktuelle Navigation führt zu Übersicht, Analyse, Portfolio, Handel, Lernen, Diagnose, Prozess, Automatik, Realhandel und den ergänzenden Fachseiten.

## Realhandel

Der globale Realhandelsstatus wird überall aus derselben Laufzeitquelle abgeleitet. REALHANDEL FREIGEGEBEN bedeutet, dass Realhandel und automatische Real-Ausführung global aktiviert sind und der Kill-Switch frei ist. Das bedeutet noch nicht, dass jede konkrete Order ausgeführt wird: Datenqualität, Edge, Portfolio-Risiko, Limits, Balance, Kraken-Market-Regeln und weitere Gates werden pro Auftrag erneut geprüft.

Die Home-Assistant-Konfiguration verwendet keine separaten real_execution_disabled- oder real_dry_run-Schalter. Automatische Ausführung wird über real_execute_enabled in Kombination mit automation_enabled und der Realhandelsfreigabe gesteuert.

## Lernen und Nachrichten

Aktive Parameter werden nicht durch die Kandidatensuche automatisch geändert. Kandidaten müssen die bestehenden Validierungs- und Stabilitätsgates bestehen; die Aktivierung bleibt eine explizite Freigabe.

## Diagnose

Die Diagnose trennt Datenstatus, Plan, konkrete Regelblockierungen und den letzten Real-Automatiklauf. Audit und Export liefern den nachvollziehbaren Nachweis.
