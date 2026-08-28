import csv, io, json, re
from flask import Blueprint, Response, jsonify, render_template_string, request
_SECRET_KEYS=re.compile(r"(api[_-]?key|secret|token|password|authorization)",re.I)
def _redact(value):
 if isinstance(value,dict): return {k:("[REDACTED]" if _SECRET_KEYS.search(str(k)) else _redact(v)) for k,v in value.items()}
 if isinstance(value,list): return [_redact(v) for v in value]
 return value
def safe_details(raw):
 try:return json.dumps(_redact(json.loads(raw or "{}")),ensure_ascii=False,sort_keys=True)
 except (TypeError,ValueError):return "[unstructured details omitted]" if _SECRET_KEYS.search(str(raw)) else str(raw or "")
class NotificationService:
 def __init__(self,db):self.db=db
 def notify(self,event,message,level="info",context=None):
  payload={"message":str(message),"context":_redact(context or {})};self.db.audit("USER_NOTIFICATION:"+str(event),json.dumps(payload,ensure_ascii=False,sort_keys=True),level);return payload
def create_monitoring_blueprint(db,page_renderer):
 bp=Blueprint("monitoring",__name__)
 def filtered_rows(limit=500):
  level=request.args.get("level","").strip().lower();event=request.args.get("event","").strip();clauses=[];params=[]
  if level:clauses.append("LOWER(level)=?");params.append(level)
  if event:clauses.append("event LIKE ?");params.append("%"+event+"%")
  where=" WHERE "+" AND ".join(clauses) if clauses else ""
  rows=db.rows("SELECT id,created_at,event,level,details FROM audit"+where+" ORDER BY id DESC LIMIT ?",tuple(params+[limit]))
  for row in rows:row["details"]=safe_details(row.get("details"))
  return rows
 @bp.get("/event-dashboard")
 def event_dashboard():
  template="""<h1>Ereignis-Dashboard</h1><p class=lead>Fehler, Warnungen und Benutzernachrichten aus dem Audit-Protokoll.</p><div class=card><form method=get><label>Stufe<select name=level><option value=''>Alle</option>{% for value in ['error','warning','info'] %}<option value='{{value}}' {{'selected' if selected_level==value else ''}}>{{value}}</option>{% endfor %}</select></label><label>Ereignis<input name=event value='{{selected_event}}'></label><button>Filtern</button></form></div><div class=tablewrap><table><tr><th>Zeit</th><th>Stufe</th><th>Ereignis</th><th>Details</th></tr>{% for row in rows %}<tr><td>{{row.created_at}}</td><td class='{{"error" if row.level=="error" else "warning" if row.level=="warning" else ""}}'>{{row.level}}</td><td>{{row.event}}</td><td><small>{{row.details}}</small></td></tr>{% else %}<tr><td colspan=4>Keine passenden Ereignisse.</td></tr>{% endfor %}</table></div>"""
  return page_renderer(render_template_string(template,rows=filtered_rows(),selected_level=request.args.get("level",""),selected_event=request.args.get("event","")))
 @bp.get("/api/audit/export")
 def audit_export():
  rows=filtered_rows(5000);fmt=request.args.get("format","json").lower()
  if fmt=="csv":
   out=io.StringIO(newline="");writer=csv.DictWriter(out,fieldnames=["id","created_at","event","level","details"]);writer.writeheader();writer.writerows(rows);return Response(out.getvalue(),mimetype="text/csv",headers={"Content-Disposition":"attachment; filename=audit-events.csv"})
  if fmt!="json":return jsonify({"status":"INVALID_FORMAT","allowed":["json","csv"]}),400
  return jsonify({"count":len(rows),"events":rows})
 return bp






