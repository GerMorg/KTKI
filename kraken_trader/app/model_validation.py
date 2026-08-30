"""Walk-forward model/strategy validation with realistic execution costs."""
import json, math
from db import now

class ModelValidationEngine:
    """Offline validation engine; it never submits live orders."""
    def __init__(self, db):
        self.db=db; self.ensure()
    def ensure(self):
        with self.db.con() as c:
            c.execute("""CREATE TABLE IF NOT EXISTS model_validation_runs(
                id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT NOT NULL,
                symbol TEXT NOT NULL, interval_min INTEGER NOT NULL, folds INTEGER NOT NULL,
                embargo_points INTEGER NOT NULL, cost_rate TEXT NOT NULL, status TEXT NOT NULL,
                results_json TEXT NOT NULL)""")
    @staticmethod
    def _stats(returns):
        if not returns:return {'total_return':0.0,'annualized_return':0.0,'volatility':0.0,'sharpe':None,'sortino':None,'max_drawdown':0.0}
        equity=peak=1.0;dd=0.0
        for r in returns:
            equity*=max(1e-12,1+r);peak=max(peak,equity);dd=min(dd,equity/peak-1)
        mean=sum(returns)/len(returns);vol=(sum((r-mean)**2 for r in returns)/max(1,len(returns)-1))**.5
        down=(sum(min(0,r)**2 for r in returns)/max(1,len(returns)-1))**.5
        annual=24*365; periods=len(returns)
        return {'total_return':equity-1,'annualized_return':equity**(annual/periods)-1 if equity>0 else -1,
                'volatility':vol*math.sqrt(annual),'sharpe':mean/vol*math.sqrt(annual) if vol else None,
                'sortino':mean/down*math.sqrt(annual) if down else None,'max_drawdown':dd}
    @staticmethod
    def _strategy(prices,cost):
        cash=1.;units=0.;curve=[1.];history=[];trades=0
        for price in prices:
            history.append(price)
            if len(history)>=30:
                want=sum(history[-10:])/10 > sum(history[-30:])/30
                if want and units==0:units=cash*(1-cost)/price;cash=0.;trades+=1
                elif not want and units>0:cash=units*price*(1-cost);units=0.;trades+=1
            curve.append(cash+units*price)
        if units:curve[-1]=cash+units*prices[-1]*(1-cost)
        return curve,trades
    def run(self,symbol,interval_min=60,cost_rate=.006,folds=4,embargo_points=1):
        rows=self.db.rows('SELECT open_time,close FROM ohlc_cache WHERE symbol=? AND interval_min=? ORDER BY open_time',(symbol,int(interval_min)))
        prices=[float(x['close']) for x in rows if float(x['close'])>0];folds=max(2,int(folds));embargo_points=max(0,int(embargo_points))
        required=max(120,folds*30+embargo_points)
        if len(prices)<required:return {'status':'INSUFFICIENT','points':len(prices),'required':required}
        n=len(prices);size=max(20,n//(folds+1));results=[]
        for i in range(folds):
            start=n-(folds-i)*size;end=min(n,start+size);train_end=max(30,start-embargo_points);test=prices[start:end]
            if len(test)<10:continue
            curve,trades=self._strategy(prices[max(0,train_end-30):end],cost_rate);warm=max(0,start-max(0,train_end-30));test_curve=curve[warm:]
            if len(test_curve)<2:continue
            strat=self._stats([test_curve[j]/test_curve[j-1]-1 for j in range(1,len(test_curve))]);hold=self._stats([test[j]/test[j-1]-1 for j in range(1,len(test))])
            results.append({'fold':i+1,'train_points':train_end,'test_points':len(test),'embargo_points':embargo_points,'strategy':strat,'buy_hold':hold,'trades':trades,'excess_return':strat['total_return']-hold['total_return']})
        if len(results)<2:return {'status':'INSUFFICIENT_FOLDS','folds':len(results)}
        sr=[x['strategy']['total_return'] for x in results];bh=[x['buy_hold']['total_return'] for x in results];ex=[x['excess_return'] for x in results]
        positive=sum(x>0 for x in sr);required_positive=math.ceil(len(results)*.75);mean_sr=sum(sr)/len(sr);mean_ex=sum(ex)/len(ex)
        gates=[{'name':'POSITIVE_AFTER_COSTS','passed':mean_sr>0,'actual':mean_sr,'required':0},{'name':'OUTPERFORMS_BUY_HOLD','passed':mean_ex>0,'actual':mean_ex,'required':0},{'name':'CONSISTENT_FOLDS','passed':positive>=required_positive,'actual':positive,'required':required_positive}]
        status='VALID' if all(x['passed'] for x in gates) else 'NOT_ROBUST';result={'status':status,'symbol':symbol,'interval_min':int(interval_min),'method':'chronological_walk_forward_with_embargo_v62','cost_rate':cost_rate,'folds':results,'aggregate':{'strategy_mean_return':mean_sr,'buy_hold_mean_return':sum(bh)/len(bh),'excess_vs_buy_hold_mean':mean_ex,'positive_strategy_folds':positive},'gates':gates}
        with self.db.con() as c:c.execute('INSERT INTO model_validation_runs(created_at,symbol,interval_min,folds,embargo_points,cost_rate,status,results_json) VALUES(?,?,?,?,?,?,?,?)',(now(),symbol,int(interval_min),len(results),embargo_points,str(cost_rate),status,json.dumps(result,sort_keys=True)))
        self.db.audit('MODEL_VALIDATION_RUN',json.dumps({'symbol':symbol,'status':status,'gates':gates}));return result
    def recent(self):return self.db.rows('SELECT * FROM model_validation_runs ORDER BY id DESC LIMIT 50')
