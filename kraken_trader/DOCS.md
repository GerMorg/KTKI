# Kraken Trader 0.1.0-dev.17

## Aktien und xStocks
Aktien/xStocks werden als `tokenized_asset` geladen. EUR- und USD-Paare dürfen in Universum, Research und öffentlichem Tickerstream erscheinen. USD-Positionen benötigen einen aktuellen EUR/USD-Kurs für die EUR-Bewertung; fehlt dieser, handelt die Paper-Engine fail-closed.

## Dynamische Paper-Allokation
Zielpositionen berücksichtigen Konfidenz, Volatilität, minimale und maximale Positionsquote sowie minimale und maximale Transfergröße. Kleine Abweichungen bleiben im No-Trade-Band. Eine schwächere Position wird nur zur Finanzierung verkauft, wenn der Konfidenzvorteil den eingestellten Mindestwert und die geschätzten Rundlaufkosten übersteigt.

## Dynamischer Paper-Hebel
Der Hebel ist standardmäßig aus. Nach Aktivierung wählt die Engine ausschließlich Werte aus `leverage_buy` des konkreten Kraken-Marktes und begrenzt sie durch `paper_max_leverage`. Geliehener Paper-Betrag wird separat gespeichert und bei der Eigenkapitalberechnung abgezogen.

## GDELT
Ein TLS-Handshake-Timeout setzt die betroffene GDELT-Quelle für sechs Stunden auf `DEGRADED TLS COOLDOWN`. Andere Quellen laufen weiter.

## Realausführung
`real_execution_adapter.py` definiert nur eine zukünftige Validierungsgrenze. `execute()` ist absichtlich hart deaktiviert; es gibt weiterhin keinen Kraken-Ordertransport.

## Externe KI-Nachrichtenanalyse
Die Funktion ist standardmäßig aus. Unterstützt werden OpenAI und Azure OpenAI über strukturierte Ausgaben. Übermittelt werden nur Feed-Quelle, Titel, Kurzbeschreibung, Veröffentlichungszeit und URL; Zielseiten werden nicht automatisiert kopiert oder gecrawlt.

Die Antwort muss dem versionierten Schema entsprechen: Relevanz, Stimmung, erwartete Wirkung, Zeithorizont, Konfidenz, Faktenstatus, mutmaßliche Einpreisung, Themen, betroffene Assets, Kurzbegründung und Gegenargumente. Ungültige Antworten werden als ERROR gespeichert und nicht verwendet. Der KI-Faktor ist auf 25 Prozent begrenzt und zusätzlich mit der KI-Konfidenz gewichtet.

Optionen: `ai_news_enabled`, `ai_provider`, `ai_endpoint`, `ai_model`, `ai_api_key`, `ai_max_items_per_run`, `ai_timeout_seconds`. Der Schlüssel wird nicht in SQLite, Audit oder Export gespeichert.
