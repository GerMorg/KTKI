import base64, hashlib, hmac, json, time, urllib.parse, urllib.request

class KrakenError(RuntimeError): pass

class KrakenClient:
    base = "https://api.kraken.com"
    def __init__(self, key="", secret="", timeout=15):
        self.key, self.secret, self.timeout = key, secret, timeout
    @staticmethod
    def sign(path, data, secret):
        encoded = urllib.parse.urlencode(data)
        message = str(data["nonce"]).encode() + encoded.encode()
        digest = hashlib.sha256(message).digest()
        mac = hmac.new(base64.b64decode(secret), path.encode()+digest, hashlib.sha512)
        return base64.b64encode(mac.digest()).decode()
    def _request(self, path, data=None, private=False):
        data = dict(data or {})
        headers={"User-Agent":"HA-Kraken-Trader/0.1"}
        if private:
            if not self.key or not self.secret: raise KrakenError("Read-only API-Zugang ist nicht konfiguriert")
            data["nonce"] = str(time.time_ns())
            headers.update({"API-Key":self.key,"API-Sign":self.sign(path,data,self.secret)})
        body=urllib.parse.urlencode(data).encode() if data else None
        req=urllib.request.Request(self.base+path, data=body, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r: payload=json.load(r)
        except Exception as e: raise KrakenError(f"Kraken nicht erreichbar: {type(e).__name__}") from e
        if payload.get("error"): raise KrakenError("; ".join(payload["error"]))
        return payload.get("result", {})
    def system_status(self): return self._request("/0/public/SystemStatus")
    def asset_pairs(self): return self._request("/0/public/AssetPairs")
    def balance(self): return self._request("/0/private/Balance", private=True)
    def ledgers(self): return self._request("/0/private/Ledgers", {"type":"all"}, private=True)
