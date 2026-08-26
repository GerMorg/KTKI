MARKERS=(chr(0x00c3),chr(0x00c2),chr(0x00e2)+chr(0x20ac),chr(0x00e2)+chr(0x201a),chr(0x00f0)+chr(0x0178),chr(0xfffd))
def corruption_score(value):return sum(str(value or '').count(x) for x in MARKERS)
def repair_text(value):
 if not isinstance(value,str):return value
 for _ in range(5):
  placeholders={};buf=[]
  for index,ch in enumerate(value):
   try:ch.encode('cp1252');buf.append(ch)
   except UnicodeEncodeError:
    token=f'[[[U{index:08d}]]]';placeholders[token]=ch;buf.append(token)
  try:candidate=''.join(buf).encode('cp1252').decode('utf-8')
  except UnicodeDecodeError:break
  for token,ch in placeholders.items():candidate=candidate.replace(token,ch)
  if corruption_score(candidate)<corruption_score(value):value=candidate
  else:break
 return value
def repair_database(db):
 marker='utf8_data_migration_v4'
 if db.value(marker,'')=='done':return {'status':'ALREADY_DONE','changed':0}
 changed=0
 with db.con() as c:
  tables=[x['name'] for x in db.rows("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
  for table in tables:
   columns=[x for x in db.rows(f'PRAGMA table_info("{table}")') if str(x.get('type') or '').upper().startswith('TEXT')]
   if not columns:continue
   pk=[x['name'] for x in db.rows(f'PRAGMA table_info("{table}")') if x.get('pk')]
   if not pk:continue
   for row in db.rows(f'SELECT * FROM "{table}"'):
    updates={col['name']:repair_text(row.get(col['name'])) for col in columns}
    updates={k:v for k,v in updates.items() if v!=row.get(k)}
    if not updates:continue
    set_sql=','.join(f'"{k}"=?' for k in updates);where=' AND '.join(f'"{k}"=?' for k in pk)
    c.execute(f'UPDATE "{table}" SET {set_sql} WHERE {where}',list(updates.values())+[row[k] for k in pk]);changed+=len(updates)
 db.set_setting(marker,'done');db.audit('UTF8_DATA_MIGRATION_V4',str(changed));return {'status':'DONE','changed':changed}




