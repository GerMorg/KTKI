"""UTF-8 and legacy-mojibake repair helpers.

The repair is deliberately conservative: a value is changed only when a
cp1252-to-UTF-8 round-trip reduces known corruption markers.
"""
MARKERS=(chr(0x00c3),chr(0x00c2),chr(0x00e2),chr(0x00f0)+chr(0x0178),chr(0xfffd))
def corruption_score(value):
 value=str(value or '')
 return sum(value.count(marker) for marker in MARKERS)
def repair_text(value):
 if not isinstance(value,str) or not value:return value
 current=value
 for _ in range(3):
  try:candidate=current.encode('cp1252').decode('utf-8')
  except (UnicodeEncodeError,UnicodeDecodeError):break
  if corruption_score(candidate)<corruption_score(current):current=candidate
  else:break
 return current
def repair_database(db):
 """Idempotently repairs previously persisted display text and records the migration."""
 if db.value('utf8_data_migration_v1','')=='done':return {'status':'ALREADY_DONE','changed':0}
 tables={
  'settings':['value'],'audit':['event','level','details'],'portfolio_assets':['display_name','classification'],
  'paper_trades':['reason','decision_json'],'paper_decisions':['action','reason','data_quality'],
  'research_watchlist':['category','status','reasons_json'],'scanner_results':['signal','quality','reasons_json'],
  'news_sources':['name','last_status','last_error'],'news_items':['title','summary','topics_json','event_types_json','raw_json'],
  'news_market_links':['reason'],'research_jobs':['stage','error','details_json']}
 changed=0
 with db.con() as c:
  existing={x['name'] for x in db.rows("SELECT name FROM sqlite_master WHERE type='table'")}
  for table,columns in tables.items():
   if table not in existing:continue
   available={x['name'] for x in db.rows(f'PRAGMA table_info({table})')};columns=[x for x in columns if x in available]
   if not columns:continue
   for row in c.execute(f"SELECT rowid AS _repair_rowid,{','.join(columns)} FROM {table}").fetchall():
    updates={column:repair_text(row[column]) for column in columns}
    updates={k:v for k,v in updates.items() if v!=row[k]}
    if updates:
     c.execute(f"UPDATE {table} SET "+','.join(f'{k}=?' for k in updates)+' WHERE rowid=?',tuple(updates.values())+(row['_repair_rowid'],));changed+=1
 db.set_setting('utf8_data_migration_v1','done');db.audit('UTF8_DATA_MIGRATION',f'changed_rows={changed}')
 return {'status':'DONE','changed':changed}
