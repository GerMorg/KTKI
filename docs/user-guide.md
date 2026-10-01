# Benutzerhandbuch · v100

Die Oberfläche ist über Home-Assistant-Ingress erreichbar. Die aktuelle Navigation führt zu Übersicht, Analyse, Portfolio, Handel, Lernen, Diagnose, Prozess, Automatik, Realhandel und den ergänzenden Fachseiten.

## Realhandel

Der globale Realhandelsstatus wird überall aus derselben Laufzeitquelle abgeleitet. REALHANDEL FREIGEGEBEN bedeutet, dass Realhandel und automatische Real-Ausführung global aktiviert sind und der Kill-Switch frei ist. Das bedeutet noch nicht, dass jede konkrete Order ausgeführt wird: Datenqualität, Edge, Portfolio-Risiko, Limits, Balance, Kraken-Market-Regeln und weitere Gates werden pro Auftrag erneut geprüft.

Die Home-Assistant-Konfiguration verwendet keine separaten real_execution_disabled- oder real_dry_run-Schalter. Automatische Ausführung wird über real_execute_enabled in Kombination mit automation_enabled und der Realhandelsfreigabe gesteuert.

## Lernen und Nachrichten

Aktive Parameter werden nicht durch die Kandidatensuche automatisch geändert. Kandidaten müssen die bestehenden Validierungs- und Stabilitätsgates bestehen; die Aktivierung bleibt eine explizite Freigabe.

## Diagnose

Die Diagnose trennt Datenstatus, Plan, konkrete Regelblockierungen und den letzten Real-Automatiklauf. Audit und Export liefern den nachvollziehbaren Nachweis.
