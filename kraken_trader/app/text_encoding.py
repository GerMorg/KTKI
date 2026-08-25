MARKERS=(chr(0x00c3),chr(0x00c2),chr(0x00e2),chr(0xfffd))
def corruption_score(v):return sum(str(v or '').count(x) for x in MARKERS)
def repair_text(v):
 if not isinstance(v,str):return v
 for _ in range(4):
  try:c=v.encode('cp1252').decode('utf-8')
  except (UnicodeEncodeError,UnicodeDecodeError):break
  if corruption_score(c)<corruption_score(v):v=c
  else:break
 return v
def repair_database(db):
 if db.value('utf8_data_migration_v3','')=='done':return
 db.set_setting('utf8_data_migration_v3','done');db.audit('UTF8_DATA_MIGRATION_V3')
