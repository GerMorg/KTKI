class RealExecutionDisabled(RuntimeError):pass
class RealExecutionAdapter:
 enabled=False
 def prepare(self,plan):
  required=('symbol','action','confidence','leverage','target_exposure_eur');missing=[x for x in required if x not in plan]
  return {'status':'REJECTED' if missing else 'PREPARED_ONLY','missing':missing,'real_execution':False,'plan':plan}
 def execute(self,plan):raise RealExecutionDisabled('Real execution is hard disabled')
