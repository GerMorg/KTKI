import json,os,sys,tempfile,unittest
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'..','app'))
from db import DB
from ws_private import PrivateStream
class FakeClient:pass
class PrivateWebSocketTests(unittest.TestCase):
 def setUp(self):self.db=DB(os.path.join(tempfile.mkdtemp(),'x.db'));self.db.init(100);self.stream=PrivateStream(self.db,FakeClient(),False)
 def test_balance_snapshot_and_update(self):
  self.stream.handle(json.dumps({'channel':'balances','type':'snapshot','sequence':1,'data':[{'asset':'EUR','balance':10,'wallets':[]}]}))
  self.stream.handle(json.dumps({'channel':'balances','type':'update','sequence':2,'data':[{'asset':'EUR','balance':12,'wallets':[]}]}))
  row=self.db.rows('SELECT * FROM private_balances')[0];self.assertEqual(row['balance'],'12');self.assertEqual(row['sequence'],2)
 def test_execution_idempotency(self):
  msg={'channel':'executions','type':'update','sequence':1,'data':[{'exec_id':'E1','order_id':'O1','exec_type':'trade','symbol':'BTC/EUR'}]}
  self.stream.handle(json.dumps(msg));self.assertEqual(len(self.db.rows('SELECT * FROM private_execution_events')),1)
 def test_sequence_gap_is_persisted_and_degraded(self):
  self.stream.handle(json.dumps({'channel':'balances','type':'snapshot','sequence':1,'data':[]}))
  with self.assertRaises(ValueError):self.stream.handle(json.dumps({'channel':'balances','type':'update','sequence':3,'data':[]}))
  self.assertEqual(self.db.private_stream_status()['state'],'DEGRADED');self.assertEqual(len(self.db.rows('SELECT * FROM private_sequence_gaps')),1)
 def test_token_not_persisted(self):
  columns=' '.join(x['name'] for x in self.db.rows('PRAGMA table_info(private_stream_state)'));self.assertNotIn('token',columns.lower())
if __name__=='__main__':unittest.main()


