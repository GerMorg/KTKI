"""v93 execution confidence: candidate conviction plus regime and model quality.

The confidence is a deterministic sizing/routing score, not a probability.
Model health changes confidence and target exposure; it is not a blanket entry
permission. Directional calibration can still limit aggressive leverage/shorts.
"""
from decimal import Decimal
D=lambda x:Decimal(str(x or 0))

def _clamp(v,lo=0,hi=100):
    return max(D(lo),min(D(hi),D(v)))

def _health_score(health):
    return _clamp((health or {}).get('quality_score',(health or {}).get('score',50)))

def _regime_score(regime,direction):
    r=str(regime or 'NEUTRAL').upper()
    d=str(direction or 'UP').upper()
    if d in ('UP','BUY'):
        return {'BULL':100,'NEUTRAL':62,'MIXED':50,'BEAR':20}.get(r,50)
    return {'BEAR':100,'NEUTRAL':62,'MIXED':50,'BULL':20}.get(r,50)

def _calibration_score(calibration):
    if not calibration or calibration.get('direction') in (None,'SPOT'):
        return D(50)
    samples=D(calibration.get('samples',0)); required=max(D(1),D(calibration.get('required_samples',20) or 20))
    if samples<=0:return D(40)
    sample_score=_clamp(samples/required*100)
    win=_clamp(D(calibration.get('win_rate',0) or 0)*100)
    net=D(calibration.get('net_return_pct',0) or 0)
    net_score=_clamp(50+net,0,100)
    return sample_score*D('.20')+win*D('.50')+net_score*D('.30')

def execution_confidence(scanner_score,health,calibration=None,regime='NEUTRAL',direction='UP'):
    scanner=_clamp(scanner_score)
    quality=_health_score(health)
    regime_quality=D(_regime_score(regime,direction))
    calibration_quality=_calibration_score(calibration) if calibration else D(50)
    # Candidate conviction remains dominant. Health and regime control risk
    # sizing/routing rather than turning an otherwise valid signal into a ban.
    return _clamp(scanner*D('.62')+quality*D('.18')+regime_quality*D('.12')+calibration_quality*D('.08'))

def choose_execution(confidence,margin_enabled,max_leverage,spot_min=65,margin_2x=78,margin_3x=86,margin_4x=93,margin_5x=97,calibration=None):
    c=D(confidence);max_lev=int(D(max_leverage))
    if c<D(spot_min):
        return {'mode':'BLOCKED','leverage':D(0),'confidence':str(c),'reason':'CANDIDATE_CONFIDENCE_BELOW_SPOT'}
    if not margin_enabled:
        return {'mode':'SPOT','leverage':D(1),'confidence':str(c),'reason':'SPOT_ONLY_MARGIN_DISABLED'}
    cal_ready=bool(calibration and calibration.get('status')=='READY')
    # 2x is available with sufficient directional evidence; higher leverage
    # requires READY calibration so learning controls leverage rather than Spot.
    if max_lev>=5 and c>=D(margin_5x) and cal_ready:return {'mode':'MARGIN','leverage':D(5),'confidence':str(c),'reason':'CONFIDENCE_AND_CALIBRATION_UNLOCK_5X'}
    if max_lev>=4 and c>=D(margin_4x) and cal_ready:return {'mode':'MARGIN','leverage':D(4),'confidence':str(c),'reason':'CONFIDENCE_AND_CALIBRATION_UNLOCK_4X'}
    if max_lev>=3 and c>=D(margin_3x) and cal_ready:return {'mode':'MARGIN','leverage':D(3),'confidence':str(c),'reason':'CONFIDENCE_AND_CALIBRATION_UNLOCK_3X'}
    if max_lev>=2 and c>=D(margin_2x) and cal_ready:return {'mode':'MARGIN','leverage':D(2),'confidence':str(c),'reason':'CONFIDENCE_AND_CALIBRATION_UNLOCK_2X'}
    return {'mode':'SPOT','leverage':D(1),'confidence':str(c),'reason':'MARGIN_CALIBRATION_NOT_READY_OR_TIER_NOT_REACHED'}

def short_execution(confidence,calibration,max_leverage,short_min=75,margin_2x=78,margin_3x=86,margin_4x=93,margin_5x=97):
    c=D(confidence)
    if c<D(short_min):return {'mode':'BLOCKED','leverage':D(0),'confidence':str(c),'reason':'SHORT_CONFIDENCE_BELOW_THRESHOLD'}
    if not calibration or calibration.get('status')!='READY':
        return {'mode':'BLOCKED','leverage':D(0),'confidence':str(c),'reason':'DOWN_CALIBRATION_NOT_READY'}
    return choose_execution(c,True,max_leverage,spot_min=short_min,margin_2x=margin_2x,margin_3x=margin_3x,margin_4x=margin_4x,margin_5x=margin_5x,calibration=calibration)
