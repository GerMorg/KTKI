import os,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'..','app'))
from db import DB
from text_encoding import repair_text,repair_database,corruption_score
class Tests(unittest.TestCase):
 def test_known_double_encoded_examples(self):
  bad=lambda *codes:''.join(chr(x) for x in codes)
  pairs=[(bad(0xc3,0x153)+'bersicht','Übersicht'),('Geb'+bad(0xc3,0xbc)+'hr','Gebühr'),(bad(0xe2,0x201a,0xac),'€'),(bad(0xe2,0x20ac,0x201d),'—'),('vollst'+bad(0xc3,0xa4)+'ndig','vollständig')]
  for broken,expected in pairs:self.assertEqual(repair_text(broken),expected)
 def test_existing_database_text_is_repaired_once(self):
  db=DB(tempfile.mktemp());db.init()
  with db.con() as c:broken='Geb'+chr(0xc3)+chr(0xbc)+'hr und '+chr(0xc3)+chr(0x153)+'bersicht';c.execute("INSERT INTO audit(created_at,event,level,details) VALUES('x','TEST','info',?)",(broken,))
  first=repair_database(db);self.assertEqual(db.rows("SELECT details FROM audit WHERE event='TEST'")[0]['details'],'Gebühr und Übersicht');self.assertGreater(first['changed'],0);self.assertEqual(repair_database(db)['status'],'ALREADY_DONE')
 def test_repository_has_no_corruption_markers(self):
  root=Path(__file__).parents[2]
  for path in root.rglob('*'):
   if path.is_file() and path.suffix in ('','.py','.md','.yaml','.yml','.txt'):
    text=path.read_text('utf-8');self.assertEqual(corruption_score(text),0,str(path))
