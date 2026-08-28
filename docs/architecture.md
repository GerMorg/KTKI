# Architektur

`kraken_trader/app` enthält die Python-Fachmodule. `kraken_trader/app/templates` und `kraken_trader/app/static` enthalten die zentralen GUI-Ressourcen. Die Tests liegen ausschließlich unter `kraken_trader/tests`.

## Grenzen

- Flask-Routen koordinieren Eingaben und Ausgaben.
- Fachlogik liegt in spezialisierten Modulen.
- Persistenz erfolgt über `db.py`.
- Realhandel, Paper-Handel und Lernfreigaben bleiben getrennt.
- Projektverträge und Entscheidungen liegen im Repository-Stamm und werden mit jedem Release mitgeführt.
