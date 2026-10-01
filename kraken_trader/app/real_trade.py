import json,secrets,hashlib,hmac
from datetime import datetime,timezone
from decimal import Decimal,InvalidOperation
from flask import Blueprint,request
from db import now

def D(v):
 if v is None or str(v).strip()=='':return Decimal(0)
 try:return Decimal(str(v))
 except (InvalidOperation,ValueError,TypeError):raise ValueError('Ungültiger Zahlenwert')

class RealTradeEngine:
 def __init__(self,db,client):self.db=db;self.client=client;self.ensure()
 def margin_settings(self):
  def num(key,default,lo=None,hi=None):
   try:v=D(self.db.value(key,str(default)))
   except Exception:v=D(default)
   if lo is not None:v=max(D(lo),v)
   if hi is not None:v=min(D(hi),v)
   return v
  return {'enabled':self.db.value('real_margin_enabled','false').lower()=='true','default_leverage':num('real_margin_default_leverage',2,2,5),'max_leverage':num('real_margin_max_leverage',3,2,5),'max_exposure_pct':num('real_margin_max_exposure_pct',20,1,100),'max_free_margin_pct':num('real_margin_max_free_margin_pct',50,1,100),'min_margin_level_pct':num('real_margin_min_margin_level_pct',200,100,1000),'safety_buffer_pct':num('real_margin_safety_buffer_pct',20,0,80),'allow_shorts':self.db.value('real_margin_allow_shorts','false').lower()=='true','balance_asset':self.db.value('real_margin_balance_asset','ZEUR')}

 def ensure(self):
  with self.db.con() as c:
   c.executescript('''CREATE TABLE IF NOT EXISTS real_trade_intents(id INTEGER PRIMARY KEY AUTOINCREMENT,created_at TEXT NOT NULL,client_order_id TEXT NOT NULL UNIQUE,symbol TEXT NOT NULL,side TEXT NOT NULL,order_type TEXT NOT NULL,volume TEXT NOT NULL,limit_price TEXT,status TEXT NOT NULL,validate_only INTEGER NOT NULL,approval_token_hash TEXT,response_json TEXT,error TEXT);CREATE INDEX IF NOT EXISTS idx_real_trade_intents_created ON real_trade_intents(created_at);CREATE TABLE IF NOT EXISTS real_trade_control(id INTEGER PRIMARY KEY CHECK(id=1),armed_until TEXT,token_hash TEXT,updated_at TEXT NOT NULL);INSERT OR IGNORE INTO real_trade_control(id,updated_at) VALUES(1,CURRENT_TIMESTAMP);CREATE TABLE IF NOT EXISTS real_margin_positions(id INTEGER PRIMARY KEY AUTOINCREMENT,position_id TEXT NOT NULL UNIQUE,symbol TEXT NOT NULL,side TEXT NOT NULL,volume TEXT NOT NULL,margin TEXT NOT NULL,entry_cost TEXT NOT NULL,current_value TEXT,unrealized_pnl TEXT,leverage TEXT,updated_at TEXT NOT NULL,details_json TEXT NOT NULL);CREATE TABLE IF NOT EXISTS real_margin_account(id INTEGER PRIMARY KEY CHECK(id=1),updated_at TEXT NOT NULL,equity TEXT,free_margin TEXT,margin_used TEXT,unrealized_pnl TEXT,margin_level TEXT,details_json TEXT NOT NULL);''')
   cols={x['name'] for x in c.execute('PRAGMA table_info(real_trade_intents)').fetchall()}
   for name,definition in [('leverage',"TEXT NOT NULL DEFAULT '1'"),('margin',"INTEGER NOT NULL DEFAULT 0"),('reduce_only',"INTEGER NOT NULL DEFAULT 0")]:
    if name not in cols:c.execute(f'ALTER TABLE real_trade_intents ADD COLUMN {name} {definition}')
 def refresh_margin_state(self):
  if not self.margin_settings()['enabled']:return {'status':'DISABLED'}
  positions=self.client.open_positions(docalcs=True,consolidation='market')
  balance=self.client.trade_balance(self.margin_settings()['balance_asset'])
  with self.db.con() as con:
   con.execute('DELETE FROM real_margin_positions')
   for pid,pos in (positions or {}).items():
    pair=str(pos.get('pair') or '')
    symbol=pair if '/' in pair else ''
    if not symbol:
     mapped=self.db.rows('SELECT symbol FROM market_universe WHERE source_key=? OR REPLACE(symbol,\'/\',\'\')=? LIMIT 1',(pair,pair))
     symbol=str(mapped[0]['symbol']) if mapped else pair.replace('XXBT','XBT').replace('ZUSD','/USD').replace('ZEUR','/EUR').replace('X','',1).replace('Z','',1)

    side=str(pos.get('type') or 'unknown').lower();vol=D(pos.get('vol') or 0);margin=D(pos.get('margin') or 0);cost=D(pos.get('cost') or 0);value=D(pos.get('value') or 0);net=D(pos.get('net') or 0);lev=(cost/margin) if margin>0 else D(0)
    con.execute('INSERT INTO real_margin_positions(position_id,symbol,side,volume,margin,entry_cost,current_value,unrealized_pnl,leverage,updated_at,details_json) VALUES(?,?,?,?,?,?,?,?,?,?,?)',(str(pid),symbol,side,str(vol),str(margin),str(cost),str(value),str(net),str(lev),now(),json.dumps(pos,sort_keys=True,default=str)))
   result=balance or {}
   con.execute('INSERT OR REPLACE INTO real_margin_account(id,updated_at,equity,free_margin,margin_used,unrealized_pnl,margin_level,details_json) VALUES(1,?,?,?,?,?,?,?)',(now(),str(result.get('e') or ''),str(result.get('mf') or ''),str(result.get('m') or ''),str(result.get('n') or ''),str(result.get('ml') or ''),json.dumps(result,sort_keys=True,default=str)))
  return {'status':'UPDATED','positions':positions or {},'balance':balance or {}}
 def _pair_leverage(self,symbol,side):
  row=self._pair(symbol);raw=row.get('leverage_buy_json' if side=='buy' else 'leverage_sell_json') or '[]'
  try:values=json.loads(raw) if isinstance(raw,str) else raw
  except Exception:values=[]
  if not values:
   try:
    meta=json.loads(row.get('metadata_json') or '{}');values=meta.get('leverage_buy' if side=='buy' else 'leverage_sell') or []
   except Exception:values=[]
  out=[]
  for x in values:
   try:out.append(D(str(x).replace(':1','')))
   except Exception:pass
  return sorted(set(x for x in out if x>=2),reverse=True)
 def _margin_preflight(self,symbol,side,volume,price,leverage,reduce_only=False):
  cfg=self.margin_settings()
  if not cfg['enabled']:raise PermissionError('Margin-/Hebelhandel ist deaktiviert')
  lev=D(leverage or cfg['default_leverage'])
  if lev<2 or lev>cfg['max_leverage']:raise ValueError('LEVERAGE_OUT_OF_RANGE')
  available=self._pair_leverage(symbol,side)
  if not available:raise ValueError('LEVERAGE_NOT_AVAILABLE_FOR_PAIR')
  if lev not in available:raise ValueError('LEVERAGE_NOT_AVAILABLE_FOR_PAIR')
  if side=='sell' and not reduce_only and not cfg['allow_shorts']:raise PermissionError('MARGIN_SHORTS_DISABLED')
  notional=D(volume)*D(price);required_margin=notional/lev;account=self.db.rows('SELECT * FROM real_margin_account WHERE id=1 LIMIT 1')
  if not account:
   try:self.refresh_margin_state();account=self.db.rows('SELECT * FROM real_margin_account WHERE id=1 LIMIT 1')
   except Exception:account=[]
  if not account:return {'notional':str(notional),'required_margin':str(required_margin),'leverage':str(lev)}
  equity=D(account[0].get('equity') or 0);free=D(account[0].get('free_margin') or 0);level_raw=account[0].get('margin_level')
  if equity>0 and notional>equity*cfg['max_exposure_pct']/100 and not reduce_only:raise ValueError('MAX_MARGIN_EXPOSURE')
  if free>0 and required_margin*(1+cfg['safety_buffer_pct']/100)>free*cfg['max_free_margin_pct']/100 and not reduce_only:raise ValueError('INSUFFICIENT_FREE_MARGIN_BUFFER')
  if level_raw not in (None,'','0') and not reduce_only:
   try:
    if D(level_raw)<cfg['min_margin_level_pct']:raise ValueError('MARGIN_LEVEL_TOO_LOW')
   except InvalidOperation:pass
  return {'notional':str(notional),'required_margin':str(required_margin),'leverage':str(lev),'equity':str(equity),'free_margin':str(free),'margin_level':str(level_raw or '')}
 def enabled(self):return self.db.value('real_trading_enabled','false').lower()=='true' and self.db.value('real_kill_switch','true').lower()!='true'
 def arm(self,phrase):
  if not self.enabled():raise PermissionError('Realhandel ist deaktiviert oder der Kill-Switch ist aktiv')
  if phrase!='REALHANDEL AKTIVIEREN':raise ValueError('Bestätigungsphrase stimmt nicht')
  token=secrets.token_urlsafe(24);h=hashlib.sha256(token.encode()).hexdigest();until=datetime.now(timezone.utc).timestamp()+300
  with self.db.con() as c:c.execute('UPDATE real_trade_control SET armed_until=?,token_hash=?,updated_at=? WHERE id=1',(str(until),h,now()))
  self.db.audit('REAL_TRADING_ARMED','{"duration_seconds":300}','warning','REAL');return token
 def _armed(self,token):
  r=self.db.rows('SELECT * FROM real_trade_control WHERE id=1')[0];h=hashlib.sha256(str(token or '').encode()).hexdigest();return bool(r['token_hash']) and hmac.compare_digest(h,r['token_hash']) and D(r['armed_until'])>=D(datetime.now(timezone.utc).timestamp())
 def _resolve_symbol(self,symbol):
  text=str(symbol or '').strip()
  try:
   rows=self.db.rows('SELECT symbol FROM market_universe WHERE symbol=? OR UPPER(symbol)=UPPER(?) ORDER BY CASE WHEN asset_class=\'currency\' THEN 0 ELSE 1 END LIMIT 1',(text,text))
  except Exception:
   rows=[]
  if rows:return str(rows[0]['symbol'])
  try:
   rows=self.db.rows('SELECT symbol FROM live_prices WHERE symbol=? OR UPPER(symbol)=UPPER(?) LIMIT 1',(text,text))
  except Exception:
   rows=[]
  if rows:return str(rows[0]['symbol'])
  return text

 def _pair(self,symbol):
  symbol=self._resolve_symbol(symbol)
  try:rows=self.db.rows("SELECT * FROM market_universe WHERE symbol=? ORDER BY CASE WHEN asset_class='currency' THEN 0 ELSE 1 END LIMIT 1",(symbol))
  except Exception:rows=[]
  return rows[0] if rows else {}
 def _fx(self):
  rows=self.db.rows("SELECT bid,ask,last,received_at FROM live_prices WHERE symbol='EUR/USD' LIMIT 1");return rows[0] if rows else None
 def _eur_notional(self,symbol,volume,price,side='buy'):
  row=self._pair(symbol);quote=str(row.get('quote_asset') or symbol.rsplit('/',1)[-1]).upper();notional=D(volume)*D(price)
  if quote=='EUR':return notional
  if quote=='USD':
   fx=self._fx()
   rate=D((fx or {}).get('bid' if str(side).lower()=='buy' else 'ask') or (fx or {}).get('last') or 0)
   if rate<=0:raise ValueError('EUR/USD fehlt für EUR-Notional')
   return notional/rate
  raise ValueError('Nur EUR- und USD-Quote sind für Realhandel freigegeben')
 def _quote_balance(self,quote):
  aliases={quote,'Z'+quote,'X'+quote};rows=self.db.rows('SELECT asset,balance FROM private_balances');return sum((D(x['balance']) for x in rows if str(x['asset']).upper() in aliases),D(0))
 def _base_balance(self,base):
  aliases={base,'X'+base,'Z'+base};rows=self.db.rows('SELECT asset,balance FROM private_balances');return sum((D(x['balance']) for x in rows if str(x['asset']).upper() in aliases),D(0))
 def _live_price(self,symbol,side):
  symbol=self._resolve_symbol(symbol)
  rows=self.db.rows('SELECT last,bid,ask,received_at FROM live_prices WHERE symbol=? LIMIT 1',(symbol,))
  if not rows:raise ValueError('Kein aktueller Marktpreis')
  r=rows[0]
  try:
   age=(datetime.now(timezone.utc)-datetime.fromisoformat(str(r.get('received_at')).replace('Z','+00:00'))).total_seconds()
   max_age=float(self.db.value('decision_market_data_max_age_seconds','120'))
   if age>max_age:raise ValueError('MARKET_DATA_STALE')
  except ValueError:
   raise
  except Exception:
   raise ValueError('MARKET_DATA_TIMESTAMP_INVALID')
  p=D((r.get('ask') if side=='buy' else r.get('bid')) or r.get('last'))
  if p<=0:raise ValueError('Ungültiger Marktpreis')
  return p,r
 def _order_limits(self):
  # 0 means no additional per-order limit from this setting; the balancing
  # limit remains the effective safety cap when both explicit limits are zero.
  return D(self.db.value('real_max_order_volume','0')),D(self.db.value('real_max_order_notional_eur','0')),D(self.db.value('real_balancing_max_trade_eur','0'))
 def _preflight_limits(self,volume,eur_notional):
  max_volume,max_notional,fallback=self._order_limits()
  if max_volume>0 and volume>max_volume:raise ValueError('MAX_ORDER_VOLUME')
  if max_notional>0 and eur_notional>max_notional:raise ValueError('MAX_ORDER_NOTIONAL_EUR')
  if max_volume<=0 and max_notional<=0 and fallback>0 and eur_notional>fallback:raise ValueError('MAX_BALANCING_TRADE_EUR')
 def preflight(self,symbol,side,volume,order_type='limit',limit_price=None,leverage=None,margin=False,reduce_only=False):
  symbol=self._resolve_symbol(symbol);side=str(side).lower();volume=D(volume);order_type=str(order_type).lower()
  if side not in ('buy','sell') or order_type not in ('limit','market') or volume<=0:raise ValueError('Ungültiger Auftrag')
  if order_type=='market' and self.db.value('real_allow_market_orders','false').lower()!='true':raise PermissionError('Market-Orders sind nicht freigegeben')
  row=self._pair(symbol);quote=str(row.get('quote_asset') or symbol.rsplit('/',1)[-1]).upper();base=str(row.get('base_asset') or symbol.split('/',1)[0]).upper()
  if quote not in ('EUR','USD'):raise PermissionError('Nur EUR/USD-Quoten sind für Realhandel freigegeben')
  price=self._live_price(symbol,side)[0] if order_type=='market' else D(limit_price)
  if price<=0:raise ValueError('Preis fehlt')
  eur_notional=self._eur_notional(symbol,volume,price,side);self._preflight_limits(volume,eur_notional);margin_details=self._margin_preflight(symbol,side,volume,price,leverage,reduce_only) if margin else {}
  ordermin=D(row.get('ordermin'));costmin=D(row.get('costmin'))
  if ordermin>0 and volume<ordermin:raise ValueError(f'Mindestmenge {ordermin} unterschritten')
  if costmin>0 and D(volume)*price<costmin:raise ValueError(f'Mindestkosten {costmin} unterschritten')
  return {'eligible':True,'symbol':symbol,'side':side,'volume':str(volume),'price':str(price),'eur_notional':str(eur_notional),'quote':quote,'base':base,'margin':bool(margin),'reduce_only':bool(reduce_only),'leverage':str(margin_details.get('leverage','1')),'margin_details':margin_details}
 def submit(self,symbol,side,volume,order_type='limit',limit_price=None,client_order_id=None,approval_token=None,validate_only=True,automation_secret=None,leverage=None,margin=False,reduce_only=False):
  symbol=self._resolve_symbol(symbol);side=str(side).lower();order_type=str(order_type).lower();volume=D(volume);live=not bool(validate_only);margin=bool(margin);reduce_only=bool(reduce_only);leverage=D(leverage or self.margin_settings()['default_leverage']) if margin else D(1)
  # Gate market-order permission before any market-price lookup so the safety
  # decision is deterministic even when no ticker has been cached yet.
  if order_type=='market' and self.db.value('real_allow_market_orders','false').lower()!='true':raise PermissionError('Market-Orders sind nicht freigegeben')
  if live:
   automation_ok=False
   if automation_secret:
    wanted=self.db.value('real_balancing_automation_secret_hash','');automation_ok=bool(wanted) and hmac.compare_digest(hashlib.sha256(str(automation_secret).encode()).hexdigest(),wanted)
   if not self.enabled() or not (self._armed(approval_token) or automation_ok):raise PermissionError('Realhandel ist nicht freigegeben oder nicht aktiv bestätigt')
  row=self._pair(symbol);quote=str(row.get('quote_asset') or symbol.rsplit('/',1)[-1]).upper();base=str(row.get('base_asset') or symbol.split('/',1)[0]).upper()
  if quote not in ('EUR','USD'):raise PermissionError('Nur EUR/USD-Quoten sind für Realhandel freigegeben')
  price=self._live_price(symbol,side)[0] if order_type=='market' else D(limit_price)
  if price<=0:raise ValueError('Preis fehlt')
  if order_type=='limit' and live:
   live_price,_=self._live_price(symbol,side);max_dev=D(self.db.value('real_max_price_deviation_pct','1'))/100
   if live_price>0 and abs(price/live_price-1)>max_dev:raise ValueError('Limitpreis weicht zu stark vom Livepreis ab')
  cid=client_order_id or secrets.token_hex(16)
  prior=self.db.rows('SELECT * FROM real_trade_intents WHERE client_order_id=?',(cid,))
  if prior:return {'duplicate':True,'status':prior[0]['status'],'client_order_id':cid}
  allowed=[x.strip().casefold() for x in self.db.value('real_allowed_symbols','').split(',') if x.strip()]
  if symbol.upper()=='EUR/USD' and self.db.value('real_allow_fx_conversion','true').lower()=='true':allowed=allowed+['eur/usd']
  if allowed and symbol.casefold() not in allowed:raise PermissionError('Symbol ist nicht für Realhandel freigegeben')
  self._preflight_limits(volume,self._eur_notional(symbol,volume,price,side))
  ordermin=D(row.get('ordermin'));costmin=D(row.get('costmin'))
  if ordermin>0 and volume<ordermin:raise ValueError(f'Mindestmenge {ordermin} unterschritten')
  if costmin>0 and D(volume)*price<costmin:raise ValueError(f'Mindestkosten {costmin} unterschritten')
  margin_details=self._margin_preflight(symbol,side,volume,price,leverage,reduce_only) if margin else {}
  if live:
   if margin:
    self.refresh_margin_state();margin_details=self._margin_preflight(symbol,side,volume,price,leverage,reduce_only)
   elif side=='buy':
    fee_bps=D(self.db.value('real_fee_bps','40'));required_quote=D(volume)*price*(1+fee_bps/10000);balance=self._quote_balance(quote)
    if balance<required_quote:raise PermissionError(f'Nicht genügend {quote}-Saldo; benötigt {required_quote}, vorhanden {balance}')
   else:
    balance=self._base_balance(base)
    if balance<volume:raise PermissionError(f'Nicht genügend {base}-Saldo; benötigt {volume}, vorhanden {balance}')
   is_fx_conversion=symbol=='EUR/USD';cap=max(1,int(float(self.db.value('real_max_fx_orders_per_day','1'))) if is_fx_conversion else int(float(self.db.value('real_max_orders_per_day','1'))));query="SELECT COUNT(*) AS n FROM real_trade_intents WHERE validate_only=0 AND status='SUBMITTED' AND date(created_at)=date('now')"+(' AND symbol=\'EUR/USD\'' if is_fx_conversion else " AND symbol!=\'EUR/USD\'");used=self.db.rows(query)[0]['n']
   if int(used)>=cap:raise PermissionError('Tageslimit für EUR/USD-Funding erreicht' if is_fx_conversion else 'Tageslimit für Realaufträge erreicht')
  data={'pair':symbol.replace('/',''),'type':side,'ordertype':order_type,'volume':str(volume),'cl_ord_id':cid,'validate':'false' if live else 'true'}
  if margin:data.update({'leverage':str(leverage),'reduce_only':'true' if reduce_only else 'false'})
  if order_type=='limit':data['price']=str(price)
  with self.db.con() as c:c.execute('INSERT INTO real_trade_intents(created_at,client_order_id,symbol,side,order_type,volume,limit_price,status,validate_only,approval_token_hash,leverage,margin,reduce_only) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',(now(),cid,symbol,side,order_type,str(volume),str(price),'SUBMITTING',0 if live else 1,None,str(leverage),1 if margin else 0,1 if reduce_only else 0))
  try:
   result=self.client.add_order(**data);status='SUBMITTED' if live else 'VALIDATED'
   if live:
    with self.db.con() as c:c.execute('UPDATE real_trade_control SET armed_until=NULL,token_hash=NULL,updated_at=? WHERE id=1',(now(),))
   with self.db.con() as c:c.execute('UPDATE real_trade_intents SET status=?,response_json=? WHERE client_order_id=?',(status,json.dumps(result,sort_keys=True),cid))
   self.db.audit('REAL_ORDER_'+status,json.dumps({'client_order_id':cid,'symbol':symbol,'side':side,'validate_only':not live,'eur_notional':str(self._eur_notional(symbol,volume,price,side)),'margin':margin,'leverage':str(leverage),'reduce_only':reduce_only}),'warning' if live else 'info','REAL');return {'duplicate':False,'status':status,'client_order_id':cid,'result':result}
  except Exception as exc:
   with self.db.con() as c:c.execute('UPDATE real_trade_intents SET status=?,error=? WHERE client_order_id=?',('FAILED',type(exc).__name__,cid))
   self.db.audit('REAL_ORDER_FAILED',json.dumps({'client_order_id':cid,'error':type(exc).__name__}),'error','REAL');raise
 def convert_eur_to_usd(self,eur_amount,automation_secret=None,approval_token=None,validate_only=True):
  fx=self._fx()
  if not fx:raise ValueError('EUR/USD Livepreis fehlt')
  bid=D(fx.get('bid') or fx.get('last'))
  if bid<=0:raise ValueError('EUR/USD Bid ungültig')
  return self.submit('EUR/USD','sell',str(D(eur_amount)),'limit',str(bid),secrets.token_hex(16),approval_token,validate_only,automation_secret)

def create_real_trade_blueprint(db,client,page):
 engine=RealTradeEngine(db,client);bp=Blueprint('real_trade',__name__)
 @bp.route('/real-trading',methods=['GET','POST'])
 def view():
  result=error=token=None
  if request.method=='POST':
   try:
    if request.form.get('action')=='arm':token=engine.arm(request.form.get('phrase'))
    else:result=engine.submit(request.form.get('symbol'),request.form.get('side'),request.form.get('volume'),request.form.get('order_type'),request.form.get('limit_price'),request.form.get('client_order_id') or None,request.form.get('approval_token'),request.form.get('live')!='yes',None,request.form.get('leverage') or None,request.form.get('margin')=='yes',request.form.get('reduce_only')=='yes')
   except Exception as exc:error=str(exc)
  rows=db.rows('SELECT id,created_at,client_order_id,symbol,side,order_type,volume,limit_price,status,validate_only,error FROM real_trade_intents ORDER BY id DESC LIMIT 50')
  return page('''<h1>Realhandel</h1><p class=lead>Strikt getrennt vom Paper-Handel. Standardmäßig wird nur gegen Kraken validiert und keine Order platziert.</p>{% if error %}<div class="card error">{{error}}</div>{% endif %}{% if result %}<div class="card"><pre>{{result|tojson(indent=2)}}</pre></div>{% endif %}{% if token %}<div class="card warning"><b>Einmaliges Freigabetoken, 5 Minuten gültig:</b><pre>{{token}}</pre></div>{% endif %}<div class=card><h2>Auftrag validieren</h2><form method=post><input type=hidden name=action value=submit><label>Symbol<input name=symbol value="BTC/EUR"></label><label>Seite<select name=side><option>buy</option><option>sell</option></select></label><label>Typ<select name=order_type><option>limit</option><option>market</option></select></label><label>Volumen<input name=volume required></label><label>Limitpreis<input name=limit_price></label><label>Margin/Leverage<select name=margin><option value=no>Spot</option><option value=yes>Margin</option></select></label><label>Hebel<input name=leverage value="2"></label><label>Reduce-only<select name=reduce_only><option value=no>Nein</option><option value=yes>Ja</option></select></label><label>Idempotenz-ID<input name=client_order_id></label><label>Freigabetoken<input name=approval_token></label><label>Live<select name=live><option value=no>Nein, nur validieren</option><option value=yes>Ja</option></select></label><button>Absenden</button></form></div><div class=card><h2>Kurzzeitig scharf schalten</h2><form method=post><input type=hidden name=action value=arm><label>Phrase<input name=phrase></label><button>5 Minuten aktiv bestätigen</button></form></div><table><tr><th>Zeit</th><th>ID</th><th>Symbol</th><th>Seite</th><th>Volumen</th><th>Status</th><th>Validierung</th></tr>{% for x in rows %}<tr><td>{{x.created_at}}</td><td>{{x.client_order_id}}</td><td>{{x.symbol}}</td><td>{{x.side}}</td><td>{{x.volume}}</td><td>{{x.status}}</td><td>{{x.validate_only}}</td></tr>{% endfor %}</table>''',result=result,error=error,token=token,rows=rows)
 return bp
