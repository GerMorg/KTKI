import json
from datetime import datetime, timezone, timedelta
from db import now
from strategy_profiles import active_profile, family_for_category


class ForecastTracker:
 def __init__(self,db):self.db=db;self.ensure()
 def ensure(self):
  with self.db.con() as c:
   c.executescript("""CREATE TABLE IF NOT EXISTS research_forecasts(id INTEGER PRIMARY KEY AUTOINCREMENT,created_at TEXT NOT NULL,symbol TEXT NOT NULL,watchlist_version_id INTEGER,model_version TEXT NOT NULL,horizon_hours INTEGER NOT NULL,direction TEXT NOT NULL,baseline_price TEXT NOT NULL,scanner_score TEXT NOT NULL,confidence TEXT NOT NULL,status TEXT NOT NULL,features_json TEXT NOT NULL);CREATE TABLE IF NOT EXISTS forecast_evaluations(forecast_id INTEGER PRIMARY KEY,evaluated_at TEXT NOT NULL,actual_price TEXT NOT NULL,actual_return_pct TEXT NOT NULL,direction_correct INTEGER NOT NULL,details_json TEXT NOT NULL);CREATE TABLE IF NOT EXISTS model_weights(version TEXT PRIMARY KEY,created_at TEXT NOT NULL,status TEXT NOT NULL,weights_json TEXT NOT NULL,parent_version TEXT,reason TEXT NOT NULL);""")
   c.execute("INSERT OR IGNORE INTO model_weights VALUES('rules-v1',?,'ACTIVE',?,NULL,'Deterministische Ausgangsgewichte')",(now(),json.dumps({'liquidity':30,'spread':35,'momentum':25,'news':10})))
   cols={x['name'] for x in self.db.rows('PRAGMA table_info(research_forecasts)')}
   for name,definition in [('family',"TEXT NOT NULL DEFAULT 'crypto_spot'"),('parameter_version','INTEGER NOT NULL DEFAULT 1'),('parameters_json',"TEXT NOT NULL DEFAULT '{}'"),('feature_schema_version','INTEGER NOT NULL DEFAULT 1')]:
    if name not in cols:c.execute(f'ALTER TABLE research_forecasts ADD COLUMN {name} {definition}')
   cols={x['name'] for x in self.db.rows('PRAGMA table_info(forecast_evaluations)')}
   for name,definition in [('target_at','TEXT'),('price_source',"TEXT NOT NULL DEFAULT 'LIVE_FALLBACK'"),('source_open_time','INTEGER'),('timing_error_seconds','INTEGER')]:
    if name not in cols:c.execute(f'ALTER TABLE forecast_evaluations ADD COLUMN {name} {definition}')

 def _cost_snapshot(self,symbol,spread_pct):
  fee_bps=float(self.db.value('paper_fee_bps','40'));fee_source='CONFIG';fee_effective_at=None
  try:
   fee=self.db.rows('SELECT taker_bps,source,effective_at FROM account_pair_fees WHERE symbol=?',(symbol,))
   if fee:fee_bps=float(fee[0]['taker_bps']);fee_source=fee[0]['source'];fee_effective_at=fee[0]['effective_at']
  except Exception:pass
  trade_fee=fee_bps/10000;slippage=float(self.db.value('paper_slippage_bps','10'))/10000
  fx_required=symbol.endswith('/USD');fx_fee=float(self.db.value('paper_fx_fee_bps','10'))/10000 if fx_required else 0.0;fx_spread=0.0
  if fx_required:
   fx=self.db.rows("SELECT bid,ask,last,received_at FROM live_prices WHERE symbol='EUR/USD'")
   if fx:
    bid=float(fx[0].get('bid') or fx[0].get('last') or 0);ask=float(fx[0].get('ask') or fx[0].get('last') or 0);mid=(bid+ask)/2
    fx_spread=(ask-bid)/mid if mid and ask>=bid else 0.0
  entry={'product_spread':spread_pct/2,'trade_fee':trade_fee*100,'slippage':slippage*100,'fx_spread':fx_spread/2*100,'fx_fee':fx_fee*100}
  exit_cost=dict(entry);entry_total=sum(entry.values());exit_total=sum(exit_cost.values());roundtrip=entry_total+exit_total
  return {'entry_cost_pct':round(entry_total,8),'exit_cost_pct':round(exit_total,8),'roundtrip_cost_pct':round(roundtrip,8),'components_pct':{'entry':entry,'exit':exit_cost},'provenance':{'trade_fee_source':fee_source,'trade_fee_effective_at':fee_effective_at,'trade_fee_bps':fee_bps,'fx_required':fx_required,'captured_at':now()}}

 def snapshot(self,symbols):
  ver=self.db.rows('SELECT id FROM watchlist_versions ORDER BY id DESC LIMIT 1');vid=ver[0]['id'] if ver else None;saved=0
  with self.db.con() as c:
   for symbol in symbols:
    p=self.db.rows('SELECT last FROM live_prices WHERE symbol=?',(symbol,));cols={x['name'] for x in self.db.rows('PRAGMA table_info(scanner_results)')};wanted=['score','signal','quality','momentum_pct','trend_pct','volatility_pct','spread_pct'];select=','.join(x if x in cols else 'NULL AS '+x for x in wanted);s=self.db.rows('SELECT '+select+' FROM scanner_results WHERE symbol=?',(symbol,))
    try:u=self.db.rows('SELECT category FROM market_universe WHERE symbol=? LIMIT 1',(symbol,))
    except Exception:u=[]
    if not p or not s or s[0]['quality']!='VALID':continue
    family=family_for_category(u[0]['category'] if u else 'crypto_spot');version,parameters=active_profile(self.db,family);features={k:s[0].get(k) for k in ('momentum_pct','trend_pct','volatility_pct','spread_pct')};costs=self._cost_snapshot(symbol,float(s[0].get('spread_pct') or 0));features.update({'schema_version':4,'entry_cost_pct':costs['entry_cost_pct'],'exit_cost_pct':costs['exit_cost_pct'],'estimated_roundtrip_cost_pct':costs['roundtrip_cost_pct'],'cost_components_pct':costs['components_pct'],'cost_provenance':costs['provenance']})
    # AVOID means "do not take a long position"; it is not a forecast of a
    # negative return.  Treating it as DOWN contaminated model evaluation.
    direction='UP' if s[0]['signal']=='BUY' else 'FLAT';confidence=str(min(1,max(0,float(s[0]['score'])/100)));model=f'{family}-controlled-v{version}'
    for h in (24,168):
     c.execute('INSERT INTO research_forecasts(created_at,symbol,watchlist_version_id,model_version,horizon_hours,direction,baseline_price,scanner_score,confidence,status,features_json,family,parameter_version,parameters_json,feature_schema_version) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(now(),symbol,vid,model,h,direction,p[0]['last'],s[0]['score'],confidence,'OPEN',json.dumps(features,sort_keys=True),family,version,json.dumps(parameters,sort_keys=True),4));saved+=1
  return saved

 def _target_candle(self,symbol,target,current):
  target_ts=int(target.timestamp());current_ts=int(current.timestamp())
  rows=self.db.rows('SELECT open_time,close,interval_min FROM ohlc_cache WHERE symbol=? AND open_time>=? AND open_time+interval_min*60<=? ORDER BY open_time ASC LIMIT 1',(symbol,target_ts,current_ts))
  return rows[0] if rows else None

 def evaluate_due(self):
  rows=self.db.rows("SELECT * FROM research_forecasts WHERE status='OPEN'");done=0;current=datetime.now(timezone.utc)
  for f in rows:
   target=datetime.fromisoformat(f['created_at'])+timedelta(hours=f['horizon_hours'])
   if current<target:continue
   candle=self._target_candle(f['symbol'],target,current)
   if not candle:continue
   base=float(f['baseline_price']);actual=float(candle['close']);ret=(actual/base-1)*100 if base else 0
   try:features=json.loads(f.get('features_json') or '{}')
   except Exception:features={}
   cost=float(features.get('estimated_roundtrip_cost_pct') or 0)
   correct=(f['direction']=='UP' and ret>cost) or (f['direction']=='FLAT' and abs(ret)<=cost)
   source_time=int(candle['open_time']);timing_error=source_time-int(target.timestamp())
   details={'direction':f['direction'],'family':f.get('family'),'parameter_version':f.get('parameter_version'),'target_at':target.isoformat(),'price_source':'OHLC_CACHE_FIRST_CLOSED_AT_OR_AFTER_TARGET','source_open_time':source_time,'interval_min':int(candle['interval_min']),'timing_error_seconds':timing_error,'roundtrip_cost_pct':cost,'cost_adjusted_return_pct':ret-cost if f['direction']=='UP' else 0.0}
   with self.db.con() as c:
    c.execute('INSERT OR REPLACE INTO forecast_evaluations(forecast_id,evaluated_at,actual_price,actual_return_pct,direction_correct,details_json,target_at,price_source,source_open_time,timing_error_seconds) VALUES(?,?,?,?,?,?,?,?,?,?)',(f['id'],now(),str(actual),str(ret),1 if correct else 0,json.dumps(details,sort_keys=True),target.isoformat(),details['price_source'],source_time,timing_error));c.execute("UPDATE research_forecasts SET status='EVALUATED' WHERE id=?",(f['id'],));done+=1
  return done
