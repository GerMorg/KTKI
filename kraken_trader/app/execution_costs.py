from decimal import Decimal
from execution_router import choose_route, route_cost
D=lambda x:Decimal(str(x or 0))

def ticker_item(tickers,market):
    for key in (market.get('source_key'),market.get('symbol')):
        if key and key in tickers:return tickers[key]
    wanted=str(market.get('symbol') or '').replace('/','').replace('BTC','XBT').upper()
    for key,value in (tickers or {}).items():
        compact=str(key).replace('/','').replace('X','').replace('Z','').upper()
        if wanted.replace('X','').replace('Z','')==compact:return value
    return None

def market_metrics(item):
    if not item:return {'valid':False,'spread_rate':D('999'),'liquidity':D(0),'mid':D(0)}
    bid=D((item.get('b') or [0])[0]);ask=D((item.get('a') or [0])[0]);last=D((item.get('c') or [0])[0]);mid=(bid+ask)/2 if bid>0 and ask>0 else last
    volume=D((item.get('v') or [0,0])[-1]);spread=(ask-bid)/mid if mid>0 and ask>=bid>0 else D('999')
    return {'valid':mid>0,'spread_rate':spread,'liquidity':volume*mid,'mid':mid,'bid':bid,'ask':ask}

def execution_cost_breakdown(market,item,fx_item,trade_fee_bps=40,fx_fee_bps=10,slippage_bps=10):
    tickers={market.get('source_key') or market.get('symbol'):item}
    if fx_item:tickers['EUR/USD']=fx_item
    result=route_cost(market,tickers,D(100),trade_fee_bps,fx_fee_bps,slippage_bps,'buy');metrics=market_metrics(item)
    if not result.get('valid'):
        return {'valid':False,'total_rate':D('999'),'product_spread_rate':D('999'),'trade_fee_rate':D(0),'slippage_rate':D(0),'fx_required':str(market.get('quote_asset') or '').upper()=='USD','fx_spread_rate':D(0),'fx_fee_rate':D(0),'liquidity':metrics['liquidity']}
    total_rate=D(result['total_cost_pct'])/100
    return {'valid':True,'product_spread_rate':D(result['product_spread_cost_eur'])/100,'trade_fee_rate':D(result['trade_fee_eur'])/100,'slippage_rate':D(result['slippage_eur'])/100,'fx_required':bool(result.get('fx_required')),'fx_spread_rate':D(result.get('fx_spread_cost_eur',0))/100,'fx_fee_rate':D(result.get('fx_fee_eur',0))/100,'liquidity':metrics['liquidity'],'total_rate':total_rate}

def choose_execution_pair(alternatives,tickers,trade_fee_bps=40,fx_fee_bps=10,slippage_bps=10):
    selected,details=choose_route(alternatives,tickers,100,trade_fee_bps,fx_fee_bps,slippage_bps,'buy')
    if not selected:
        if not alternatives:return None,{'valid':False,'total_rate':D('999'),'liquidity':D(0)},[]
        fallback=alternatives[0];cost=execution_cost_breakdown(fallback,ticker_item(tickers,fallback),tickers.get('EUR/USD'),trade_fee_bps,fx_fee_bps,slippage_bps)
        return fallback,cost,details.get('routes',[])
    chosen=selected
    chosen_cost=details['selected']
    cost={'valid':True,'total_rate':D(chosen_cost['total_cost_pct'])/100,'product_spread_rate':D(chosen_cost['product_spread_cost_eur'])/100,'trade_fee_rate':D(chosen_cost['trade_fee_eur'])/100,'slippage_rate':D(chosen_cost['slippage_eur'])/100,'fx_required':bool(chosen_cost.get('fx_required')),'fx_spread_rate':D(chosen_cost.get('fx_spread_cost_eur',0))/100,'fx_fee_rate':D(chosen_cost.get('fx_fee_eur',0))/100,'liquidity':market_metrics(ticker_item(tickers,chosen))['liquidity']}
    return selected,cost,[{'symbol':x.get('symbol'),'total_cost_rate':str(D(x.get('total_cost_pct',999))/100),'liquidity':str(market_metrics(ticker_item(tickers,next((m for m in alternatives if m.get('symbol')==x.get('symbol')),{})))['liquidity']),'valid':x.get('valid')} for x in details.get('routes',[])]
