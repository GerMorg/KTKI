import re

TRADITIONAL_ASSET_CLASSES={"equity","stock","stocks","traditional_equity"}

def normalized_asset(value):
 value=str(value or "").upper().strip()
 value=value.removeprefix("X").removeprefix("Z") if value not in ("XBT",) else value
 return re.sub(r"[^A-Z0-9]","",value)

def canonical_product_id(asset_class,base_asset,category=None):
 ac=str(asset_class or "currency")
 kind="xstock" if ac=="tokenized_asset" else ("forex" if ac=="forex" else ("traditional_stock" if ac in TRADITIONAL_ASSET_CLASSES else str(category or ac)))
 return kind+":"+normalized_asset(base_asset)

def is_traditional_stock(asset_class):return str(asset_class or "") in TRADITIONAL_ASSET_CLASSES
