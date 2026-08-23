from decimal import Decimal,InvalidOperation
FIAT={'ZEUR':'EUR','EUR':'EUR','ZUSD':'USD','USD':'USD','ZGBP':'GBP','GBP':'GBP','ZCHF':'CHF','CHF':'CHF'}
def dec(v):
 try:return Decimal(str(v))
 except (InvalidOperation,ValueError,TypeError):return Decimal(0)
def normalize_asset(code,assets):
 alt=(assets.get(code) or {}).get('altname',code);return FIAT.get(code,FIAT.get(alt,alt.removeprefix('X').removeprefix('Z')))
def build_rows(balances,ledger_assets,assets,pairs,tickers):
 known=set(balances)|set(ledger_assets);rows=[];total=Decimal(0)
 for code in sorted(known):
  amount=dec(balances.get(code,0));name=normalize_asset(code,assets);price=None
  if name=='EUR':price=Decimal(1)
  else:
   for pair_id,pair in pairs.items():
    if normalize_asset(pair.get('base',''),assets)==name and normalize_asset(pair.get('quote',''),assets)=='EUR':
     tick=tickers.get(pair_id) or tickers.get(pair.get('altname'))
     if tick and tick.get('c'):price=dec(tick['c'][0]);break
  value=amount*price if price is not None else None
  if value is not None:total+=value
  rows.append({'asset':code,'display_name':name,'amount':str(amount),'eur_price':str(price) if price is not None else None,'eur_value':str(value) if value is not None else None,'classification':'HELD' if amount!=0 else 'HISTORICAL_ZERO','ever_held':1 if code in ledger_assets or amount!=0 else 0})
 quality='VALID' if all(x['eur_value'] is not None or dec(x['amount'])==0 for x in rows) else 'INCOMPLETE'
 return rows,str(total),quality
