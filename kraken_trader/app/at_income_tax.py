import csv,io,json,os
from datetime import datetime,timezone
from decimal import Decimal,InvalidOperation
from flask import Blueprint,Response,request
from db import now
from kraken import KrakenClient
RATE=Decimal('0.275')
DISCLAIMER='Unverbindliche Ausfüll- und Prüfhilfe, keine Steuer- oder Rechtsberatung. Die endgültige steuerliche Beurteilung muss anhand der vollständigen Unterlagen erfolgen.'
def D(v):
 try:return Decimal(str(v if v not in (None,'') else 0))
 except (InvalidOperation,ValueError,TypeError):return Decimal(0)
def money(v):return str(D(v).quantize(Decimal('0.01')))
def tax_year(v):
 try:y=int(v)
 except (TypeError,ValueError):y=datetime.now(timezone.utc).year-1
 return max(2009,min(datetime.now(timezone.utc).year,y))
class AustrianTaxInfo:
 def __init__(self,db):self.db=db;self.ensure()
 def ensure(self):
  with self.db.con() as c:
   c.execute('CREATE TABLE IF NOT EXISTS at_tax_reports(id INTEGER PRIMARY KEY AUTOINCREMENT,created_at TEXT NOT NULL,tax_year INTEGER NOT NULL,source TEXT NOT NULL,status TEXT NOT NULL,row_count INTEGER NOT NULL,taxable_gain_eur TEXT NOT NULL,deductible_loss_eur TEXT NOT NULL,estimated_tax_eur TEXT NOT NULL,warnings_json TEXT NOT NULL,details_json TEXT NOT NULL,csv_text TEXT NOT NULL)')
   c.execute('CREATE INDEX IF NOT EXISTS idx_at_tax_reports_year ON at_tax_reports(tax_year,id)')
   c.execute('CREATE TABLE IF NOT EXISTS real_tax_trades(txid TEXT PRIMARY KEY,trade_time REAL NOT NULL,pair TEXT NOT NULL,side TEXT NOT NULL,price TEXT NOT NULL,volume TEXT NOT NULL,cost TEXT NOT NULL,fee TEXT NOT NULL,payload_json TEXT NOT NULL,imported_at TEXT NOT NULL)')
   c.execute('CREATE INDEX IF NOT EXISTS idx_real_tax_trades_time ON real_tax_trades(trade_time,txid)')
 def _client(self):
  try:
   with open(os.getenv('APP_OPTIONS','/data/options.json'),encoding='utf-8') as f:o=json.load(f)
   return KrakenClient(o.get('kraken_api_key',''),o.get('kraken_api_secret','')) if o.get('kraken_api_key') and o.get('kraken_api_secret') else None
  except Exception:return None
 def refresh_real_trades(self):
  client=self._client()
  if not client:return {'status':'NO_API_CREDENTIALS','imported':0}
  imported=0;offset=0
  try:
   while True:
    result=client.call('/0/private/TradesHistory',{'type':'all','ofs':offset},private=True)
    if not isinstance(result,dict):raise TypeError('TradesHistory result is not a dict')
    trades=result.get('trades') or {}
    if not isinstance(trades,dict):raise TypeError('TradesHistory trades is not a dict')
    if not trades:break
    with self.db.con() as c:
     for txid,item in trades.items():
      if not isinstance(item,dict):continue
      c.execute('INSERT OR REPLACE INTO real_tax_trades VALUES(?,?,?,?,?,?,?,?,?,?)',(txid,float(item.get('time') or 0),str(item.get('pair') or ''),str(item.get('type') or '').lower(),str(item.get('price') or 0),str(item.get('vol') or 0),str(item.get('cost') or 0),str(item.get('fee') or 0),json.dumps(item,sort_keys=True),now()));imported+=1
    if len(trades)<50:break
    offset+=len(trades)
   self.db.audit('AT_TAX_REAL_TRADES_REFRESH',json.dumps({'imported':imported}));return {'status':'VALID','imported':imported}
  except Exception as exc:
   self.db.audit('AT_TAX_REAL_TRADES_REFRESH_FAILED',type(exc).__name__,'warning');return {'status':'ERROR','imported':imported,'error':type(exc).__name__}
 def _eur_pair(self,pair):return str(pair or '').upper().replace('/','').replace('XXBT','XBT').endswith('EUR')
 def _asset(self,pair):
  x=str(pair or '').upper().replace('/','').replace('XXBT','XBT').replace('XETH','ETH');return x[:-3].lstrip('XZ') if x.endswith(('EUR','USD')) else x
 def _real_rows(self,year):
  inventory={};rows=[];warnings=[]
  for t in self.db.rows('SELECT * FROM real_tax_trades ORDER BY trade_time,txid'):
   moment=datetime.fromtimestamp(float(t['trade_time']),tz=timezone.utc) if t['trade_time'] else None;side=str(t['side']).lower();qty=D(t['volume']);cost=D(t['cost']);fee=D(t['fee']);pair=t['pair'];eur=self._eur_pair(pair);asset=self._asset(pair);state=inventory.setdefault(asset,[Decimal(0),Decimal(0)])
   if moment is None or qty<=0 or side not in ('buy','sell'):warnings.append('Ungültiger Real-Trade: '+str(t['txid']));continue
   if side=='buy':
    if eur:state[0]+=qty;state[1]+=cost+fee
    else:warnings.append(f"Real-Trade {t['txid']}: Nicht-EUR-Paar benötigt vollständige FX-Bewertung")
    continue
   gap=qty>state[0];basis=Decimal(0) if gap or not eur else state[1]/state[0]*qty
   if not gap and eur:state[0]-=qty;state[1]-=basis
   if moment.year!=year:continue
   proceeds=cost-fee if eur else Decimal(0);gain=proceeds-basis if eur and not gap else Decimal(0);review=(not eur) or gap
   if review:warnings.append(f"Real-Trade {t['txid']}: {'Nicht-EUR-Paar' if not eur else 'Anschaffungsbestand nicht vollständig vorhanden'}")
   rows.append({'trade_id':t['txid'],'date':moment.isoformat(),'symbol':pair,'source':'real','quantity':money(qty),'proceeds_eur':money(proceeds),'acquisition_cost_eur':money(basis),'gain_loss_eur':money(gain),'tax_rate':'27,5 %' if not review else '','estimated_tax_eur':money(max(Decimal(0),gain)*RATE) if not review else '','review_required':'yes' if review else 'no'})
  return rows,warnings
 def _paper_rows(self,year):
  inventory={};rows=[];warnings=[]
  trades=self.db.rows("SELECT * FROM paper_trades WHERE substr(created_at,1,4)<=? ORDER BY created_at,id",(str(year),))
  for t in trades:
   s=inventory.setdefault(t['symbol'],[Decimal(0),Decimal(0)]);qty=D(t['quantity']);side=str(t['side']).upper()
   if qty<=0 or side not in ('BUY','SELL'):continue
   if side=='BUY':s[0]+=qty;s[1]+=D(t['net_eur']);continue
   gap=qty>s[0];basis=Decimal(0) if gap else s[1]/s[0]*qty
   if not gap:s[0]-=qty;s[1]-=basis
   if str(t['created_at'])[:4]!=str(year):continue
   proceeds=D(t['gross_eur'])-D(t['fee_eur']);gain=proceeds-basis;review=gap
   if review:warnings.append(f"Paper-Trade {t['id']}: Anschaffungsbestand nicht vollständig vorhanden")
   rows.append({'trade_id':str(t['id']),'date':t['created_at'],'symbol':t['symbol'],'source':'paper','quantity':money(qty),'proceeds_eur':money(proceeds),'acquisition_cost_eur':money(basis),'gain_loss_eur':money(gain),'tax_rate':'27,5 %' if not review else '','estimated_tax_eur':money(max(Decimal(0),gain)*RATE) if not review else '','review_required':'yes' if review else 'no'})
  return rows,warnings
 def analyze(self,year,source='real'):
  year=tax_year(year);source=source if source in ('real','paper','both') else 'real';refresh=self.refresh_real_trades() if source in ('real','both') else {'status':'NOT_REQUESTED','imported':0};rows=[];warnings=[]
  if source in ('real','both'):r,w=self._real_rows(year);rows+=r;warnings+=w
  if source in ('paper','both'):r,w=self._paper_rows(year);rows+=r;warnings+=w
  if not rows:warnings.append('Keine steuerlich auswertbaren Verkäufe im ausgewählten Steuerjahr gefunden')
  if source in ('real','both') and refresh['status']!='VALID':warnings.append('Realhandelsdaten konnten nicht vollständig importiert werden')
  fields=['trade_id','date','symbol','source','quantity','proceeds_eur','acquisition_cost_eur','gain_loss_eur','tax_rate','estimated_tax_eur','review_required'];b=io.StringIO();w=csv.DictWriter(b,fields,delimiter=';');w.writeheader();w.writerows(rows);valid=[x for x in rows if x['review_required']=='no'];g=sum((max(Decimal(0),D(x['gain_loss_eur'])) for x in valid),Decimal(0));l=sum((min(Decimal(0),D(x['gain_loss_eur'])) for x in valid),Decimal(0));result={'year':year,'source':source,'status':'REVIEW_REQUIRED' if warnings else 'READY_FOR_REVIEW','rows':rows,'warnings':sorted(set(warnings)),'taxable_gain_eur':money(g),'deductible_loss_eur':money(l),'estimated_tax_eur':money(max(Decimal(0),g+l)*RATE),'disclaimer':DISCLAIMER,'refresh':refresh,'rate':'27,5 %','csv':b.getvalue()}
  with self.db.con() as c:c.execute('INSERT INTO at_tax_reports(created_at,tax_year,source,status,row_count,taxable_gain_eur,deductible_loss_eur,estimated_tax_eur,warnings_json,details_json,csv_text) VALUES(?,?,?,?,?,?,?,?,?,?,?)',(now(),year,source,result['status'],len(rows),result['taxable_gain_eur'],result['deductible_loss_eur'],result['estimated_tax_eur'],json.dumps(result['warnings'],ensure_ascii=False),json.dumps(result,ensure_ascii=False),result['csv']))
  return result
 def latest(self,year):
  r=self.db.rows('SELECT * FROM at_tax_reports WHERE tax_year=? ORDER BY id DESC LIMIT 1',(tax_year(year),));return r[0] if r else None
def create_tax_blueprint(db,page):
 service=AustrianTaxInfo(db);bp=Blueprint('at_tax_v63',__name__)
 @bp.get('/tax-info',endpoint='tax_info')
 def tax_info():
  year=tax_year(request.args.get('year'));source=request.args.get('source','real');return page(_TAX_TEMPLATE,year=year,source=source,report=None)
 @bp.post('/tax-info',endpoint='tax_info_generate')
 def tax_info_generate():
  year=tax_year(request.form.get('year'));source=request.form.get('source','real')
  try:report=service.analyze(year,source)
  except Exception as exc:db.audit('AT_TAX_INFO_GUI_FAILED',type(exc).__name__+': '+str(exc)[:300],'error');report={'year':year,'source':source,'status':'ERROR','rows':[],'warnings':['Bericht konnte nicht erstellt werden: '+type(exc).__name__],'taxable_gain_eur':'0,00','deductible_loss_eur':'0,00','estimated_tax_eur':'0,00','rate':'27,5 %','refresh':{'status':'ERROR','imported':0},'disclaimer':DISCLAIMER}
  return page(_TAX_TEMPLATE,year=year,source=source,report=report)
 @bp.get('/tax-info.csv',endpoint='tax_csv_export')
 def tax_csv_export():
  report=service.latest(request.args.get('year'))
  if not report:return Response('Kein Bericht vorhanden',404,mimetype='text/plain')
  return Response(report['csv_text'],mimetype='text/csv',headers={'Content-Disposition':f"attachment; filename=steuerinfo-at-{report['tax_year']}.csv"})
 return bp
_TAX_TEMPLATE='''<h1>Steuerinfo Österreich</h1><p class=lead>Steuerliche Arbeits- und Prüfhilfe mit <b>Realhandel als Standardquelle</b>.</p><div class=card><form method=post><label>Steuerjahr<input name=year type=number min=2009 value="{{year}}"></label><label>Datenquelle<select name=source><option value=real {% if source=="real" %}selected{% endif %}>Realhandel – Kraken</option><option value=paper {% if source=="paper" %}selected{% endif %}>Paper-Handel</option><option value=both {% if source=="both" %}selected{% endif %}>Realhandel + Paper</option></select></label><button>Bericht erstellen / Realhandel aktualisieren</button></form></div>{% if report %}<div class=card><h2>{{report.status}}</h2><p>{{report.disclaimer}}</p><p>Quelle: <b>{{report.source}}</b> · Steuersatz: <b>{{report.rate}}</b></p><p>Positive Einkünfte {{report.taxable_gain_eur}} EUR · Verluste {{report.deductible_loss_eur}} EUR · rechnerische Steuer {{report.estimated_tax_eur}} EUR</p><p>Real-Import: {{report.refresh.status}} · {{report.refresh.imported}} Trades</p></div>{% if report.warnings %}<div class=card><b>Prüfhinweise</b><ul>{% for x in report.warnings %}<li>{{x}}</li>{% endfor %}</ul></div>{% endif %}<p><a class=button href="{{export_url}}">CSV exportieren</a></p><div class=tablewrap><table><tr><th>Datum</th><th>Quelle</th><th>Symbol</th><th>Erlös</th><th>Anschaffung</th><th>Ergebnis</th><th>Prüfung</th></tr>{% for x in report.rows %}<tr><td>{{x.date}}</td><td>{{x.source}}</td><td>{{x.symbol}}</td><td>{{x.proceeds_eur}}</td><td>{{x.acquisition_cost_eur}}</td><td>{{x.gain_loss_eur}}</td><td>{{x.review_required}}</td></tr>{% endfor %}</table></div>{% endif %}'''
