from __future__ import annotations
from dataclasses import dataclass
import hashlib,re,time,urllib.request,xml.etree.ElementTree as ET

SOURCES=(("ECB","https://www.ecb.europa.eu/rss/press.html",1.0),("FED","https://www.federalreserve.gov/feeds/press_all.xml",1.0),("Kraken Blog","https://blog.kraken.com/feed",0.85))
BULL={"approval","approved","inflow","adoption","growth","partnership","launch","surge","beat","easing","rate cut","positive"}
BEAR={"hack","exploit","ban","sanction","outflow","collapse","recession","rate hike","negative","lawsuit","downgrade","liquidation"}
ENTITY_TERMS=("bitcoin","btc","ethereum","eth","solana","sol","xrp","ripple","apple","aapl","tesla","tsla","nvidia","nvda","euro","eur","dollar","usd","fed","ecb")

@dataclass(frozen=True)
class NewsItem:
    news_id:str;source:str;title:str;url:str;observed_at:float;published_at:float|None
    entity:str="";event:str="";direction:str="neutral";impact:float=0.0;novelty:float=1.0;credibility:float=0.5;horizon:str="24h"

def clean(s): return re.sub(r"\s+"," ",re.sub(r"<[^>]+>"," ",str(s or ""))).strip()
def classify(title,summary=""):
    text=(clean(title)+" "+clean(summary)).lower()
    bull=sum(x in text for x in BULL);bear=sum(x in text for x in BEAR)
    direction="bullish" if bull>bear else ("bearish" if bear>bull else "neutral")
    impact=min(1.0,abs(bull-bear)*0.2)
    entity=next((x for x in ENTITY_TERMS if re.search(r"\b"+re.escape(x)+r"\b",text)),"")
    event=next((x for x in ("earnings","rate decision","regulation","hack","acquisition","launch","sanction") if x in text),"market_event")
    return entity,event,direction,impact

class NewsEngine:
    def __init__(self,db,timeout=12,enabled=True): self.db,self.timeout,self.enabled=db,int(timeout),enabled
    def collect(self):
        if not self.enabled:return {"status":"DISABLED","saved":0,"errors":[]}
        saved=0;errors=[]
        for source,url,cred in SOURCES:
            try:
                req=urllib.request.Request(url,headers={"User-Agent":"autonomous-kraken-trader/1.0","Accept":"application/rss+xml,application/xml,text/xml"})
                with urllib.request.urlopen(req,timeout=self.timeout) as r:data=r.read()
                root=ET.fromstring(data);nodes=root.findall(".//item") or root.findall(".//{http://www.w3.org/2005/Atom}entry")
                for n in nodes[:100]:
                    def pick(names):
                        for name in names:
                            x=n.find(name)
                            if x is not None:
                                v=x.text or x.get("href","")
                                if v:return clean(v)
                        return ""
                    title=pick(("title","{http://www.w3.org/2005/Atom}title"));urlv=pick(("link","{http://www.w3.org/2005/Atom}link"));summary=pick(("description","summary","{http://www.w3.org/2005/Atom}summary"))
                    if not title:continue
                    entity,event,direction,impact=classify(title,summary);nid=hashlib.sha256((source+"|"+title+"|"+urlv).encode()).hexdigest()
                    with self.db.tx() as c:
                        before=c.total_changes
                        c.execute("INSERT OR IGNORE INTO news_events(id,source,title,url,published_at,observed_at,entity_json,direction,impact,novelty,credibility,horizon,market_confirmation,outcome_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                                  (nid,source,title,urlv,None,time.time(),__import__("json").dumps({"entity":entity,"event":event}),direction,str(impact),"1.0",str(cred),"24h","0.0","{}"))
                        saved+=c.total_changes-before
            except Exception as exc:errors.append({"source":source,"error":type(exc).__name__})
        self.db.event("warning" if errors else "info","NEWS_FETCH","NEWS_ANALYSIS",message=f"saved={saved}",details={"errors":errors})
        return {"status":"READY" if not errors else ("DEGRADED" if saved else "ERROR"),"saved":saved,"errors":errors}
    def recent(self,limit=200): return self.db.rows("SELECT * FROM news_events ORDER BY observed_at DESC LIMIT ?",(int(limit),))
    def effect_for_symbol(self,symbol):
        base=str(symbol).split("/")[0].upper();rows=self.recent(500);effect=0.0
        for r in rows:
            raw=r.get("entity_json") or "{}"; text=str(r.get("title","")).lower()+" "+str(r.get("direction","neutral"))
            direct=base.lower() in raw.lower() or base.lower() in text
            if direct:
                v=float(r.get("impact") or 0);effect += v if r.get("direction")=="bullish" else (-v if r.get("direction")=="bearish" else 0)
        return max(-1.0,min(1.0,effect))
