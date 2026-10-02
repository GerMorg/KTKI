from __future__ import annotations
import json,urllib.request
SCHEMA={"type":"object","properties":{"asset":{"type":"string"},"event":{"type":"string"},"direction":{"type":"string"},"impact":{"type":"number"},"confidence":{"type":"number"},"time_horizon":{"type":"string"},"novelty":{"type":"number"},"market_confirmation":{"type":"number"},"risk_flags":{"type":"array","items":{"type":"string"}}},"required":["asset","event","direction","impact","confidence","time_horizon","novelty","market_confirmation","risk_flags"]}

class GeminiAnalyzer:
    def __init__(self,db,api_key="",model="gemini-3.8-flash",enabled=True,timeout=30):self.db,self.api_key,self.model,self.enabled,self.timeout=db,api_key,model,enabled,int(timeout)
    def analyze(self,news):
        if not self.enabled:return {"status":"DISABLED"}
        if not self.api_key:return {"status":"BLOCKED","reason":"BLOCKED_GEMINI"}
        prompt=("Return only JSON matching the provided schema. This is research/event interpretation only; "
                "never place or recommend an order, never alter limits. Title: "+str(news.get("title",""))+
                " Summary: "+str(news.get("summary",""))+" Asset hint: "+str(news.get("asset","")))
        body={"contents":[{"parts":[{"text":prompt}]}],"generationConfig":{"responseMimeType":"application/json","responseSchema":SCHEMA}}
        req=urllib.request.Request(f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent",
                                   data=json.dumps(body).encode(),headers={"Content-Type":"application/json","x-goog-api-key":self.api_key},method="POST")
        try:
            with urllib.request.urlopen(req,timeout=self.timeout) as r:payload=json.load(r)
            txt=((payload.get("candidates") or [{}])[0].get("content") or {}).get("parts",[{}])[0].get("text","");value=json.loads(txt);self.validate(value)
            self.db.event("info","GEMINI_RESPONSE","GEMINI_ANALYSIS",message="structured response received",details={"model":self.model})
            return value
        except Exception as exc:
            self.db.error("GEMINI_MISINTERPRETATION","GEMINI_ANALYSIS",message=type(exc).__name__)
            return {"status":"DEGRADED","reason":type(exc).__name__}
    @staticmethod
    def validate(v):
        for k in SCHEMA["required"]:
            if k not in v:raise ValueError("schema missing")
        if v["direction"] not in ("bullish","bearish","neutral"):raise ValueError("invalid direction")
        for k in ("impact","confidence","novelty","market_confirmation"):
            if not 0<=float(v[k])<=1:raise ValueError(f"{k} out of range")
