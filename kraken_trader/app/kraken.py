import base64,hashlib,hmac,json,time,urllib.parse,urllib.request
class KrakenError(Exception):pass
class KrakenClient:
 base="https://api.kraken.com"
 def __init__(self,key="",secret="",timeout=25):self.key,self.secret,self.timeout=key,secret,timeout
 @staticmethod
 def sign(path,data,secret):
  enc=urllib.parse.urlencode(data);digest=hashlib.sha256(str(data["nonce"]).encode()+enc.encode()).digest()
  return base64.b64encode(hmac.new(base64.b64decode(secret),path.encode()+digest,hashlib.sha512).digest()).decode()
 def call(self,path,data=None,private=False):
  data=dict(data or {});headers={"User-Agent":"HA-Kraken-Trader/0.1.0-dev.29"}
  if private:
   if not self.key or not self.secret:raise KrakenError("API-Key oder Private Key fehlt")
   data["nonce"]=str(time.time_ns());headers.update({"API-Key":self.key,"API-Sign":self.sign(path,data,self.secret)})
  req=urllib.request.Request(self.base+path,data=urllib.parse.urlencode(data).encode() if data else None,headers=headers)
  try:
   with urllib.request.urlopen(req,timeout=self.timeout) as r:payload=json.load(r)
  except Exception as exc:raise KrakenError("Verbindungsfehler: "+type(exc).__name__) from exc
  if payload.get("error"):raise KrakenError("; ".join(payload["error"]))
  return payload.get("result",{})
 def status(self):return self.call("/0/public/SystemStatus")
 def pairs(self,asset_class="currency"):
  requested=asset_class
  api_class='tokenized_asset' if requested=='tokenized_asset' else 'currency'
  data={"aclass_base":api_class,"assetVersion":1,"info":"info"}
  if requested=='tokenized_asset':data["execution_venue"]="international"
  result=self.call("/0/public/AssetPairs",data)
  if requested!='forex':return result
  fiat={'EUR','USD','GBP','CHF','JPY','CAD','AUD','NZD'}
  return {k:v for k,v in result.items() if str(v.get('base')) in fiat and str(v.get('quote')) in fiat}
 def assets(self,asset_class="currency"):return self.call("/0/public/Assets",{"aclass":asset_class,"assetVersion":1})
 def ticker(self,pairs,asset_class="currency"):
  if not pairs:return {}
  data={"pair":",".join(pairs),"assetVersion":1}
  if asset_class=="tokenized_asset":data["asset_class"]=asset_class
  return self.call("/0/public/Ticker",data)
 def trade_volume(self,pairs,fee_info=True):
  data={'pair':','.join(pairs),'fee-info':'true' if fee_info else 'false'}
  return self.call('/0/private/TradeVolume',data,private=True)
 def balance(self):return self.call("/0/private/Balance",private=True)
 def balance_ex(self):return self.call("/0/private/BalanceEx",private=True)
 def ledgers(self,offset=0):return self.call("/0/private/Ledgers",{"type":"all","ofs":offset},private=True)
 def websocket_token(self):return self.call("/0/private/GetWebSocketsToken",private=True)

 def ohlc(self,pair,interval=60,asset_class='currency',since=None):
  data={'pair':pair,'interval':int(interval),'assetVersion':1}
  if since is not None:data['since']=int(since)
  if asset_class=='tokenized_asset':data['asset_class']=asset_class
  return self.call('/0/public/OHLC',data)




