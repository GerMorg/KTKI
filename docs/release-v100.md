# Release v100 · 2026-10-01

v100 konsolidiert die aktive Runtime- und GUI-Struktur. Es gibt nur noch einen ausgelieferten Einstiegspunkt: v100_main:app.

Der globale Realhandelsstatus wird nicht mehr aus verschiedenen historischen GUI-Schichten zusammengesetzt. Übersicht, Automatik, Realhandel und Health verwenden dieselbe Real-State-Quelle. Die alten Benutzerbegriffe real_execution_disabled und real_dry_run sind keine v100-Konfiguration mehr.

Die Home-Assistant-Konfiguration enthält nur die bewusst notwendigen Schalter. Alte versionierte Runtime-Wrapper und nicht mehr benötigte GUI-Routen wurden aus dem aktiven Programmbaum gelöscht. Historische Tests, die ausschließlich die Existenz dieser Wrapper absicherten, wurden entfernt; fachlich relevante Regressionen bleiben erhalten oder wurden auf v100 ausgerichtet.

Der Health-Endpunkt /health verwendet ebenfalls den zentralen v100-Real-State und berichtet Runtime-Version, manuelle Realfreigabe und automatische Real-Ausführung getrennt.
