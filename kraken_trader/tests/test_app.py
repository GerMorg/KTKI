import os,sys,tempfile,unittest
os.environ['APP_DISABLE_PAPER_SCHEDULER']='1';os.environ['APP_DATA_DIR']=tempfile.mkdtemp();sys.path.insert(0,os.path.join(os.path.dirname(__file__),'..','app'));import main
class T(unittest.TestCase):
 def setUp(self):self.c=main.app.test_client()
 def test_tabs(self):
  for p in ['/','/api','/portfolio','/paper','/paper/decisions','/audit','/settings','/exports']:self.assertEqual(self.c.get(p).status_code,200,p)
 def test_ingress_links(self):
  d=self.c.get('/',headers={'X-Ingress-Path':'/api/hassio_ingress/token'}).data;self.assertIn(b'/api/hassio_ingress/token/api',d);self.assertNotIn(b'href="/"',d)
 def test_disabled(self):self.assertFalse(self.c.get('/health').json['real_trading'])
if __name__=='__main__':unittest.main()
