# Entwicklung und Tests

## Lokal prüfen

```sh
cd kraken_trader
./run_tests.sh
python -m compileall -q app tests
```

## Qualitätsregeln

1. Keine bestehende Funktion ungefragt entfernen.
2. UTF-8 und LF verwenden.
3. Versionsnummern in `version.py`, `config.yaml` und `repository.yaml` synchron halten.
4. GUI-Stile nur in `app/static/style.css` pflegen.
5. Änderungen in Changelog, Testmatrix, Handover und append-only-Protokollen dokumentieren.
