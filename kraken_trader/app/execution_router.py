"""All-in execution routing for EUR/USD Kraken products.

The router is side-effect free. It compares the complete EUR cost of each
available product route, including the EUR/USD conversion leg for USD quotes.
"""
from decimal import Decimal
D=lambda value:Decimal(str(value or 0))

class ExecutionRouteError(ValueError): pass

def _ticker(item):
 if not item:return None
 bid=D((item.get('b') or [0])[0]);ask=D((item.get('a') or [0])[0]);last=D((item.get('c') or [0])[0])
 if bid<=0 or ask<=0:
  if last<=0:return None
  bid=ask=last
 return {'bid':bid,'ask':ask,'mid':(bid+ask)/2}

def _find(tickers,*keys):
 wanted={str(x or '').upper().replace('/','') for x in keys if x}
 normalized={x.replace('XBT','BTC') for x in wanted}
 for key,value in (tickers or {}).items():
  compact=str(key).upper().replace('/','')
  if compact in wanted or compact.replace('XBT','BTC') in normalized:return value
 return None

def route_cost(alternative,tickers,notional_eur,trade_fee_bps,fx_fee_bps,slippage_bps,side='buy'):
 market=_ticker(_find(tickers,alternative.get('source_key'),alternative.get('symbol')))
 if not market:return {'valid':False,'reason':'NO_PRODUCT_TICKER'}
 fx_required=str(alternative.get('quote_asset') or '').upper()=='USD' or str(alternative.get('symbol') or '').upper().endswith('/USD')
 fx=_ticker(_find(tickers,'EUR/USD','EURUSD')) if fx_required else None
 if fx_required and not fx:return {'valid':False,'reason':'NO_EUR_USD_TICKER'}
 eur=D(notional_eur)
 if eur<=0:raise ExecutionRouteError('notional_eur must be positive')
 trade_fee=D(trade_fee_bps)/10000;fx_fee=D(fx_fee_bps)/10000 if fx_required else D(0);slip=D(slippage_bps)/10000
 buy=str(side).lower()=='buy';executable=market['ask'] if buy else market['bid'];product_spread=abs(executable-market['mid'])/market['mid'];product_slippage=slip
 product_spread_cost=eur*product_spread;trade_fee_cost=eur*trade_fee;slippage_cost=eur*product_slippage
 if not fx_required:
  total=product_spread_cost+trade_fee_cost+slippage_cost
  return {'valid':True,'symbol':alternative.get('symbol'),'quote_currency':'EUR','fx_required':False,'fx_rate':D(1),'product_notional_eur':eur,'fx_notional_eur':D(0),'product_spread_cost_eur':product_spread_cost,'trade_fee_eur':trade_fee_cost,'slippage_eur':slippage_cost,'fx_cost_eur':D(0),'total_cost_eur':total,'total_cost_pct':total/eur*100}
 # A EUR/USD quote converts the intended EUR exposure into USD at mid for
 # comparison. The actual conversion uses bid when buying USD and ask when
 # converting USD proceeds back to EUR.
 fx_rate=fx['bid'] if buy else fx['ask'];mid=fx['mid']
 usd_notional=eur*mid
 ideal_eur=usd_notional/mid
 actual_eur=usd_notional/fx_rate
 fx_spread_cost=abs(actual_eur-ideal_eur)
 fx_fee_cost=eur*fx_fee
 total=product_spread_cost+trade_fee_cost+slippage_cost+fx_spread_cost+fx_fee_cost
 return {'valid':True,'symbol':alternative.get('symbol'),'quote_currency':'USD','fx_required':True,'fx_rate':fx_rate,'product_notional_eur':eur,'product_notional_usd':usd_notional,'fx_notional_eur':actual_eur,'product_spread_cost_eur':product_spread_cost,'trade_fee_eur':trade_fee_cost,'slippage_eur':slippage_cost,'fx_spread_cost_eur':fx_spread_cost,'fx_fee_eur':fx_fee_cost,'fx_cost_eur':fx_spread_cost+fx_fee_cost,'total_cost_eur':total,'total_cost_pct':total/eur*100}

def choose_route(alternatives,tickers,notional_eur,trade_fee_bps=40,fx_fee_bps=10,slippage_bps=10,side='buy'):
 ranked=[]
 for market in alternatives:
  cost=route_cost(market,tickers,notional_eur,trade_fee_bps,fx_fee_bps,slippage_bps,side);ranked.append((cost.get('total_cost_eur',D('999999999')),cost.get('symbol',market.get('symbol')),market,cost))
 valid=[x for x in ranked if x[3].get('valid')]
 if not valid:return None,{'status':'NO_VALID_ROUTE','routes':[x[3] for x in ranked]}
 valid.sort(key=lambda x:(x[0],x[1]));_,_,selected,cost=valid[0]
 return selected,{'status':'VALID','selected':cost,'routes':[x[3] for x in valid]}
