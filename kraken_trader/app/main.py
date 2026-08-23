import csv,io,json,os
from flask import Flask,Response,redirect,render_template_string,request,url_for
from db import DB
from kraken import KrakenClient,KrakenError
from portfolio_sync import build_rows,normalize_asset
from ws_market import MarketStream
from ws_private import PrivateStream
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
db=DB(os.path.join(DATA,'kraken_trader.db'));db.init(opts.get('paper_start_eur',1000));client=KrakenClient(opts.get('kraken_api_key',''),opts.get('kraken_api_secret',''))
app=Flask(__name__);app.wsgi_app=IngressPrefix(app.wsgi_app)
stream=MarketStream(db,bool(opts.get('public_websocket_enabled',False)),opts.get('websocket_stale_seconds',30))
private_stream=PrivateStream(db,client,bool(opts.get('private_websocket_readonly_enabled',False)),opts.get('websocket_stale_seconds',30))
def ws_asset(name):return 'BTC' if name=='XBT' else name
def restore_stream_symbols():
 rows=db.rows("SELECT display_name FROM portfolio_assets WHERE classification='HELD'");stream.set_symbols([ws_asset(x['display_name'])+'/EUR' for x in rows if x['display_name']!='EUR']);stream.start()
restore_stream_symbols();private_stream.start()
BASE='''<!doctype html><html lang=de><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1"><style>:root{color-scheme:dark;--b:#09111f;--c:#142238;--a:#55c6ff;--m:#a9b8cb;--g:#5ee090;--r:#ff7272}*{box-sizing:border-box}body{margin:0;background:var(--b);color:#eef6ff;font:15px system-ui}nav{display:flex;gap:18px;flex-wrap:wrap;padding:16px;background:#101b2d;position:sticky;top:0}a{color:var(--a);text-decoration:none}main{padding:20px;max-width:1200px;margin:auto}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px}.card{background:var(--c);padding:18px;border-radius:14px;margin-bottom:14px}.muted{color:var(--m)}.good{color:var(--g)}.bad{color:var(--r)}table{width:100%;border-collapse:collapse}td,th{text-align:left;padding:9px;border-bottom:1px solid #29405f}button{background:var(--a);border:0;border-radius:8px;padding:10px 14px;font-weight:700}.tag{padding:3px 7px;border-radius:9px;background:#243956}</style></head><body><nav><b>Kraken Trader dev.5</b><a href="{{url_for('dashboard')}}">Übersicht</a><a href="{{url_for('api_status')}}">API</a><a href="{{url_for('portfolio')}}">Portfolio</a><a href="{{url_for('paper')}}">Musterdepot</a><a href="{{url_for('audit')}}">Audit</a><a href="{{url_for('settings')}}">Einstellungen</a><a href="{{url_for('exports')}}">Export</a></nav><main>{{body|safe}}</main></body></html>'''
def page(body,**ctx):return render_template_string(BASE,body=render_template_string(body,**ctx))
@app.get('/')
def dashboard():
 latest=db.rows('SELECT * FROM portfolio_snapshots ORDER BY id DESC LIMIT 1');return page('<h1>HA Kraken Trader</h1><div class=grid><div class=card><h2>Realportfolio</h2><p>{{latest.total_eur if latest else "Noch nicht synchronisiert"}} EUR</p><span class="{{"good" if latest and latest.quality=="VALID" else "bad"}}">{{latest.quality if latest else "UNKNOWN"}}</span></div><div class=card><h2>Sicherheit</h2><p>Echte Orders sind serverseitig nicht implementiert.</p><b>REAL TRADING: AUS</b></div></div>',latest=latest[0] if latest else None)
@app.get('/health')
def health():return {'status':'ok','version':'0.1.0-dev.5','real_trading':False,'websocket_status':db.value('websocket_status','not_checked'),'market_stream':stream.status(),'private_stream':private_stream.status()}
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
 return page('<h1>API</h1><div class=card><p>REST: <b>{{rest}}</b> · privater WebSocket: <b>{{ws}}</b></p><form method=post><button name=action value=rest>REST prüfen</button> <button name=action value=websocket>WebSocket-Berechtigung prüfen</button></form><p>{{msg}}</p><p class=muted>Öffentliche WebSocket-Marktdaten benötigen keinen API-Schlüssel. Für private Kontokanäle wird die Kraken-Berechtigung „Access WebSockets API“ benötigt.</p></div><div class=card><h2>Öffentlicher WebSocket-v2-Livestream</h2><p>Status: <b>{{stream.effective_state}}</b> · Kraken: {{stream.system_status or "—"}} · Symbole: {{stream.symbol_count}}</p><p>Letzte Nachricht: {{stream.last_message_at or "—"}}</p><table>{% for x in prices %}<tr><td>{{x.symbol}}</td><td>{{x.last}}</td><td>Bid {{x.bid or "—"}}</td><td>Ask {{x.ask or "—"}}</td><td>{{x.received_at}}</td></tr>{% endfor %}</table></div><div class=card><h2>Privater Read-only WebSocket v2</h2><p>Status: <b>{{private.effective_state}}</b> · Balances-Sequenz: {{private.sequences.get("balances","—")}} · Executions-Sequenz: {{private.sequences.get("executions","—")}}</p><p>Letzte Nachricht: {{private.last_message_at or "—"}} · Fehler: {{private.last_error or "—"}}</p><h3>Live-Balances</h3><table>{% for x in private_balances %}<tr><td>{{x.asset}}</td><td>{{x.balance}}</td><td>Seq {{x.sequence}}</td><td>{{x.received_at}}</td></tr>{% endfor %}</table><h3>Letzte Ausführungsereignisse</h3><table>{% for x in executions %}<tr><td>{{x.event_type}}</td><td>{{x.symbol or "—"}}</td><td>{{x.order_id or "—"}}</td><td>Seq {{x.sequence}}</td><td>{{x.received_at}}</td></tr>{% endfor %}</table></div>',rest=db.value('kraken_status'),ws=db.value('websocket_status'),msg=msg,stream=stream.status(),prices=db.rows('SELECT * FROM live_prices ORDER BY symbol'),private=private_stream.status(),private_balances=db.rows('SELECT * FROM private_balances ORDER BY asset'),executions=db.rows('SELECT event_type,order_id,symbol,sequence,received_at FROM private_execution_events ORDER BY received_at DESC LIMIT 50'))
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
 return page('''<h1>Realportfolio</h1><div class=card><form method=post><button>Kraken vollständig synchronisieren</button></form><p>{{msg}}</p><p class=muted>Nullpositionen bleiben als HISTORICAL_ZERO erhalten, wenn das Asset in der Ledger-Historie vorkam.</p><table><tr><th>Asset</th><th>Menge</th><th>EUR-Kurs</th><th>EUR-Wert</th><th>Status</th></tr>{% for x in rows %}<tr><td>{{x.display_name}} <small>{{x.asset}}</small></td><td>{{x.amount}}</td><td>{{x.eur_price or "—"}}</td><td>{{x.eur_value or "—"}}</td><td><span class=tag>{{x.classification}}</span></td></tr>{% endfor %}</table></div><div class=card><h2>Historie</h2><table><tr><th>Zeit</th><th>Gesamt EUR</th><th>Qualität</th><th>Unbewertet</th></tr>{% for x in history %}<tr><td>{{x.created_at}}</td><td>{{x.total_eur}}</td><td>{{x.quality}}</td><td>{{x.unpriced_asset_count}}</td></tr>{% endfor %}</table></div>''',rows=rows,history=history,msg=msg)
@app.get('/paper')
def paper():return page('<h1>Musterdepot</h1><div class=card><p>Bestehendes lokales Musterdepot bleibt erhalten.</p><table>{% for x in rows %}<tr><td>{{x.asset}}</td><td>{{x.amount}}</td></tr>{% endfor %}</table></div>',rows=db.rows('SELECT * FROM paper_balances ORDER BY asset'))
@app.get('/audit')
def audit():return page('<h1>Audit</h1><div class=card><table>{% for x in rows %}<tr><td>{{x.created_at}}</td><td>{{x.event}}</td><td>{{x.level}}</td><td>{{x.details}}</td></tr>{% endfor %}</table></div>',rows=db.rows('SELECT * FROM audit ORDER BY id DESC LIMIT 200'))
@app.route('/settings',methods=['GET','POST'])
def settings():
 if request.method=='POST':db.set('automation_enabled','true' if request.form.get('automation_enabled') else 'false');db.allow(request.form.getlist('allow'));db.audit('SETTINGS_CHANGED');return redirect(url_for('settings'))
 return page('<h1>Einstellungen</h1><div class=card><form method=post><label><input type=checkbox name=automation_enabled {% if enabled=="true" %}checked{% endif %}> Analyse- und Paper-Automatik freigeben</label><p>Realhandel bleibt unabhängig davon deaktiviert.</p><button>Speichern</button></form></div>',enabled=db.value('automation_enabled'))
@app.get('/exports')
def exports():return page('<h1>Export</h1><div class=card><a href="{{url_for("ledger_csv")}}">Ledger CSV</a> · <a href="{{url_for("portfolio_csv")}}">Portfolio-Historie CSV</a></div>')
@app.get('/exports/ledger.csv')
def ledger_csv():
 out=io.StringIO();w=csv.writer(out);w.writerow(['id','occurred_at','payload']);[w.writerow([x['id'],x['occurred_at'],x['payload']]) for x in db.rows('SELECT * FROM ledger ORDER BY occurred_at')];return Response(out.getvalue(),mimetype='text/csv',headers={'Content-Disposition':'attachment; filename=kraken-ledger.csv'})
@app.get('/exports/portfolio-history.csv')
def portfolio_csv():
 out=io.StringIO();w=csv.writer(out);w.writerow(['created_at','total_eur','priced_asset_count','unpriced_asset_count','quality']);[w.writerow(x.values()) for x in db.rows('SELECT created_at,total_eur,priced_asset_count,unpriced_asset_count,quality FROM portfolio_snapshots ORDER BY id')];return Response(out.getvalue(),mimetype='text/csv',headers={'Content-Disposition':'attachment; filename=kraken-portfolio-history.csv'})
