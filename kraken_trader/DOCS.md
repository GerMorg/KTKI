# Kraken Trader 0.1.0-dev.13

## Nachrichtenarchitektur
GDELT sorgt für breite internationale Themenabdeckung. EZB und Federal Reserve liefern geldpolitische Primärmeldungen. Der Kraken-Feed ergänzt börsen- und produktspezifische Ereignisse. Gespeichert werden Überschrift, Kurzbeschreibung, URL, Quelle, Veröffentlichungs- und Abrufzeit sowie Taxonomie.

Reuters wurde nicht fest eingebaut, weil für den Repository-Stand kein lizenzierter Reuters-Zugang vorausgesetzt werden darf. Die Quellenarchitektur bleibt erweiterbar.

## Taxonomie
Nachrichten werden deterministisch unter anderem Geldpolitik, Inflation, Wachstum, Arbeitsmarkt, Regulierung, Geopolitik, Unternehmenszahlen, Produkt-Ereignisse, Sicherheit und Kapitalflüssen zugeordnet. Ereignistypen unterscheiden politische, überraschende, geplante und strukturelle Meldungen.

## Watchlist und Prognosen
Jeder Vorfilterlauf erzeugt eine unveränderliche Watchlist-Version. Nach valider Detailanalyse werden Prognosesnapshots für 24 Stunden und 168 Stunden gespeichert. Nach Ablauf wird die Richtung mit dem dann vorhandenen realen Marktpreis verglichen. Modellgewichte sind versioniert; automatische Änderungen sind nicht aktiviert.

Nachrichten erhöhen oder senken nur die Research-Priorität. Sie können keine Paper- oder Realorder auslösen.
