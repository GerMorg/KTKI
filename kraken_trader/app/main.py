import csv,io,json,os,threading,time
from flask import Flask,Response,redirect,render_template_string,request,url_for
from db import DB
from kraken import KrakenClient,KrakenError
from portfolio_sync import build_rows,normalize_asset
from ws_market import MarketStream
from ws_private import PrivateStream
from paper_engine import PaperEngine,configure_engine
from scanner import MarketScanner
from market_universe import MarketUniverse
from news_prefilter import NewsPrefilter
from prefilter import MarketPrefilter
from forecast_tracker import ForecastTracker
from research_pipeline import ResearchPipeline
from external_ai import ExternalNewsAI
from text_encoding import repair_database
from learning_approval import LearningApproval
from market_history import MarketHistory
from backtest import BacktestEngine
from fee_profile import FeeProfile
from forex_shadow import ForexShadow
from product_view import ProductView
from decision_matrix import DecisionMatrix
from controlled_learning import ControlledLearning
from strategy_profiles import FAMILIES
from news_learning import NewsLearning
from version import APP_VERSION
from monitoring import NotificationService,create_monitoring_blueprint
from at_income_tax import create_tax_blueprint
from real_trade import create_real_trade_blueprint
class IngressPrefix:
 def __init__(self,app):self.app=app
 def __call__(self,environ,start_response):
  prefix=environ.get('HTTP_X_INGRESS_PATH','').rstrip('/')
  if prefix:environ['SCRIPT_NAME']=prefix
  return self.app(environ,start_response)
DATA=os.getenv('APP_DATA_DIR','/tmp/kraken-trader');os.makedirs(DATA,exist_ok=True)
try:
 with open(os.getenv('APP_OPTIONS','/data/options.json')) as f:opts=json.load(f)
except Exception:opts={}
db=DB(os.path.join(DATA,'kraken_trader.db'));db.init(opts.get('paper_start_eur',1000));repair_database(db);paper_engine=PaperEngine(db,opts.get('paper_start_eur',1000),opts.get('paper_fee_bps',40),opts.get('paper_slippage_bps',10),opts.get('paper_max_position_pct',10),opts.get('paper_trade_eur',25));client=KrakenClient(opts.get('kraken_api_key',''),opts.get('kraken_api_secret',''))
for key,value in {'paper_fee_bps':opts.get('paper_fee_bps',40),'paper_slippage_bps':opts.get('paper_slippage_bps',10),'paper_max_position_pct':opts.get('paper_max_position_pct',10),'paper_trade_eur':opts.get('paper_trade_eur',25),'paper_interval_minutes':opts.get('paper_interval_minutes',15),'scanner_required':opts.get('scanner_required',True),'scanner_delay_seconds':opts.get('scanner_delay_seconds',1.05),'prefilter_top_per_category':opts.get('prefilter_top_per_category',8),'research_auto_enabled':opts.get('research_auto_enabled',False),'research_interval_minutes':opts.get('research_interval_minutes',60),'paper_leverage_enabled':opts.get('paper_leverage_enabled',False),'paper_max_leverage':opts.get('paper_max_leverage',3),'paper_min_position_pct':opts.get('paper_min_position_pct',2),'paper_min_transfer_eur':opts.get('paper_min_transfer_eur',20),'paper_max_transfer_eur':opts.get('paper_max_transfer_eur',250),'paper_rebalance_edge_pct':opts.get('paper_rebalance_edge_pct',8),'paper_fx_fee_bps':opts.get('paper_fx_fee_bps',10),'paper_min_hold_hours':opts.get('paper_min_hold_hours',24),'paper_cooldown_hours':opts.get('paper_cooldown_hours',12),'paper_confirmation_runs':opts.get('paper_confirmation_runs',2),'paper_max_turnovers_per_day':opts.get('paper_max_turnovers_per_day',2),'paper_sell_hysteresis_pct':opts.get('paper_sell_hysteresis_pct',2),'paper_buy_score_threshold':opts.get('paper_buy_score_threshold',62),'paper_tax_rate_pct':opts.get('paper_tax_rate_pct',27.5),'learning_required_horizons':opts.get('learning_required_horizons','24,168'),'learning_min_horizon_samples':opts.get('learning_min_horizon_samples',5),'learning_min_candidate_coverage':opts.get('learning_min_candidate_coverage',.5),'learning_min_net_return_improvement':opts.get('learning_min_net_return_improvement',.01),'learning_max_candidate_drawdown_pct':opts.get('learning_max_candidate_drawdown_pct',-25),'learning_max_drawdown_degradation_pct':opts.get('learning_max_drawdown_degradation_pct',2),'real_trading_enabled':opts.get('real_trading_enabled',False),'real_kill_switch':opts.get('real_kill_switch',True),'real_max_order_volume':opts.get('real_max_order_volume',0),'real_max_order_notional_eur':opts.get('real_max_order_notional_eur',0),'real_allowed_symbols':opts.get('real_allowed_symbols','')}.items():
 if not db.rows('SELECT value FROM settings WHERE key=?',(key,)):db.set_setting(key,value)
configure_engine(paper_engine)
scanner=MarketScanner(db,client)
universe=MarketUniverse(db,client)
external_news_ai=ExternalNewsAI(db,opts)
news_prefilter=NewsPrefilter(db)
news_learning=NewsLearning(db)
news_prefilter.external_ai=external_news_ai
news_prefilter.news_learning=news_learning
external_news_ai.news_learning=news_learning
prefilter=MarketPrefilter(db,client,news_prefilter)
learning=LearningApproval(db)
history=MarketHistory(db);backtests=BacktestEngine(db);fees=FeeProfile(db,client);forex_shadow=ForexShadow(db);product_view=ProductView(db);decision_matrix=DecisionMatrix(db);controlled_learning=ControlledLearning(db)
forecasts=ForecastTracker(db)
pipeline=ResearchPipeline(db,universe,prefilter,scanner,forecasts)
app=Flask(__name__);app.wsgi_app=IngressPrefix(app.wsgi_app)
@app.after_request
def force_utf8(response):
 if response.mimetype in ('text/html','text/plain','text/csv','application/json'):response.headers['Content-Type']=response.mimetype+'; charset=utf-8';response.headers['X-Content-Type-Options']='nosniff'
 return response
stream=MarketStream(db,bool(opts.get('public_websocket_enabled',False)),opts.get('websocket_stale_seconds',30))
private_stream=PrivateStream(db,client,bool(opts.get('private_websocket_readonly_enabled',False)),opts.get('websocket_stale_seconds',30))
def D(x):
 try:return __import__('decimal').Decimal(str(x or 0))
 except:return __import__('decimal').Decimal(0)
def ws_asset(name):return 'BTC' if name=='XBT' else name
def restore_stream_symbols():
 rows=db.rows("SELECT display_name FROM portfolio_assets WHERE classification='HELD'");stream.set_symbols([ws_asset(x['display_name'])+'/EUR' for x in rows if x['display_name']!='EUR']);stream.start()

if os.getenv('APP_DISABLE_WEBSOCKETS')!='1':
 restore_stream_symbols();private_stream.start()
def allowed_symbols():
 rows=db.rows('SELECT symbol FROM allowlist WHERE enabled=1 ORDER BY symbol')
 return [x['symbol'] for x in rows] if rows else universe.symbols(None)
def current_market_batch():
 symbols=prefilter.candidates();return symbols if symbols else allowed_symbols()[:10]
def refresh_allowed_prices():
 symbols=current_market_batch()
 if any(x.endswith('/USD') for x in symbols) and 'EUR/USD' not in symbols:symbols.append('EUR/USD')
 if not symbols:return 0
 received=__import__('db').now();saved=0
 groups={}
 for symbol in symbols:
  row=db.rows('SELECT asset_class FROM market_universe WHERE symbol=? LIMIT 1',(symbol,));groups.setdefault(row[0]['asset_class'] if row else 'currency',[]).append(symbol)
 for ac,batch in groups.items():
  try:
   try:payload=client.ticker(batch,ac)
   except TypeError:payload=client.ticker(batch)
  except Exception as exc:db.audit('PAPER_PRICE_REFRESH_FAILED',ac+': '+type(exc).__name__,'error');continue
  for requested in batch:
   wanted=requested.replace('BTC/','XBT/').replace('/','');item=None
   for key,value in payload.items():
    compact=key.replace('X','').replace('Z','').replace('/','')
    if requested.replace('BTC','XBT').replace('/','') in compact or wanted in key:item=value;break
   if item is None and len(payload)==1:item=next(iter(payload.values()))
   if not item:continue
   last=str(item.get('c',[''])[0]);bid=str(item.get('b',[''])[0]);ask=str(item.get('a',[''])[0]);openp=D(item.get('o'));change=str(((D(last)-openp)/openp*100) if openp else D(0));db.upsert_live_price({'symbol':requested,'last':last,'bid':bid,'ask':ask,'change_pct':change,'received_at':received});saved+=1
 stream.set_symbols(symbols);stream.start();return saved
def run_paper_cycle():
 refresh_allowed_prices();configure_engine(paper_engine);forecasts.evaluate_due();return paper_engine.run()
def paper_scheduler():
 while True:
  rows=db.rows("SELECT value FROM settings WHERE key='paper_interval_minutes'");minutes=max(1,int(float(rows[0]['value'] if rows else 15)));time.sleep(minutes*60);run_paper_cycle()
if os.getenv('APP_DISABLE_PAPER_SCHEDULER')!='1':threading.Thread(target=paper_scheduler,daemon=True,name='paper-scheduler').start()
def research_scheduler():
 while True:
  minutes=max(5,int(float(db.value('research_interval_minutes','60'))));time.sleep(minutes*60)
  if db.value('research_auto_enabled','false')=='true':
   result=pipeline.start();db.audit('RESEARCH_SCHEDULER_TICK',json.dumps(result))
if os.getenv('APP_DISABLE_RESEARCH_SCHEDULER')!='1':threading.Thread(target=research_scheduler,daemon=True,name='research-scheduler').start()
BASE='''<!doctype html><html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Kraken Trader</title><style>
:root{color-scheme:dark;--bg:#07111f;--panel:#101e31;--panel2:#152842;--line:#29405d;--text:#f2f7fc;--muted:#9eb1c8;--accent:#57c7ff;--good:#5fe090;--warn:#ffc861;--bad:#ff7b7b;--radius:14px}*{box-sizing:border-box}body{margin:0;background:linear-gradient(145deg,#07111f,#0c1728 55%,#07111f);color:var(--text);font:15px/1.5 system-ui,-apple-system,Segoe UI,sans-serif}a{color:var(--accent)}.shell{min-height:100vh}.top{position:sticky;top:0;z-index:10;background:rgba(7,17,31,.96);border-bottom:1px solid var(--line)}.brand{display:flex;align-items:center;justify-content:space-between;max-width:1500px;margin:auto;padding:12px 20px}.brand strong{font-size:18px}.brand small,.muted,small{color:var(--muted)}.safety{padding:5px 10px;border:1px solid #83555b;border-radius:999px;color:#ffb5b5;background:#321a22;font-size:12px;font-weight:700}.nav{display:flex;gap:6px;overflow-x:auto;max-width:1500px;margin:auto;padding:0 20px 12px}.nav a{white-space:nowrap;text-decoration:none;color:#cbd8e8;padding:8px 10px;border-radius:9px}.nav a:hover,.nav a.active{color:white;background:var(--panel2)}main{max-width:1500px;margin:auto;padding:24px 20px 64px}h1{font-size:clamp(25px,4vw,38px);margin:0 0 8px}h2{margin-top:28px}h3{margin-top:0}.lead{color:var(--muted);max-width:900px;margin-top:0}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:14px}.card{background:linear-gradient(145deg,var(--panel),#0d1a2c);border:1px solid var(--line);border-radius:var(--radius);padding:18px;margin:14px 0;box-shadow:0 10px 26px #0003}.metric{font-size:28px;font-weight:750}.pill{display:inline-block;border:1px solid var(--line);border-radius:999px;padding:3px 9px;font-size:12px}.ok{color:var(--good)}.warning{color:var(--warn)}.error{color:var(--bad)}form{display:flex;gap:10px;flex-wrap:wrap;align-items:end}label{display:grid;gap:5px;color:var(--muted)}input,select,button,textarea{font:inherit;color:var(--text);background:#0a1728;border:1px solid #365171;border-radius:9px;padding:10px 12px}button,.button{background:#1679a8;border-color:#45bdec;color:white;font-weight:700;cursor:pointer;text-decoration:none;display:inline-block}.tablewrap{width:100%;overflow:auto;border:1px solid var(--line);border-radius:12px;margin:14px 0}table{width:100%;border-collapse:collapse;background:#0c192a}th,td{text-align:left;padding:11px 12px;border-bottom:1px solid #223750;vertical-align:top}th{background:#14253b;color:#acc4df;font-size:12px;text-transform:uppercase;letter-spacing:.04em}.steps{counter-reset:step;display:grid;gap:10px}.step{display:grid;grid-template-columns:34px 1fr;gap:10px}.step:before{counter-increment:step;content:counter(step);display:grid;place-items:center;width:28px;height:28px;border-radius:50%;background:#173d59;color:#8dd9ff;font-weight:800}details{background:#0b1727;border:1px solid var(--line);border-radius:10px;padding:10px 13px;margin:8px 0}@media(max-width:700px){main,.brand,.nav{padding-left:12px;padding-right:12px}.safety{display:none}th,td{padding:9px 8px}}
</style></head><body><div class="shell"><header class="top"><div class="brand"><div><strong>Kraken Trader</strong> <small>v{{app_version}}</small></div><span class="safety">REALHANDEL STANDARDMÄSSIG AUSIERT</span></div><nav class="nav">{% for href,label in nav %}<a href="{{href}}" class="{% if current_path==href %}active{% endif %}">{{label}}</a>{% endfor %}</nav></header><main>{{body|safe}}</main></div></body></html>'''
NAV_ITEMS=[('/', 'ÃƒÅ“bersicht'),('/portfolio','Portfolio'),('/products','Produkte'),('/scanner','Analyse'),('/paper','Paper-Handel'),('/real-trading','Realhandel'),('/controlled-learning','Lernen'),('/news-learning','Nachrichten-Lernen'),('/fees','GebÃƒÂ¼hren'),('/data-quality','DatenqualitÃƒÂ¤t'),('/backtests','Backtests'),('/decision-matrix','Regelmatrix'),('/settings','Einstellungen'),('/tax-info','Steuerinfo AT'),('/event-dashboard','Ereignisse'),('/audit','Audit'),('/exports','Export')]
def page(body,**ctx):
 return render_template_string(BASE,body=render_template_string(body,**ctx),app_version=APP_VERSION,nav=[(request.script_root+href,label) for href,label in NAV_ITEMS],current_path=request.script_root+request.path)
notifications=NotificationService(db)
app.register_blueprint(create_monitoring_blueprint(db,page))
app.register_blueprint(create_tax_blueprint(db,page))
app.register_blueprint(create_real_trade_blueprint(db,client,page))
@app.get('/')
def index():
 portfolio=db.rows('SELECT total_eur,quality,created_at FROM portfolio_snapshots ORDER BY id DESC LIMIT 1');stream_state=stream.status();private_state=private_stream.status();market_rows=db.rows('SELECT received_at FROM live_prices ORDER BY received_at DESC LIMIT 1');private_rows=db.rows('SELECT received_at FROM private_balances ORDER BY received_at DESC LIMIT 1');stream_state['dashboard_state']='DATEN VERFÃƒÅ“GBAR' if market_rows else ('DEAKTIVIERT' if not stream_state.get('configured_enabled') else stream_state.get('effective_state','NOCH KEINE DATEN'));private_state['dashboard_state']='KONTODATEN VERFÃƒÅ“GBAR' if private_rows or portfolio else ('DEAKTIVIERT' if not private_state.get('configured_enabled') else private_state.get('effective_state','NOCH KEINE DATEN'));pending=db.rows("SELECT COUNT(*) n FROM learning_candidates WHERE status='PENDING'");latest_fee=fees.latest()
 return page("""<h1>ÃƒÅ“bersicht</h1><p class=lead>Zentrale ArbeitsoberflÃƒÂ¤che fÃƒÂ¼r Daten, Analyse, Simulation und kontrollierte Lernfreigaben. Jeder Schritt bleibt nachvollziehbar; reale Orders sind technisch ausgeschlossen.</p><div class=grid><div class=card><h3>Portfolio</h3><div class=metric>{{portfolio[0].total_eur if portfolio else 'Ã¢â‚¬â€'}} Ã¢â€šÂ¬</div><span class=pill>{{portfolio[0].quality if portfolio else 'Noch kein Snapshot'}}</span></div><div class=card><h3>Marktdaten</h3><div class=metric>{{stream.dashboard_state}}</div><small>Public WebSocket: {{stream.effective_state}}</small></div><div class=card><h3>Kontodaten</h3><div class=metric>{{private.dashboard_state}}</div><small>Read-only Private WebSocket: {{private.effective_state}}</small></div><div class=card><h3>Lernfreigaben</h3><div class=metric>{{pending[0].n if pending else 0}}</div><small>offene Kandidaten</small></div><div class=card><h3>GebÃƒÂ¼hrenprofil</h3><div class=metric>{{fee.status if fee else 'Ã¢â‚¬â€'}}</div><small>{{fee.created_at if fee else 'Noch nicht abgerufen'}}</small></div></div><div class=card><h2>Empfohlener Ablauf</h2><div class=steps><div class=step><div><b>Daten verbinden und prÃƒÂ¼fen</b><br><span class=muted>API, Portfolio und DatenqualitÃƒÂ¤t kontrollieren.</span><br><a href="{{url_for('api_status')}}">API ÃƒÂ¶ffnen</a> Ã‚Â· <a href="{{url_for('data_quality')}}">DatenqualitÃƒÂ¤t</a></div></div><div class=step><div><b>Produkte und GebÃƒÂ¼hren aktualisieren</b><br><a href="{{url_for('products_page')}}">Produkte</a> Ã‚Â· <a href="{{url_for('fees_page')}}">GebÃƒÂ¼hren</a></div></div><div class=step><div><b>Analyse und Simulation ausfÃƒÂ¼hren</b><br><a href="{{url_for('scanner_page')}}">Analyse</a> Ã‚Â· <a href="{{url_for('paper')}}">Paper-Handel</a></div></div><div class=step><div><b>Lernkandidaten bewusst freigeben</b><br><span class=muted>Ohne ausdrÃƒÂ¼ckliche Freigabe ÃƒÂ¤ndert sich kein aktiver Parameter.</span><br><a href="{{url_for('controlled_learning_page')}}">Kontrolliertes Lernen</a><a href="{{url_for('news_learning_page')}}">Nachrichten-Lernen</a></div></div></div></div>""",portfolio=portfolio,stream=stream_state,private=private_state,pending=pending,fee=latest_fee)
@app.get('/health')
def health():return {'status':'ok','version':APP_VERSION,'real_trading':False,'websocket_status':db.value('websocket_status','not_checked'),'market_stream':stream.status(),'private_stream':private_stream.status()}
@app.get('/api/private-stream')
def private_stream_api():return {'status':private_stream.status(),'balances':db.rows('SELECT * FROM private_balances ORDER BY asset'),'executions':db.rows('SELECT event_type,order_id,exec_id,symbol,sequence,received_at FROM private_execution_events ORDER BY received_at DESC LIMIT 100'),'sequence_gaps':db.rows('SELECT * FROM private_sequence_gaps ORDER BY id DESC LIMIT 20')}
@app.post('/api/private-stream/reconnect')
def private_stream_reconnect():
 private_stream.shutdown();private_stream.start();db.audit('PRIVATE_WEBSOCKET_RECONNECT_REQUESTED');return private_stream.status()
@app.get('/api/market-stream')
def market_stream():return {'status':stream.status(),'prices':db.rows('SELECT * FROM live_prices ORDER BY symbol')}
@app.post('/api/market-stream/reconnect')
def market_stream_reconnect():
 stream.shutdown();stream.start();db.audit('PUBLIC_WEBSOCKET_RECONNECT_REQUESTED');return stream.status()
@app.route('/api',methods=['GET','POST'])
def api_status():
 msg=''
 if request.method=='POST':
  action=request.form.get('action')
  try:
   if action=='rest':
    st=client.status();db.set('kraken_status','ok');db.audit('KRAKEN_REST_TEST','success');msg='REST erfolgreich: '+str(st.get('status','online'))
   elif action=='websocket':
    token=client.websocket_token();db.set('websocket_status','ok');db.audit('KRAKEN_WEBSOCKET_TOKEN_TEST','success');msg='Privater WebSocket-Zugriff erfolgreich. Token wurde nicht gespeichert.' if token.get('token') else 'Keine Token-Antwort.'
  except KrakenError as e:
   if action=='websocket':db.set('websocket_status','error')
   else:db.set('kraken_status','error')
   db.audit('KRAKEN_API_TEST',str(e),'error');msg=str(e)
 return page('<h1>API</h1><div class=card><p>REST: <b>{{rest}}</b> Ã‚Â· privater WebSocket: <b>{{ws}}</b></p><form method=post><button name=action value=rest>REST prÃƒÂ¼fen</button> <button name=action value=websocket>WebSocket-Berechtigung prÃƒÂ¼fen</button></form><p>{{msg}}</p><p class=muted>Ãƒâ€“ffentliche WebSocket-Marktdaten benÃƒÂ¶tigen keinen API-SchlÃƒÂ¼ssel. FÃƒÂ¼r private KontokanÃƒÂ¤le wird die Kraken-Berechtigung "Access WebSockets API" benÃƒÂ¶tigt.</p></div><div class=card><h2>Ãƒâ€“ffentlicher WebSocket-v2-Livestream</h2><p>Status: <b>{{stream.effective_state}}</b> Ã‚Â· Kraken: {{stream.system_status or "Ã¢â‚¬â€"}} Ã‚Â· Symbole: {{stream.symbol_count}}</p><p>Letzte Nachricht: {{stream.last_message_at or "Ã¢â‚¬â€"}}</p><table>{% for x in prices %}<tr><td>{{x.symbol}}</td><td>{{x.last}}</td><td>Bid {{x.bid or "Ã¢â‚¬â€"}}</td><td>Ask {{x.ask or "Ã¢â‚¬â€"}}</td><td>{{x.received_at}}</td></tr>{% endfor %}</table></div><div class=card><h2>Privater Read-only WebSocket v2</h2><p>Status: <b>{{private.effective_state}}</b> Ã‚Â· Balances-Sequenz: {{private.sequences.get("balances","Ã¢â‚¬â€")}} Ã‚Â· Executions-Sequenz: {{private.sequences.get("executions","Ã¢â‚¬â€")}}</p><p>Letzte Nachricht: {{private.last_message_at or "Ã¢â‚¬â€"}} Ã‚Â· Fehler: {{private.last_error or "Ã¢â‚¬â€"}}</p><h3>Live-Balances</h3><table>{% for x in private_balances %}<tr><td>{{x.asset}}</td><td>{{x.balance}}</td><td>Seq {{x.sequence}}</td><td>{{x.received_at}}</td></tr>{% endfor %}</table><h3>Letzte AusfÃƒÂ¼hrungsereignisse</h3><table>{% for x in executions %}<tr><td>{{x.event_type}}</td><td>{{x.symbol or "Ã¢â‚¬â€"}}</td><td>{{x.order_id or "Ã¢â‚¬â€"}}</td><td>Seq {{x.sequence}}</td><td>{{x.received_at}}</td></tr>{% endfor %}</table></div>',rest=db.value('kraken_status'),ws=db.value('websocket_status'),msg=msg,stream=stream.status(),prices=db.rows('SELECT * FROM live_prices ORDER BY symbol'),private=private_stream.status(),private_balances=db.rows('SELECT * FROM private_balances ORDER BY asset'),executions=db.rows('SELECT event_type,order_id,symbol,sequence,received_at FROM private_execution_events ORDER BY received_at DESC LIMIT 50'))
def sync_portfolio():
 balances=client.balance();ledger_assets=set();offset=0
 while True:
  result=client.ledgers(offset);entries=result.get('ledger',{});db.import_ledger(entries);ledger_assets.update(x.get('asset') for x in entries.values() if x.get('asset'))
  count=int(result.get('count',len(entries)))
  if not entries or offset+len(entries)>=count:break
  offset+=len(entries)
 assets=client.assets();pairs=client.pairs();relevant=[]
 names={normalize_asset(x,assets) for x in set(balances)|ledger_assets}
 for pair_id,pair in pairs.items():
  if normalize_asset(pair.get('base',''),assets) in names and normalize_asset(pair.get('quote',''),assets)=='EUR':relevant.append(pair.get('altname',pair_id))
 tickers=client.ticker(relevant);rows,total,quality=build_rows(balances,ledger_assets,assets,pairs,tickers);db.replace_balances(balances);sid=db.store_portfolio(rows,total,quality);held_names={normalize_asset(code,assets) for code,value in balances.items() if str(value) not in ('0','0.0','0.00')};symbols=[ws_asset(normalize_asset(pair.get('base',''),assets))+'/EUR' for pair in pairs.values() if normalize_asset(pair.get('base',''),assets) in held_names and normalize_asset(pair.get('quote',''),assets)=='EUR'];stream.set_symbols(symbols);stream.start();db.audit('REAL_PORTFOLIO_SYNC',json.dumps({'snapshot_id':sid,'assets':len(rows),'quality':quality,'websocket_symbols':len(stream.symbols)}));return sid
@app.route('/portfolio',methods=['GET','POST'])
def portfolio():
 msg=''
 if request.method=='POST':
  try:msg='Snapshot '+str(sync_portfolio())+' gespeichert.'
  except KrakenError as e:db.audit('REAL_PORTFOLIO_SYNC_FAILED',str(e),'error');msg=str(e)
 rows=db.rows('SELECT * FROM portfolio_assets ORDER BY classification,display_name');history=db.rows('SELECT * FROM portfolio_snapshots ORDER BY id DESC LIMIT 50')
 return page('''<h1>Realportfolio</h1><div class=card><form method=post><button>Kraken vollstÃƒÂ¤ndig synchronisieren</button></form><p>{{msg}}</p><p class=muted>Nullpositionen bleiben als HISTORICAL_ZERO erhalten, wenn das Asset in der Ledger-Historie vorkam.</p><table><tr><th>Asset</th><th>Menge</th><th>EUR-Kurs</th><th>EUR-Wert</th><th>Status</th></tr>{% for x in rows %}<tr><td>{{x.display_name}} <small>{{x.asset}}</small></td><td>{{x.amount}}</td><td>{{x.eur_price or "Ã¢â‚¬â€"}}</td><td>{{x.eur_value or "Ã¢â‚¬â€"}}</td><td><span class=tag>{{x.classification}}</span></td></tr>{% endfor %}</table></div><div class=card><h2>Historie</h2><table><tr><th>Zeit</th><th>Gesamt EUR</th><th>QualitÃƒÂ¤t</th><th>Unbewertet</th></tr>{% for x in history %}<tr><td>{{x.created_at}}</td><td>{{x.total_eur}}</td><td>{{x.quality}}</td><td>{{x.unpriced_asset_count}}</td></tr>{% endfor %}</table></div>''',rows=rows,history=history,msg=msg)
@app.get('/scanner')
def scanner_page():
 rows=db.rows("SELECT w.symbol,w.category,w.prefilter_score,w.status,s.score,s.signal,s.quality FROM research_watchlist w LEFT JOIN scanner_results s ON s.symbol=w.symbol ORDER BY CAST(w.prefilter_score AS REAL) DESC");job=pipeline.latest();sources=news_prefilter.sources();versions=db.rows('SELECT * FROM watchlist_versions ORDER BY id DESC LIMIT 10');stats=db.rows("SELECT COUNT(*) total,COALESCE(SUM(direction_correct),0) correct FROM forecast_evaluations")
 return page(render_template_string("""<h1>Research-Scanner</h1><p class=muted>Globale Nachrichten und PrimÃƒÂ¤rquellen Ã¢â€ â€™ Taxonomie Ã¢â€ â€™ Vorfilter Ã¢â€ â€™ versionierte Watchlist Ã¢â€ â€™ Detailanalyse Ã¢â€ â€™ Prognosevergleich. Nachrichten sind kein Handelssignal.</p><form method=post action="{{url_for('run_scanner')}}"><button>Research-Pipeline starten</button></form>{% if job %}<div class=card><b>Job #{{job.id}} {{job.status}}</b> Ã‚Â· {{job.stage}} Ã‚Â· {{job.progress_current}}/{{job.progress_total}}<p class=bad>{{job.error or ''}}</p></div>{% endif %}<h2>Quellen</h2><table>{% for x in sources %}<tr><td>{{x.name}}</td><td>{{x.source_class}}</td><td>{{x.last_status or 'offen'}}</td><td>{{x.last_error or 'Ã¢â‚¬â€'}}</td><td>{{x.last_checked_at or 'Ã¢â‚¬â€'}}</td></tr>{% endfor %}</table><h2>Watchlist</h2><table><tr><th>Symbol</th><th>Kategorie</th><th>Vorfilter</th><th>Status</th><th>Detailscore</th><th>Signal</th></tr>{% for x in rows %}<tr><td>{{x.symbol}}</td><td>{{x.category}}</td><td>{{x.prefilter_score}}</td><td>{{x.status}}</td><td>{{x.score or 'Ã¢â‚¬â€'}}</td><td>{{x.signal or 'Ã¢â‚¬â€'}}</td></tr>{% endfor %}</table><h2>Versionen und Prognosen</h2><p>Ausgewertet: {{stats.total if stats else 0}} Ã‚Â· Richtung richtig: {{stats.correct if stats else 0}}</p><table>{% for x in versions %}<tr><td>#{{x.id}}</td><td>{{x.created_at}}</td><td>{{x.item_count}} Kandidaten</td><td>{{x.status}}</td></tr>{% endfor %}</table>""",rows=rows,job=job,sources=sources,versions=versions,stats=stats[0] if stats else None))
@app.post('/scanner/run')
def run_scanner():db.audit('RESEARCH_PIPELINE_REQUEST',json.dumps(pipeline.start()));return redirect(url_for('scanner_page'))
@app.get('/api/research-job')
def research_job_api():return pipeline.latest() or {'status':'NONE'}
@app.get('/paper')
def paper():
 cash,pv,total,missing=paper_engine.equity();positions=paper_engine.positions();trades=db.rows('SELECT * FROM paper_trades ORDER BY id DESC LIMIT 100')
 return page(render_template_string('''<h1>Musterdepot</h1><div class=grid><div class=card><h3>Gesamtwert</h3><b>Ã¢â€šÂ¬ {{total}}</b></div><div class=card><h3>Cash</h3><b>Ã¢â€šÂ¬ {{cash}}</b></div><div class=card><h3>Positionen</h3><b>Ã¢â€šÂ¬ {{pv}}</b></div><div class=card><h3>DatenqualitÃƒÂ¤t</h3><b>{{'VALID' if not missing else 'INCOMPLETE'}}</b></div></div><form method=post action="{{url_for('run_paper')}}"><p><button>Paper-Strategie jetzt ausfÃƒÂ¼hren</button></p></form><h2>Positionen</h2><table><tr><th>Symbol</th><th>Menge</th><th>Ã‹Å“ Kosten EUR</th></tr>{% for x in positions %}<tr><td>{{x.symbol}}</td><td>{{x.quantity}}</td><td>{{x.avg_cost_eur}}</td></tr>{% endfor %}</table><h2>Simulierte Trades</h2><table><tr><th>Zeit</th><th>Symbol</th><th>Seite</th><th>Menge</th><th>AusfÃƒÂ¼hrung</th><th>GebÃƒÂ¼hr</th><th>Slippage</th><th>Grund</th></tr>{% for x in trades %}<tr><td>{{x.created_at}}</td><td>{{x.symbol}}</td><td>{{x.side}}</td><td>{{x.quantity}}</td><td>{{x.execution_price}}</td><td>{{x.fee_eur}}</td><td>{{x.slippage_eur}}</td><td>{{x.reason}}</td></tr>{% endfor %}</table>''',cash=cash,pv=pv,total=total,missing=missing,positions=positions,trades=trades))
@app.post('/paper/run')
def run_paper():
 try:run_paper_cycle()
 except Exception as exc:db.audit('PAPER_MANUAL_RUN_FAILED',type(exc).__name__+': '+str(exc)[:300],'error')
 return redirect(url_for('paper_decisions'))
@app.get('/paper/decisions')
def paper_decisions():return page(render_template_string('''<h1>Paper-Entscheidungen</h1><p class=muted>Deterministische Baseline: BUY ab +1 % 24h, SELL ab -1,5 % 24h; nur freigegebene Produkte, nur bei LIVE-Daten und aktivierter Analyse-/Paper-Automatik.</p><table><tr><th>Zeit</th><th>Symbol</th><th>Aktion</th><th>Score</th><th>QualitÃƒÂ¤t</th><th>AusgefÃƒÂ¼hrt</th><th>BegrÃƒÂ¼ndung</th></tr>{% for x in r %}<tr><td>{{x.created_at}}</td><td>{{x.symbol}}</td><td>{{x.action}}</td><td>{{x.score}} %</td><td>{{x.data_quality}}</td><td>{{'ja' if x.executed else 'nein'}}</td><td>{{x.reason}}</td></tr>{% endfor %}</table>''',r=db.rows('SELECT * FROM paper_decisions ORDER BY id DESC LIMIT 500')))
@app.route('/learning',methods=['GET','POST'])
def learning_page():
 msg=''
 if request.method=='POST':
  action=request.form.get('action');result=learning.create_proposal() if action=='create' else learning.approve_latest();msg=json.dumps(result,ensure_ascii=False)
 latest=learning.latest();rows=learning.rows()
 return page(render_template_string('''<h1>Lernfreigaben</h1><div class=card><p>Die Strategie ÃƒÂ¤ndert keine Parameter automatisch. Ein Vorschlag wird zunÃƒÂ¤chst angezeigt und erst mit deiner Freigabe als gemeinsame Version aktiviert.</p><form method=post><button name=action value=create>Neuen Vorschlag berechnen</button> {% if latest and latest.status=='PENDING' %}<button name=action value=approve>Alle neun Parameter mit einem Klick bestÃƒÂ¤tigen</button>{% endif %}</form><p>{{msg}}</p>{% if latest %}<p>Status: <b>{{latest.status}}</b> Ã‚Â· Stichprobe: {{latest.sample_count}} Ã‚Â· Trefferquote: {{latest.accuracy or 'Ã¢â‚¬â€'}}</p>{% endif %}</div><table><tr><th>Parameter</th><th>Aktuell</th><th>Vorschlag</th><th>ZulÃƒÂ¤ssiger Bereich</th></tr>{% for x in rows %}<tr><td>{{x.label}}</td><td>{{x.current}}</td><td>{{x.proposed if x.proposed is not none else 'Ã¢â‚¬â€'}}</td><td>{{x.minimum}} bis {{x.maximum}}</td></tr>{% endfor %}</table>''',latest=latest,rows=rows,msg=msg))





@app.route('/controlled-learning',methods=['GET','POST'])
def controlled_learning_page():
 result=None;family=request.form.get('family') or request.args.get('family') or 'forex';family=family if family in FAMILIES else 'forex'
 if request.method=='POST':
  action=request.form.get('action')
  if action=='propose':result=controlled_learning.propose(family)
  elif action in ('approve','reject'):result=controlled_learning.decide(int(request.form.get('candidate_id')),action)
  elif action=='rollback':result=controlled_learning.rollback(family,int(request.form.get('target_version')))
 candidates=controlled_learning.candidates(family);versions=controlled_learning.versions(family);learning_metrics=controlled_learning.metrics(family=family);gate_policy=controlled_learning.gate_policy();active=controlled_learning.active(family);active_versions=controlled_learning.active_versions();family_overview=controlled_learning.family_overview();active_params=json.loads(active['parameters_json']) if active else {};family_labels={'forex':'Forex','xstocks':'xStocks','crypto_spot':'Krypto Spot'}
 views=[]
 for item in candidates:
  row=dict(item);row['parameters']=json.loads(row.get('parameters_json') or '{}');row['gates']=json.loads(row.get('gate_results_json') or '[]');row['gate_passed']=sum(1 for x in row['gates'] if x.get('passed'));row['gate_total']=len(row['gates']);views.append(row)
 return page("""<h1>Kontrolliertes Lernen</h1><p class=lead>Neue Strategieparameter werden zuerst als wirkungsloser Kandidat geprÃƒÂ¼ft. Sie werden erst nach bestandenen Gates und Ihrer ausdrÃƒÂ¼cklichen Freigabe als neue gemeinsame Version aktiviert.</p>{% if result %}<div class=card><b>Ergebnis:</b> {{result}}</div>{% endif %}<div class=grid><div class=card><h3>1. Familie wÃƒÂ¤hlen</h3><form method=post><label>Parameterfamilie<select name=family><option value=forex {% if family=='forex' %}selected{% endif %}>Forex</option><option value=xstocks {% if family=='xstocks' %}selected{% endif %}>xStocks</option><option value=crypto_spot {% if family=='crypto_spot' %}selected{% endif %}>Krypto Spot</option></select></label><button name=action value=propose>Kandidaten berechnen</button></form><p class=muted>Das Berechnen verÃƒÂ¤ndert keine aktiven Parameter.</p></div><div class=card><h3>Aktuelle Versionen (Aktive Version)</h3><table><tr><th>Familie</th><th>Version</th><th>Offen</th><th>Letzter Kandidat</th></tr>{% for item in family_overview %}<tr{% if item.family==family %} class=selected{% endif %}><td><a href="{{url_for('controlled_learning_page',family=item.family)}}">{{family_labels.get(item.family,item.family)}}</a></td><td><b>v{{item.active_version if item.active_version is not none else 'Ã¢â‚¬â€'}}</b></td><td><span class=pill>{{item.pending_count}}</span></td><td>{% if item.latest_candidate_id %}#{{item.latest_candidate_id}} Ã‚Â· {{item.latest_status}}{% else %}Noch keiner{% endif %}</td></tr>{% endfor %}</table><small>Familie anklicken, um Kandidaten, Historie und Metriken gezielt zu filtern.</small><details><summary>Aktive Parameter fÃƒÂ¼r {{family_labels.get(family,family)}} anzeigen</summary><table>{% for key,value in active_params.items() %}<tr><td>{{key}}</td><td>{{value}}</td></tr>{% endfor %}</table></details></div><div class=card><h3>Freigaberegeln</h3><p>{{gate_policy.required_horizons|join(', ')}} Stunden</p><small>Mindeststichprobe {{gate_policy.minimum_horizon_samples}}, Mindestabdeckung {{gate_policy.minimum_candidate_coverage}}, positive Nettorenditeverbesserung und Drawdown-Grenzen.</small></div></div><h2>Kandidaten</h2>{% for x in candidates %}<div class=card><div class=grid><div><span class=pill>{{x.status}}</span><h3>#{{x.id}} Ã‚Â· {{x.family}}</h3><p>Basisversion {{x.base_version}}, Stichprobe {{x.sample_count}}</p></div><div><b>Trefferquote</b><br>Aktiv {{'%.2f'|format(x.active_accuracy|float*100)}} %<br>Kandidat {{'%.2f'|format(x.candidate_accuracy|float*100)}} %</div><div><b>Verbesserung</b><br>{{'%.2f'|format(x.improvement|float*100)}} Prozentpunkte<br><small>Gates {{x.gate_passed}} / {{x.gate_total}}</small></div></div><details><summary>Parametervergleich</summary><div class=tablewrap><table><tr><th>Parameter</th><th>Aktiv</th><th>Kandidat</th><th>Ãƒâ€žnderung</th></tr>{% for key,value in x.parameters.items() %}<tr><td>{{key}}</td><td>{{active_params.get(key,'Ã¢â‚¬â€') if x.family==family else 'siehe aktive Familienversion'}}</td><td>{{value}}</td><td>{% if x.family==family and key in active_params %}{{'%+.4f'|format(value|float-active_params[key]|float)}}{% else %}Ã¢â‚¬â€{% endif %}</td></tr>{% endfor %}</table></div></details><details><summary>Gate-PrÃƒÂ¼fung</summary><div class=tablewrap><table><tr><th>Gate</th><th>Horizont</th><th>Ergebnis</th><th>Ist</th><th>Soll</th></tr>{% for g in x.gates %}<tr><td>{{g.gate}}</td><td>{{g.horizon_hours or 'alle'}}</td><td class={{'ok' if g.passed else 'error'}}>{{'Bestanden' if g.passed else 'Nicht bestanden'}}</td><td>{{g.actual}}</td><td>{{g.required}}</td></tr>{% endfor %}</table></div></details>{% if x.status=='PENDING' %}<form method=post><input type=hidden name=family value={{x.family}}><input type=hidden name=candidate_id value={{x.id}}><button name=action value=approve>Nach erneuter PrÃƒÂ¼fung freigeben</button><button class=danger name=action value=reject>Ablehnen</button></form><p class=warning>Die Freigabe aktiviert alle neun Parameter atomar als neue Version.</p>{% endif %}</div>{% else %}<div class=card>Noch keine Kandidaten vorhanden.</div>{% endfor %}<h2>Horizontmetriken</h2><div class=tablewrap><table><tr><th>Kandidat</th><th>Horizont</th><th>Stichprobe</th><th>Abdeckung aktiv / Kandidat</th><th>Nettorendite aktiv / Kandidat</th><th>Drawdown aktiv / Kandidat</th></tr>{% for x in metrics %}<tr><td>{{x.candidate_id}}</td><td>{{x.horizon_hours}} h</td><td>{{x.sample_count}}</td><td>{{x.active_coverage}} / {{x.candidate_coverage}}</td><td>{{x.active_net_return}} / {{x.candidate_net_return}}</td><td>{{x.active_max_drawdown}} / {{x.candidate_max_drawdown}}</td></tr>{% endfor %}</table></div>""",result=result,family=family,candidates=views,versions=versions,metrics=learning_metrics,gate_policy=gate_policy,active=active,active_versions=active_versions,family_overview=family_overview,active_params=active_params,family_labels=family_labels)


@app.route('/news-learning',methods=['GET','POST'])
def news_learning_page():
 result=None
 if request.method=='POST':
  action=request.form.get('action')
  if action=='analyze':result=external_news_ai.analyze_pending()
  elif action=='compare':result=news_learning.propose()
  elif action in ('approve','reject'):result=news_learning.decide(int(request.form.get('candidate_id')),action)
 active=news_learning.active();candidates=news_learning.candidates();versions=news_learning.versions();data_status=news_learning.data_status()
 return page(render_template_string("""<h1>Nachrichten-AI und lokale Auswertung</h1><div class=card><p>Die externe Nachrichten-AI dient nur als Vergleichsinstanz. Neue lokale Parameter werden im Schattenmodus geprÃƒÂ¼ft und niemals automatisch aktiviert.</p><p>Aktive lokale Version: <b>v{{active.version}}</b></p><div class=grid><div><b>Nachrichten</b><div class=metric>{{data_status.news_items}}</div></div><div><b>GÃƒÂ¼ltige AI-Auswertungen</b><div class=metric>{{data_status.ai_valid}} / {{data_status.required}}</div></div><div><b>Noch erforderlich</b><div class=metric>{{data_status.missing}}</div></div><div><b>Nicht verarbeitet / ungÃƒÂ¼ltig</b><div class=metric>{{data_status.ai_unprocessed}} / {{data_status.ai_invalid}}</div></div></div>{% if data_status.ready %}<p class=ok>Die Datenbasis ist fÃƒÂ¼r einen Vergleich bereit.</p>{% elif data_status.status=='NO_NEWS_ITEMS' %}<p class=warning>Es sind noch keine Nachrichten vorhanden. Zuerst Nachrichten abrufen.</p>{% elif data_status.status=='NO_VALID_AI_RESULTS' %}<p class=warning>Es gibt noch keine gÃƒÂ¼ltigen AI-Auswertungen. AI-Konfiguration prÃƒÂ¼fen und anschlieÃƒÅ¸end "AI auswerten" verwenden.</p>{% else %}<p class=warning>FÃƒÂ¼r den Vergleich fehlen noch {{data_status.missing}} gÃƒÂ¼ltige AI-Auswertungen.</p>{% endif %}<form method=post><button name=action value=analyze>AI auswerten</button> <button name=action value=compare {% if not data_status.ready %}disabled title="Mindestens {{data_status.required}} gÃƒÂ¼ltige AI-Auswertungen erforderlich"{% endif %}>Vergleich berechnen</button></form>{% if result %}<details open><summary>Ergebnis</summary><pre>{{result|tojson(indent=2)}}</pre></details>{% endif %}</div><h2>Kandidaten</h2>{% if candidates %}<table><tr><th>ID</th><th>Status</th><th>Gesamt</th><th>Training / Validierung</th><th>Stabile Fenster</th><th>Verbesserung</th><th>Freigabe</th></tr>{% for x in candidates %}<tr><td>#{{x.id}}</td><td>{{x.status}}</td><td>{{x.sample_count}}</td><td>{{x.training_count}} / {{x.validation_count}}</td><td>{{x.stable_window_count}} / {{x.required_stable_windows}}</td><td>{{x.improvement}}</td><td>{% if x.status=='PENDING' %}<form method=post><input type=hidden name=candidate_id value={{x.id}}><button name=action value=approve>Freigeben</button><button name=action value=reject>Ablehnen</button></form>{% endif %}</td></tr>{% endfor %}</table>{% else %}<div class=card>Noch keine Vergleichskandidaten vorhanden.</div>{% endif %}<h2>Lokale Versionen</h2><table>{% for x in versions %}<tr><td>v{{x.version}}</td><td>{{x.status}}</td><td>{{x.source}}</td><td><small>{{x.parameters_json}}</small></td></tr>{% endfor %}</table>""",active=active,candidates=candidates,versions=versions,result=result,data_status=data_status))

@app.get('/products')
def products_page():
 rows=product_view.rows();return page(render_template_string("""<h1>Kanonische Produkte</h1><p class=muted>Eine IdentitÃƒÂ¤t je Basiswert und Anlageklasse. Alternative AusfÃƒÂ¼hrungspaare bleiben sichtbar, wÃƒÂ¤hrend genau ein Paar ausgewÃƒÂ¤hlt wird.</p><table><tr><th>IdentitÃƒÂ¤t</th><th>Klasse</th><th>GewÃƒÂ¤hltes Paar</th><th>Alternativen</th><th>EUR-Kosten</th><th>USD-Kosten</th><th>Letzte Wahl</th><th>Grund</th><th>Position</th></tr>{% for x in rows %}<tr><td>{{x.canonical_id}}</td><td>{{x.asset_class}}</td><td>{{x.selected_symbol or 'Ã¢â‚¬â€'}}</td><td>{{x.alternatives|join(', ')}}</td><td>{{x.eur_cost or 'Ã¢â‚¬â€'}}</td><td>{{x.usd_cost or 'Ã¢â‚¬â€'}}</td><td>{{x.updated_at}}</td><td>{{x.selection_reason}}</td><td>{% if x.position_symbol %}{{x.position_symbol}} / {{x.position_quantity}}{% else %}Ã¢â‚¬â€{% endif %}</td></tr>{% endfor %}</table>""",rows=rows))
@app.get('/decision-matrix')
def decision_matrix_page():
 rows=decision_matrix.recent();return page(render_template_string("""<h1>Umschichtungs-Regelmatrix</h1><p class=muted>Jede Regel wird einzeln gespeichert. Die erste nicht erfÃƒÂ¼llte Regel ist der sichtbare Blockierungsgrund.</p><table><tr><th>Zeit</th><th>Produkt</th><th>Aktion</th><th>Regel</th><th>Status</th><th>BegrÃƒÂ¼ndung</th></tr>{% for x in rows %}<tr><td>{{x.created_at}}</td><td>{{x.canonical_id}}<br><small>{{x.symbol}}</small></td><td>{{x.action}}</td><td>{{x.rule_key}}</td><td class={{'good' if x.passed else 'bad'}}>{{'ERFÃƒÅ“LLT' if x.passed else 'BLOCKIERT'}}</td><td>{{x.reason}}</td></tr>{% endfor %}</table>""",rows=rows))

@app.route('/forex-shadow',methods=['GET','POST'])
def forex_shadow_page():
 result=forex_shadow.run() if request.method=='POST' else None;rows=forex_shadow.comparisons();return page(render_template_string("""<h1>Forex v2 Schattenmodus</h1><div class=card><p><b>Keine Handelswirkung.</b> forex-v2 wird parallel zu forex-v1 ausgewertet. Alle EingÃƒÂ¤nge werden versioniert gespeichert. Nicht verfÃƒÂ¼gbare Makrofaktoren bleiben ausdrÃƒÂ¼cklich <code>null</code> und verbessern den Score nicht.</p><form method=post><button>Schattenbewertung ausfÃƒÂ¼hren</button></form><p>{{result or ''}}</p></div><table><tr><th>Zeit</th><th>Symbol</th><th>Aktiv</th><th>Kandidat</th><th>Abweichung</th></tr>{% for x in rows %}<tr><td>{{x.created_at}}</td><td>{{x.symbol}}</td><td>{{x.active_model}}: {{x.active_score}} / {{x.active_signal}}</td><td>{{x.candidate_model}}: {{x.candidate_score}} / {{x.candidate_signal}}</td><td>{{'ja' if x.disagrees else 'nein'}}</td></tr>{% endfor %}</table>""",rows=rows,result=result))

@app.route('/fees',methods=['GET','POST'])
def fees_page():
 result=None
 if request.method=='POST':
  symbols=[x['symbol'] for x in db.rows("SELECT symbol FROM market_universe WHERE LOWER(COALESCE(status,'online')) IN ('online','post_only','limit_only')")];result=fees.refresh(symbols)
 latest=fees.latest();rows=fees.rows();return page(render_template_string("""<h1>Kontospezifische GebÃƒÂ¼hren</h1><div class=card><p>Read-only Abruf der 30-Tage-HandelsaktivitÃƒÂ¤t und paarbezogenen Maker-/Taker-Stufen. Bei fehlender Berechtigung bleiben die konfigurierten konservativen GebÃƒÂ¼hren aktiv.</p><form method=post><button>GebÃƒÂ¼hrenprofil abrufen</button></form><p>{{result or ''}}</p>{% if latest %}<p>Status: <b>{{latest.status}}</b> Ã‚Â· Quelle: {{latest.source}} Ã‚Â· Volumen: {{latest.volume_30d or 'Ã¢â‚¬â€'}} {{latest.volume_currency or ''}} Ã‚Â· {{latest.created_at}}</p><p class=bad>{{latest.error_reason or ''}}</p>{% endif %}</div><table><tr><th>Symbol</th><th>Maker bps</th><th>Taker bps</th><th>Quelle</th><th>Zeitpunkt</th></tr>{% for x in rows %}<tr><td>{{x.symbol}}</td><td>{{x.maker_bps}}</td><td>{{x.taker_bps}}</td><td>{{x.source}}</td><td>{{x.effective_at}}</td></tr>{% endfor %}</table>""",result=result,latest=latest,rows=rows))

@app.get('/data-quality')
def data_quality():
 rows=history.diagnostics();return page(render_template_string("""<h1>DatenqualitÃƒÂ¤t</h1><p class=muted>Forex und andere MÃƒÂ¤rkte werden getrennt nach Ticker, Bid/Ask, Volumen, OHLC und Fehlergrund geprÃƒÂ¼ft. Eine laufende OHLC-Kerze zÃƒÂ¤hlt nicht als abgeschlossen.</p><table><tr><th>Symbol</th><th>Klasse</th><th>Ticker</th><th>Bid / Ask</th><th>Volumen</th><th>OHLC</th><th>Punkte</th><th>Fehler</th></tr>{% for x in rows %}<tr><td>{{x.symbol}}</td><td>{{x.asset_class}}</td><td>{{x.ticker_status}}<br><small>{{x.ticker_at or 'Ã¢â‚¬â€'}}</small></td><td>{{x.bid or 'Ã¢â‚¬â€'}} / {{x.ask or 'Ã¢â‚¬â€'}}</td><td>{{x.volume or 'Ã¢â‚¬â€'}}</td><td>{{x.ohlc_status}}<br><small>{{x.ohlc_at or 'Ã¢â‚¬â€'}}</small></td><td>{{x.ohlc_points}}</td><td>{{x.error_reason or 'Ã¢â‚¬â€'}}</td></tr>{% endfor %}</table>""",rows=rows))
@app.route('/backtests',methods=['GET','POST'])
def backtest_page():
 result=None
 if request.method=='POST':result=backtests.run(request.form.get('symbol',''),int(request.form.get('interval',60)),float(request.form.get('cost_rate',.006)))
 symbols=[x['symbol'] for x in db.rows('SELECT DISTINCT symbol FROM ohlc_cache ORDER BY symbol')];runs=db.rows('SELECT * FROM backtest_runs ORDER BY id DESC LIMIT 50')
 return page(render_template_string("""<h1>Backtests & Benchmarks</h1><div class=card><form method=post><select name=symbol>{% for s in symbols %}<option>{{s}}</option>{% endfor %}</select> <input name=interval type=number value=60> <input name=cost_rate type=number step=.0001 value=.006> <button>Walk-forward-Test</button></form><p>{{result or ''}}</p></div><table><tr><th>Zeit</th><th>Symbol</th><th>Klasse</th><th>Training/Test</th><th>Kostenrate</th><th>Ergebnis</th></tr>{% for x in runs %}<tr><td>{{x.created_at}}</td><td>{{x.symbol}}</td><td>{{x.asset_class}}</td><td>{{x.train_points}} / {{x.test_points}}</td><td>{{x.cost_rate}}</td><td><small>{{x.results_json}}</small></td></tr>{% endfor %}</table>""",symbols=symbols,runs=runs,result=result))

@app.get('/audit')
def audit():return page('<h1>Audit</h1><div class=card><table>{% for x in rows %}<tr><td>{{x.created_at}}</td><td>{{x.event}}</td><td>{{x.level}}</td><td>{{x.details}}</td></tr>{% endfor %}</table></div>',rows=db.rows('SELECT * FROM audit ORDER BY id DESC LIMIT 200'))
@app.route('/settings',methods=['GET','POST'])
def settings():
 if request.method=='POST':
  db.set_setting('automation_enabled','true' if request.form.get('automation') else 'false');db.set_setting('scanner_required','true' if request.form.get('scanner_required') else 'false');db.set_setting('research_auto_enabled','true' if request.form.get('research_auto_enabled') else 'false');db.set_setting('paper_leverage_enabled','true' if request.form.get('paper_leverage_enabled') else 'false');universe.set_categories(set(request.form.getlist('categories')))
  if 'products' in request.form:db.allow(request.form.getlist('products'))
  rules={'paper_fee_bps':(0,500,40),'paper_slippage_bps':(0,500,10),'paper_max_position_pct':(1,100,10),'paper_trade_eur':(1,100000,25),'paper_interval_minutes':(1,1440,15),'scanner_delay_seconds':(.5,10,1.05),'prefilter_top_per_category':(1,25,8),'research_interval_minutes':(5,1440,60),'paper_max_leverage':(1,20,3),'paper_min_position_pct':(.1,20,2),'paper_min_transfer_eur':(1,10000,20),'paper_max_transfer_eur':(1,100000,250),'paper_rebalance_edge_pct':(1,50,8),'paper_fx_fee_bps':(0,500,10),'paper_min_hold_hours':(0,720,24),'paper_cooldown_hours':(0,720,12),'paper_confirmation_runs':(1,10,2),'paper_max_turnovers_per_day':(0,50,2),'paper_sell_hysteresis_pct':(0,25,2),'paper_buy_score_threshold':(0,100,62),'paper_tax_rate_pct':(0,100,27.5)}
  for key,(lo,hi,d) in rules.items():
   try:v=max(lo,min(hi,float(request.form.get(key,d))))
   except:v=d
   db.set_setting(key,v)
  try:universe.sync()
  except Exception as exc:db.audit('UNIVERSE_SYNC_FAILED',type(exc).__name__,'error')
  configure_engine(paper_engine);return redirect(url_for('settings'))
 vals={k:db.value(k,d) for k,d in {'paper_fee_bps':40,'paper_slippage_bps':10,'paper_max_position_pct':10,'paper_trade_eur':25,'paper_interval_minutes':15,'scanner_delay_seconds':1.05,'prefilter_top_per_category':8,'research_interval_minutes':60,'paper_max_leverage':3,'paper_min_position_pct':2,'paper_min_transfer_eur':20,'paper_max_transfer_eur':250,'paper_rebalance_edge_pct':8,'paper_fx_fee_bps':10,'paper_min_hold_hours':24,'paper_cooldown_hours':12,'paper_confirmation_runs':2,'paper_max_turnovers_per_day':2,'paper_sell_hysteresis_pct':2,'paper_buy_score_threshold':62,'paper_tax_rate_pct':27.5}.items()};cats=universe.categories()
 return page(render_template_string("""<h1>Einstellungen</h1><div class=card><b class=bad>Realhandel bleibt technisch deaktiviert.</b></div><form method=post><div class=grid><div class=card><h3>Automatik</h3><label><input type=checkbox name=automation {{'checked' if enabled}}> Paper-Automatik aktivieren</label><p><label><input type=checkbox name=scanner_required {{'checked' if required}}> Valide Detailanalyse zwingend</label></p><label>Intervall Minuten<br><input type=number name=paper_interval_minutes value="{{v.paper_interval_minutes}}"></label></div><div class=card><h3>Risiko & Allokation</h3><label><input type=checkbox name=paper_leverage_enabled {{'checked' if leverage_enabled}}> Dynamischen Paper-Hebel aktivieren</label><p>Maximaler Hebel<br><input type=number name=paper_max_leverage value="{{v.paper_max_leverage}}"></p><p>Min. Position %<br><input type=number step=.1 name=paper_min_position_pct value="{{v.paper_min_position_pct}}"></p><p>Min./Max. Transfer EUR<br><input type=number name=paper_min_transfer_eur value="{{v.paper_min_transfer_eur}}"> / <input type=number name=paper_max_transfer_eur value="{{v.paper_max_transfer_eur}}"></p><p>Umschichtungs-Vorteil %<br><input type=number name=paper_rebalance_edge_pct value="{{v.paper_rebalance_edge_pct}}"></p><label>Paper-Orderwert EUR<br><input type=number name=paper_trade_eur value="{{v.paper_trade_eur}}"></label><p><label>Max. Position %<br><input type=number name=paper_max_position_pct value="{{v.paper_max_position_pct}}"></label></p></div><div class=card><h3>Research</h3><label><input type=checkbox name=research_auto_enabled {{'checked' if research_auto}}> Automatische Research-Pipeline</label><p><label>Research-Intervall Minuten<br><input type=number min=5 max=1440 name=research_interval_minutes value="{{v.research_interval_minutes}}"></label></p><label>Kandidaten je Kategorie<br><input type=number name=prefilter_top_per_category value="{{v.prefilter_top_per_category}}"></label><p><label>OHLC-Pause Sekunden<br><input type=number step=.05 name=scanner_delay_seconds value="{{v.scanner_delay_seconds}}"></label></p></div><div class=card><h3>Stabile Umschichtung</h3><p>Mindesthaltedauer Stunden<br><input type=number name=paper_min_hold_hours value="{{v.paper_min_hold_hours}}"></p><p>Cooldown Stunden<br><input type=number name=paper_cooldown_hours value="{{v.paper_cooldown_hours}}"></p><p>BestÃƒÂ¤tigungen<br><input type=number name=paper_confirmation_runs value="{{v.paper_confirmation_runs}}"></p><p>Max. Umschichtungen pro Tag<br><input type=number name=paper_max_turnovers_per_day value="{{v.paper_max_turnovers_per_day}}"></p><p>Verkaufs-Hysterese %<br><input type=number step=.1 name=paper_sell_hysteresis_pct value="{{v.paper_sell_hysteresis_pct}}"></p><p>Kauf-Score-Schwelle<br><input type=number step=.1 name=paper_buy_score_threshold value="{{v.paper_buy_score_threshold}}"></p><p>FX-GebÃƒÂ¼hr Basispunkte<br><input type=number name=paper_fx_fee_bps value="{{v.paper_fx_fee_bps}}"></p><p>Steuersatz Simulation %<br><input type=number step=.1 name=paper_tax_rate_pct value="{{v.paper_tax_rate_pct}}"></p></div></div><h2>Produktgruppen</h2>{% for c in cats %}<div class=card><label><input type=checkbox name=categories value="{{c.category}}" {{'checked' if c.enabled}}> {{c.label}}</label></div>{% endfor %}<input type=hidden name=paper_fee_bps value="{{v.paper_fee_bps}}"><input type=hidden name=paper_slippage_bps value="{{v.paper_slippage_bps}}"><button>Speichern</button></form>""",enabled=db.value('automation_enabled','false')=='true',required=db.value('scanner_required','true')=='true',research_auto=db.value('research_auto_enabled','false')=='true',leverage_enabled=db.value('paper_leverage_enabled','false')=='true',cats=cats,v=vals))
@app.get('/exports')
def exports():return page('<h1>Export</h1><div class=card><a href="{{url_for("ledger_csv")}}">Ledger CSV</a> Ã‚Â· <a href="{{url_for("portfolio_csv")}}">Portfolio-Historie CSV</a></div>')
@app.get('/exports/ledger.csv')
def ledger_csv():
 out=io.StringIO();w=csv.writer(out);w.writerow(['id','occurred_at','payload']);[w.writerow([x['id'],x['occurred_at'],x['payload']]) for x in db.rows('SELECT * FROM ledger ORDER BY occurred_at')];return Response(out.getvalue(),mimetype='text/csv',headers={'Content-Disposition':'attachment; filename=kraken-ledger.csv'})
@app.get('/exports/portfolio-history.csv')
def portfolio_csv():
 out=io.StringIO();w=csv.writer(out);w.writerow(['created_at','total_eur','priced_asset_count','unpriced_asset_count','quality']);[w.writerow(x.values()) for x in db.rows('SELECT created_at,total_eur,priced_asset_count,unpriced_asset_count,quality FROM portfolio_snapshots ORDER BY id')];return Response(out.getvalue(),mimetype='text/csv',headers={'Content-Disposition':'attachment; filename=kraken-portfolio-history.csv'})
