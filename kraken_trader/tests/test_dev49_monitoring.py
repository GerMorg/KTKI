import json, os, sys, tempfile, unittest
from pathlib import Path
ROOT=Path(__file__).parents[1]
os.environ["APP_DATA_DIR"]=tempfile.mkdtemp()
os.environ["APP_DISABLE_PAPER_SCHEDULER"]="1"
os.environ["APP_DISABLE_RESEARCH_SCHEDULER"]="1"
os.environ["APP_DISABLE_WEBSOCKETS"]="1"
sys.path.insert(0,str(ROOT/"app"))
import main
class Dev49MonitoringTests(unittest.TestCase):
 def setUp(self):
  self.client=main.app.test_client()
  with main.db.con() as c:c.execute("DELETE FROM audit")
 def test_dashboard_filters(self):
  main.db.audit("TEST_ERROR","sichtbar","error");main.db.audit("TEST_INFO","ausblenden","info")
  body=self.client.get("/event-dashboard?level=error&event=TEST").get_data(as_text=True)
  self.assertIn("TEST_ERROR",body);self.assertNotIn("TEST_INFO",body)
 def test_json_export_redacts(self):
  main.db.audit("CONFIG",json.dumps({"api_key":"privat","safe":"ok"}))
  details=self.client.get("/api/audit/export").get_json()["events"][0]["details"]
  self.assertIn("[REDACTED]",details);self.assertNotIn("privat",details)
 def test_csv_and_invalid_format(self):
  main.db.audit("TEST","ok")
  self.assertIn("text/csv",self.client.get("/api/audit/export?format=csv").content_type)
  self.assertEqual(self.client.get("/api/audit/export?format=xml").status_code,400)
 def test_notification_is_audit_only(self):
  main.notifications.notify("PENDING","Freigabe erforderlich","warning",{"token":"secret"})
  row=main.db.rows("SELECT * FROM audit ORDER BY id DESC LIMIT 1")[0]
  self.assertEqual(row["event"],"USER_NOTIFICATION:PENDING");self.assertNotIn("secret",row["details"])
 def test_real_trading_disabled(self):self.assertFalse(self.client.get("/health").get_json()["real_trading"])
if __name__=="__main__":unittest.main()






