import unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
from autonomous_orchestrator_v66 import AutonomousOrchestratorV66, ModelInput

class Matrix:
 def evaluate(self,symbol,action,context,trade_context):
  if trade_context=='REAL' and not context['real_trading_enabled']:
   return {'allowed':False,'blocker':'Realhandel deaktiviert','checks':[]}
  return {'allowed':True,'blocker':'Alle Regeln erfüllt','checks':[]}

class V66IntegrationTests(unittest.TestCase):
 def setUp(self): self.o=AutonomousOrchestratorV66(decision_matrix=Matrix())
 def model(self,currency='EUR',status='VALID',symbol=None):
  symbol=symbol or ('BTC/USD' if currency=='USD' else 'BTC/EUR')
  return ModelInput('model-v66',True,2.0,10.0,.9,status,[{'symbol':symbol,'score':90,'expected_return_pct':2.0,'volatility_pct':10.0,'currency':currency}])
 def test_validation_status_is_required(self):
  r=self.o.decide([self.model(status='NOT_ROBUST')],{'total_eur':1000,'holdings':[],'data_fresh':True})
  self.assertEqual(r.status,'BLOCKED')
 def test_real_gate_stays_closed(self):
  r=self.o.decide([self.model()],{'total_eur':1000,'holdings':[],'data_fresh':True,'eur_balance':1000},route_options={'BTC/EUR':[{'symbol':'BTC/EUR','quote_asset':'EUR'}]},tickers={'BTC/EUR':{'b':['50000'],'a':['50010'],'c':['50005']}},trade_context='REAL')
  self.assertEqual(r.status,'BLOCKED')
 def test_end_to_end_digital_twin(self):
  r=self.o.decide([self.model()],{'total_eur':1000,'holdings':[],'data_fresh':True,'eur_balance':1000},route_options={'BTC/EUR':[{'symbol':'BTC/EUR','quote_asset':'EUR'}]},tickers={'BTC/EUR':{'b':['50000'],'a':['50010'],'c':['50005']}})
  self.assertEqual(r.status,'READY');self.assertEqual(r.twin['status'],'SIMULATED')
 def test_usd_requires_fx(self):
  r=self.o.decide([self.model('USD')],{'total_eur':1000,'holdings':[],'data_fresh':True,'eur_balance':1000},route_options={'BTC/USD':[{'symbol':'BTC/USD','quote_asset':'USD'}]},tickers={'BTC/USD':{'b':['50000'],'a':['50010'],'c':['50005']}})
  self.assertEqual(r.status,'BLOCKED')
if __name__=='__main__': unittest.main()
