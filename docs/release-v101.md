# Release v101 · 2026-10-01

v101 behebt den Startabbruch nach der v100-Konsolidierung.

## Ursache

`v100_main.py` erwartete beim Import eine `legacy`-Kompatibilitätsreferenz. Nach dem Verschieben des alten Kerns nach `core_runtime.py` war dieses Modulalias nicht mehr vorhanden. Dadurch brach Gunicorn bereits beim Worker-Boot mit `AttributeError: module 'core_runtime' has no attribute 'legacy'` ab.

## Korrektur

- `core_runtime.py` exponiert sich explizit als `legacy`-Kompatibilitätsfassade.
- `options` und `controller` bleiben als stabile Runtime-Attribute verfügbar.
- `run.sh` startet ausschließlich `v101_main:app`.
- Der Tax-ZIP-Endpunkt erhält den fehlenden Flask-`Response`-Import.
- Ein echter `import v101_main`-Smoke-Test wurde in die CI-Tests aufgenommen.
