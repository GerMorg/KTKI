# Architektur · v103

v103_main.py bildet den aktuellen GUI-/Prozessrahmen. Paper und Real verwenden weiterhin den gemeinsamen kanonischen Planner und Execution Intent. Paper persistiert Simulationsfills unabhängig von nachgelagerter Snapshot-/Guard-Buchhaltung; Real wird im letzten Schritt über explizite HA-Automatikgates, Kill-Switch, Kontostand, Limits und Kraken-Preflight zur Übermittlung freigegeben.

## Aktiver Ablauf

1. Marktdaten und Nachrichten erfassen.
2. Datenqualität, Analyse, Prognose- und Lernnachweise prüfen.
3. Kanonischen Plan mit Targets, Current, Edge, Kosten und Regime erzeugen.
4. Shared Execution Intent für Richtung, Paar, Notional, Mode und Leverage erzeugen.
5. Paper simuliert und persistiert den Fill; Real prüft zusätzlich Kontostand, Kill-Switch, Freigabe, Limits und Kraken-Preflight.
6. Audit, Portfolio-Snapshot und Nachkontrolle speichern das Ergebnis.

# Architektur · v102

v102 trennt drei Ebenen: `core_runtime.py` stellt die gemeinsamen Fachobjekte bereit, `market_feed_v102.py` ist die einzige öffentliche Kraken-Market-Schnittstelle, und `v102_main.py` bildet ausschließlich den aktuellen GUI-/Prozessrahmen. Paper und Real verwenden weiterhin den gemeinsamen kanonischen Planner und Execution Intent.

# Architektur · v101

kraken_trader/app/v101_main.py ist der einzige aktive GUI-/Runtime-Einstiegspunkt. kraken_trader/app/core_runtime.py stellt die gemeinsamen Daten- und Fachobjekte bereit; die kanonische Entscheidungsstrecke baut einen Plan, daraus einen gemeinsamen Execution Intent und trennt erst am letzten Schritt Paper von Real.

## Aktiver Ablauf

1. Marktdaten und Nachrichten erfassen.
2. Datenqualität, Analyse, Prognose- und Lernnachweise prüfen.
3. Kanonischen Plan mit Targets, Current, Edge, Kosten und Regime erzeugen.
4. Shared Execution Intent für Richtung, Paar, Notional, Mode und Leverage erzeugen.
5. Paper simuliert; Real prüft zusätzlich Kontostand, Kill-Switch, Freigabe, Limits und Kraken-Preflight.
6. Audit, Portfolio-Snapshot und Nachkontrolle speichern das Ergebnis.

## Real-State

Alle aktuellen Oberflächen verwenden real_state_v100.build_real_state(). real_execution_disabled, real_dry_run und unabhängige alte Balancing-Schalter sind keine v101-Benutzerkonfiguration.

## Grenzen

Persistenz erfolgt über db.py. Realhandel, Paper-Handel und Lernfreigaben bleiben fachlich getrennt, nutzen aber die gemeinsame Entscheidungsbasis. Historische v67-v99 Runtime-Wrapper sind nicht Bestandteil des aktiven Programms.
