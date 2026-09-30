import json
from datetime import datetime, timezone, timedelta
from db import now
from strategy_profiles import active_profile, family_for_category
from decision_pipeline_v96 import CanonicalDecisionPlannerV96


class ForecastTracker:
 def __init__(self,db):self.db=db;self.ensure()
 def ensure(self):
  with self.db.con() as c:
   c.executescript("""CREATE TABLE IF NOT EXISTS research_forecasts(id INTEGER PRIMARY KEY AUTOINCREMENT,created_at TEXT NOT NULL,symbol TEXT NOT NULL,watchlist_version_id INTEGER,model_version TEXT NOT NULL,horizon_hours INTEGER NOT NULL,direction TEXT NOT NULL,baseline_price TEXT NOT NULL,scanner_score TEXT NOT NULL,confidence TEXT NOT NULL,status TEXT NOT NULL,features_json TEXT NOT NULL);CREATE TABLE IF NOT EXISTS forecast_evaluations(forecast_id INTEGER PRIMARY KEY,evaluated_at TEXT NOT NULL,actual_price TEXT NOT NULL,actual_return_pct TEXT NOT NULL,direction_correct INTEGER NOT NULL,details_json TEXT NOT NULL);CREATE TABLE IF NOT EXISTS model_weights(version TEXT PRIMARY KEY,created_at TEXT NOT NULL,status TEXT NOT NULL,weights_json TEXT NOT NULL,parent_version TEXT,reason TEXT NOT NULL);""")
   c.execute("INSERT OR IGNORE INTO model_weights VALUES('rules-v1',?,'ACTIVE',?,NULL,'Deterministische Ausgangsgewichte')",(now(),json.dumps({'liquidity':30,'spread':35,'momentum':25,'news':10})))
   cols={x['name'] for x in self.db.rows('PRAGMA table_info(research_forecasts)')}
   for name,definition in [('family',"TEXT NOT NULL DEFAULT 'crypto_spot'"),('parameter_version','INTEGER NOT NULL DEFAULT 1'),('parameters_json',"TEXT NOT NULL DEFAULT '{}'"),('feature_schema_version',"INTEGER NOT NULL DEFAULT 1")]:
    if name not in cols:c.execute(f'ALTER TABLE research_forecasts ADD COLUMN {name} {definition}')
   cols={x['name'] for x in self.db.rows('PRAGMA table_info(forecast_evaluations)')}
   for name,definition in [('target_at','TEXT'),('price_source',"TEXT NOT NULL DEFAULT 'LIVE_FALLBACK'"),('source_open_time','INTEGER'),('timing_error_seconds','INTEGER')]:
    if name not in cols:c.execute(f'ALTER TABLE forecast_evaluations ADD COLUMN {name} {definition}')

 def _cost_snapshot(self,symbol,spread_pct):
  settings=CanonicalDecisionPlannerV96(self.db).settings()
  rows=self.db.rows("SELECT symbol,base_asset,quote_asset,source_key,ordermin,costmin,asset_class,category,canonical_id FROM market_universe WHERE symbol=? LIMIT 1",(symbol,))
  if not rows:
   return {'entry_cost_pct':999,'exit_cost_pct':999,'roundtrip_cost_pct':999,'components_pct':{},'provenance':{'status':'NO_MARKET_METADATA'}}
  row=dict(rows[0]);tickers={}
  try:
   for x in self.db.rows("SELECT symbol,last,bid,ask,received_at FROM live_prices"):
    tickers[x['symbol']]={'b':[x['bid'] or x['last']],'a':[x['ask'] or x['last']],'c':[x['last']],'received_at':x.get('received_at')}
  except Exception:
   tickers={}
  from decision_context_v95 import routes_for_symbol
  route=routes_for_symbol(self.db,symbol,tickers,settings['decision_fee_bps'],settings['decision_fx_fee_bps'],settings['decision_slippage_bps'])
  total=float(route.get('roundtrip_cost_pct') or 999)
  return {
   'entry_cost_pct':round(total/2,8),
   'exit_cost_pct':round(total/2,8),
   'roundtrip_cost_pct':round(total,8),
   'components_pct':route,
   'provenance':{'source':'CANONICAL_ROUTE_COST_V96','captured_at':now()},
  }
 def snapshot(self,symbols):
  ver=self.db.rows('SELECT id FROM watchlist_versions ORDER BY id DESC LIMIT 1');vid=ver[0]['id'] if ver else None;saved=0;failed=0
  for symbol in symbols:
   try:
    p=self.db.rows('SELECT last FROM live_prices WHERE symbol=?',(symbol,));cols={x['name'] for x in self.db.rows('PRAGMA table_info(scanner_results)')};wanted=['score','signal','quality','momentum_pct','trend_pct','volatility_pct','spread_pct','news_score'];select=','.join(x if x in cols else 'NULL AS '+x for x in wanted);s=self.db.rows('SELECT '+select+' FROM scanner_results WHERE symbol=?',(symbol,))
    try:u=self.db.rows('SELECT category FROM market_universe WHERE symbol=? LIMIT 1',(symbol,))
    except Exception:u=[]
    if not p or not s or s[0]['quality']!='VALID':continue
    family=family_for_category(u[0]['category'] if u else 'crypto_spot');version,parameters=active_profile(self.db,family);features={k:s[0].get(k) for k in ('momentum_pct','trend_pct','volatility_pct','spread_pct')};costs=self._cost_snapshot(symbol,float(s[0].get('spread_pct') or 0));features.update({'schema_version':4,'entry_cost_pct':costs['entry_cost_pct'],'exit_cost_pct':costs['exit_cost_pct'],'estimated_roundtrip_cost_pct':costs['roundtrip_cost_pct'],'cost_components_pct':costs['components_pct'],'cost_provenance':costs['provenance']})
    direction='UP' if s[0]['signal']=='BUY' else ('DOWN' if s[0]['signal']=='AVOID' and float(s[0].get('momentum_pct') or 0)<0 and float(s[0].get('trend_pct') or 0)<0 else 'FLAT');confidence=str(min(1,max(0,float(s[0]['score'])/100)));model=f'{family}-controlled-v{version}'
    with self.db.con() as c:
     for h in (24,168):
      c.execute('INSERT INTO research_forecasts(created_at,symbol,watchlist_version_id,model_version,horizon_hours,direction,baseline_price,scanner_score,confidence,status,features_json,family,parameter_version,parameters_json,feature_schema_version) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(now(),symbol,vid,model,h,direction,p[0]['last'],s[0]['score'],confidence,'OPEN',json.dumps(features,sort_keys=True),family,version,json.dumps(parameters,sort_keys=True),4));saved+=1
   except Exception as exc:
    failed+=1
    self.db.audit('FORECAST_SNAPSHOT_SYMBOL_FAILED',json.dumps({'symbol':symbol,'error':type(exc).__name__+': '+str(exc)[:500]},sort_keys=True),'error')
  self.db.audit('FORECAST_SNAPSHOT_COMPLETED',json.dumps({'requested_symbols':len(symbols),'saved':saved,'failed_symbols':failed},sort_keys=True),'warning' if failed else 'info')
  return saved

 def _target_candle(self,symbol,target,current):
  target_ts=int(target.timestamp());current_ts=int(current.timestamp())
  rows=self.db.rows(
   'SELECT open_time,close,interval_min FROM ohlc_cache '
   'WHERE symbol=? AND open_time+interval_min*60<=? AND open_time+interval_min*60<=? '
   'ORDER BY open_time DESC LIMIT 1',
   (symbol,current_ts,target_ts)
  )
  if rows:return rows[0]
  # Only when no fully completed candle exists at/before target do we use the
  # first fully completed candle after target, and record the positive timing error.
  rows=self.db.rows(
   'SELECT open_time,close,interval_min FROM ohlc_cache '
   'WHERE symbol=? AND open_time>=? AND open_time+interval_min*60<=? '
   'ORDER BY open_time ASC LIMIT 1',
   (symbol,target_ts,current_ts)
  )
  return rows[0] if rows else None

 def evaluate_due(self):
  rows=self.db.rows("SELECT * FROM research_forecasts WHERE status='OPEN'");done=0;failed=0;current=datetime.now(timezone.utc)
  for f in rows:
   try:
    target=datetime.fromisoformat(f['created_at'])+timedelta(hours=f['horizon_hours'])
    if current<target:continue
    candle=self._target_candle(f['symbol'],target,current)
    if not candle:continue
    base=float(f['baseline_price']);actual=float(candle['close']);ret=(actual/base-1)*100 if base else 0
    try:features=json.loads(f.get('features_json') or '{}')
    except Exception:features={}
    cost=float(features.get('estimated_roundtrip_cost_pct') or 0)
    correct=(f['direction']=='UP' and ret>cost) or (f['direction']=='DOWN' and ret < -cost) or (f['direction']=='FLAT' and abs(ret)<=cost)
    source_time=int(candle['open_time']);timing_error=source_time-int(target.timestamp())
    details={'direction':f['direction'],'family':f.get('family'),'parameter_version':f.get('parameter_version'),'target_at':target.isoformat(),'price_source':'OHLC_CACHE_LAST_CLOSED_AT_OR_BEFORE_TARGET_WITH_AFTER_TARGET_FALLBACK','source_open_time':source_time,'interval_min':int(candle['interval_min']),'timing_error_seconds':timing_error,'roundtrip_cost_pct':cost,'cost_adjusted_return_pct':ret-cost if f['direction']=='UP' else (-ret-cost if f['direction']=='DOWN' else 0.0)}
    with self.db.con() as c:
     c.execute('INSERT OR REPLACE INTO forecast_evaluations(forecast_id,evaluated_at,actual_price,actual_return_pct,direction_correct,details_json,target_at,price_source,source_open_time,timing_error_seconds) VALUES(?,?,?,?,?,?,?,?,?,?)',(f['id'],now(),str(actual),str(ret),1 if correct else 0,json.dumps(details,sort_keys=True),target.isoformat(),details['price_source'],source_time,timing_error));c.execute("UPDATE research_forecasts SET status='EVALUATED' WHERE id=?",(f['id'],));done+=1
   except Exception as exc:
    failed+=1
    self.db.audit('FORECAST_EVALUATION_FAILED',json.dumps({'forecast_id':f.get('id'),'symbol':f.get('symbol'),'horizon_hours':f.get('horizon_hours'),'error':type(exc).__name__+': '+str(exc)[:500]},sort_keys=True),'error')
  if failed:self.db.audit('FORECAST_EVALUATION_COMPLETED_WITH_ERRORS',json.dumps({'evaluated':done,'failed':failed},sort_keys=True),'warning')
  return done
