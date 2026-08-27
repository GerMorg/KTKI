import os,sys,tempfile,unittest
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'..','app'))
from db import DB,now
from market_history import MarketHistory
from backtest import BacktestEngine
class T(unittest.TestCase):
 def setUp(self):self.db=DB(tempfile.mktemp());self.db.init();self.h=MarketHistory(self.db)
 def test_diagnostics_separate_ticker_and_ohlc(self):
  self.h.ticker('EUR/USD','forex',{'b':['1.1'],'a':['1.2'],'c':['1.15'],'v':['2','3']});self.h.ohlc('EUR/USD','forex',[[i,'1','1','1','1','1','1',1] for i in range(40)]);r=self.h.diagnostics()[0];self.assertEqual(r['ticker_status'],'VALID');self.assertEqual(r['ohlc_points'],39)
 def test_csv_history_and_walk_forward_benchmarks(self):
  text='\n'.join(f'{i},{100+i},{101+i},{99+i},{100+i},100,{10+i},2' for i in range(100));self.assertEqual(self.h.import_csv('EUR/USD',60,text)['rows_saved'],100)
  with self.db.con() as c:c.execute("CREATE TABLE market_universe(symbol TEXT,asset_class TEXT)");c.execute("INSERT INTO market_universe VALUES('EUR/USD','forex')")
  r=BacktestEngine(self.db).run('EUR/USD',60,.001);self.assertEqual(r['status'],'VALID');self.assertIn('buy_hold_return',r);self.assertIn('trend_max_drawdown',r)
 def test_kraken_last_candle_not_persisted_as_committed_status(self):
  self.h.ohlc('EUR/USD','forex',[[1,'1','1','1','1','1','1',1],[2,'1','1','1','1','1','1',1]]);self.assertEqual(self.h.diagnostics()[0]['last_committed_open_time'],1)
if __name__=='__main__':unittest.main()
