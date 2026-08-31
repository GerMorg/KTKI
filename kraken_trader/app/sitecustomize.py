"""Small runtime compatibility patches loaded by Python's site module.

KTKI still contains legacy paper execution code whose public callers can hand
its decision argument as a one-element list. Normalize that boundary once so
both manual and automatic Paper paths share the same safe contract.
"""
try:
    from paper_engine import PaperEngine

    if not getattr(PaperEngine, '_v67_decision_normalized', False):
        _original_execute = PaperEngine.execute

        def _execute_normalized(self, symbol, side, gross, reason, decision):
            if isinstance(decision, list):
                decision = next((dict(item) for item in decision if isinstance(item, dict)), {})
            elif not isinstance(decision, dict):
                decision = {}
            return _original_execute(self, symbol, side, gross, reason, decision)

        PaperEngine.execute = _execute_normalized
        PaperEngine._v67_decision_normalized = True
except Exception:
    # The patch must never prevent application startup; the underlying engine
    # retains its original behavior when unavailable during interpreter boot.
    pass
