import ast
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1];APP=ROOT/'app'
class V77KrakenDataflowTests(unittest.TestCase):
 def test_portfolio_builder_values_eur_balance_and_asset(self):
  from portfolio_sync import build_rows
  balances={'EUR':'1250.50','BTC':'0.1'};assets={'EUR':{'altname':'EUR'},'BTC':{'altname':'XBT'}};pairs={'XXBTZEUR':{'base':'BTC','quote':'EUR','altname':'BTCEUR'}};tickers={'BTCEUR':{'c':['60000']}}
  rows,total,quality=build_rows(balances,set(),assets,pairs,tickers);self.assertEqual(total,'7250.50');self.assertEqual(quality,'VALID');by_name={row['display_name']:row for row in rows};self.assertEqual(by_name['EUR']['eur_value'],'1250.50');self.assertEqual(by_name['BT']['eur_value'],'6000.0')
if __name__=='__main__':unittest.main()
