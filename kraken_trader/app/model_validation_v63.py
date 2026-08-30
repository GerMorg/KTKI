"""v63 validation: chronological walk-forward, benchmarks and cost-aware metrics."""
import math, statistics

class ValidationResult:
    def __init__(self, status, folds, aggregate, gates, diagnostics=None):
        self.status=status; self.folds=folds; self.aggregate=aggregate; self.gates=gates; self.diagnostics=diagnostics or []
    def as_dict(self): return {'status':self.status,'folds':self.folds,'aggregate':self.aggregate,'gates':self.gates,'diagnostics':self.diagnostics}

class StrategyValidationEngine:
    """Pure offline evaluator. It never calls an exchange order endpoint."""
    def __init__(self, cost_model=None): self.cost_model=cost_model or {}
    @staticmethod
    def _returns(prices):
        return [prices[i]/prices[i-1]-1 for i in range(1,len(prices)) if prices[i-1]>0 and prices[i]>0]
    @staticmethod
    def _stats(returns):
        if not returns:return {'total_return':0.0,'volatility':0.0,'sharpe':None,'sortino':None,'max_drawdown':0.0,'observations':0}
        equity=peak=1.;worst=0.
        for r in returns:
            equity*=max(1e-12,1+r);peak=max(peak,equity);worst=min(worst,equity/peak-1)
        mean=sum(returns)/len(returns);vol=statistics.stdev(returns) if len(returns)>1 else 0.;down=statistics.stdev([min(0,r) for r in returns]) if len(returns)>1 else 0.
        annual=365*24
        return {'total_return':equity-1,'volatility':vol*math.sqrt(annual),'sharpe':mean/vol*math.sqrt(annual) if vol else None,'sortino':mean/down*math.sqrt(annual) if down else None,'max_drawdown':worst,'observations':len(returns)}
    def _cost(self, trade, context):
        if callable(self.cost_model): return max(0.,float(self.cost_model(trade,context)))
        base=float(context.get('roundtrip_cost_rate',self.cost_model.get('roundtrip_cost_rate',0.0)))
        return max(0.,base)
    def _simulate(self, prices, signals, context):
        cash=1.;units=0.;equity=[];trade_count=0;cost_paid=0.
        for i,price in enumerate(prices):
            signal=signals[i] if i<len(signals) else 'HOLD'; signal=str(signal).upper()
            if signal=='BUY' and units==0:
                cost=self._cost('BUY',dict(context,price=price));units=cash*(1-cost)/price;cash=0.;trade_count+=1;cost_paid+=cost
            elif signal in ('SELL','AVOID') and units>0:
                cost=self._cost('SELL',dict(context,price=price));cash=units*price*(1-cost);units=0.;trade_count+=1;cost_paid+=cost
            equity.append(cash+units*price)
        if units:
            cost=self._cost('SELL',dict(context,price=prices[-1]));equity[-1]=cash+units*prices[-1]*(1-cost);cost_paid+=cost
        return equity,trade_count,cost_paid
    @staticmethod
    def _folds(n,folds,embargo):
        folds=max(2,int(folds));test=max(10,n//(folds+1));out=[]
        for i in range(folds):
            start=n-(folds-i)*test;end=min(n,start+test);train_end=max(0,start-int(embargo))
            if train_end<30 or end-start<10:continue
            out.append((train_end,start,end))
        return out
    def validate(self,prices,signals,folds=5,embargo=5,context=None):
        context=dict(context or {});prices=[float(x) for x in prices if float(x)>0]
        if len(prices)<120:return ValidationResult('INSUFFICIENT',[],{},[],['Mindestens 120 valide Preise erforderlich']).as_dict()
        if len(signals)!=len(prices):return ValidationResult('INVALID_INPUT',[],{},[],['Signal- und Preisreihen müssen gleich lang sein']).as_dict()
        fold_results=[]
        for no,(train_end,start,end) in enumerate(self._folds(len(prices),folds,embargo),1):
            test_prices=prices[start:end];test_signals=signals[start:end];equity,trades,costs=self._simulate(test_prices,test_signals,context);strategy=self._stats(self._returns(equity));hold=self._stats(self._returns(test_prices));cash=self._stats([0.]*(len(test_prices)-1));
            fold_results.append({'fold':no,'train_end':train_end,'embargo_points':start-train_end,'test_points':len(test_prices),'strategy':strategy,'buy_hold':hold,'cash':cash,'trades':trades,'cost_paid_fraction':costs,'excess_vs_buy_hold':strategy['total_return']-hold['total_return'],'excess_vs_cash':strategy['total_return']})
        if len(fold_results)<2:return ValidationResult('INSUFFICIENT_FOLDS',fold_results,{},[],['Mindestens zwei unabhängige Testfenster erforderlich']).as_dict()
        sr=[x['strategy']['total_return'] for x in fold_results];ex=[x['excess_vs_buy_hold'] for x in fold_results];sh=[x['strategy']['sharpe'] for x in fold_results if x['strategy']['sharpe'] is not None];positive=sum(x>0 for x in sr);outperform=sum(x>0 for x in ex)
        gates=[{'name':'POSITIVE_NET_RETURN','passed':sum(sr)/len(sr)>0,'actual':sum(sr)/len(sr),'required':0.0},{'name':'OUTPERFORM_BUY_HOLD','passed':sum(ex)/len(ex)>0,'actual':sum(ex)/len(ex),'required':0.0},{'name':'OUTPERFORM_CASH','passed':sum(x['excess_vs_cash'] for x in fold_results)/len(fold_results)>0,'actual':sum(x['excess_vs_cash'] for x in fold_results)/len(fold_results),'required':0.0},{'name':'FOLD_CONSISTENCY','passed':positive>=math.ceil(.75*len(fold_results)),'actual':positive,'required':math.ceil(.75*len(fold_results))},{'name':'BENCHMARK_CONSISTENCY','passed':outperform>=math.ceil(.60*len(fold_results)),'actual':outperform,'required':math.ceil(.60*len(fold_results))}]
        aggregate={'mean_net_return':sum(sr)/len(sr),'mean_excess_vs_buy_hold':sum(ex)/len(ex),'median_net_return':statistics.median(sr),'positive_folds':positive,'outperform_buy_hold_folds':outperform,'mean_sharpe':sum(sh)/len(sh) if sh else None,'fold_count':len(fold_results)}
        return ValidationResult('VALID' if all(g['passed'] for g in gates) else 'NOT_ROBUST',fold_results,aggregate,gates).as_dict()
