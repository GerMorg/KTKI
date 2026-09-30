"""Deterministic execution-confidence tiers for autonomous real trading.

Confidence is a decision aid, not a probability. It combines the live scanner
score with the current family health score and, when available, directional
calibration. Higher confidence unlocks higher leverage; lower confidence stays
unleveraged. Short opening has an independent DOWN-calibration gate.
"""
from decimal import Decimal

D=lambda x:Decimal(str(x or 0))

def _clamp(v,lo=0,hi=100):
    return max(D(lo),min(D(hi),D(v)))

def _health_score(health):
    try:return _clamp(health.get('score',0))
    except Exception:return D(0)

def _calibration_score(calibration):
    if not calibration or calibration.get('direction') in (None,'SPOT'):
        return D(50)
    samples=D(calibration.get('samples',0))
    required=D(calibration.get('required_samples',20) or 20)
    win=D(calibration.get('win_rate',0) or 0)*100
    net=D(calibration.get('net_return_pct',0) or 0)
    sample_score=_clamp(samples/required*100 if required else 0)
    net_score=_clamp(50+net)
    return sample_score*D('0.25')+win*D('0.45')+net_score*D('0.30')

def execution_confidence(scanner_score,health,calibration=None):
    return _clamp(D(scanner_score)*D('0.65')+_health_score(health)*D('0.20')+_calibration_score(calibration)*D('0.15'))

def choose_execution(confidence,margin_enabled,max_leverage,spot_min=70,margin_2x=80,margin_3x=88,margin_4x=94,margin_5x=97):
    c=D(confidence);max_lev=int(D(max_leverage))
    if c<D(spot_min):return {'mode':'BLOCKED','leverage':D(0),'confidence':str(c),'reason':'EXECUTION_CONFIDENCE_BELOW_SPOT'}
    if not margin_enabled:return {'mode':'SPOT','leverage':D(1),'confidence':str(c),'reason':'SPOT_ONLY_MARGIN_DISABLED'}
    for lev,threshold in ((5,D(margin_5x)),(4,D(margin_4x)),(3,D(margin_3x)),(2,D(margin_2x))):
        if max_lev>=lev and c>=threshold:return {'mode':'MARGIN','leverage':D(lev),'confidence':str(c),'reason':f'CONFIDENCE_UNLOCKS_{lev}X'}
    return {'mode':'SPOT','leverage':D(1),'confidence':str(c),'reason':'CONFIDENCE_BELOW_MARGIN_TIER'}

def short_execution(confidence,calibration,max_leverage,short_min=82,margin_2x=80,margin_3x=88,margin_4x=94,margin_5x=97):
    c=D(confidence)
    if c<D(short_min):return {'mode':'BLOCKED','leverage':D(0),'confidence':str(c),'reason':'SHORT_CONFIDENCE_BELOW_THRESHOLD'}
    if not calibration or calibration.get('status')!='READY':return {'mode':'BLOCKED','leverage':D(0),'confidence':str(c),'reason':'DOWN_CALIBRATION_NOT_READY'}
    return choose_execution(c,True,max_leverage,spot_min=0,margin_2x=margin_2x,margin_3x=margin_3x,margin_4x=margin_4x,margin_5x=margin_5x)
