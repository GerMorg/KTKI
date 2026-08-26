from decimal import Decimal
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
 metrics=market_metrics(item);fee=D(trade_fee_bps)/10000;slippage=D(slippage_bps)/10000
 out={'valid':metrics['valid'],'product_spread_rate':metrics['spread_rate'],'trade_fee_rate':fee,'slippage_rate':slippage,'fx_required':str(market.get('quote_asset') or '').upper()=='USD' or str(market.get('symbol') or '').endswith('/USD'),'fx_spread_rate':D(0),'fx_fee_rate':D(0),'liquidity':metrics['liquidity']}
 if out['fx_required']:
  fx=market_metrics(fx_item);out['valid']=out['valid'] and fx['valid'];out['fx_spread_rate']=fx['spread_rate'];out['fx_fee_rate']=D(fx_fee_bps)/10000
 out['total_rate']=out['product_spread_rate']+out['trade_fee_rate']+out['slippage_rate']+out['fx_spread_rate']+out['fx_fee_rate']
 if not out['valid']:out['total_rate']=D('999')
 return out

def choose_execution_pair(alternatives,tickers,trade_fee_bps=40,fx_fee_bps=10,slippage_bps=10):
 fx=tickers.get('EUR/USD') or tickers.get('EURUSD')
 ranked=[]
 for market in alternatives:
  costs=execution_cost_breakdown(market,ticker_item(tickers,market),fx,trade_fee_bps,fx_fee_bps,slippage_bps)
  ranked.append((costs['total_rate'],-costs['liquidity'],0 if str(market.get('quote_asset') or '').upper()=='EUR' else 1,str(market.get('symbol')),market,costs))
 ranked.sort(key=lambda x:x[:4])
 _,_,_,_,selected,costs=ranked[0]
 return selected,costs,[{'symbol':x[4]['symbol'],'total_cost_rate':str(x[5]['total_rate']),'liquidity':str(x[5]['liquidity']),'valid':x[5]['valid']} for x in ranked]


