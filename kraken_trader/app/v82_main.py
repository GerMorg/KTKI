"""v82 runtime: autonomous real execution with managed automation-secret lifecycle."""
import json,os
import v80_main as base
from real_autonomous_v81 import RealPortfolioAllocatorV81,install_real_settings,replace_controller
from automation_secret import sync_automation_secret
app=base.app
legacy=base.legacy

def _options():
    path=os.environ.get('APP_OPTIONS','/data/options.json')
    try:
        with open(path,encoding='utf-8') as fh:return json.load(fh) or {}
    except (OSError,ValueError,TypeError):return {}

options=_options()
install_real_settings(legacy.db,options)
sync_automation_secret(legacy.db,options)
allocator=RealPortfolioAllocatorV81(legacy.db,legacy.real_trade_engine)
legacy.real_allocator=allocator
controller=replace_controller(base,allocator)
base.controller=controller
legacy.NAV_ITEMS=[
 ('/','Übersicht'),('/products','Märkte & Produkte'),('/scanner','Analyse & Research'),('/portfolio','Portfolio'),
 ('/paper','Paper-Trading'),('/controlled-learning','Kontrolliertes Lernen'),('/news-learning','Nachrichten & AI'),
 ('/automatik','Automatik'),('/backtests','Evaluation & Backtests'),('/data-quality','Datenqualität'),
 ('/fees','Gebühren & Kosten'),('/process','Systemablauf'),('/real-trading','Realhandel'),
 ('/decision-matrix','Regelmatrix'),('/tax-info','Steuerinfo AT'),('/settings','Einstellungen'),
 ('/api','API & Verbindungen'),('/audit','Audit & Ereignisse')]
@app.get('/v82-health')
def v82_health():
    cfg=controller.settings()
    return {'version':'0.1.0-dev.82','runtime':'v82_main','real_trading_enabled':legacy.db.value('real_trading_enabled','false')=='true','real_kill_switch':legacy.db.value('real_kill_switch','true')=='true','real_balancing_enabled':legacy.db.value('real_balancing_enabled','false')=='true','real_balancing_execute_enabled':legacy.db.value('real_balancing_execute_enabled','false')=='true','automation_secret_configured':bool(legacy.db.value('real_balancing_automation_secret_hash','')),'automation':cfg,'recent_real_runs':controller.latest(20)}
