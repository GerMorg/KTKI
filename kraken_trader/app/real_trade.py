import json,secrets
from datetime import datetime,timezone
from decimal import Decimal,InvalidOperation
from flask import Blueprint,request
from db import now

def D(v):
 try:return Decimal(str(v))
 except (InvalidOperation,ValueError,TypeError):raise ValueError('Ungültiger Zahlenwert')

class RealTradeEngine:
 def __init__(self,db,client):self.db=db;self.client=client;self.ensure()
 def ensure(self):
  with self.db.con() as c:c.executescript('''
  CREATE TABLE IF NOT EXISTS real_trade_intents(id INTEGER PRIMARY KEY AUTOINCREMENT,created_at TEXT NOT NULL,client_order_id TEXT NOT NULL UNIQUE,symbol TEXT NOT NULL,side TEXT NOT NULL,order_type TEXT NOT NULL,volume TEXT NOT NULL,limit_price TEXT,status TEXT NOT NULL,validate_only INTEGER NOT NULL,approval_token_hash TEXT,response_json TEXT,error TEXT);
  CREATE INDEX IF NOT EXISTS idx_real_trade_intents_created ON real_trade_intents(created_at);
  CREATE TABLE IF NOT EXISTS real_trade_control(id INTEGER PRIMARY KEY CHECK(id=1),armed_until TEXT,token_hash TEXT,updated_at TEXT NOT NULL);
  INSERT OR IGNORE INTO real_trade_control(id,updated_at) VALUES(1,CURRENT_TIMESTAMP);
  ''')
 def enabled(self):return self.db.value('real_trading_enabled','false').lower()=='true' and self.db.value('real_kill_switch','true').lower()!='true'
 def arm(self,phrase):
  if not self.enabled():raise PermissionError('Realhandel ist deaktiviert oder der Kill-Switch ist aktiv')
  if phrase!='REALHANDEL AKTIVIEREN':raise ValueError('Bestätigungsphrase stimmt nicht')
  token=secrets.token_urlsafe(24);h=__import__('hashlib').sha256(token.encode()).hexdigest()
  until=datetime.now(timezone.utc).timestamp()+300
  with self.db.con() as c:c.execute('UPDATE real_trade_control SET armed_until=?,token_hash=?,updated_at=? WHERE id=1',(str(until),h,now()))
  self.db.audit('REAL_TRADING_ARMED','{"duration_seconds":300}','warning');return token
 def _armed(self,token):
  r=self.db.rows('SELECT * FROM real_trade_control WHERE id=1')[0];h=__import__('hashlib').sha256(str(token or '').encode()).hexdigest()
  return bool(r['token_hash']) and secrets.compare_digest(h,r['token_hash']) and D(r['armed_until'])>=D(datetime.now(timezone.utc).timestamp())
 def submit(self,symbol,side,volume,order_type='limit',limit_price=None,client_order_id=None,approval_token=None,validate_only=True):
  symbol=str(symbol).upper().strip();side=str(side).lower();order_type=str(order_type).lower();volume=D(volume)
  if side not in ('buy','sell') or order_type not in ('limit','market') or volume<=0:raise ValueError('Ungültiger Auftrag')
  if order_type=='market' and self.db.value('real_allow_market_orders','false').lower()!='true':raise PermissionError('Market-Orders sind nicht freigegeben')
  if order_type=='limit' and D(limit_price)<=0:raise ValueError('Limitpreis fehlt')
  cid=client_order_id or secrets.token_hex(16)
  prior=self.db.rows('SELECT * FROM real_trade_intents WHERE client_order_id=?',(cid,))
  if prior:return {'duplicate':True,'status':prior[0]['status'],'client_order_id':cid}
  max_volume=D(self.db.value('real_max_order_volume','0'))
  if max_volume<=0 or volume>max_volume:raise ValueError('Real-Auftragslimit nicht konfiguriert oder überschritten')
  allowed=[x.strip().upper() for x in self.db.value('real_allowed_symbols','').split(',') if x.strip()]
  if allowed and symbol not in allowed:raise PermissionError('Symbol ist nicht für Realhandel freigegeben')
  notional=volume*(D(limit_price) if limit_price not in (None,'') else D(0));max_notional=D(self.db.value('real_max_order_notional_eur','0'))
  if order_type=='limit' and (max_notional<=0 or notional>max_notional):raise ValueError('Real-Auftragswert nicht konfiguriert oder überschritten')
  live=not bool(validate_only)
  if live and (not self.enabled() or not self._armed(approval_token)):raise PermissionError('Realhandel ist nicht freigegeben oder nicht aktiv bestätigt')
  if live:
   cap=max(1,int(float(self.db.value('real_max_orders_per_day','1'))))
   used=self.db.rows("SELECT COUNT(*) AS n FROM real_trade_intents WHERE validate_only=0 AND status='SUBMITTED' AND date(created_at)=date('now')")[0]['n']
   if int(used)>=cap:raise PermissionError('Tageslimit für Realaufträge erreicht')
  data={'pair':symbol.replace('/',''),'type':side,'ordertype':order_type,'volume':str(volume),'cl_ord_id':cid,'validate':'false' if live else 'true'}
  if order_type=='limit':data['price']=str(D(limit_price))
  with self.db.con() as c:c.execute('INSERT INTO real_trade_intents(created_at,client_order_id,symbol,side,order_type,volume,limit_price,status,validate_only,approval_token_hash) VALUES(?,?,?,?,?,?,?,?,?,?)',(now(),cid,symbol,side,order_type,str(volume),str(limit_price or ''),'SUBMITTING',0 if live else 1,None))
  try:
   result=self.client.add_order(**data);status='SUBMITTED' if live else 'VALIDATED'
   if live:
    with self.db.con() as c:c.execute('UPDATE real_trade_control SET armed_until=NULL,token_hash=NULL,updated_at=? WHERE id=1',(now(),))
   with self.db.con() as c:c.execute('UPDATE real_trade_intents SET status=?,response_json=? WHERE client_order_id=?',(status,json.dumps(result,sort_keys=True),cid))
   self.db.audit('REAL_ORDER_'+status,json.dumps({'client_order_id':cid,'symbol':symbol,'side':side,'validate_only':not live}),'warning' if live else 'info')
   return {'duplicate':False,'status':status,'client_order_id':cid,'result':result}
  except Exception as exc:
   with self.db.con() as c:c.execute('UPDATE real_trade_intents SET status=?,error=? WHERE client_order_id=?',('FAILED',type(exc).__name__,cid))
   self.db.audit('REAL_ORDER_FAILED',json.dumps({'client_order_id':cid,'error':type(exc).__name__}),'error');raise

def create_real_trade_blueprint(db,client,page):
 engine=RealTradeEngine(db,client);bp=Blueprint('real_trade',__name__)
 @bp.route('/real-trading',methods=['GET','POST'])
 def view():
  result=error=token=None
  if request.method=='POST':
   try:
    if request.form.get('action')=='arm':token=engine.arm(request.form.get('phrase'))
    else:result=engine.submit(request.form.get('symbol'),request.form.get('side'),request.form.get('volume'),request.form.get('order_type'),request.form.get('limit_price'),request.form.get('client_order_id') or None,request.form.get('approval_token'),request.form.get('live')!='yes')
   except Exception as exc:error=str(exc)
  rows=db.rows('SELECT id,created_at,client_order_id,symbol,side,order_type,volume,limit_price,status,validate_only,error FROM real_trade_intents ORDER BY id DESC LIMIT 50')
  return page('''<h1>Realhandel</h1><p class=lead>Strikt getrennt vom Paper-Handel. Standardmäßig wird nur gegen Kraken validiert und keine Order platziert.</p>{% if error %}<div class="card error">{{error}}</div>{% endif %}{% if result %}<div class="card"><pre>{{result|tojson(indent=2)}}</pre></div>{% endif %}{% if token %}<div class="card warning"><b>Einmaliges Freigabetoken, 5 Minuten gültig:</b><pre>{{token}}</pre></div>{% endif %}<div class=card><h2>Auftrag validieren</h2><form method=post><input type=hidden name=action value=submit><label>Symbol<input name=symbol value="BTC/EUR"></label><label>Seite<select name=side><option>buy</option><option>sell</option></select></label><label>Typ<select name=order_type><option>limit</option><option>market</option></select></label><label>Volumen<input name=volume required></label><label>Limitpreis<input name=limit_price></label><label>Idempotenz-ID<input name=client_order_id></label><label>Freigabetoken<input name=approval_token></label><label>Live<select name=live><option value=no>Nein, nur validieren</option><option value=yes>Ja</option></select></label><button>Absenden</button></form></div><div class=card><h2>Kurzzeitig scharf schalten</h2><form method=post><input type=hidden name=action value=arm><label>Phrase<input name=phrase></label><button>5 Minuten aktiv bestätigen</button></form></div><table><tr><th>Zeit</th><th>ID</th><th>Symbol</th><th>Seite</th><th>Volumen</th><th>Status</th><th>Validierung</th></tr>{% for x in rows %}<tr><td>{{x.created_at}}</td><td>{{x.client_order_id}}</td><td>{{x.symbol}}</td><td>{{x.side}}</td><td>{{x.volume}}</td><td>{{x.status}}</td><td>{{x.validate_only}}</td></tr>{% endfor %}</table>''',result=result,error=error,token=token,rows=rows)
 return bp
