import re
TRADITIONAL_ASSET_CLASSES={'equity','stock','stocks','traditional_equity'}

def normalized_asset(value):
 value=re.sub(r'[^A-Z0-9]','',str(value or '').upper().strip())
 aliases={'XXBT':'BTC','XBT':'BTC','ZEUR':'EUR','ZUSD':'USD'}
 return aliases.get(value,value)

def product_kind(asset_class,category=None):
 ac=str(asset_class or 'currency')
 if ac=='tokenized_asset':return 'xstock'
 if ac=='forex':return 'forex'
 if ac in TRADITIONAL_ASSET_CLASSES:return 'traditional_stock'
 return str(category or ac)

def canonical_product_id(asset_class,base_asset,category=None):return product_kind(asset_class,category)+':'+normalized_asset(base_asset)
def is_traditional_stock(asset_class):return str(asset_class or '') in TRADITIONAL_ASSET_CLASSES


