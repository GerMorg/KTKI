import base64,hashlib,hmac,json,time,urllib.parse,urllib.request
class KrakenError(RuntimeError):pass
class KrakenClient:
 base='https://api.kraken.com'
 def __init__(self,key='',secret='',timeout=20):self.key,self.secret,self.timeout=key,secret,timeout
 @staticmethod
 def sign(path,data,secret):
  enc=urllib.parse.urlencode(data); digest=hashlib.sha256(str(data['nonce']).encode()+enc.encode()).digest(); return base64.b64encode(hmac.new(base64.b64decode(secret),path.encode()+digest,hashlib.sha512).digest()).decode()
 def call(self,path,data=None,private=False):
  data=dict(data or {}); headers={'User-Agent':'HA-Kraken-Trader/0.1.0-dev.2'}
  if private:
   if not self.key or not self.secret:raise KrakenError('API-Key oder Private Key fehlt')
   data['nonce']=str(time.time_ns()); headers.update({'API-Key':self.key,'API-Sign':self.sign(path,data,self.secret)})
  req=urllib.request.Request(self.base+path,data=urllib.parse.urlencode(data).encode() if data else None,headers=headers)
  try:
   with urllib.request.urlopen(req,timeout=self.timeout) as r:p=json.load(r)
  except Exception as e:raise KrakenError('Verbindungsfehler: '+type(e).__name__) from e
  if p.get('error'):raise KrakenError('; '.join(p['error']))
  return p.get('result',{})
 def status(self):return self.call('/0/public/SystemStatus')
 def pairs(self):return self.call('/0/public/AssetPairs')
 def balance(self):return self.call('/0/private/Balance',private=True)
 def ledgers(self):return self.call('/0/private/Ledgers',{'type':'all'},private=True)
