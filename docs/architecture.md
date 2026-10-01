# Architektur · v100

kraken_trader/app/v100_main.py ist der einzige aktive GUI-/Runtime-Einstiegspunkt. kraken_trader/app/core_runtime.py stellt die gemeinsamen Daten- und Fachobjekte bereit; die kanonische Entscheidungsstrecke baut einen Plan, daraus einen gemeinsamen Execution Intent und trennt erst am letzten Schritt Paper von Real.

## Aktiver Ablauf

1. Marktdaten und Nachrichten erfassen.
2. Datenqualität, Analyse, Prognose- und Lernnachweise prüfen.
3. Kanonischen Plan mit Targets, Current, Edge, Kosten und Regime erzeugen.
4. Shared Execution Intent für Richtung, Paar, Notional, Mode und Leverage erzeugen.
5. Paper simuliert; Real prüft zusätzlich Kontostand, Kill-Switch, Freigabe, Limits und Kraken-Preflight.
6. Audit, Portfolio-Snapshot und Nachkontrolle speichern das Ergebnis.

## Real-State

Alle aktuellen Oberflächen verwenden real_state_v100.build_real_state(). real_execution_disabled, real_dry_run und unabhängige alte Balancing-Schalter sind keine v100-Benutzerkonfiguration.

## Grenzen

Persistenz erfolgt über db.py. Realhandel, Paper-Handel und Lernfreigaben bleiben fachlich getrennt, nutzen aber die gemeinsame Entscheidungsbasis. Historische v67-v99 Runtime-Wrapper sind nicht Bestandteil des aktiven Programms.
