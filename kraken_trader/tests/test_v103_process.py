import re
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"app"))

from db import DB
from paper_engine import PaperEngine
from v103_paper_engine import PaperEngineV103
from real_trade import RealTradeEngine
import v103_main


class DummyClient:
    def __init__(self):
        self.orders=[]

    def add_order(self, **kwargs):
        self.orders.append(kwargs)
        return {"txid":["V103-TEST"],"descr":kwargs}


class V103ProcessTests(unittest.TestCase):
    def db(self):
        f=tempfile.NamedTemporaryFile(suffix=".db",delete=False)
        f.close()
        db=DB(f.name)
        db.init()
        return f,db

    @staticmethod
    def market_schema(db):
        with db.con() as c:
            c.execute("""CREATE TABLE IF NOT EXISTS market_universe(
                symbol TEXT PRIMARY KEY,asset_class TEXT,category TEXT,base_asset TEXT,
                quote_asset TEXT,source_key TEXT,ordermin TEXT,costmin TEXT,
                canonical_id TEXT
            )""")
            c.execute("""INSERT OR REPLACE INTO market_universe
                VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                ("BTC/EUR","currency","crypto_spot","BTC","EUR","XXBTZEUR","0","0","btc",8,5))

    def live_price(self,db):
        db.upsert_live_price({
            "symbol":"BTC/EUR","last":"1000","bid":"999","ask":"1001",
            "change_pct":"0","received_at":datetime.now(timezone.utc).isoformat()
        })

    def test_paper_fill_updates_simulated_depot(self):
        f,db=self.db()
        try:
            self.market_schema(db)
            self.live_price(db)
            engine=PaperEngineV103(db,1000,40,10,10,25)
            tid=engine.execute("BTC/EUR","BUY",100,"v103 test",{"leverage":1})
            account=engine.account()
            positions=engine.positions()
            trades=db.rows("SELECT * FROM paper_trades WHERE id=?",(tid,))
            self.assertEqual(len(trades),1)
            self.assertTrue(positions)
            self.assertLess(Decimal(account["cash_eur"]),Decimal("1000"))
            self.assertGreater(Decimal(positions[0]["quantity"]),Decimal("0"))
        finally:
            Path(f.name).unlink(missing_ok=True)

    def test_committed_paper_fill_survives_snapshot_failure(self):
        f,db=self.db()
        try:
            self.market_schema(db)
            self.live_price(db)
            engine=PaperEngine(db,1000,40,10,10,25)
            def boom():
                raise RuntimeError("snapshot test failure")
            engine.snapshot=boom
            tid=engine.execute("BTC/EUR","BUY",100,"v103 snapshot test",{"leverage":1})
            self.assertGreater(int(tid),0)
            self.assertEqual(int(db.rows("SELECT COUNT(*) n FROM paper_trades")[0]["n"]),1)
        finally:
            Path(f.name).unlink(missing_ok=True)

    def test_real_automation_path_can_submit_to_kraken_client(self):
        f,db=self.db()
        client=DummyClient()
        try:
            self.market_schema(db)
            self.live_price(db)
            with db.con() as c:
                c.execute("""CREATE TABLE IF NOT EXISTS private_balances(
                    asset TEXT PRIMARY KEY,balance TEXT,wallets_json TEXT,
                    sequence INTEGER,received_at TEXT
                )""")
                c.execute("INSERT OR REPLACE INTO private_balances VALUES(?,?,?,?,?)",
                          ("ZEUR","1000","[]",None,"2026-10-01T18:00:00+00:00"))
            for key,value in {
                "real_trading_enabled":"true",
                "real_kill_switch":"false",
                "automation_master_enabled":"true",
                "automation_real_enabled":"true",
                "automation_real_execute_enabled":"true",
                "real_allowed_symbols":"BTC/EUR",
                "real_max_orders_per_day":"5",
                "real_allow_market_orders":"false",
            }.items():
                db.set(key,value)
            engine=RealTradeEngine(db,client)
            result=engine.submit(
                "BTC/EUR","buy","0.05","limit","1001",
                client_order_id="v103-real-test",
                validate_only=False,
                automation_context=True,
            )
            self.assertEqual(result["status"],"SUBMITTED")
            self.assertEqual(len(client.orders),1)
            self.assertEqual(client.orders[0]["pair"],"BTCEUR")
            self.assertEqual(client.orders[0]["validate"],"false")
        finally:
            Path(f.name).unlink(missing_ok=True)

    def test_manual_live_order_still_requires_explicit_arm(self):
        f,db=self.db()
        client=DummyClient()
        try:
            self.market_schema(db)
            self.live_price(db)
            for key,value in {
                "real_trading_enabled":"true",
                "real_kill_switch":"false",
                "real_allowed_symbols":"BTC/EUR",
                "real_max_orders_per_day":"5",
            }.items():
                db.set(key,value)
            engine=RealTradeEngine(db,client)
            with self.assertRaises(PermissionError):
                engine.submit("BTC/EUR","buy","0.05","limit","1001",
                              client_order_id="v103-manual-test",
                              validate_only=False)
            self.assertEqual(client.orders,[])
        finally:
            Path(f.name).unlink(missing_ok=True)

    def test_current_gui_pages_and_rendered_local_actions_have_routes(self):
        client=v103_main.app.test_client()
        pages=[
            "/","/markt","/analyse","/portfolio","/handel","/lernen",
            "/real-trading","/system","/steuerinfo-at",
            "/health","/api/market","/api/process","/v103-health"
        ]
        for page in pages:
            response=client.get(page)
            self.assertEqual(response.status_code,200,page)
            html=response.get_data(as_text=True)
            self.assertNotIn("404: not found",html.lower(),page)
            for href in re.findall(r'''<a[^>]+href=["']([^"']+)["']''',html,re.I):
                if href.startswith(("http://","https://","mailto:","javascript:","#")):
                    continue
                path=urlsplit(href).path
                if not path or path.startswith("/static/"):
                    continue
                self.assertTrue(
                    any("GET" in rule.methods for rule in v103_main.app.url_map.iter_rules()
                        if rule.rule==path),
                    f"Missing GET route {path} rendered by {page}"
                )
            for form in re.findall(r'''<form([^>]*)>''',html,re.I):
                method_match=re.search(r'''method=["']([^"']+)["']''',form,re.I)
                method=(method_match.group(1).upper() if method_match else "GET")
                action_match=re.search(r'''action=["']([^"']+)["']''',form,re.I)
                path=urlsplit(action_match.group(1)).path if action_match else page
                if path.startswith("/static/"):
                    continue
                self.assertTrue(
                    any(method in rule.methods for rule in v103_main.app.url_map.iter_rules()
                        if rule.rule==path),
                    f"Missing {method} route {path} used by {page}"
                )

    def test_legacy_tax_urls_no_longer_return_404(self):
        client=v103_main.app.test_client()
        for path in ("/tax-info-v68","/tax-info-v68.zip","/tax-info-v68.csv","/tax-info"):
            response=client.get(path)
            self.assertEqual(response.status_code,302,path)
            self.assertIn("/steuerinfo-at",response.headers.get("Location",""))

    def test_austrian_tax_help_is_present_and_uses_current_exports(self):
        response=v103_main.app.test_client().get("/steuerinfo-at")
        html=response.get_data(as_text=True)
        self.assertEqual(response.status_code,200)
        self.assertIn("Einkommensteuer",html)
        self.assertIn("BMF",html)
        self.assertIn("Keine Steuer- oder Rechtsberatung",html)
        source=(ROOT/"app"/"v103_main.py").read_text(encoding="utf-8")
        self.assertIn("/tax-info.zip",source)
        self.assertIn("/tax-info.csv",source)

    def test_v103_runtime_contract(self):
        self.assertEqual(v103_main.VERSION,"0.1.0-dev.103")
        self.assertEqual(v103_main.app.view_functions["health"]()["version"],"0.1.0-dev.103")
        self.assertEqual(v103_main._health()["runtime"],"v103_main")


if __name__=="__main__":
    unittest.main()
