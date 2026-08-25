class RealExecutionDisabled(RuntimeError):pass
class RealExecutionAdapter:
 enabled=False
 def validate(self,plan):
  required={'symbol','action','amount'}
  if not isinstance(plan,dict) or not required.issubset(plan):raise ValueError('Unvollständiger Ausführungsplan')
  return {'valid':True,'real_execution_enabled':False}
 def execute(self,plan):
  raise RealExecutionDisabled('Realausführung ist hart deaktiviert')
