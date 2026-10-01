## v101 Runtime-Korrektur

`core_runtime.py` enthält die zentrale Initialisierung. Das Alias `legacy` verweist explizit auf dieses Modul, damit v101 die bestehenden Fachkomponenten ohne versionierte Runtime-Kette nutzen kann. `run.sh` startet ausschließlich `v101_main:app`.

# Datei-Audit · v100

Der aktive Runtimebaum wurde von den historischen v67-v99-Wrappern bereinigt. Die folgenden Dateien bilden den aktuellen Kern.

| Datei | Status |
|---|---|
| kraken_trader/app/v100_main.py | aktiver Runtime-/GUI-Einstieg |
| kraken_trader/app/core_runtime.py | gemeinsamer Core ohne alte GUI-/Scheduler-Einstiegspfade |
| kraken_trader/app/real_state_v100.py | einzige Real-State-Quelle für aktuelle GUI |
| kraken_trader/app/decision_pipeline_v98.py | kanonischer Entscheidungsplan |
| kraken_trader/app/v98_paper_engine.py | aktueller Paper-Ausführungsadapter |
| kraken_trader/app/v98_real_allocator.py | aktueller Real-Ausführungsadapter |
| kraken_trader/app/real_trade.py | Kraken RealTradeEngine und explizite Live-Freigabe |
| kraken_trader/app/templates/base.html | zentraler GUI-Rahmen |
| kraken_trader/config.yaml | aktuelle Home-Assistant-Konfiguration |
| kraken_trader/run.sh | startet ausschließlich v100_main:app |
| kraken_trader/app/version.py | zentrale Version 0.1.0-dev.100 |
| kraken_trader/tests/test_v100_repairs.py | v100-Konsolidierungsregressionen |

Historische Reviews und Releasebeschreibungen sind Archivmaterial und nicht Teil des aktiven Runtimepfads.
