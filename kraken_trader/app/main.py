import csv, io, json, os
from flask import Flask, Response, redirect, render_template_string, request, url_for
from db import DB
from kraken import KrakenClient, KrakenError

DATA=os.getenv("APP_DATA_DIR","/tmp/kraken-trader"); os.makedirs(DATA,exist_ok=True)
opts={}
try:
 with open(os.getenv("APP_OPTIONS","/data/options.json")) as f: opts=json.load(f)
except Exception: pass
db=DB(os.path.join(DATA,"kraken_trader.db")); db.init(opts.get("paper_start_eur",1000))
client=KrakenClient(opts.get("kraken_api_key",""),opts.get("kraken_api_secret",""))
app=Flask(__name__)

BASE='''<!doctype html><html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>:root{color-scheme:dark;--bg:#0b1220;--card:#152238;--accent:#56c2ff;--muted:#9fb0c8;--bad:#ff6b6b}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:#eef6ff;font:15px system-ui}nav{display:flex;gap:16px;flex-wrap:wrap;padding:16px;background:#101b2d}a{color:var(--accent);text-decoration:none}main{padding:20px;max-width:1200px;margin:auto}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px}.card{background:var(--card);padding:18px;border-radius:14px}.muted{color:var(--muted)}table{width:100%;border-collapse:collapse}td,th{text-align:left;padding:9px;border-bottom:1px solid #29405f}button{background:var(--accent);border:0;border-radius:8px;padding:10px 14px;font-weight:700}.danger{color:var(--bad)}input[type=checkbox]{transform:scale(1.2)}code{word-break:break-all}</style></head><body><nav><b>Kraken Trader</b><a href="{{url_for('dashboard')}}">Dashboard</a><a href="{{url_for('portfolio')}}">Portfolio</a><a href="{{url_for('paper')}}">Musterdepot</a><a href="{{url_for('decisions')}}">Audit</a><a href="{{url_for('settings')}}">Einstellungen</a><a href="{{url_for('exports')}}">Export</a></nav><main>{{body|safe}}</main></body></html>'''
def page(body): return render_template_string(BASE,body=body)

@app.get('/')
def dashboard():
 real=db.rows('SELECT * FROM balances ORDER BY asset'); paper=db.rows('SELECT * FROM paper_balances ORDER BY asset'); settings={x['key']:x['value'] for x in db.rows('SELECT * FROM settings')}
 return page(render_template_string('''<h1>Systemuebersicht</h1><div class="grid"><div class="card"><h3>Realportfolio</h3><b>{{real|length}}</b> Assets<div class="muted">Rohmengen, noch ohne EUR-Bewertung</div></div><div class="card"><h3>Musterdepot</h3><b>{{paper|length}}</b> Assets<div class="muted">Lokal und strikt vom Realportfolio getrennt</div></div><div class="card"><h3>Automatik</h3><b>{{'AKTIV' if enabled else 'GESTOPPT'}}</b></div><div class="card"><h3>Realhandel</h3><b class="danger">HART DEAKTIVIERT</b></div></div><p><form method="post" action="{{url_for('sync')}}"><button>Jetzt synchronisieren</button></form></p>''',real=real,paper=paper,enabled=settings.get('automation_enabled')=='true'))
@app.post('/sync')
def sync():
 try:
  status=client.system_status(); pairs=client.asset_pairs(); db.audit('kraken_public_sync',f"status={status.get('status','?')}; products={len(pairs)}")
  if client.key:
   db.replace_balances(client.balance()); led=client.ledgers().get('ledger',{}); db.import_ledger(led); db.audit('kraken_private_sync',f"ledger_import={len(led)}")
 except KrakenError as e: db.audit('sync_failed',str(e),'error')
 return redirect(url_for('dashboard'))
@app.get('/portfolio')
def portfolio():
 rows=db.rows('SELECT * FROM balances ORDER BY asset'); return page(render_template_string('<h1>Reales Kraken-Portfolio</h1><p class="muted">Read-only; Mengen werden unveraendert als Dezimaltext gespeichert.</p><table><tr><th>Asset</th><th>Menge</th><th>Stand</th></tr>{% for r in rows %}<tr><td>{{r.asset}}</td><td>{{r.amount}}</td><td>{{r.updated_at}}</td></tr>{% else %}<tr><td colspan=3>Noch keine Daten. Read-only-Schluessel konfigurieren und synchronisieren.</td></tr>{% endfor %}</table>',rows=rows))
@app.get('/paper')
def paper():
 rows=db.rows('SELECT * FROM paper_balances ORDER BY asset'); return page(render_template_string('<h1>Musterdepot</h1><table><tr><th>Asset</th><th>Menge</th><th>Stand</th></tr>{% for r in rows %}<tr><td>{{r.asset}}</td><td>{{r.amount}}</td><td>{{r.updated_at}}</td></tr>{% endfor %}</table><p class="muted">Der Paper-Broker folgt im naechsten Entwicklungsschritt.</p>',rows=rows))
@app.get('/audit')
def decisions():
 rows=db.rows('SELECT * FROM audit ORDER BY id DESC LIMIT 200'); return page(render_template_string('<h1>Entscheidungen & Audit</h1><table><tr><th>Zeit</th><th>Ereignis</th><th>Stufe</th><th>Details</th></tr>{% for r in rows %}<tr><td>{{r.created_at}}</td><td>{{r.event}}</td><td>{{r.level}}</td><td>{{r.details}}</td></tr>{% endfor %}</table>',rows=rows))
@app.route('/settings',methods=['GET','POST'])
def settings():
 if request.method=='POST':
  enabled='true' if request.form.get('automation_enabled') else 'false'; db.set_setting('automation_enabled',enabled); db.set_allowlist(request.form.getlist('products')); db.audit('settings_changed',f"automation={enabled}; allowlist_count={len(request.form.getlist('products'))}"); return redirect(url_for('settings'))
 enabled=db.rows("SELECT value FROM settings WHERE key='automation_enabled'")[0]['value']=='true'; chosen={x['symbol'] for x in db.rows('SELECT symbol FROM allowlist WHERE enabled=1')}; products=['BTC/EUR','ETH/EUR','SOL/EUR','ADA/EUR','XRP/EUR']
 return page(render_template_string('''<h1>Rechte & Automatik</h1><div class="card"><b class="danger">Realhandel ist in 0.1 serverseitig nicht vorhanden.</b></div><form method=post><p><label><input type=checkbox name=automation_enabled {{'checked' if enabled}}> Analyse-/Paper-Automatik freigeben</label></p><h3>Erlaubte Produkte</h3>{% for p in products %}<p><label><input type=checkbox name=products value="{{p}}" {{'checked' if p in chosen}}> {{p}}</label></p>{% endfor %}<button>Speichern</button></form>''',enabled=enabled,products=products,chosen=chosen))
@app.get('/exports')
def exports(): return page('<h1>Exporte</h1><div class="grid"><div class="card"><a href="export/audit.csv">Audit CSV</a></div><div class="card"><a href="export/ledger.csv">Kraken Ledger CSV (Rohdaten)</a></div></div><p class="muted">Datengrundlage, keine Steuerberatung oder fertige Steuererklaerung.</p>')
@app.get('/export/<kind>.csv')
def export_csv(kind):
 if kind=='audit': rows=db.rows('SELECT * FROM audit ORDER BY id'); fields=['id','created_at','event','level','details']
 elif kind=='ledger': rows=db.rows('SELECT * FROM ledger ORDER BY occurred_at'); fields=['id','payload','occurred_at','imported_at']
 else: return ('Nicht gefunden',404)
 out=io.StringIO(); w=csv.DictWriter(out,fieldnames=fields); w.writeheader(); w.writerows(rows); return Response(out.getvalue(),mimetype='text/csv',headers={'Content-Disposition':f'attachment; filename={kind}.csv'})
@app.get('/health')
def health(): return {'status':'ok','version':'0.1.0-dev.1','real_trading':False}
