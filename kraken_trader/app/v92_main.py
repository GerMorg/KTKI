"""v92 runtime: gated Kraken spot-margin leverage, long/short automation and directional calibration. H168 remains advisory."""
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
 'real_margin_enabled':'false','real_margin_default_leverage':'2','real_margin_max_leverage':'4',
 'real_margin_max_exposure_pct':'20','real_margin_max_free_margin_pct':'50',
 'real_margin_min_margin_level_pct':'200','real_margin_safety_buffer_pct':'20',
 'real_margin_allow_shorts':'false','real_margin_balance_asset':'ZEUR','real_execution_confidence_spot_min':'70','real_execution_confidence_margin_2x':'80','real_execution_confidence_margin_3x':'88','real_execution_confidence_margin_4x':'94','real_execution_confidence_margin_5x':'97','real_execution_confidence_short_min':'82'
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

def v92_health():
 payload=base.v90_health()
 cfg=allocator.settings()
 margin_state={}
 try:
  margin_state=legacy.real_trade_engine.refresh_margin_state() if cfg.get('margin_enabled') else {'status':'DISABLED'}
 except Exception as exc:
  margin_state={'status':'ERROR','error':type(exc).__name__}
 payload={**payload,'version':'0.1.0-dev.92','runtime':'v92_main',
  'execution_confidence':{'spot_min':str(cfg.get('confidence_spot_min')),'margin_2x':str(cfg.get('confidence_margin_2x')),'margin_3x':str(cfg.get('confidence_margin_3x')),'margin_4x':str(cfg.get('confidence_margin_4x')),'margin_5x':str(cfg.get('confidence_margin_5x')),'short_min':str(cfg.get('confidence_short_min'))},'automatic_leverage_mode':'CONFIDENCE_TIERED','margin_trading':{'enabled':cfg.get('margin_enabled',False),'default_leverage':str(cfg.get('margin_default_leverage')),'max_leverage':str(cfg.get('margin_max_leverage')),'max_exposure_pct':str(cfg.get('margin_max_exposure_pct')),'max_free_margin_pct':str(cfg.get('margin_max_free_margin_pct')),'min_margin_level_pct':str(cfg.get('margin_min_margin_level_pct')),'safety_buffer_pct':str(cfg.get('margin_safety_buffer_pct')),'allow_shorts':cfg.get('margin_allow_shorts',False),'account_state':margin_state},
  'margin_model_gate':'DIRECTIONAL_H24_CALIBRATION','margin_execution':'SPOT_MARGIN_LEVERAGE','futures_not_enabled':True,'existing_position_exit':{'enabled':True,'margin_reduce_only':True,'entry_gates_bypassed':True}}
 return payload

if 'v92_health' not in app.view_functions:app.add_url_rule('/v92-health','v92_health',v92_health)
