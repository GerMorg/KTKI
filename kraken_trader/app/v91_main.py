"""v91 runtime: gated Kraken spot-margin leverage, long/short automation and directional calibration. H168 remains advisory."""
import json,os
from automation_v67 import AutomationControllerV67
from controlled_learning import ControlledLearning
from news_learning import NewsLearning
import v90_main as base
from real_autonomous_v91 import RealPortfolioAllocatorV91

app=base.app
legacy=base.legacy
options=getattr(base,'options',{})

MARGIN_DEFAULTS={
 'real_margin_enabled':'false','real_margin_default_leverage':'2','real_margin_max_leverage':'3',
 'real_margin_max_exposure_pct':'20','real_margin_max_free_margin_pct':'50',
 'real_margin_min_margin_level_pct':'200','real_margin_safety_buffer_pct':'20',
 'real_margin_allow_shorts':'false','real_margin_balance_asset':'ZEUR'
}

def _options():
 path=os.environ.get('APP_OPTIONS','/data/options.json')
 try:
  with open(path,encoding='utf-8') as fh:return json.load(fh) or {}
 except (OSError,ValueError,TypeError):return {}

def install_margin_settings(db,opts):
 for key,default in MARGIN_DEFAULTS.items():
  if not db.rows('SELECT value FROM settings WHERE key=?',(key,)):db.set_setting(key,str(opts.get(key,default)).lower() if isinstance(opts.get(key,default),bool) else str(opts.get(key,default)))
 for key in MARGIN_DEFAULTS:
  if key in opts:
   value=opts[key];db.set_setting(key,'true' if value is True else 'false' if value is False else str(value))

options=_options() or options
install_margin_settings(legacy.db,options)
try:base.controller.stop()
except Exception:pass
allocator=RealPortfolioAllocatorV91(legacy.db,legacy.real_trade_engine)
legacy.real_allocator=allocator
controller=AutomationControllerV67(legacy.db,legacy.pipeline,legacy.news_prefilter,ControlledLearning(legacy.db),NewsLearning(legacy.db),legacy.run_paper_cycle,allocator)
controller.start_background()
base.controller=controller
legacy.controller=controller

def v91_health():
 payload=base.v90_health()
 cfg=allocator.settings()
 margin_state={}
 try:
  margin_state=legacy.real_trade_engine.refresh_margin_state() if cfg.get('margin_enabled') else {'status':'DISABLED'}
 except Exception as exc:
  margin_state={'status':'ERROR','error':type(exc).__name__}
 payload={**payload,'version':'0.1.0-dev.91','runtime':'v91_main',
  'margin_trading':{'enabled':cfg.get('margin_enabled',False),'default_leverage':str(cfg.get('margin_default_leverage')),'max_leverage':str(cfg.get('margin_max_leverage')),'max_exposure_pct':str(cfg.get('margin_max_exposure_pct')),'max_free_margin_pct':str(cfg.get('margin_max_free_margin_pct')),'min_margin_level_pct':str(cfg.get('margin_min_margin_level_pct')),'safety_buffer_pct':str(cfg.get('margin_safety_buffer_pct')),'allow_shorts':cfg.get('margin_allow_shorts',False),'account_state':margin_state},
  'margin_model_gate':'DIRECTIONAL_H24_CALIBRATION','margin_execution':'SPOT_MARGIN_LEVERAGE','futures_not_enabled':True}
 return payload

if 'v91_health' not in app.view_functions:app.add_url_rule('/v91-health','v91_health',v91_health)
