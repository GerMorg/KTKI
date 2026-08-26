import json
from datetime import datetime,timezone,timedelta
from db import now
from strategy_profiles import active_profile,family_for_category
class ForecastTracker:
 def __init__(self,db):self.db=db;self.ensure()
 def ensure(self):
  with self.db.con() as c:
   c.executescript("""CREATE TABLE IF NOT EXISTS research_forecasts(id INTEGER PRIMARY KEY AUTOINCREMENT,created_at TEXT NOT NULL,symbol TEXT NOT NULL,watchlist_version_id INTEGER,model_version TEXT NOT NULL,horizon_hours INTEGER NOT NULL,direction TEXT NOT NULL,baseline_price TEXT NOT NULL,scanner_score TEXT NOT NULL,confidence TEXT NOT NULL,status TEXT NOT NULL,features_json TEXT NOT NULL);CREATE TABLE IF NOT EXISTS forecast_evaluations(forecast_id INTEGER PRIMARY KEY,evaluated_at TEXT NOT NULL,actual_price TEXT NOT NULL,actual_return_pct TEXT NOT NULL,direction_correct INTEGER NOT NULL,details_json TEXT NOT NULL);CREATE TABLE IF NOT EXISTS model_weights(version TEXT PRIMARY KEY,created_at TEXT NOT NULL,status TEXT NOT NULL,weights_json TEXT NOT NULL,parent_version TEXT,reason TEXT NOT NULL);""")
   c.execute("INSERT OR IGNORE INTO model_weights VALUES('rules-v1',?,'ACTIVE',?,NULL,'Deterministische Ausgangsgewichte')",(now(),json.dumps({'liquidity':30,'spread':35,'momentum':25,'news':10})))
   cols={x['name'] for x in self.db.rows('PRAGMA table_info(research_forecasts)')}
   for name,definition in [('family',"TEXT NOT NULL DEFAULT 'crypto_spot'"),('parameter_version','INTEGER NOT NULL DEFAULT 1'),('parameters_json',"TEXT NOT NULL DEFAULT '{}'"),('feature_schema_version','INTEGER NOT NULL DEFAULT 1')]:
    if name not in cols:c.execute(f'ALTER TABLE research_forecasts ADD COLUMN {name} {definition}')
 def snapshot(self,symbols):
  ver=self.db.rows('SELECT id FROM watchlist_versions ORDER BY id DESC LIMIT 1');vid=ver[0]['id'] if ver else None;saved=0
  with self.db.con() as c:
   for symbol in symbols:
    p=self.db.rows('SELECT last FROM live_prices WHERE symbol=?',(symbol,));cols={x['name'] for x in self.db.rows('PRAGMA table_info(scanner_results)')};wanted=['score','signal','quality','momentum_pct','trend_pct','volatility_pct','spread_pct'];select=','.join(x if x in cols else 'NULL AS '+x for x in wanted);s=self.db.rows('SELECT '+select+' FROM scanner_results WHERE symbol=?',(symbol,));
    try:u=self.db.rows('SELECT category FROM market_universe WHERE symbol=? LIMIT 1',(symbol,))
    except Exception:u=[]
    if not p or not s or s[0]['quality']!='VALID':continue
    family=family_for_category(u[0]['category'] if u else 'crypto_spot');version,parameters=active_profile(self.db,family);features={k:s[0].get(k) for k in ('momentum_pct','trend_pct','volatility_pct','spread_pct')};spread=float(s[0].get('spread_pct') or 0);fee=float(self.db.value('paper_fee_bps','40'))/100;slippage=float(self.db.value('paper_slippage_bps','10'))/100;fx=(float(self.db.value('paper_fx_fee_bps','10'))/100 if symbol.endswith('/USD') else 0);features.update({'schema_version':2,'estimated_roundtrip_cost_pct':round(spread+fee+slippage+fx,8),'cost_components_pct':{'spread':spread,'trade_fee':fee,'slippage':slippage,'fx_fee':fx}})
    direction='UP' if s[0]['signal']=='BUY' else ('DOWN' if s[0]['signal']=='AVOID' else 'FLAT');confidence=str(min(1,max(0,float(s[0]['score'])/100)));model=f'{family}-controlled-v{version}'
    for h in (24,168):
     c.execute('INSERT INTO research_forecasts(created_at,symbol,watchlist_version_id,model_version,horizon_hours,direction,baseline_price,scanner_score,confidence,status,features_json,family,parameter_version,parameters_json,feature_schema_version) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(now(),symbol,vid,model,h,direction,p[0]['last'],s[0]['score'],confidence,'OPEN',json.dumps(features,sort_keys=True),family,version,json.dumps(parameters,sort_keys=True),2));saved+=1
  return saved
 def evaluate_due(self):
  rows=self.db.rows("SELECT * FROM research_forecasts WHERE status='OPEN'");done=0;current=datetime.now(timezone.utc)
  for f in rows:
   if current<datetime.fromisoformat(f['created_at'])+timedelta(hours=f['horizon_hours']):continue
   p=self.db.rows('SELECT last FROM live_prices WHERE symbol=?',(f['symbol'],))
   if not p:continue
   base=float(f['baseline_price']);actual=float(p[0]['last']);ret=(actual/base-1)*100 if base else 0;correct=(f['direction']=='UP' and ret>0) or (f['direction']=='DOWN' and ret<0) or (f['direction']=='FLAT' and abs(ret)<1)
   with self.db.con() as c:c.execute('INSERT OR REPLACE INTO forecast_evaluations VALUES(?,?,?,?,?,?)',(f['id'],now(),str(actual),str(ret),1 if correct else 0,json.dumps({'direction':f['direction'],'family':f.get('family'),'parameter_version':f.get('parameter_version')})));c.execute("UPDATE research_forecasts SET status='EVALUATED' WHERE id=?",(f['id'],));done+=1
  return done
