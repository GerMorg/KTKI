class ExternalNewsAI:
 def __init__(self,db,options):self.db,self.options=db,options or {}
 def analyze_pending(self):return {'status':'DISABLED' if not self.options.get('ai_news_enabled') else 'DEFERRED','processed':0}
