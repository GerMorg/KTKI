# Kraken Trader 0.1.0-dev.20

## Vorfilter
Ein Markt kann mehreren Produktgruppen angehören. Für `prefilter_results` wird er dennoch genau einmal je Lauf und Symbol gespeichert. Bei einem hebelfähigen xStock hat die Kategorie `xstocks` Vorrang vor der zusätzlichen Gruppenzuordnung `leveraged_spot`; die Hebelmetadaten bleiben erhalten.

## Aktien und xStocks
EUR- und USD-Paare bleiben zugelassen. xStocks werden als `tokenized_asset` am internationalen Ausführungsplatz geladen. Fehlende Vorfilter-Ticker dürfen als `PENDING_TICKER` in die Detailprüfung gelangen, lösen ohne valide Detailanalyse aber keinen Paper-Trade aus.

## Zeichenkodierung
Alle Python-, Markdown-, YAML- und Textdateien sind UTF-8. Ein Repository-Test prüft typische Mojibake-Marker sowie sichtbare Wörter wie „Übersicht“ und „Gebühr“.
