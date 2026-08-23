# Kraken Trader 0.1.0-dev.11

## Scanner bei großem Marktumfang
Das vollständige Marktuniversum aktivierter Kategorien bleibt verfügbar. Der Scanner verarbeitet es rotierend in Teil-Läufen, standardmäßig zehn Märkte pro Lauf. Der Fortschritt wird als Cursor gespeichert; der nächste Lauf setzt beim folgenden Markt fort.

Unter **Einstellungen** können Paketgröße und Pause zwischen OHLC-Aufrufen angepasst werden. Der manuelle Start läuft im Hintergrund. Ein zweiter gleichzeitiger Lauf wird nicht gestartet.

## Zeichenkodierung
Quelltexte sind UTF-8-kodiert. HTML-, Text-, CSV- und JSON-Antworten deklarieren zusätzlich ausdrücklich `charset=utf-8`.
