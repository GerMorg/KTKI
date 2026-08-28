import csv,io,json
from datetime import datetime,timezone
from decimal import Decimal,InvalidOperation
from flask import Blueprint,Response,request
from db import now
RATE=Decimal("0.275")
DISCLAIMER="Unverbindliche AusfÃƒÂ¼ll- und PrÃƒÂ¼fhilfe, keine Steuer- oder Rechtsberatung. Paper-Trades sind Simulationen."
def D(v):
 try:return Decimal(str(v or 0))
 except (InvalidOperation,ValueError,TypeError):return Decimal(0)
def money(v):return str(D(v).quantize(Decimal(".01")))
def tax_year(v):
 try:y=int(v)
 except (TypeError,ValueError):y=datetime.now(timezone.utc).year-1
 return max(2009,min(datetime.now(timezone.utc).year,y))
class AustrianTaxInfo:
 def __init__(self,db):self.db=db;self.ensure()
 def ensure(self):
  with self.db.con() as c:c.executescript("CREATE TABLE IF NOT EXISTS at_tax_reports(id INTEGER PRIMARY KEY AUTOINCREMENT,created_at TEXT NOT NULL,tax_year INTEGER NOT NULL,source TEXT NOT NULL,status TEXT NOT NULL,row_count INTEGER NOT NULL,taxable_gain_eur TEXT NOT NULL,deductible_loss_eur TEXT NOT NULL,estimated_tax_eur TEXT NOT NULL,warnings_json TEXT NOT NULL,details_json TEXT NOT NULL,csv_text TEXT NOT NULL);CREATE INDEX IF NOT EXISTS idx_at_tax_reports_year ON at_tax_reports(tax_year,id);")
 def analyze(self,year):
  year=tax_year(year);inventory={};rows=[];warnings=[]
  trades=self.db.rows("SELECT t.*,u.asset_class,u.category FROM paper_trades t LEFT JOIN market_universe u ON u.symbol=t.symbol WHERE substr(t.created_at,1,4)<=? ORDER BY t.created_at,t.id",(str(year),))
  for t in trades:
   symbol=t["symbol"];side=str(t["side"]).upper();qty=D(t["quantity"]);state=inventory.setdefault(symbol,[D(0),D(0)])
   if qty<=0 or side not in ("BUY","SELL"):warnings.append(f"Trade {t['id']}: ungÃƒÂ¼ltige Daten");continue
   if side=="BUY":state[0]+=qty;state[1]+=D(t["net_eur"]);continue
   gap=qty>state[0];basis=D(0) if gap else state[1]/state[0]*qty
   if not gap:state[0]-=qty;state[1]-=basis
   if int(str(t["created_at"])[:4])!=year:continue
   try:details=json.loads(t.get("decision_json") or "{}")
   except Exception:details={}
   ac=t.get("asset_class") or details.get("asset_class") or "unknown";cat=t.get("category") or details.get("category");crypto=ac in ("currency","crypto","crypto_spot") or cat=="crypto_spot";review=gap or not crypto
   proceeds=D(t["gross_eur"])-D(t["fee_eur"]);gain=proceeds-basis
   if review:warnings.append(f"Trade {t['id']}: Bestand oder Anlageklasse fachlich prÃƒÂ¼fen")
   rows.append({"trade_id":t["id"],"date":t["created_at"],"symbol":symbol,"asset_class":ac,"quantity":str(qty),"proceeds_eur":money(proceeds),"acquisition_cost_eur":money(basis),"gain_loss_eur":money(gain),"tax_rate":"27.5%" if crypto else "","estimated_tax_eur":money(max(D(0),gain)*RATE) if crypto and not review else "","review_required":"yes" if review else "no","classification_note":"Krypto-NeuvermÃƒÂ¶gen, gleitender Durchschnitt" if crypto else "Anlageklasse prÃƒÂ¼fen"})
  gains=sum((max(D(0),D(x["gain_loss_eur"])) for x in rows if x["review_required"]=="no"),D(0));losses=sum((min(D(0),D(x["gain_loss_eur"])) for x in rows if x["review_required"]=="no"),D(0));estimate=max(D(0),gains+losses)*RATE
  if not rows:warnings.append("Keine VerkÃƒÂ¤ufe im Steuerjahr gefunden")
  if self.db.rows("SELECT 1 FROM ledger LIMIT 1"):warnings.append("REST-Ledger vorhanden: v50 erklÃƒÂ¤rt bewusst nur Paper-Trades")
  fields=["trade_id","date","symbol","asset_class","quantity","proceeds_eur","acquisition_cost_eur","gain_loss_eur","tax_rate","estimated_tax_eur","review_required","classification_note"];buf=io.StringIO(newline="");w=csv.DictWriter(buf,fields,delimiter=";");w.writeheader();w.writerows(rows)
  status="REVIEW_REQUIRED" if warnings or any(x["review_required"]=="yes" for x in rows) else "READY_FOR_REVIEW";r={"year":year,"source":"paper_trades","status":status,"rows":rows,"warnings":sorted(set(warnings)),"taxable_gain_eur":money(gains),"deductible_loss_eur":money(losses),"estimated_tax_eur":money(estimate),"disclaimer":DISCLAIMER}
  with self.db.con() as c:c.execute("INSERT INTO at_tax_reports(created_at,tax_year,source,status,row_count,taxable_gain_eur,deductible_loss_eur,estimated_tax_eur,warnings_json,details_json,csv_text) VALUES(?,?,?,?,?,?,?,?,?,?,?)",(now(),year,"paper_trades",status,len(rows),r["taxable_gain_eur"],r["deductible_loss_eur"],r["estimated_tax_eur"],json.dumps(r["warnings"],ensure_ascii=False),json.dumps(r,ensure_ascii=False,sort_keys=True),buf.getvalue()))
  self.db.audit("AT_TAX_INFO_REPORT",json.dumps({"year":year,"status":status,"rows":len(rows)}));r["csv"]=buf.getvalue();return r
 def latest(self,year):
  x=self.db.rows("SELECT * FROM at_tax_reports WHERE tax_year=? ORDER BY id DESC LIMIT 1",(tax_year(year),));return x[0] if x else None
def create_tax_blueprint(db,page):
 service=AustrianTaxInfo(db);bp=Blueprint("at_tax",__name__)
 @bp.route("/tax-info",methods=["GET","POST"])
 def view():
  y=tax_year(request.values.get("year"));r=service.analyze(y) if request.method=="POST" else None
  return page("""<h1>Steuerinfo Ãƒâ€“sterreich</h1><p class=lead>Unverbindliche AusfÃƒÂ¼ll- und PrÃƒÂ¼fhilfe. Keine Steuer- oder Rechtsberatung.</p><div class=card><form method=post><label>Steuerjahr<input name=year type=number min=2009 value={{year}}></label><button>Paper-Bericht erzeugen</button></form></div>{% if report %}<div class=card><h2>{{report.status}}</h2><p>{{report.disclaimer}}</p><p>Gewinne {{report.taxable_gain_eur}} EUR Ã‚Â· Verluste {{report.deductible_loss_eur}} EUR Ã‚Â· rechnerische Steuer {{report.estimated_tax_eur}} EUR</p></div>{% if report.warnings %}<div class=card><ul>{% for x in report.warnings %}<li>{{x}}</li>{% endfor %}</ul></div>{% endif %}<p><a class=button href="{{url_for('at_tax.csv_export',year=year)}}">CSV herunterladen</a></p><table><tr><th>Datum</th><th>Symbol</th><th>ErlÃƒÂ¶s</th><th>Kosten</th><th>Ergebnis</th><th>PrÃƒÂ¼fung</th></tr>{% for x in report.rows %}<tr><td>{{x.date}}</td><td>{{x.symbol}}</td><td>{{x.proceeds_eur}}</td><td>{{x.acquisition_cost_eur}}</td><td>{{x.gain_loss_eur}}</td><td>{{x.review_required}}</td></tr>{% endfor %}</table>{% endif %}""",year=y,report=r)
 @bp.get("/tax-info.csv")
 def csv_export():
  r=service.latest(request.args.get("year"))
  if not r:return Response("Kein Bericht vorhanden",404,mimetype="text/plain")
  return Response(r["csv_text"],mimetype="text/csv",headers={"Content-Disposition":f"attachment; filename=steuerinfo-at-{r['tax_year']}.csv"})
 return bp
