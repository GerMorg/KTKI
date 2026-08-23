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
  data=dict(data or {});headers={"User-Agent":"HA-Kraken-Trader/0.1.0-dev.3"}
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
 def pairs(self):return self.call("/0/public/AssetPairs")
 def assets(self):return self.call("/0/public/Assets")
 def ticker(self,pairs):return self.call("/0/public/Ticker",{"pair":",".join(pairs)}) if pairs else {}
 def balance(self):return self.call("/0/private/Balance",private=True)
 def balance_ex(self):return self.call("/0/private/BalanceEx",private=True)
 def ledgers(self,offset=0):return self.call("/0/private/Ledgers",{"type":"all","ofs":offset},private=True)
 def websocket_token(self):return self.call("/0/private/GetWebSocketsToken",private=True)
