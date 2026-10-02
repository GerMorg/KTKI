from __future__ import annotations
from decimal import Decimal
import base64,hashlib,hmac,json,time,urllib.parse,urllib.request,urllib.error

class KrakenAPIError(RuntimeError):
    def __init__(self,message,ambiguous=False,code="API_ERROR"):super().__init__(message);self.ambiguous=ambiguous;self.code=code

class SpotClient:
    base="https://api.kraken.com"
    def __init__(self,key="",secret="",timeout=20,user_agent="autonomous-kraken-trader/1.0"):
        self.key,self.secret,self.timeout,self.user_agent=key,secret,timeout,user_agent;self._nonce=time.time_ns()
    @staticmethod
    def sign(path,data,secret):
        encoded=urllib.parse.urlencode(data);digest=hashlib.sha256(str(data["nonce"]).encode()+encoded.encode()).digest()
        return base64.b64encode(hmac.new(base64.b64decode(secret),path.encode()+digest,hashlib.sha512).digest()).decode()
    def _request(self,path,data=None,private=False):
        data=dict(data or {});headers={"User-Agent":self.user_agent,"Accept":"application/json"}
        if private:
            if not self.key or not self.secret:raise KrakenAPIError("private credentials missing",code="AUTH_ERROR")
            self._nonce=max(self._nonce+1,time.time_ns());data["nonce"]=str(self._nonce);headers.update({"API-Key":self.key,"API-Sign":self.sign(path,data,self.secret)})
        req=urllib.request.Request(self.base+path,data=urllib.parse.urlencode(data).encode() if data else None,headers=headers,method="POST" if private else "GET")
        try:
            with urllib.request.urlopen(req,timeout=self.timeout) as resp:payload=json.load(resp)
        except urllib.error.HTTPError as exc:
            body=exc.read().decode("utf-8","replace")[:500];raise KrakenAPIError(f"HTTP {exc.code}: {body}",private and exc.code in (408,429,500,502,503,504),"API_ERROR") from exc
        except (urllib.error.URLError,TimeoutError,OSError) as exc:raise KrakenAPIError(type(exc).__name__,private, "NETWORK_AMBIGUITY" if private else "API_ERROR") from exc
        if payload.get("error"):raise KrakenAPIError("; ".join(payload["error"]),code=self._map_error(payload["error"]))
        return payload.get("result",{})
    @staticmethod
    def _map_error(errors):
        t=" ".join(map(str,errors)).lower()
        if "permission" in t or "denied" in t:return "PERMISSION_ERROR"
        if "insufficient" in t:return "INSUFFICIENT_FUNDS"
        if "invalid price" in t:return "INVALID_PRICE"
        if "invalid volume" in t:return "INVALID_VOLUME"
        return "API_ERROR"
    def status(self):return self._request("/0/public/SystemStatus")
    def asset_pairs(self,asset_class="currency"):
        d={"aclass_base":"tokenized_asset" if asset_class=="tokenized_asset" else "currency","assetVersion":1,"info":"info"}
        if asset_class=="tokenized_asset":d["execution_venue"]="international"
        return self._request("/0/public/AssetPairs",d)
    def ticker(self,pair=""):return self._request("/0/public/Ticker",({"pair":pair,"assetVersion":1} if pair else {"assetVersion":1}))
    def ohlc(self,pair,interval=60,asset_class="currency",since=None):
        d={"pair":pair,"interval":int(interval),"assetVersion":1}
        if asset_class=="tokenized_asset":d["asset_class"]="tokenized_asset"
        if since is not None:d["since"]=int(since)
        return self._request("/0/public/OHLC",d)
    def assets(self,asset_class="currency"):return self._request("/0/public/Assets",{"aclass":asset_class,"assetVersion":1})
    def get_api_key_info(self):return self._request("/0/private/GetApiKeyInfo",private=True)
    def balance(self):return self._request("/0/private/Balance",private=True)
    def balance_ex(self):return self._request("/0/private/BalanceEx",private=True)
    def trade_balance(self):return self._request("/0/private/TradeBalance",private=True)
    def open_orders(self):return self._request("/0/private/OpenOrders",{"trades":True},private=True)
    def closed_orders(self):return self._request("/0/private/ClosedOrders",{"trades":True},private=True)
    def query_orders(self,txid):return self._request("/0/private/QueryOrders",{"txid":txid,"trades":True},private=True)
    def trades_history(self):return self._request("/0/private/TradesHistory",{"trades":True},private=True)
    def open_positions(self):return self._request("/0/private/OpenPositions",{"docalcs":True,"consolidation":"market","rebase_multiplier":"rebased"},private=True)
    def get_ws_token(self):return self._request("/0/private/GetWebSocketsToken",private=True)
    def add_order(self,**data):return self._request("/0/private/AddOrder",data,private=True)

class FuturesClient:
    base="https://futures.kraken.com/derivatives/api/v3";auth_base="https://futures.kraken.com/api/auth/v1"
    def __init__(self,key="",secret="",timeout=20,user_agent="autonomous-kraken-trader/1.0"):self.key,self.secret,self.timeout,self.user_agent=key,secret,timeout,user_agent
    @staticmethod
    def authent(endpoint_path,params,secret,nonce=""):
        post=urllib.parse.urlencode(list(params.items()));digest=hashlib.sha256((post+str(nonce)+endpoint_path).encode()).digest()
        return base64.b64encode(hmac.new(base64.b64decode(secret),digest,hashlib.sha512).digest()).decode()
    def _request(self,path,params=None,private=False,auth_v1=False):
        params=dict(params or {});headers={"User-Agent":self.user_agent,"Accept":"application/json"}
        if private:
            if not self.key or not self.secret:raise KrakenAPIError("private credentials missing",code="AUTH_ERROR")
            headers.update({"APIKey":self.key,"Authent":self.authent(path,params,self.secret)})
        base=self.auth_base if auth_v1 else self.base;query=urllib.parse.urlencode(params);url=base+path+("?" + query if query else "")
        req=urllib.request.Request(url,headers=headers,method="POST" if path in ("/sendorder","/cancelorder","/editorder") else "GET")
        try:
            with urllib.request.urlopen(req,timeout=self.timeout) as resp:payload=json.load(resp)
        except (urllib.error.URLError,TimeoutError,OSError) as exc:raise KrakenAPIError(type(exc).__name__,private,"NETWORK_AMBIGUITY" if private else "API_ERROR") from exc
        if str(payload.get("result","")).lower() not in ("success",""):raise KrakenAPIError(str(payload),code="API_ERROR")
        return payload
    def instruments(self):return self._request("/instruments")
    def tickers(self):return self._request("/tickers")
    def accounts(self):return self._request("/accounts",private=True)
    def open_positions(self):return self._request("/openpositions",private=True)
    def open_orders(self):return self._request("/openorders",private=True)
    def orders(self):return self._request("/orders",private=True)
    def send_order(self,**params):return self._request("/sendorder",params,private=True)
    def cancel_order(self,**params):return self._request("/cancelorder",params,private=True)
    def check_key(self):return self._request("/api-keys/v3/check",private=True,auth_v1=True)
    def candles(self,symbol,resolution="1m",count=200):
        query=urllib.parse.urlencode({"count":int(count)})
        url="https://futures.kraken.com/api/charts/v1/trade/"+urllib.parse.quote(str(symbol),safe="")+"/"+resolution+"?"+query
        req=urllib.request.Request(url,headers={"User-Agent":self.user_agent,"Accept":"application/json"},method="GET")
        try:
            with urllib.request.urlopen(req,timeout=self.timeout) as resp: payload=json.load(resp)
            return payload.get("candles",[])
        except (urllib.error.URLError,TimeoutError,OSError) as exc: raise KrakenAPIError(type(exc).__name__,False,"API_ERROR") from exc

class KrakenVenue:
    def __init__(self,key="",secret=""):self.spot=SpotClient(key,secret);self.futures=FuturesClient(key,secret)
    def system_status(self):return self.spot.status()
    def auth_info(self):return self.spot.get_api_key_info()
    def discover(self):
        out=[]
        for ac in ("currency","tokenized_asset"):
            try:payload=self.spot.asset_pairs(ac)
            except Exception:payload={}
            for source,p in (payload or {}).items():
                if not isinstance(p,dict):continue
                symbol=p.get("wsname") or p.get("altname") or source;base=p.get("base") or str(symbol).split("/")[0];quote=p.get("quote") or str(symbol).split("/")[-1]
                lev=[]
                for k in ("leverage_buy","leverage_sell"):lev += [str(x).replace(":1","") for x in (p.get(k) or [])]
                out.append({"venue":"kraken","product_type":"spot","symbol":symbol,"instrument_id":source,"altname":p.get("altname") or source,
                 "base":base,"quote":quote,"status":p.get("status","unknown"),"contract_type":"spot","margin":bool(lev),"long_short":bool(lev),
                 "leverage_levels":sorted(set(lev),key=lambda x:Decimal(x),reverse=True),"max_leverage":max([Decimal(x) for x in lev],default=Decimal("1")),
                 "order_min":p.get("ordermin") or "0","cost_min":p.get("costmin") or "0","lot_precision":int(p.get("lot_decimals") or 8),
                 "price_precision":int(p.get("pair_decimals") or 8),"tick_size":p.get("tick_size") or "0","position_limit_long":p.get("long_position_limit") or "0",
                 "position_limit_short":p.get("short_position_limit") or "0","margin_class":"","collateral":quote,"funding":"0","fee_model":"kraken-account-fees","metadata":p})
        try:
            for p in (self.futures.instruments() or {}).get("instruments",[]):
                if not isinstance(p,dict):continue
                symbol=str(p.get("symbol") or p.get("instrument") or "")
                if not symbol:continue
                lev=Decimal(str(p.get("maxLeverage") or p.get("max_leverage") or 1))
                out.append({"venue":"kraken","product_type":"derivative","symbol":symbol,"instrument_id":symbol,"altname":symbol,
                  "base":p.get("underlying") or symbol,"quote":p.get("quote") or "USD","status":str(p.get("tradeable") or p.get("status") or "unknown"),
                  "contract_type":p.get("contractType","futures_vanilla"),"margin":True,"long_short":True,"leverage_levels":(str(lev),),
                  "max_leverage":lev,"order_min":p.get("minLotSize") or "0","cost_min":"0","lot_precision":int(p.get("sizePrecision") or 8),
                  "price_precision":int(p.get("pricePrecision") or 8),"tick_size":p.get("tickSize") or "0","position_limit_long":"0",
                  "position_limit_short":"0","margin_class":p.get("marginClass",""),"collateral":p.get("quote") or "USD",
                  "funding":p.get("fundingRate") or "0","fee_model":"kraken-derivatives","metadata":p})
        except Exception:pass
        return out
