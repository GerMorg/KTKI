import json
class ProductView:
 def __init__(self,db):self.db=db
 def rows(self):
  products=self.db.rows('SELECT * FROM canonical_products ORDER BY category,canonical_id');positions={x['symbol']:x for x in self.db.rows('SELECT * FROM paper_positions')};out=[]
  for p in products:
   raw=json.loads(p.get('alternatives_json') or '[]');alts=raw.get('pairs',[]) if isinstance(raw,dict) else [x.get('symbol') for x in raw if isinstance(x,dict)];ranking=raw.get('ranking',[]) if isinstance(raw,dict) else []
   by={x.get('symbol'):x for x in ranking};eur=next((x for x in ranking if str(x.get('symbol','')).endswith('/EUR')),None);usd=next((x for x in ranking if str(x.get('symbol','')).endswith('/USD')),None);selected=p.get('selected_symbol');position=next((x for s,x in positions.items() if s==selected or s in alts),None)
   reason='Niedrigste vollstÃ¤ndige erwartete AusfÃ¼hrungskosten' if selected else 'Noch keine Paarwahl nach aktuellem Tickerlauf'
   out.append(dict(p,alternatives=alts,ranking=ranking,eur_cost=(eur or {}).get('total_cost_rate'),usd_cost=(usd or {}).get('total_cost_rate'),selection_reason=reason,position_symbol=position.get('symbol') if position else None,position_quantity=position.get('quantity') if position else None))
  return out


