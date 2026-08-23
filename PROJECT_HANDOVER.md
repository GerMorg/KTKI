# Project Handover

## Ziel
Eine eigenstaendige Home-Assistant-App, die Kraken-Instrumente vollautomatisch analysiert, ein Musterdepot fuehrt, ein reales Portfolio auswertet und spaeter unter strengen Grenzen automatisiert handeln kann. Entscheidungen muessen erklaerbar, exportierbar und reproduzierbar sein.

## Aktueller Stand
`0.1.0-dev.1` ist bewusst ein sicherer vertikaler Schnitt: installierbare App, GUI, Persistenz, Kraken read-only, Paper-Startbestand, Audit und Konfiguration. Die Oberflaeche erlaubt keine manuellen Orders. Realhandel ist im Backend hart ausgeschaltet.

## Weiterentwicklung
Vor jeder Aenderung `PROJECT_MEMORY.yaml`, `FEATURE_CONTRACT.yaml`, `TEST_MATRIX.yaml` und die append-only Ledgers lesen. Bestehende Features beibehalten. Nach der Aenderung Tests ausfuehren und Dokumentation fortschreiben.

## Testbefehl
```bash
cd kraken_trader && python -m unittest discover -s tests -v
```
