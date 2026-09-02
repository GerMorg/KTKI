import ast
import os
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/'app'

class V78RegressionTests(unittest.TestCase):
 def test_runtime_shell_is_v78(self):
  run=(ROOT/'run.sh').read_text(encoding='utf-8');runtime=(APP/'v78_main.py').read_text(encoding='utf-8')
  self.assertIn('v78_main:app',run)
  self.assertIn("app.view_functions['index'] = _dashboard",runtime)
  self.assertIn("@app.get('/v78-health')",runtime)

 def test_gui_root_is_defensive(self):
  source=(APP/'v78_main.py').read_text(encoding='utf-8')
  self.assertIn('def _safe(fn, default=None):',source)
  self.assertIn('portfolio, public, private, research = _status_snapshot()',source)
  self.assertIn('render_template(html',source)
  self.assertNotIn('url_for(',source.split("def _dashboard():",1)[1].split("# Replace",1)[0])

 def test_analysis_has_candidate_recovery(self):
  source=(APP/'research_pipeline.py').read_text(encoding='utf-8')
  self.assertIn('def _recover_watchlist',source)
  self.assertIn('symbols=list(self.prefilter.candidates() or [])',source)
  self.assertIn('if not symbols:',source)
  self.assertIn('symbols=self._recover_watchlist',source)
  self.assertIn("'candidate_count':len(symbols)",source)

 def test_universe_defaults_have_categories(self):
  source=(APP/'market_universe.py').read_text(encoding='utf-8')
  self.assertIn("VALUES(?,?,1,?)",source)
  self.assertIn('return enabled or set(CATEGORIES)',source)

 def test_all_v78_runtime_sources_parse(self):
  for name in ('v78_main.py','v77_main.py','v76_main.py','research_pipeline.py','market_universe.py','scanner.py','prefilter.py','ws_private.py','portfolio_sync.py'):
   ast.parse((APP/name).read_text(encoding='utf-8'),filename=name)

 def test_root_can_be_smoke_imported_without_network_feeds(self):
  old=os.environ.get('APP_DISABLE_WEBSOCKETS')
  old_data=os.environ.get('APP_DATA_DIR')
  os.environ['APP_DISABLE_WEBSOCKETS']='1'
  os.environ['APP_DATA_DIR']='/tmp/kraken-trader-v78-test'
  try:
   import importlib
   import sys
   sys.modules.pop('v78_main',None)
   mod=importlib.import_module('v78_main')
   client=mod.app.test_client()
   response=client.get('/')
   self.assertEqual(response.status_code,200)
   self.assertIn(b'Kraken Trader',response.data)
  finally:
   if old is None: os.environ.pop('APP_DISABLE_WEBSOCKETS',None)
   else: os.environ['APP_DISABLE_WEBSOCKETS']=old
   if old_data is None: os.environ.pop('APP_DATA_DIR',None)
   else: os.environ['APP_DATA_DIR']=old_data

if __name__=='__main__': unittest.main()
