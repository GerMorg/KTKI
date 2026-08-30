import sys
sys.path.insert(0,'kraken_trader/app')
from autonomous_portfolio_v65 import AssetView,Holding,DecisionPolicy,AutonomousPortfolioEngine,DigitalTwin

def test_target_weights_respect_cash_and_position_cap():
 e=AutonomousPortfolioEngine(DecisionPolicy(cash_reserve_pct=20,max_position_pct=5))
 w=e.target_weights([AssetView('A',90,10,5),AssetView('B',80,8,10)])
 assert sum(w.values())<=80.000001
 assert all(x<=5.000001 for x in w.values())

def test_low_score_is_not_traded():
 e=AutonomousPortfolioEngine(DecisionPolicy())
 assert e.target_weights([AssetView('A',99,-2,5)])=={}

def test_no_trade_band_and_action_limit():
 p=DecisionPolicy(cash_reserve_pct=0,max_position_pct=50,no_trade_band_pct=2,min_trade_eur=1,max_trade_eur=100,max_actions=1,minimum_score=0)
 e=AutonomousPortfolioEngine(p)
 plan=e.rebalance(1000,[Holding('A',490)], [AssetView('A',1,10,1),AssetView('B',1,9,1)])
 assert plan['action_count']<=1

def test_usd_buy_requires_fx_rate():
 p=DecisionPolicy(cash_reserve_pct=0,max_position_pct=100,min_trade_eur=1,max_trade_eur=1000,minimum_score=0)
 e=AutonomousPortfolioEngine(p)
 plan=e.rebalance(1000,[],[AssetView('USD_ASSET',1,10,1,'USD')]);plan['assets']=[{'symbol':'USD_ASSET','currency':'USD'}]
 r=DigitalTwin(p).execute(plan,1000)
 assert r['status']=='BLOCKED_FX_RATE_MISSING'

def test_usd_path_charges_fx_and_trade_costs():
 p=DecisionPolicy(cash_reserve_pct=0,max_position_pct=100,min_trade_eur=1,max_trade_eur=1000,minimum_score=0,fx_fee_bps=10,trading_fee_bps=40,slippage_bps=10)
 e=AutonomousPortfolioEngine(p);plan=e.rebalance(1000,[],[AssetView('USD_ASSET',1,10,1,'USD')]);plan['assets']=[{'symbol':'USD_ASSET','currency':'USD'}]
 r=DigitalTwin(p).execute(plan,1000,fx_rate_eur_per_usd=.85)
 assert r['status']=='SIMULATED' and r['fx_cost_eur']>0 and r['trade_cost_eur']>0

def test_serializable_dataclass():
 assert DigitalTwin.serializable(DecisionPolicy())['cash_reserve_pct']==20
