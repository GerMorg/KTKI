import json

FAMILY_SCHEMAS={
 'crypto_spot':{
  'base_score':(50.0,35,65),'momentum_weight':(5.0,1,10),'trend_weight':(8.0,2,16),
  'volatility_penalty':(1.5,.2,4),'spread_penalty':(25.0,5,60),'buy_threshold':(65.0,50,80),
  'buy_max_spread_pct':(.8,.1,3),'avoid_threshold':(35.0,15,50),'avoid_spread_pct':(1.5,.4,5)},
 'xstocks':{
  'base_score':(50.0,40,60),'momentum_weight':(4.0,2,6),'trend_weight':(10.0,6,14),
  'volatility_penalty':(1.2,.6,2),'spread_penalty':(18.0,10,28),'buy_threshold':(62.0,55,75),
  'buy_max_spread_pct':(1.2,.4,2),'avoid_threshold':(32.0,20,45),'avoid_spread_pct':(2.5,1,4)},
 'forex':{
  'base_score':(50.0,35,65),'momentum_weight':(4.0,1,8),'trend_weight':(9.0,3,16),
  'volatility_penalty':(1.1,.2,4),'spread_penalty':(30.0,8,80),'buy_threshold':(64.0,50,80),
  'buy_max_spread_pct':(.7,.05,2),'avoid_threshold':(34.0,15,50),'avoid_spread_pct':(1.3,.2,4)} }
FAMILIES={family:{name:spec[0] for name,spec in schema.items()} for family,schema in FAMILY_SCHEMAS.items()}
BOUNDS={family:{name:(spec[1],spec[2]) for name,spec in schema.items()} for family,schema in FAMILY_SCHEMAS.items()}

def family_for_category(category):
 return category if category in FAMILY_SCHEMAS else 'crypto_spot'

def active_profile(db,family):
 try:r=db.rows("SELECT version,parameters_json FROM parameter_family_versions WHERE family=? AND status='ACTIVE' ORDER BY version DESC LIMIT 1",(family,))
 except Exception:r=[]
 if not r:return 1,dict(FAMILIES[family])
 try:params=json.loads(r[0]['parameters_json'])
 except Exception:params={}
 merged=dict(FAMILIES[family]);merged.update({k:float(v) for k,v in params.items() if k in merged});return int(r[0]['version']),merged

def score_features(features,params):
 momentum=float(features.get('momentum_pct') or 0);trend=float(features.get('trend_pct') or 0);vol=float(features.get('volatility_pct') or 0);spread=float(features.get('spread_pct') if features.get('spread_pct') is not None else 999);news=float(features.get('news_score') or 0)
 score=params['base_score']+max(-25,min(25,momentum*params['momentum_weight']))+max(-18,min(18,trend*params['trend_weight']))-max(0,min(22,vol*params['volatility_penalty']))-max(0,min(30,spread*params['spread_penalty']))+news
 score=max(0,min(100,score));buy=score>=params['buy_threshold'] and momentum>0 and trend>0 and spread<=params['buy_max_spread_pct'];avoid=score<params['avoid_threshold'] or spread>params['avoid_spread_pct']
 return score,'BUY' if buy else ('AVOID' if avoid else 'HOLD')


