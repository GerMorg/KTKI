import csv,io,json,os
from flask import Flask,Response,redirect,render_template_string,request,url_for
from db import DB
from kraken import KrakenClient,KrakenError
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
BASE='''<!doctype html><html lang=de><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1"><style>:root{color-scheme:dark;--b:#09111f;--c:#142238;--a:#55c6ff;--m:#a9b8cb;--g:#5ee090;--r:#ff7272}*{box-sizing:border-box}body{margin:0;background:var(--b);color:#eef6ff;font:15px system-ui}nav{display:flex;gap:18px;flex-wrap:wrap;padding:16px;background:#101b2d;position:sticky;top:0}a{color:var(--a);text-decoration:none}main{padding:20px;max-width:1200px;margin:auto}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px}.card{background:var(--c);padding:18px;border-radius:14px}.muted{color:var(--m)}.good{color:var(--g)}.bad{color:var(--r)}table{width:100%;border-collapse:collapse}td,th{text-align:left;padding:9px;border-bottom:1px solid #29405f}button{background:var(--a);border:0;border-radius:8px;padding:10px 14px;font-weight:700}</style></head><body><nav><b>Kraken Trader</b><a href="{{url_for('dashboard')}}">Übersicht</a><a href="{{url_for('api_status')}}">API</a><a href="{{url_for('portfolio')}}">Portfolio</a><a href="{{url_for('paper')}}">Musterdepot</a><a href="{{url_for('audit')}}">Audit</a><a href="{{url_for('settings')}}">Einstellungen</a><a href="{{url_for('exports')}}">Export</a></nav><main>{{body|safe}}</main></body></html>'''
def page(body):return render_template_string(BASE,body=body)
def sync_all():
 try:
  s=client.status();pairs=client.pairs();db.set('kraken_status',s.get('status','unknown'));db.set('product_count',len(pairs));db.set('last_public_sync',__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat())
  if client.key:
   b=client.balance();db.replace_balances(b);led=client.ledgers().get('ledger',{});db.import_ledger(led);db.set('private_api','connected');db.audit('kraken_sync',f'assets={len(b)}; ledger={len(led)}')
  else:db.set('private_api','not_configured')
 except KrakenError as e:db.set('private_api','error');db.set('last_error',str(e));db.audit('sync_failed',str(e),'error')
@app.get('/')
def dashboard():
 return page(render_template_string('''<h1>Übersicht</h1><div class=grid><div class=card><h3>Kraken API</h3><b>{{pub}}</b><p class=muted>Privat: {{priv}}</p></div><div class=card><h3>Realportfolio</h3><b>{{n}} Assets</b></div><div class=card><h3>Musterdepot</h3><b>{{pn}} Assets</b></div><div class=card><h3>Realhandel</h3><b class=bad>HART DEAKTIVIERT</b></div></div><form method=post action="{{url_for('sync')}}"><p><button>Kraken jetzt synchronisieren</button></p></form>''',pub=db.value('kraken_status'),priv=db.value('private_api','not_checked'),n=len(db.rows('SELECT * FROM balances')),pn=len(db.rows('SELECT * FROM paper_balances'))))
@app.post('/sync')
def sync():sync_all();return redirect(url_for('api_status'))
@app.get('/api')
def api_status():
 return page(render_template_string('''<h1>Kraken API</h1><div class=grid><div class=card><h3>Öffentliche API</h3><b>{{s}}</b><p>{{count}} Instrumente erkannt</p></div><div class=card><h3>Private Read-only API</h3><b>{{p}}</b><p class=muted>Key erkannt: {{key}}</p></div><div class=card><h3>Letzte Synchronisierung</h3><p>{{last}}</p></div></div>{% if err %}<div class=card><h3 class=bad>Letzter Fehler</h3><code>{{err}}</code></div>{% endif %}<form method=post action="{{url_for('sync')}}"><p><button>Verbindung testen und Portfolio laden</button></p></form>''',s=db.value('kraken_status'),count=db.value('product_count','0'),p=db.value('private_api','not_checked'),key='ja' if client.key else 'nein',last=db.value('last_public_sync','noch nie'),err=db.value('last_error')))
@app.get('/portfolio')
def portfolio():
 r=db.rows('SELECT * FROM balances ORDER BY asset');return page(render_template_string('''<h1>Reales Kraken-Portfolio</h1><p class=muted>Read-only Rohbestände. EUR-Bewertung folgt im nächsten Schritt.</p><table><tr><th>Asset</th><th>Menge</th><th>Stand</th></tr>{% for x in r %}<tr><td>{{x.asset}}</td><td>{{x.amount}}</td><td>{{x.updated_at}}</td></tr>{% else %}<tr><td colspan=3>Noch keine Bestände geladen. Im API-Tab synchronisieren.</td></tr>{% endfor %}</table>''',r=r))
@app.get('/paper')
def paper():return page(render_template_string('<h1>Musterdepot</h1><table><tr><th>Asset</th><th>Menge</th></tr>{% for x in r %}<tr><td>{{x.asset}}</td><td>{{x.amount}}</td></tr>{% endfor %}</table>',r=db.rows('SELECT * FROM paper_balances')))
@app.get('/audit')
def audit():return page(render_template_string('<h1>Audit</h1><table><tr><th>Zeit</th><th>Ereignis</th><th>Stufe</th><th>Details</th></tr>{% for x in r %}<tr><td>{{x.created_at}}</td><td>{{x.event}}</td><td>{{x.level}}</td><td>{{x.details}}</td></tr>{% endfor %}</table>',r=db.rows('SELECT * FROM audit ORDER BY id DESC LIMIT 200')))
@app.route('/settings',methods=['GET','POST'])
def settings():
 if request.method=='POST':db.set('automation_enabled','true' if request.form.get('automation') else 'false');db.allow(request.form.getlist('products'));db.audit('settings_changed');return redirect(url_for('settings'))
 chosen={x['symbol'] for x in db.rows('SELECT symbol FROM allowlist WHERE enabled=1')};products=['BTC/EUR','ETH/EUR','SOL/EUR','ADA/EUR','XRP/EUR'];return page(render_template_string('''<h1>Einstellungen</h1><div class=card><b class=bad>Realhandel bleibt technisch deaktiviert.</b></div><form method=post><p><label><input type=checkbox name=automation {{'checked' if enabled}}> Analyse-/Paper-Automatik</label></p>{% for p in products %}<p><label><input type=checkbox name=products value="{{p}}" {{'checked' if p in chosen}}> {{p}}</label></p>{% endfor %}<button>Speichern</button></form>''',enabled=db.value('automation_enabled')=='true',products=products,chosen=chosen))
@app.get('/exports')
def exports():return page(render_template_string('<h1>Exporte</h1><div class=grid><div class=card><a href="{{url_for(\'export_csv\',kind=\'audit\')}}">Audit CSV</a></div><div class=card><a href="{{url_for(\'export_csv\',kind=\'ledger\')}}">Ledger CSV</a></div></div>'))
@app.get('/export/<kind>.csv')
def export_csv(kind):
 if kind=='audit':r=db.rows('SELECT * FROM audit ORDER BY id');f=['id','created_at','event','level','details']
 elif kind=='ledger':r=db.rows('SELECT * FROM ledger ORDER BY occurred_at');f=['id','payload','occurred_at','imported_at']
 else:return 'Nicht gefunden',404
 o=io.StringIO();w=csv.DictWriter(o,fieldnames=f);w.writeheader();w.writerows(r);return Response(o.getvalue(),mimetype='text/csv',headers={'Content-Disposition':f'attachment; filename={kind}.csv'})
@app.get('/health')
def health():return {'status':'ok','version':'0.1.0-dev.2','real_trading':False}
