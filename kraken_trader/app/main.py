import csv,io,json,os,threading,time
from flask import Flask, Response, redirect, render_template, render_template_string, request, url_for
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
from display_format import display_number,display_tree
from monitoring import NotificationService,create_monitoring_blueprint
from at_income_tax import create_tax_blueprint
from real_trade import create_real_trade_blueprint,RealTradeEngine
from real_portfolio_allocator import RealPortfolioAllocator
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
for key,value in {'paper_fee_bps':opts.get('paper_fee_bps',40),'paper_slippage_bps':opts.get('paper_slippage_bps',10),'paper_max_position_pct':opts.get('paper_max_position_pct',10),'paper_trade_eur':opts.get('paper_trade_eur',25),'paper_interval_minutes':opts.get('paper_interval_minutes',15),'scanner_required':opts.get('scanner_required',True),'scanner_delay_seconds':opts.get('scanner_delay_seconds',1.05),'prefilter_top_per_category':opts.get('prefilter_top_per_category',8),'research_auto_enabled':opts.get('research_auto_enabled',False),'research_interval_minutes':opts.get('research_interval_minutes',60),'paper_leverage_enabled':opts.get('paper_leverage_enabled',False),'paper_max_leverage':opts.get('paper_max_leverage',3),'paper_min_position_pct':opts.get('paper_min_position_pct',2),'paper_min_transfer_eur':opts.get('paper_min_transfer_eur',20),'paper_max_transfer_eur':opts.get('paper_max_transfer_eur',250),'paper_rebalance_edge_pct':opts.get('paper_rebalance_edge_pct',8),'paper_fx_fee_bps':opts.get('paper_fx_fee_bps',10),'paper_min_hold_hours':opts.get('paper_min_hold_hours',24),'paper_cooldown_hours':opts.get('paper_cooldown_hours',12),'paper_confirmation_runs':opts.get('paper_confirmation_runs',2),'paper_max_turnovers_per_day':opts.get('paper_max_turnovers_per_day',2),'paper_sell_hysteresis_pct':opts.get('paper_sell_hysteresis_pct',2),'paper_buy_score_threshold':opts.get('paper_buy_score_threshold',62),'paper_tax_rate_pct':opts.get('paper_tax_rate_pct',27.5),'learning_required_horizons':opts.get('learning_required_horizons','24,168'),'learning_min_horizon_samples':opts.get('learning_min_horizon_samples',5),'learning_min_candidate_coverage':opts.get('learning_min_candidate_coverage',.5),'learning_min_net_return_improvement':opts.get('learning_min_net_return_improvement',.01),'learning_max_candidate_drawdown_pct':opts.get('learning_max_candidate_drawdown_pct',-25),'learning_max_drawdown_degradation_pct':opts.get('learning_max_drawdown_degradation_pct',2),'real_trading_enabled':opts.get('real_trading_enabled',False),'real_kill_switch':opts.get('real_kill_switch',True),'real_max_order_volume':opts.get('real_max_order_volume',0),'real_max_order_notional_eur':opts.get('real_max_order_notional_eur',0),'real_allowed_symbols':opts.get('real_allowed_symbols',''),'real_allow_market_orders':opts.get('real_allow_market_orders',False),'real_max_orders_per_day':opts.get('real_max_orders_per_day',1),'learning_min_validation_samples':opts.get('learning_min_validation_samples',5)}.items():
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
real_trade_engine=RealTradeEngine(db,client)
real_allocator=RealPortfolioAllocator(db,real_trade_engine)
app=Flask(__name__);app.wsgi_app=IngressPrefix(app.wsgi_app)
@app.after_request
def force_utf8(response):
 if response.mimetype in ('text/html','text/plain','text/csv','application/json'):response.headers['Content-Type']=response.mimetype+'; charset=utf-8';response.headers['X-Content-Type-Options']='nosniff'
 return response
stream=MarketStream(db,bool(opts.get('public_websocket_enabled',True)),opts.get('websocket_stale_seconds',30))
private_stream=PrivateStream(db,client,bool(opts.get('private_websocket_readonly_enabled',True)),opts.get('websocket_stale_seconds',30))
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
def real_balancing_scheduler():
 while True:
  minutes=max(5,int(float(db.value('real_balancing_interval_minutes','60'))));time.sleep(minutes*60)
  if db.value('real_balancing_enabled','false')=='true':real_allocator.run(automatic=True)
if os.getenv('APP_DISABLE_REAL_BALANCING_SCHEDULER')!='1':threading.Thread(target=real_balancing_scheduler,daemon=True,name='real-balancing-scheduler').start()
NAV_ITEMS=[('/', 'Übersicht'),('/portfolio','Portfolio'),('/products','Produkte'),('/scanner','Analyse'),('/paper','Paper-Handel'),('/real-trading','Realhandel'),('/process','Ablauf & Systeme'),('/controlled-learning','Lernen'),('/news-learning','Nachrichten-Lernen'),('/fees','Gebühren'),('/data-quality','Datenqualität'),('/backtests','Backtests'),('/decision-matrix','Regelmatrix'),('/settings','Einstellungen'),('/tax-info','Steuerinfo AT'),('/event-dashboard','Ereignisse'),('/audit','Audit'),('/exports','Export')]
def page(body,**ctx):
 clean={k:display_tree(v) for k,v in ctx.items()}
 return render_template('base.html', body=render_template_string(body, **clean), app_version=APP_VERSION, nav=[(request.script_root + href, label) for href, label in NAV_ITEMS], current_path=request.script_root + request.path)
notifications=NotificationService(db)
app.register_blueprint(create_monitoring_blueprint(db,page))
app.register_blueprint(create_tax_blueprint(db,page))
app.register_blueprint(create_real_trade_blueprint(db,client,page))
@app.get('/')
def index():
 portfolio=db.rows('SELECT total_eur,quality,created_at FROM portfolio_snapshots ORDER BY id DESC LIMIT 1');stream_state=stream.status();private_state=private_stream.status();market_rows=db.rows('SELECT received_at FROM live_prices ORDER BY received_at DESC LIMIT 1');private_rows=db.rows('SELECT received_at FROM private_balances ORDER BY received_at DESC LIMIT 1');stream_state['dashboard_state']='DATEN VERFÜGBAR' if market_rows else ('DEAKTIVIERT' if not stream_state.get('configured_enabled') else stream_state.get('effective_state','NOCH KEINE DATEN'));private_state['dashboard_state']='KONTODATEN VERFÜGBAR' if private_rows or portfolio else ('DEAKTIVIERT' if not private_state.get('configured_enabled') else private_state.get('effective_state','NOCH KEINE DATEN'));pending=db.rows("SELECT COUNT(*) n FROM learning_candidates WHERE status='PENDING'");latest_fee=fees.latest()
 return page("""<h1>Übersicht</h1><p class=lead>Zentrale Arbeitsoberfläche für Daten, Analyse, Simulation und kontrollierte Lernfreigaben. Jeder Schritt bleibt nachvollziehbar; reale Orders sind technisch ausgeschlossen.</p><div class=grid><div class=card><h3>Portfolio</h3><div class=metric>{{portfolio[0].total_eur if portfolio else '→'}} €</div><span class=pill>{{portfolio[0].quality if portfolio else 'Noch kein Snapshot'}}</span></div><div class=card><h3>Marktdaten</h3><div class=metric>{{stream.dashboard_state}}</div><small>Public WebSocket: {{stream.effective_state}}</small></div><div class=card><h3>Kontodaten</h3><div class=metric>{{private.dashboard_state}}</div><small>Read-only Private WebSocket: {{private.effective_state}}</small></div><div class=card><h3>Lernfreigaben</h3><div class=metric>{{pending[0].n if pending else 0}}</div><small>offene Kandidaten</small></div><div class=card><h3>Gebührenprofil</h3><div class=metric>{{fee.status if fee else '→'}}</div><small>{{fee.created_at if fee else 'Noch nicht abgerufen'}}</small></div></div><div class=card><h2>Empfohlener Ablauf</h2><div class=steps><div class=step><div><b>Daten verbinden und prüfen</b><br><span class=muted>API, Portfolio und Datenqualität kontrollieren.</span><br><a href="{{url_for('api_status')}}">API öffnen</a> · <a href="{{url_for('data_quality')}}">Datenqualität</a></div></div><div class=step><div><b>Produkte und Gebühren aktualisieren</b><br><a href="{{url_for('products_page')}}">Produkte</a> · <a href="{{url_for('fees_page')}}">Gebühren</a></div></div><div class=step><div><b>Analyse und Simulation ausführen</b><br><a href="{{url_for('scanner_page')}}">Analyse</a> · <a href="{{url_for('paper')}}">Paper-Handel</a></div></div><div class=step><div><b>Lernkandidaten bewusst freigeben</b><br><span class=muted>Ohne ausdrückliche Freigabe ändert sich kein aktiver Parameter.</span><br><a href="{{url_for('controlled_learning_page')}}">Kontrolliertes Lernen</a><a href="{{url_for('news_learning_page')}}">Nachrichten-Lernen</a></div></div></div></div>""",portfolio=portfolio,stream=stream_state,private=private_state,pending=pending,fee=latest_fee)

@app.get('/process')
def process_page():
 systems=[
  {'name':'Marktuniversum','role':'wählt verfügbare Produkte','status':'Kernpfad'},
  {'name':'Nachrichten + externe AI','role':'liefert gefilterte Nachrichtenmerkmale, sofern konfiguriert','status':'Kernpfad optional'},
  {'name':'Prefilter + Scanner','role':'reduziert Kandidaten und berechnet Marktmerkmale','status':'Kernpfad'},
  {'name':'Aktive Strategieprofile','role':'wandelt Merkmale je Produktfamilie in BUY, HOLD oder AVOID um','status':'Kernpfad'},
  {'name':'Kontrolliertes Lernen','role':'sucht bessere Parameter; Aktivierung nur nach Freigabe','status':'Kernpfad indirekt'},
  {'name':'Nachrichten-Lernen','role':'optimiert lokale Nachrichtenparameter; Aktivierung nur nach Freigabe','status':'Kernpfad indirekt'},
  {'name':'Prognosebewertung + Forex Shadow','role':'liefert Holdout-, Kosten- und Qualitätsnachweise','status':'Qualitätssicherung'},
  {'name':'Paper Engine','role':'simuliert Orders und Portfolioeffekte','status':'Vorstufe, nicht Live-Ausführung'},
  {'name':'Gebührenprofil + Execution Costs','role':'liefert Kostenschätzungen','status':'Kernpfad Bewertung'},
  {'name':'Portfolio Allocator + Decision Matrix','role':'unterstützt Zielgewicht und Regeln','status':'Noch nicht automatisch an Live-Order gekoppelt'},
  {'name':'Backtests','role':'historische Prüfung','status':'Qualitätssicherung'},
  {'name':'RealTradeEngine + Kraken','role':'validiert oder übermittelt die ausdrücklich bestätigte Order','status':'Live-Ausführung'},
  {'name':'Private WebSocket + Portfolio Sync','role':'liest Kontostand und Ausführungsereignisse zurück','status':'Nachkontrolle'},
  {'name':'Audit, Monitoring, Steuerinfo','role':'Nachweis, Warnungen und Auswertung','status':'Begleitend'}]
 return page("""<h1>Von der Information zur realen Order</h1><p class=lead>Diese Seite zeigt den tatsächlich implementierten Datenweg und trennt automatische Analyse, bewusste Freigaben und Live-Ausführung.</p><div class=flow>
 {% for title,text in steps %}<div class=card><div class=flowstep><span class=num>{{loop.index}}</span><div><h3>{{title}}</h3><p>{{text}}</p></div></div></div>{% endfor %}</div>
 <h2>Werden alle Systeme verwendet?</h2><div class=card><p><b>Nein, nicht alle Systeme liegen direkt im Live-Entscheidungspfad.</b> Analyse, aktive Lernparameter, Kosten und Freigabegates wirken auf die Vorbereitung. Paper-Handel, Backtests, Steuerinfo, Monitoring und Audit sind bewusste Prüf- oder Begleitsysteme. Portfolio Allocator und Decision Matrix sind derzeit nicht automatisch mit dem Live-Auftragsformular verdrahtet. Das verhindert, dass eine interne Empfehlung ohne ausdrückliche Kontrolle zur Order wird.</p></div>
 <div class=tablewrap><table><tr><th>System</th><th>Aufgabe</th><th>Einordnung</th></tr>{% for x in systems %}<tr><td><b>{{x.name}}</b></td><td>{{x.role}}</td><td><span class=badge>{{x.status}}</span></td></tr>{% endfor %}</table></div>""",steps=[
 ('Information erfassen','REST, öffentliche Marktdaten, Produktdaten und optional Nachrichten werden eingelesen. Private Kontodaten bleiben davon getrennt.'),
 ('Qualität und Kosten prüfen','Datenqualität, Gebührenprofil, Spread, Volatilität und geschätzte Roundtrip-Kosten werden geprüft.'),
 ('Kandidaten reduzieren','Marktuniversum, Prefilter und Scanner bestimmen die analysierten Symbole und erzeugen Merkmale.'),
 ('Signal berechnen','Das aktive freigegebene Strategieprofil der Produktfamilie erzeugt BUY, HOLD oder AVOID. Nachrichtenmerkmale können einfließen, wenn der Nachrichtenpfad Daten liefert.'),
 ('Lernen und validieren','Beide Lernloops suchen automatisch Parameterkandidaten. Zeitlicher Holdout, Walk-forward-, Abdeckungs-, Rendite- und Drawdown-Gates entscheiden, ob ein Kandidat zur Freigabe angeboten wird.'),
 ('Parameter bewusst aktivieren','Ein bestandener Kandidat wird erst nach einem Klick atomar als neue aktive Version freigegeben. Ohne Freigabe bleibt das bisherige Profil aktiv.'),
 ('Zuerst simulieren','Paper Engine und Kraken-Validierungsmodus prüfen den Ablauf ohne Live-Order. Backtests und Prognoseauswertung liefern zusätzliche Qualitätsnachweise.'),
 ('Live-Auftrag vorbereiten','Symbol, Seite, Typ, Volumen und gegebenenfalls Limitpreis werden eingegeben. Allowlist sowie Volumen-, Auftragswert-, Market-Order- und Tageslimits werden geprüft.'),
 ('Realhandel freigeben','Realhandel muss aktiviert, der Kill-Switch aufgehoben und die Freigabephrase bestätigt sein. Das daraufhin erzeugte Token ist zeitlich begrenzt und nur einmal nutzbar.'),
 ('Order übermitteln und überwachen','RealTradeEngine ruft Krakens AddOrder-Endpunkt auf. Antwort, Audit-Ereignis und private Ausführungsdaten dienen der Nachkontrolle.')],systems=systems)

@app.get('/health')
def health():return {'status':'ok','version':APP_VERSION,'real_trading':db.value('real_trading_enabled','false')=='true' and db.value('real_kill_switch','true')!='true','websocket_status':db.value('websocket_status','not_checked'),'market_stream':stream.status(),'private_stream':private_stream.status()}
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
 return page('<h1>API</h1><div class=card><p>REST: <b>{{rest}}</b> · privater WebSocket: <b>{{ws}}</b></p><form method=post><button name=action value=rest>REST prüfen</button> <button name=action value=websocket>WebSocket-Berechtigung prüfen</button></form><p>{{msg}}</p><p class=muted>Öffentliche WebSocket-Marktdaten benötigen keinen API-Schlüssel. Für private Kontokanäle wird die Kraken-Berechtigung "Access WebSockets API" benötigt.</p></div><div class=card><h2>Öffentlicher WebSocket-v2-Livestream</h2><p>Status: <b>{{stream.effective_state}}</b> · Kraken: {{stream.system_status or "→"}} · Symbole: {{stream.symbol_count}}</p><p>Letzte Nachricht: {{stream.last_message_at or "→"}}</p><table>{% for x in prices %}<tr><td>{{x.symbol}}</td><td>{{x.last}}</td><td>Bid {{x.bid or "→"}}</td><td>Ask {{x.ask or "→"}}</td><td>{{x.received_at}}</td></tr>{% endfor %}</table></div><div class=card><h2>Privater Read-only WebSocket v2</h2><p>Status: <b>{{private.effective_state}}</b> · Balances-Sequenz: {{private.sequences.get("balances","→")}} · Executions-Sequenz: {{private.sequences.get("executions","→")}}</p><p>Letzte Nachricht: {{private.last_message_at or "→"}} · Fehler: {{private.last_error or "→"}}</p><h3>Live-Balances</h3><table>{% for x in private_balances %}<tr><td>{{x.asset}}</td><td>{{x.balance}}</td><td>Seq {{x.sequence}}</td><td>{{x.received_at}}</td></tr>{% endfor %}</table><h3>Letzte Ausführungsereignisse</h3><table>{% for x in executions %}<tr><td>{{x.event_type}}</td><td>{{x.symbol or "→"}}</td><td>{{x.order_id or "→"}}</td><td>Seq {{x.sequence}}</td><td>{{x.received_at}}</td></tr>{% endfor %}</table></div>',rest=db.value('kraken_status'),ws=db.value('websocket_status'),msg=msg,stream=stream.status(),prices=db.rows('SELECT * FROM live_prices ORDER BY symbol'),private=private_stream.status(),private_balances=db.rows('SELECT * FROM private_balances ORDER BY asset'),executions=db.rows('SELECT event_type,order_id,symbol,sequence,received_at FROM private_execution_events ORDER BY received_at DESC LIMIT 50'))
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
 return page('''<h1>Realportfolio</h1><div class=card><form method=post><button>Kraken vollständig synchronisieren</button></form><p>{{msg}}</p><p class=muted>Nullpositionen bleiben als HISTORICAL_ZERO erhalten, wenn das Asset in der Ledger-Historie vorkam.</p><table><tr><th>Asset</th><th>Menge</th><th>EUR-Kurs</th><th>EUR-Wert</th><th>Status</th></tr>{% for x in rows %}<tr><td>{{x.display_name}} <small>{{x.asset}}</small></td><td>{{x.amount}}</td><td>{{x.eur_price or "→"}}</td><td>{{x.eur_value or "→"}}</td><td><span class=tag>{{x.classification}}</span></td></tr>{% endfor %}</table></div><div class=card><h2>Historie</h2><table><tr><th>Zeit</th><th>Gesamt EUR</th><th>Qualität</th><th>Unbewertet</th></tr>{% for x in history %}<tr><td>{{x.created_at}}</td><td>{{x.total_eur}}</td><td>{{x.quality}}</td><td>{{x.unpriced_asset_count}}</td></tr>{% endfor %}</table></div>''',rows=rows,history=history,msg=msg)
@app.get('/scanner')
def scanner_page():
 rows=db.rows("SELECT w.symbol,w.category,w.prefilter_score,w.status,s.score,s.signal,s.quality FROM research_watchlist w LEFT JOIN scanner_results s ON s.symbol=w.symbol ORDER BY CAST(w.prefilter_score AS REAL) DESC");job=pipeline.latest();sources=news_prefilter.sources();versions=db.rows('SELECT * FROM watchlist_versions ORDER BY id DESC LIMIT 10');stats=db.rows("SELECT COUNT(*) total,COALESCE(SUM(direction_correct),0) correct FROM forecast_evaluations")
 return page(render_template_string("""<h1>Research-Scanner</h1><p class=muted>Globale Nachrichten und Primärquellen → ’ Taxonomie → ’ Vorfilter → ’ versionierte Watchlist → ’ Detailanalyse → ’ Prognosevergleich. Nachrichten sind kein Handelssignal.</p><form method=post action="{{url_for('run_scanner')}}"><button>Research-Pipeline starten</button></form>{% if job %}<div class=card><b>Job #{{job.id}} {{job.status}}</b> · {{job.stage}} · {{job.progress_current}}/{{job.progress_total}}<p class=bad>{{job.error or ''}}</p></div>{% endif %}<h2>Quellen</h2><table>{% for x in sources %}<tr><td>{{x.name}}</td><td>{{x.source_class}}</td><td>{{x.last_status or 'offen'}}</td><td>{{x.last_error or '→'}}</td><td>{{x.last_checked_at or '→'}}</td></tr>{% endfor %}</table><h2>Watchlist</h2><table><tr><th>Symbol</th><th>Kategorie</th><th>Vorfilter</th><th>Status</th><th>Detailscore</th><th>Signal</th></tr>{% for x in rows %}<tr><td>{{x.symbol}}</td><td>{{x.category}}</td><td>{{x.prefilter_score}}</td><td>{{x.status}}</td><td>{{x.score or '→'}}</td><td>{{x.signal or '→'}}</td></tr>{% endfor %}</table><h2>Versionen und Prognosen</h2><p>Ausgewertet: {{stats.total if stats else 0}} · Richtung richtig: {{stats.correct if stats else 0}}</p><table>{% for x in versions %}<tr><td>#{{x.id}}</td><td>{{x.created_at}}</td><td>{{x.item_count}} Kandidaten</td><td>{{x.status}}</td></tr>{% endfor %}</table>""",rows=rows,job=job,sources=sources,versions=versions,stats=stats[0] if stats else None))
@app.post('/scanner/run')
def run_scanner():db.audit('RESEARCH_PIPELINE_REQUEST',json.dumps(pipeline.start()));return redirect(url_for('scanner_page'))
@app.get('/api/research-job')
def research_job_api():return pipeline.latest() or {'status':'NONE'}
@app.get('/paper')
def paper():
 cash,pv,total,missing=paper_engine.equity();positions=paper_engine.positions();trades=db.rows('SELECT * FROM paper_trades ORDER BY id DESC LIMIT 100')
 return page(render_template_string('''<h1>Musterdepot</h1><div class=grid><div class=card><h3>Gesamtwert</h3><b>€ {{total}}</b></div><div class=card><h3>Cash</h3><b>€ {{cash}}</b></div><div class=card><h3>Positionen</h3><b>€ {{pv}}</b></div><div class=card><h3>Datenqualität</h3><b>{{'VALID' if not missing else 'INCOMPLETE'}}</b></div></div><form method=post action="{{url_for('run_paper')}}"><p><button>Paper-Strategie jetzt ausführen</button></p></form><h2>Positionen</h2><table><tr><th>Symbol</th><th>Menge</th><th>˜ Kosten EUR</th></tr>{% for x in positions %}<tr><td>{{x.symbol}}</td><td>{{x.quantity}}</td><td>{{x.avg_cost_eur}}</td></tr>{% endfor %}</table><h2>Simulierte Trades</h2><table><tr><th>Zeit</th><th>Symbol</th><th>Seite</th><th>Menge</th><th>Ausführung</th><th>Gebühr</th><th>Slippage</th><th>Grund</th></tr>{% for x in trades %}<tr><td>{{x.created_at}}</td><td>{{x.symbol}}</td><td>{{x.side}}</td><td>{{x.quantity}}</td><td>{{x.execution_price}}</td><td>{{x.fee_eur}}</td><td>{{x.slippage_eur}}</td><td>{{x.reason}}</td></tr>{% endfor %}</table>''',cash=cash,pv=pv,total=total,missing=missing,positions=positions,trades=trades))
@app.post('/paper/run')
def run_paper():
 try:run_paper_cycle()
 except Exception as exc:db.audit('PAPER_MANUAL_RUN_FAILED',type(exc).__name__+': '+str(exc)[:300],'error')
 return redirect(url_for('paper_decisions'))
@app.get('/paper/decisions')
def paper_decisions():return page(render_template_string('''<h1>Paper-Entscheidungen</h1><p class=muted>Deterministische Baseline: BUY ab +1 % 24h, SELL ab -1,5 % 24h; nur freigegebene Produkte, nur bei LIVE-Daten und aktivierter Analyse-/Paper-Automatik.</p><table><tr><th>Zeit</th><th>Symbol</th><th>Aktion</th><th>Score</th><th>Qualität</th><th>Ausgeführt</th><th>Begründung</th></tr>{% for x in r %}<tr><td>{{x.created_at}}</td><td>{{x.symbol}}</td><td>{{x.action}}</td><td>{{x.score}} %</td><td>{{x.data_quality}}</td><td>{{'ja' if x.executed else 'nein'}}</td><td>{{x.reason}}</td></tr>{% endfor %}</table>''',r=db.rows('SELECT * FROM paper_decisions ORDER BY id DESC LIMIT 500')))
@app.route('/learning',methods=['GET','POST'])
def learning_page():
 msg=''
 if request.method=='POST':
  action=request.form.get('action');result=learning.create_proposal() if action=='create' else learning.approve_latest();msg=json.dumps(result,ensure_ascii=False)
 latest=learning.latest();rows=learning.rows()
 return page(render_template_string('''<h1>Lernfreigaben</h1><div class=card><p>Die Strategie ändert keine Parameter automatisch. Ein Vorschlag wird zunächst angezeigt und erst mit deiner Freigabe als gemeinsame Version aktiviert.</p><form method=post><button name=action value=create>Neuen Vorschlag berechnen</button> {% if latest and latest.status=='PENDING' %}<button name=action value=approve>Alle neun Parameter mit einem Klick bestätigen</button>{% endif %}</form><p>{{msg}}</p>{% if latest %}<p>Status: <b>{{latest.status}}</b> · Stichprobe: {{latest.sample_count}} · Trefferquote: {{latest.accuracy or '→'}}</p>{% endif %}</div><table><tr><th>Parameter</th><th>Aktuell</th><th>Vorschlag</th><th>Zulässiger Bereich</th></tr>{% for x in rows %}<tr><td>{{x.label}}</td><td>{{x.current}}</td><td>{{x.proposed if x.proposed is not none else '→'}}</td><td>{{x.minimum}} bis {{x.maximum}}</td></tr>{% endfor %}</table>''',latest=latest,rows=rows,msg=msg))





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
 return page("""<h1>Kontrolliertes Lernen</h1><p class=lead>Neue Strategieparameter werden zuerst als wirkungsloser Kandidat geprüft. Sie werden erst nach bestandenen Gates und Ihrer ausdrücklichen Freigabe als neue gemeinsame Version aktiviert.</p>{% if result %}<div class=card><b>Ergebnis:</b> {{result}}</div>{% endif %}<div class=grid><div class=card><h3>1. Familie wählen</h3><form method=post><label>Parameterfamilie<select name=family><option value=forex {% if family=='forex' %}selected{% endif %}>Forex</option><option value=xstocks {% if family=='xstocks' %}selected{% endif %}>xStocks</option><option value=crypto_spot {% if family=='crypto_spot' %}selected{% endif %}>Krypto Spot</option></select></label><button name=action value=propose>Kandidaten berechnen</button></form><p class=muted>Das Berechnen verändert keine aktiven Parameter.</p></div><div class=card><h3>Aktuelle Versionen (Aktive Version)</h3><table><tr><th>Familie</th><th>Version</th><th>Offen</th><th>Letzter Kandidat</th></tr>{% for item in family_overview %}<tr{% if item.family==family %} class=selected{% endif %}><td><a href="{{url_for('controlled_learning_page',family=item.family)}}">{{family_labels.get(item.family,item.family)}}</a></td><td><b>v{{item.active_version if item.active_version is not none else '→'}}</b></td><td><span class=pill>{{item.pending_count}}</span></td><td>{% if item.latest_candidate_id %}#{{item.latest_candidate_id}} · {{item.latest_status}}{% else %}Noch keiner{% endif %}</td></tr>{% endfor %}</table><small>Familie anklicken, um Kandidaten, Historie und Metriken gezielt zu filtern.</small><details><summary>Aktive Parameter für {{family_labels.get(family,family)}} anzeigen</summary><table>{% for key,value in active_params.items() %}<tr><td>{{key}}</td><td>{{value}}</td></tr>{% endfor %}</table></details></div><div class=card><h3>Freigaberegeln</h3><p>{{gate_policy.required_horizons|join(', ')}} Stunden</p><small>Mindeststichprobe {{gate_policy.minimum_horizon_samples}}, Mindestabdeckung {{gate_policy.minimum_candidate_coverage}}, positive Nettorenditeverbesserung und Drawdown-Grenzen.</small></div></div><h2>Kandidaten</h2>{% for x in candidates %}<div class=card><div class=grid><div><span class=pill>{{x.status}}</span><h3>#{{x.id}} · {{x.family}}</h3><p>Basisversion {{x.base_version}}, Stichprobe {{x.sample_count}}</p></div><div><b>Trefferquote</b><br>Aktiv {{'%.2f'|format(x.active_accuracy|float*100)}} %<br>Kandidat {{'%.2f'|format(x.candidate_accuracy|float*100)}} %</div><div><b>Verbesserung</b><br>{{'%.2f'|format(x.improvement|float*100)}} Prozentpunkte<br><small>Gates {{x.gate_passed}} / {{x.gate_total}}</small></div></div><details><summary>Parametervergleich</summary><div class=tablewrap><table><tr><th>Parameter</th><th>Aktiv</th><th>Kandidat</th><th>Änderung</th></tr>{% for key,value in x.parameters.items() %}<tr><td>{{key}}</td><td>{{active_params.get(key,'→') if x.family==family else 'siehe aktive Familienversion'}}</td><td>{{value}}</td><td>{% if x.family==family and key in active_params %}{{'%+.4f'|format(value|float-active_params[key]|float)}}{% else %}→{% endif %}</td></tr>{% endfor %}</table></div></details><details><summary>Gate-Prüfung</summary><div class=tablewrap><table><tr><th>Gate</th><th>Horizont</th><th>Ergebnis</th><th>Ist</th><th>Soll</th></tr>{% for g in x.gates %}<tr><td>{{g.gate}}</td><td>{{g.horizon_hours or 'alle'}}</td><td class={{'ok' if g.passed else 'error'}}>{{'Bestanden' if g.passed else 'Nicht bestanden'}}</td><td>{{g.actual}}</td><td>{{g.required}}</td></tr>{% endfor %}</table></div></details>{% if x.status=='PENDING' %}<form method=post><input type=hidden name=family value={{x.family}}><input type=hidden name=candidate_id value={{x.id}}><button name=action value=approve>Nach erneuter Prüfung freigeben</button><button class=danger name=action value=reject>Ablehnen</button></form><p class=warning>Die Freigabe aktiviert alle neun Parameter atomar als neue Version.</p>{% endif %}</div>{% else %}<div class=card>Noch keine Kandidaten vorhanden.</div>{% endfor %}<h2>Horizontmetriken</h2><div class=tablewrap><table><tr><th>Kandidat</th><th>Horizont</th><th>Stichprobe</th><th>Abdeckung aktiv / Kandidat</th><th>Nettorendite aktiv / Kandidat</th><th>Drawdown aktiv / Kandidat</th></tr>{% for x in metrics %}<tr><td>{{x.candidate_id}}</td><td>{{x.horizon_hours}} h</td><td>{{x.sample_count}}</td><td>{{x.active_coverage}} / {{x.candidate_coverage}}</td><td>{{x.active_net_return}} / {{x.candidate_net_return}}</td><td>{{x.active_max_drawdown}} / {{x.candidate_max_drawdown}}</td></tr>{% endfor %}</table></div>""",result=result,family=family,candidates=views,versions=versions,metrics=learning_metrics,gate_policy=gate_policy,active=active,active_versions=active_versions,family_overview=family_overview,active_params=active_params,family_labels=family_labels)


@app.route('/news-learning',methods=['GET','POST'])
def news_learning_page():
 result=None
 if request.method=='POST':
  action=request.form.get('action')
  if action=='analyze':result=external_news_ai.analyze_pending()
  elif action=='compare':result=news_learning.propose()
  elif action in ('approve','reject'):result=news_learning.decide(int(request.form.get('candidate_id')),action)
 active=news_learning.active();candidates=news_learning.candidates();versions=news_learning.versions();data_status=news_learning.data_status()
 return page(render_template_string("""<h1>Nachrichten-AI und lokale Auswertung</h1><div class=card><p>Die externe Nachrichten-AI dient nur als Vergleichsinstanz. Neue lokale Parameter werden im Schattenmodus geprüft und niemals automatisch aktiviert.</p><p>Aktive lokale Version: <b>v{{active.version}}</b></p><div class=grid><div><b>Nachrichten</b><div class=metric>{{data_status.news_items}}</div></div><div><b>Gültige AI-Auswertungen</b><div class=metric>{{data_status.ai_valid}} / {{data_status.required}}</div></div><div><b>Noch erforderlich</b><div class=metric>{{data_status.missing}}</div></div><div><b>Nicht verarbeitet / ungültig</b><div class=metric>{{data_status.ai_unprocessed}} / {{data_status.ai_invalid}}</div></div></div>{% if data_status.ready %}<p class=ok>Die Datenbasis ist für einen Vergleich bereit.</p>{% elif data_status.status=='NO_NEWS_ITEMS' %}<p class=warning>Es sind noch keine Nachrichten vorhanden. Zuerst Nachrichten abrufen.</p>{% elif data_status.status=='NO_VALID_AI_RESULTS' %}<p class=warning>Es gibt noch keine gültigen AI-Auswertungen. AI-Konfiguration prüfen und anschließend "AI auswerten" verwenden.</p>{% else %}<p class=warning>Für den Vergleich fehlen noch {{data_status.missing}} gültige AI-Auswertungen.</p>{% endif %}<form method=post><button name=action value=analyze>AI auswerten</button> <button name=action value=compare {% if not data_status.ready %}disabled title="Mindestens {{data_status.required}} gültige AI-Auswertungen erforderlich"{% endif %}>Vergleich berechnen</button></form>{% if result %}<details open><summary>Ergebnis</summary><pre>{{result|tojson(indent=2)}}</pre></details>{% endif %}</div><h2>Kandidaten</h2>{% if candidates %}<table><tr><th>ID</th><th>Status</th><th>Gesamt</th><th>Training / Validierung</th><th>Stabile Fenster</th><th>Verbesserung</th><th>Freigabe</th></tr>{% for x in candidates %}<tr><td>#{{x.id}}</td><td>{{x.status}}</td><td>{{x.sample_count}}</td><td>{{x.training_count}} / {{x.validation_count}}</td><td>{{x.stable_window_count}} / {{x.required_stable_windows}}</td><td>{{x.improvement}}</td><td>{% if x.status=='PENDING' %}<form method=post><input type=hidden name=candidate_id value={{x.id}}><button name=action value=approve>Freigeben</button><button name=action value=reject>Ablehnen</button></form>{% endif %}</td></tr>{% endfor %}</table>{% else %}<div class=card>Noch keine Vergleichskandidaten vorhanden.</div>{% endif %}<h2>Lokale Versionen</h2><table>{% for x in versions %}<tr><td>v{{x.version}}</td><td>{{x.status}}</td><td>{{x.source}}</td><td><small>{{x.parameters_json}}</small></td></tr>{% endfor %}</table>""",active=active,candidates=candidates,versions=versions,result=result,data_status=data_status))

@app.get('/products')
def products_page():
 rows=product_view.rows();return page(render_template_string("""<h1>Kanonische Produkte</h1><p class=muted>Eine Identität je Basiswert und Anlageklasse. Alternative Ausführungspaare bleiben sichtbar, während genau ein Paar ausgewählt wird.</p><table><tr><th>Identität</th><th>Klasse</th><th>Gewähltes Paar</th><th>Alternativen</th><th>EUR-Kosten</th><th>USD-Kosten</th><th>Letzte Wahl</th><th>Grund</th><th>Position</th></tr>{% for x in rows %}<tr><td>{{x.canonical_id}}</td><td>{{x.asset_class}}</td><td>{{x.selected_symbol or '→'}}</td><td>{{x.alternatives|join(', ')}}</td><td>{{x.eur_cost or '→'}}</td><td>{{x.usd_cost or '→'}}</td><td>{{x.updated_at}}</td><td>{{x.selection_reason}}</td><td>{% if x.position_symbol %}{{x.position_symbol}} / {{x.position_quantity}}{% else %}→{% endif %}</td></tr>{% endfor %}</table>""",rows=rows))
@app.get('/decision-matrix')
def decision_matrix_page():
 rows=decision_matrix.recent();return page(render_template_string("""<h1>Umschichtungs-Regelmatrix</h1><p class=muted>Jede Regel wird einzeln gespeichert. Die erste nicht erfüllte Regel ist der sichtbare Blockierungsgrund.</p><table><tr><th>Zeit</th><th>Produkt</th><th>Aktion</th><th>Regel</th><th>Status</th><th>Begründung</th></tr>{% for x in rows %}<tr><td>{{x.created_at}}</td><td>{{x.canonical_id}}<br><small>{{x.symbol}}</small></td><td>{{x.action}}</td><td>{{x.rule_key}}</td><td class={{'good' if x.passed else 'bad'}}>{{'ERFÜLLT' if x.passed else 'BLOCKIERT'}}</td><td>{{x.reason}}</td></tr>{% endfor %}</table>""",rows=rows))
@app.route('/forex-shadow',methods=['GET','POST'])
def forex_shadow_page():
 result=forex_shadow.run() if request.method=='POST' else None;rows=forex_shadow.comparisons();return page(render_template_string("""<h1>Forex v2 Schattenmodus</h1><div class=card><p><b>Keine Handelswirkung.</b> forex-v2 wird parallel zu forex-v1 ausgewertet. Alle Eingänge werden versioniert gespeichert. Nicht verfügbare Makrofaktoren bleiben ausdrücklich <code>null</code> und verbessern den Score nicht.</p><form method=post><button>Schattenbewertung ausführen</button></form><p>{{result or ''}}</p></div><table><tr><th>Zeit</th><th>Symbol</th><th>Aktiv</th><th>Kandidat</th><th>Abweichung</th></tr>{% for x in rows %}<tr><td>{{x.created_at}}</td><td>{{x.symbol}}</td><td>{{x.active_model}}: {{x.active_score}} / {{x.active_signal}}</td><td>{{x.candidate_model}}: {{x.candidate_score}} / {{x.candidate_signal}}</td><td>{{'ja' if x.disagrees else 'nein'}}</td></tr>{% endfor %}</table>""",rows=rows,result=result))
@app.route('/fees',methods=['GET','POST'])
def fees_page():
 result=None
 if request.method=='POST':
  symbols=[x['symbol'] for x in db.rows("SELECT symbol FROM market_universe WHERE LOWER(COALESCE(status,'online')) IN ('online','post_only','limit_only')")];result=fees.refresh(symbols)
 latest=fees.latest();rows=fees.rows();return page(render_template_string("""<h1>Kontospezifische Gebühren</h1><div class=card><p>Read-only Abruf der 30-Tage-Handelsaktivität und paarbezogenen Maker-/Taker-Stufen. Bei fehlender Berechtigung bleiben die konfigurierten konservativen Gebühren aktiv.</p><form method=post><button>Gebührenprofil abrufen</button></form><p>{{result or ''}}</p>{% if latest %}<p>Status: <b>{{latest.status}}</b> · Quelle: {{latest.source}} · Volumen: {{latest.volume_30d or '→'}} {{latest.volume_currency or ''}} · {{latest.created_at}}</p><p class=bad>{{latest.error_reason or ''}}</p>{% endif %}</div><table><tr><th>Symbol</th><th>Maker bps</th><th>Taker bps</th><th>Quelle</th><th>Zeitpunkt</th></tr>{% for x in rows %}<tr><td>{{x.symbol}}</td><td>{{x.maker_bps}}</td><td>{{x.taker_bps}}</td><td>{{x.source}}</td><td>{{x.created_at}}</td></tr>{% endfor %}</table>""",result=result,latest=latest,rows=rows))
