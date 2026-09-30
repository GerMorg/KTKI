"""v94 active runtime: one decision path, two execution adapters."""
import json,os
from automation_v67 import AutomationControllerV67
from controlled_learning import ControlledLearning
from news_learning import NewsLearning
import v90_main as base
from real_autonomous_v91 import RealPortfolioAllocatorV91
from v94_real_allocator import RealPortfolioAllocatorV94
from v94_paper_engine import PaperEngineV94
from decimal import Decimal as D

app=base.app
legacy=base.legacy
options=getattr(base,'options',{})

V94_DEFAULTS={
 'real_execution_confidence_spot_min':'65','real_execution_confidence_margin_2x':'78',
 'real_execution_confidence_margin_3x':'86','real_execution_confidence_margin_4x':'93',
 'real_execution_confidence_margin_5x':'97','real_execution_confidence_short_min':'75',
 'paper_cash_reserve_pct':'20'
}
def _options():
 try:
  with open(os.environ.get('APP_OPTIONS','/data/options.json'),encoding='utf-8') as f:return json.load(f) or {}
 except Exception:return {}
def install(db,opts):
 for k,v in V94_DEFAULTS.items():
  if not db.rows('SELECT value FROM settings WHERE key=?',(k,)):db.set_setting(k,str(opts.get(k,v)))
 for k in V94_DEFAULTS:
  if k in opts:db.set_setting(k,str(opts[k]))
options=_options() or options
install(legacy.db,options)
try:base.controller.stop()
except Exception:pass
allocator=RealPortfolioAllocatorV94(legacy.db,legacy.real_trade_engine)
legacy.real_allocator=allocator

def run_paper_cycle():
    return PaperEngineV94(legacy.db,start_eur=D(legacy.db.value('paper_start_eur','1000'))).run()

# Preserve the existing pipeline/news/learning order. Only the portfolio
# decision+execution stage is replaced.
controller=AutomationControllerV67(legacy.db,legacy.pipeline,legacy.news_prefilter,ControlledLearning(legacy.db),NewsLearning(legacy.db),run_paper_cycle,allocator)
controller.start_background()
base.controller=controller
legacy.controller=controller

def v94_health():
    payload=base.v90_health()
    cfg=allocator.settings()
    return {**payload,'version':'0.1.0-dev.94','runtime':'v94_main',
      'decision_engine':'DecisionEngineV94',
      'paper_real_decision_path':'IDENTICAL_DECISION_ENGINE_SEPARATE_EXECUTION_ADAPTERS',
      'economic_entry_gate':'EXPECTED_EDGE_AFTER_ALL_ROUTE_COSTS > 0',
      'model_health_role':'QUALITY_AND_SIZING_NOT_ENTRY_GATE',
      'rebalancing':'TARGET_EXPOSURE_MINUS_CURRENT_EXPOSURE',
      'existing_position_policy':'EXPLICIT_ZERO_TARGET_FOR_NO_THESIS',
      'long_short_discovery':'SYMMETRIC_BUY_AVOID_UNIVERSE',
      'news_input':'CANDIDATE_DECISION_INPUT_WHEN_AVAILABLE',
      'h24':'OPERATIONAL','h168':'ADVISORY',
      'margin_gate':'DIRECTIONAL_H24_CALIBRATION'}
if 'v94_health' not in app.view_functions:app.add_url_rule('/v94-health','v94_health',v94_health)
