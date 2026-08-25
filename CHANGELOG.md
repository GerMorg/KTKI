# Changelog
## 0.1.0-dev.17
- Basis korrekt von 0.1.0-dev.16 übernommen
- Fehlende Module `portfolio_allocator.py` und `real_execution_adapter.py` ergänzt
- Optionale externe GPT-Nachrichtenanalyse für OpenAI und Azure OpenAI
- Striktes JSON-Schema, begrenzte Kosten und fail-closed bei ungültiger Antwort
- API-Schlüssel bleibt ausschließlich in den Home-Assistant-App-Optionen
- KI beeinflusst nur den gedeckelten Research-Faktor; keine direkte Order


## 0.1.0-dev.16
- Aktien/xStocks über `tokenized_asset`
- EUR- und USD-Märkte in Universum und öffentlichem Stream
- EUR-Bewertung von USD-Produkten über EUR/USD
- GDELT-TLS-Cooldown
- dynamische Paper-Zielgewichte und Transfergrößen
- kostenbewusste Umschichtung mit No-Trade-Band
- dynamischer Paper-Hebel aus Kraken-Metadaten
- simulierte Finanzierungsschuld und Eigenkapitalberechnung
- Realausführungsadapter vorbereitet, aber hart deaktiviert

## 0.1.0-dev.15
- Robuste Nachrichtenquellen und automatischer Research-Scheduler
