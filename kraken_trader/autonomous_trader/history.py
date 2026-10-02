from __future__ import annotations
import time

class HistoryEngine:
    def __init__(self,db,venue,lookback=200):self.db,self.venue,self.lookback=db,venue,int(lookback)
    def _save_spot(self,symbol,rows):
        saved=0
        for row in rows:
            if len(row)<7:continue
            open_time=int(float(row[0]));interval=60
            if open_time+interval>int(time.time()):continue
            with self.db.tx() as c:
                c.execute("INSERT OR REPLACE INTO ohlc_history(symbol,open_time,interval_seconds,open,high,low,close,volume,trade_count,source) VALUES(?,?,?,?,?,?,?,?,?,?)",
                          (symbol,open_time,interval,str(row[1]),str(row[2]),str(row[3]),str(row[4]),str(row[6]),int(float(row[7])) if len(row)>7 else None,"kraken_spot_ohlc"))
                saved+=1
        return saved
    def backfill(self,instruments):
        saved=0;errors=0
        for i in instruments:
            try:
                if i.product_type=="spot":
                    raw=self.venue.spot.ohlc(i.altname or i.symbol,60)
                    rows=raw.get(i.altname) or raw.get(i.symbol) or raw.get(i.instrument_id) or []
                    saved+=self._save_spot(i.symbol,list(rows)[-self.lookback:])
                else:
                    candles=self.venue.futures.candles(i.instrument_id,"1m",self.lookback)
                    for row in candles:
                        open_time=int(row.get("time",0)); 
                        if open_time>10_000_000_000:open_time//=1000
                        if open_time+60>int(time.time()):continue
                        with self.db.tx() as c:
                            c.execute("INSERT OR REPLACE INTO ohlc_history(symbol,open_time,interval_seconds,open,high,low,close,volume,trade_count,source) VALUES(?,?,?,?,?,?,?,?,?,?)",
                                      (i.symbol,open_time,60,str(row.get("open","0")),str(row.get("high","0")),str(row.get("low","0")),str(row.get("close","0")),str(row.get("volume","0")),None,"kraken_futures_chart"))
                            saved+=1
            except Exception:
                errors+=1
        self.db.event("warning" if errors else "info","HISTORY_BACKFILL_COMPLETED","HISTORY_BACKFILL",message=f"saved={saved},errors={errors}")
        return {"saved":saved,"errors":errors}
    def closes(self,symbol,limit=200):
        rows=self.db.rows("SELECT open_time,open,high,low,close,volume,trade_count,interval_seconds FROM ohlc_history WHERE symbol=? ORDER BY open_time DESC LIMIT ?",(symbol,int(limit)))
        return list(reversed(rows))
