class RealExecutionAdapter:
 """Validated boundary for a future execution transport. No Kraken order method exists here."""
 enabled=False
 def prepare(self,plan):
  required=('symbol','action','confidence','leverage','target_exposure_eur')
  missing=[x for x in required if x not in plan]
  return {'status':'REJECTED' if missing else 'PREPARED_ONLY','missing':missing,'real_execution':False,'plan':plan}
 def execute(self,plan):raise RuntimeError('Real execution is hard disabled')
