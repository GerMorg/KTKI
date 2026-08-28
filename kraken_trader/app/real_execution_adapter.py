class RealExecutionDisabled(RuntimeError): pass
class RealExecutionAdapter:
 def __init__(self,engine):self.engine=engine
 @property
 def enabled(self):return self.engine.enabled()
 def prepare(self,plan):
  missing=[x for x in ('symbol','action','volume') if x not in plan]
  return {'status':'REJECTED' if missing else 'PREPARED','missing':missing,'real_execution':False,'plan':dict(plan)}
 def execute(self,plan,approval_token,validate_only=True):
  if not validate_only and not plan.get('explicit_live_confirmation'):raise RealExecutionDisabled('Explizite Live-BestÃ¤tigung fehlt')
  return self.engine.submit(plan['symbol'],plan['action'],plan['volume'],plan.get('order_type','limit'),plan.get('limit_price'),plan.get('client_order_id'),approval_token,validate_only)
