import os,sys
if '/app' not in sys.path and os.path.isdir('/app'): sys.path.insert(0,'/app')

# The canonical runtime explicitly disables expensive startup migration. Patch
# the imported symbol before core.py binds it so the old service layer cannot
# turn database text repair into a startup blocker.
if os.environ.get('APP_SKIP_TEXT_REPAIR') == '1':
    try:
        import text_encoding
        text_encoding.repair_database = lambda db: {'status':'SKIPPED','changed':0}
    except Exception:
        pass

# v78 supersedes selected legacy Flask views. Remove an existing endpoint before
# Flask registers the canonical replacement. This keeps the new route explicit.
try:
    from flask import Flask
    if not getattr(Flask,'_ktki_endpoint_replacement',False):
        _orig=Flask.add_url_rule
        def _patched(self,rule,endpoint=None,view_func=None,**options):
            ep=endpoint or (view_func.__name__ if view_func else None)
            if ep and ep in self.view_functions:
                self.view_functions.pop(ep,None)
                self.url_map._rules[:]=[r for r in self.url_map._rules if r.endpoint!=ep]
                self.url_map._rules_by_endpoint.pop(ep,None)
                self.url_map._remap=True
            return _orig(self,rule,endpoint,view_func,**options)
        Flask.add_url_rule=_patched
        Flask._ktki_endpoint_replacement=True
except Exception:
    pass

# Preserve PaperEngine payload normalization used by both manual and automatic paths.
try:
    from paper_engine import PaperEngine
    if not getattr(PaperEngine,'_ktki_decision_normalized',False):
        _original_execute=PaperEngine.execute
        def _execute_normalized(self,symbol,side,gross,reason,decision):
            if isinstance(decision,list): decision=next((dict(item) for item in decision if isinstance(item,dict)),{})
            elif not isinstance(decision,dict): decision={}
            return _original_execute(self,symbol,side,gross,reason,decision)
        PaperEngine.execute=_execute_normalized
        PaperEngine._ktki_decision_normalized=True
except Exception:
    pass
