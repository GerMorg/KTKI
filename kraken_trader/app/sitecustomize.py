import os,sys
APP_DIR='/app'
if os.path.isdir(APP_DIR) and APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

# v78 deliberately supersedes selected legacy Flask views. Flask normally rejects
# registering another function under the same endpoint. Remove the old mapping
# before the canonical runtime registers its replacement.
try:
    from flask import Flask
    if not getattr(Flask, '_ktki_endpoint_replacement', False):
        _original_add_url_rule = Flask.add_url_rule
        def _add_url_rule_clean(self, rule, endpoint=None, view_func=None, **options):
            resolved = endpoint or (view_func.__name__ if view_func is not None else None)
            if resolved and resolved in self.view_functions:
                self.view_functions.pop(resolved, None)
                self.url_map._rules[:] = [r for r in self.url_map._rules if r.endpoint != resolved]
                self.url_map._rules_by_endpoint.pop(resolved, None)
                self.url_map._remap = True
            if rule == '/':
                self.url_map._rules[:] = [r for r in self.url_map._rules if r.rule != '/']
                for key,rules in list(self.url_map._rules_by_endpoint.items()):
                    kept=[r for r in rules if r.rule != '/']
                    if kept:self.url_map._rules_by_endpoint[key]=kept
                    else:self.url_map._rules_by_endpoint.pop(key,None)
                self.url_map._remap = True
            return _original_add_url_rule(self, rule, endpoint, view_func, **options)
        Flask.add_url_rule = _add_url_rule_clean
        Flask._ktki_endpoint_replacement = True
except Exception:
    pass

try:
    from paper_engine import PaperEngine
    if not getattr(PaperEngine, '_ktki_decision_normalized', False):
        _original_execute = PaperEngine.execute
        def _execute_normalized(self, symbol, side, gross, reason, decision):
            if isinstance(decision, list):
                decision = next((dict(item) for item in decision if isinstance(item, dict)), {})
            elif not isinstance(decision, dict):
                decision = {}
            return _original_execute(self, symbol, side, gross, reason, decision)
        PaperEngine.execute = _execute_normalized
        PaperEngine._ktki_decision_normalized = True
except Exception:
    pass
