import os,sys,unittest
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'..','app'))
from execution_router import choose_route
from portfolio_target import build_targets
from strategy_profiles import score_features

class V60RoutingTests(unittest.TestCase):
 def setUp(self):
  self.tickers={'BTC/EUR':{'b':['90000'],'a':['90010'],'c':['90005']},'BTC/USD':{'b':['99000'],'a':['99010'],'c':['99005']},'EUR/USD':{'b':['1.0800'],'a':['1.0802'],'c':['1.0801']}}
 def test_eur_route_wins_when_fx_is_more_expensive(self):
  alts=[{'symbol':'BTC/EUR','quote_asset':'EUR'},{'symbol':'BTC/USD','quote_asset':'USD'}]
  selected,details=choose_route(alts,self.tickers,1000,40,10,10)
  self.assertEqual(selected['symbol'],'BTC/EUR');self.assertTrue(details['selected']['total_cost_eur']>=0)
 def test_usd_route_requires_eurusd(self):
  alts=[{'symbol':'BTC/USD','quote_asset':'USD'}]
  selected,details=choose_route(alts,{'BTC/USD':self.tickers['BTC/USD']},1000,40,10,10)
  self.assertIsNone(selected);self.assertEqual(details['status'],'NO_VALID_ROUTE')
 def test_usd_route_reports_fx_cost_separately(self):
  alts=[{'symbol':'BTC/USD','quote_asset':'USD'}]
  selected,details=choose_route(alts,self.tickers,1000,40,10,10)
  self.assertEqual(selected['symbol'],'BTC/USD');self.assertGreater(details['selected']['fx_cost_eur'],0)

class V60PortfolioTests(unittest.TestCase):
 def test_targets_are_normalized_and_cash_reserve_is_respected(self):
  rows=[{'symbol':'A/EUR','score':80,'volatility_pct':10,'roundtrip_cost_pct':.4},{'symbol':'B/EUR','score':70,'volatility_pct':20,'roundtrip_cost_pct':.5},{'symbol':'C/EUR','score':50,'volatility_pct':5,'roundtrip_cost_pct':.2}]
  targets=build_targets(rows,1000,cash_reserve_pct=20,max_position_pct=50,buy_threshold=62,min_target_eur=20)
  self.assertTrue(targets);self.assertLessEqual(sum(float(x['target_exposure_eur']) for x in targets),800.0001);self.assertTrue(all(float(x['target_exposure_eur'])<=500.0001 for x in targets))

class V60ModelTests(unittest.TestCase):
 def test_avoid_is_not_a_bearish_forecast(self):
  score,signal=score_features({'momentum_pct':-2,'trend_pct':-1,'volatility_pct':0,'spread_pct':.2,'news_score':0},{'base_score':50,'momentum_weight':4,'trend_weight':9,'volatility_penalty':1,'spread_penalty':10,'buy_threshold':64,'buy_max_spread_pct':.7,'avoid_threshold':34,'avoid_spread_pct':1.3})
  self.assertEqual(signal,'AVOID')

if __name__=='__main__':unittest.main()
