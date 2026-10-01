"""KTKI v102 public market interface.

Keeps public Kraken market data independent from private credentials and exposes
one reliable path for REST snapshots plus the public WebSocket ticker feed.
"""
import json
import os
import threading
import time
from datetime import datetime, timezone

SEED_SYMBOLS = ("BTC/EUR", "ETH/EUR", "SOL/EUR", "XRP/EUR", "BTC/USD", "ETH/USD")

class PublicMarketServiceV102:
    def __init__(self, db, client, universe, stream, max_symbols=30):
        self.db = db
        self.client = client
        self.universe = universe
        self.stream = stream
        self.max_symbols = max(6, min(60, int(max_symbols)))
        self.lock = threading.RLock()
        self.thread = None
        self.stop = threading.Event()
        self.last_bootstrap_at = None
        self.last_result = None

    @staticmethod
    def _norm_pair(value):
        text = str(value or "").upper().strip().replace("/", "").replace("-", "")
        if not text:
            return ""
        # Legacy Kraken REST keys use X<base>Z<quote>, e.g. XXBTZEUR.
        if len(text) > 4 and text.startswith(("X", "Z")):
            body = text[1:]
            pos = body.find("Z")
            if pos > 0 and pos < len(body) - 1:
                text = body[:pos] + body[pos + 1:]
        aliases = {
            "XBT": "BTC",
            "XDG": "DOGE",
            "XETH": "ETH",
            "XXBT": "BTC",
        }
        for old, new in aliases.items():
            text = text.replace(old, new)
        return text

    @classmethod
    def _payload_item(cls, payload, requested):
        wanted = cls._norm_pair(requested)
        if isinstance(payload, dict):
            direct = payload.get(requested) or payload.get(str(requested).replace("/", ""))
            if isinstance(direct, dict):
                return direct
            for key, value in payload.items():
                if cls._norm_pair(key) == wanted and isinstance(value, dict):
                    return value
            if len(payload) == 1:
                value = next(iter(payload.values()))
                if isinstance(value, dict):
                    return value
        return None

    @staticmethod
    def _first(value):
        if isinstance(value, (list, tuple)):
            return value[0] if value else None
        return value

    def _pair_aliases(self):
        mapping = {}
        for asset_class in ("currency", "tokenized_asset"):
            try:
                pairs = self.client.pairs(asset_class)
            except Exception:
                continue
            for pair_id, pair in (pairs or {}).items():
                if not isinstance(pair, dict):
                    continue
                names = [pair.get("wsname"), pair.get("altname"), pair_id]
                canonical = next((x for x in names if x and "/" in str(x)), None)
                if not canonical:
                    continue
                for name in names:
                    if name:
                        mapping[self._norm_pair(name)] = pair.get("altname") or pair_id
                mapping[self._norm_pair(canonical)] = pair.get("altname") or pair_id
        return mapping

    def _request_batch(self, symbols, asset_class):
        try:
            payload = self.client.ticker(symbols, asset_class)
            return payload, list(symbols), None
        except Exception as first_exc:
            aliases = self._pair_aliases()
            requests = [aliases.get(self._norm_pair(symbol), symbol) for symbol in symbols]
            try:
                payload = self.client.ticker(requests, asset_class)
                return payload, requests, type(first_exc).__name__
            except Exception as second_exc:
                return {}, requests, type(second_exc).__name__ + ":" + str(second_exc)[:250]

    def snapshot(self, symbols):
        symbols = list(dict.fromkeys(str(x) for x in (symbols or []) if "/" in str(x)))
        if not symbols:
            symbols = list(SEED_SYMBOLS)
        groups = {"currency": [], "tokenized_asset": []}
        for symbol in symbols:
            rows = self.db.rows(
                "SELECT asset_class FROM market_universe WHERE UPPER(symbol)=UPPER(?) ORDER BY CASE WHEN asset_class='currency' THEN 0 ELSE 1 END LIMIT 1",
                (symbol,),
            )
            asset_class = rows[0]["asset_class"] if rows else "currency"
            groups["tokenized_asset" if asset_class == "tokenized_asset" else "currency"].append(symbol)

        received = datetime.now(timezone.utc).isoformat()
        saved = []
        warnings = []
        for asset_class, batch in groups.items():
            if not batch:
                continue
            payload, requested_batch, warning = self._request_batch(batch, asset_class)
            if warning:
                warnings.append({"asset_class": asset_class, "detail": warning})
            for original, requested in zip(batch, requested_batch):
                item = self._payload_item(payload, requested) or self._payload_item(payload, original)
                if not isinstance(item, dict):
                    continue
                last = self._first(item.get("c"))
                bid = self._first(item.get("b"))
                ask = self._first(item.get("a"))
                if last is None:
                    last = item.get("last") or item.get("last_price")
                if bid is None:
                    bid = item.get("bid") or item.get("bid_price")
                if ask is None:
                    ask = item.get("ask") or item.get("ask_price")
                if last in (None, ""):
                    continue
                open_price = self._first(item.get("o")) or item.get("open")
                try:
                    change_pct = str((float(last) - float(open_price)) / float(open_price) * 100) if float(open_price) else "0"
                except Exception:
                    change_pct = "0"
                self.db.upsert_live_price({
                    "symbol": original,
                    "last": str(last),
                    "bid": str(bid) if bid is not None else None,
                    "ask": str(ask) if ask is not None else None,
                    "change_pct": change_pct,
                    "received_at": received,
                })
                saved.append(original)

        self.stream.enabled = True
        self.stream.set_symbols(symbols[:self.max_symbols])
        self.stream.start()
        result = {
            "status": "READY" if saved else "NO_DATA",
            "requested": len(symbols),
            "saved": len(saved),
            "symbols": symbols[:self.max_symbols],
            "warnings": warnings,
            "received_at": received,
        }
        self.db.set_setting("v102_market_last_refresh", received)
        self.db.set_setting("v102_market_last_result", json.dumps(result, sort_keys=True))
        self.db.audit("V102_MARKET_REFRESH", json.dumps(result, ensure_ascii=False, sort_keys=True), "warning" if warnings else "info")
        self.last_result = result
        return result

    def _discover(self):
        try:
            self.universe.sync()
        except Exception as exc:
            self.db.audit("V102_MARKET_UNIVERSE_SYNC_FAILED", type(exc).__name__ + ":" + str(exc)[:300], "warning")
        symbols = []
        try:
            symbols = self.universe.symbols(None)
        except Exception:
            symbols = []
        eur = [x for x in symbols if str(x).upper().endswith("/EUR")]
        usd = [x for x in symbols if str(x).upper().endswith("/USD")]
        ordered = []
        for symbol in list(eur) + list(usd) + list(SEED_SYMBOLS):
            if symbol not in ordered:
                ordered.append(symbol)
            if len(ordered) >= self.max_symbols:
                break
        return ordered or list(SEED_SYMBOLS)

    def bootstrap(self, force=False):
        with self.lock:
            now = time.time()
            if not force and self.last_bootstrap_at and now - self.last_bootstrap_at < 60:
                return self.last_result or {"status": "READY", "reused": True}
            symbols = self._discover()
            result = self.snapshot(symbols)
            self.last_bootstrap_at = now
            result["reused"] = False
            return result

    def start_background(self):
        if os.getenv("APP_DISABLE_WEBSOCKETS") == "1":
            self.stream.enabled = False
            return None
        self.stream.enabled = True
        self.stream.set_symbols(list(SEED_SYMBOLS))
        self.stream.start()
        if self.thread:
            return self.thread
        self.stop.clear()
        self.thread = threading.Thread(target=self._loop, name="v102-public-market", daemon=True)
        self.thread.start()
        return self.thread

    def _loop(self):
        self.stop.wait(0.5)
        while not self.stop.is_set():
            try:
                self.bootstrap(force=True)
            except Exception as exc:
                self.db.audit("V102_MARKET_BOOTSTRAP_FAILED", type(exc).__name__ + ":" + str(exc)[:300], "error")
            self.stop.wait(900)

    def stop_background(self):
        self.stop.set()

    def refresh_for_process(self):
        symbols = list(self.stream.symbols or [])
        if not symbols:
            symbols = list(SEED_SYMBOLS)
        result = self.snapshot(symbols)
        return int(result.get("saved", 0))

    def status(self):
        stream = self.stream.status()
        prices = self.db.rows("SELECT COUNT(*) AS n FROM live_prices WHERE received_at >= datetime('now','-10 minutes')")
        stream["live_price_count_10m"] = int(prices[0]["n"]) if prices else 0
        stream["last_rest_refresh"] = self.db.value("v102_market_last_refresh", "")
        stream["last_refresh_result"] = self.last_result or {}
        return stream
