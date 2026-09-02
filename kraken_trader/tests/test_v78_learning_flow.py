import os
import tempfile
import unittest
from pathlib import Path

APP=Path(__file__).resolve().parents[1]/'app'
import sys
sys.path.insert(0,str(APP))
from db import DB
from controlled_learning import ControlledLearning

class V78LearningTests(unittest.TestCase):
 def make_db(self):
  tmp=tempfile.NamedTemporaryFile(suffix='.db',delete=False);tmp.close()
  db=DB(tmp.name);db.init(1000)
  return db,tmp.name
 def test_families_are_explicit_and_separate(self):
  db,path=self.make_db()
  try:
   learning=ControlledLearning(db)
   self.assertEqual({x['family'] for x in learning.family_overview()},{'forex','xstocks','crypto_spot'})
  finally:
   try:os.unlink(path)
   except OSError:pass
 def test_insufficient_data_does_not_change_active_version(self):
  db,path=self.make_db()
  try:
   learning=ControlledLearning(db)
   active={x['family']:x['active_version'] for x in learning.family_overview()}
   result=learning.propose('forex')
   self.assertIn(str(result.get('status','')).upper(),{'INSUFFICIENT_DATA','NO_CANDIDATE','COMPLETED'})
   after={x['family']:x['active_version'] for x in learning.family_overview()}
   self.assertEqual(active,after)
  finally:
   try:os.unlink(path)
   except OSError:pass

if __name__=='__main__':unittest.main()
