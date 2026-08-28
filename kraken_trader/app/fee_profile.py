import json
from decimal import Decimal
from db import now

D = lambda value: Decimal(str(value or 0))


class FeeProfile:
    """Read-only Kraken fee tier cache with canonical pair resolution.

    Internal display symbols are never sent blindly to TradeVolume. Currency
    markets are mapped to Kraken's source key/altname. Unsupported asset
    classes stay on the documented conservative configuration fallback.
    """

    SUPPORTED_ASSET_CLASSES = {'currency', 'forex'}

    def __init__(self, db, client):
        self.db, self.client = db, client
        self.ensure()

    def ensure(self):
        with self.db.con() as c:
            c.executescript("""
            CREATE TABLE IF NOT EXISTS account_fee_snapshots(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,status TEXT NOT NULL,
                volume_currency TEXT,volume_30d TEXT,source TEXT NOT NULL,
                error_reason TEXT,payload_json TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS account_pair_fees(
                symbol TEXT PRIMARY KEY,maker_bps TEXT NOT NULL,
                taker_bps TEXT NOT NULL,source TEXT NOT NULL,
                effective_at TEXT NOT NULL,snapshot_id INTEGER,
                payload_json TEXT NOT NULL);
            """)

    def _rate(self, value):
        return str((D(value) * 100).quantize(Decimal('0.0001')))

    @staticmethod
    def _compact(value):
        return str(value or '').upper().replace('/', '').replace('-', '')

    def _market_rows(self, symbols):
        if not symbols:
            return []
        try:
            marks = ','.join('?' for _ in symbols)
            return self.db.rows(
                'SELECT symbol,asset_class,source_key FROM market_universe '
                f'WHERE symbol IN ({marks})', tuple(symbols))
        except Exception:
            return []

    def _pair_catalog(self):
        try:
            return self.client.pairs('currency') or {}
        except (AttributeError, TypeError, RuntimeError):
            return {}
        except Exception as exc:
            self.db.audit('ACCOUNT_FEE_PAIR_CATALOG_FAILED',
                          type(exc).__name__ + ': ' + str(exc)[:200], 'warning')
            return {}

    def _resolve(self, symbols):
        rows = {x['symbol']: x for x in self._market_rows(symbols)}
        catalog = self._pair_catalog()
        aliases = {}
        for key, item in catalog.items():
            values = {key, item.get('altname'), item.get('wsname')}
            for value in values:
                if value:
                    aliases[self._compact(value)] = (key, item)
        resolved, skipped = [], []
        for symbol in symbols:
            row = rows.get(symbol, {})
            asset_class = row.get('asset_class', 'currency')
            if asset_class not in self.SUPPORTED_ASSET_CLASSES:
                skipped.append({'symbol': symbol, 'reason': 'UNSUPPORTED_ASSET_CLASS',
                                'asset_class': asset_class})
                continue
            candidates = [row.get('source_key'), symbol,
                          symbol.replace('BTC', 'XBT')]
            match = None
            for candidate in candidates:
                if not candidate:
                    continue
                if candidate in catalog:
                    match = (candidate, catalog[candidate])
                    break
                match = aliases.get(self._compact(candidate))
                if match:
                    break
            pair = match[0] if match else (row.get('source_key') or symbol)
            item = match[1] if match else {}
            resolved.append({'symbol': symbol, 'pair': pair,
                             'altname': item.get('altname'),
                             'wsname': item.get('wsname'),
                             'asset_class': asset_class})
        return resolved, skipped

    @staticmethod
    def _fee_item(collection, mapping):
        keys = [mapping.get('pair'), mapping.get('altname'), mapping.get('wsname'),
                mapping.get('symbol')]
        compact = {FeeProfile._compact(key): value
                   for key, value in (collection or {}).items()}
        for key in keys:
            if key in (collection or {}):
                return collection[key]
            item = compact.get(FeeProfile._compact(key))
            if item is not None:
                return item
        return {}

    def _request(self, resolved):
        pairs = [x['pair'] for x in resolved]
        try:
            return self.client.trade_volume(pairs, fee_info=True), [], resolved
        except Exception as batch_error:
            payloads, errors, valid = [], [], []
            for mapping in resolved:
                try:
                    payloads.append(self.client.trade_volume(
                        [mapping['pair']], fee_info=True))
                    valid.append(mapping)
                except Exception as exc:
                    errors.append({'symbol': mapping['symbol'],
                                   'pair': mapping['pair'],
                                   'error': type(exc).__name__ + ': ' + str(exc)[:160]})
            if not payloads:
                raise batch_error
            merged = {'fees': {}, 'fees_maker': {}}
            for payload in payloads:
                merged['currency'] = payload.get('currency', merged.get('currency', ''))
                merged['volume'] = payload.get('volume', merged.get('volume', ''))
                merged['fees'].update(payload.get('fees') or {})
                merged['fees_maker'].update(payload.get('fees_maker') or {})
            return merged, errors, valid

    def refresh(self, symbols):
        symbols = sorted(set(x for x in symbols if x))
        stamp = now()
        resolved, skipped = self._resolve(symbols)
        if not resolved:
            error = 'Keine von TradeVolume unterstÃ¼tzten WÃ¤hrungspaare'
            self._save_failure(stamp, error, skipped)
            return {'status': 'FALLBACK', 'saved': 0, 'skipped': skipped,
                    'error': 'NO_SUPPORTED_PAIRS'}
        try:
            payload, errors, valid = self._request(resolved)
        except Exception as exc:
            error = type(exc).__name__ + ': ' + str(exc)[:200]
            self._save_failure(stamp, error, skipped)
            return {'status': 'FALLBACK', 'saved': 0, 'skipped': skipped,
                    'error': type(exc).__name__}
        fees = payload.get('fees') or {}
        makers = payload.get('fees_maker') or {}
        diagnostic = {'requested': symbols, 'resolved': valid,
                      'skipped': skipped, 'errors': errors}
        status = 'PARTIAL' if skipped or errors else 'VALID'
        saved = 0
        with self.db.con() as c:
            cur = c.execute(
                'INSERT INTO account_fee_snapshots(created_at,status,volume_currency,'
                'volume_30d,source,error_reason,payload_json) VALUES(?,?,?,?,?,?,?)',
                (stamp, status, str(payload.get('currency') or ''),
                 str(payload.get('volume') or ''), 'KRAKEN_TRADE_VOLUME',
                 json.dumps(errors, ensure_ascii=False) if errors else None,
                 json.dumps({'response': payload, 'diagnostic': diagnostic},
                            sort_keys=True, ensure_ascii=False)))
            snapshot_id = cur.lastrowid
            for mapping in valid:
                item = self._fee_item(fees, mapping)
                maker = self._fee_item(makers, mapping) or item
                taker_value = item.get('fee') if isinstance(item, dict) else None
                maker_value = maker.get('fee') if isinstance(maker, dict) else None
                if taker_value is None:
                    errors.append({'symbol': mapping['symbol'],
                                   'pair': mapping['pair'],
                                   'error': 'FEE_NOT_RETURNED'})
                    continue
                taker = self._rate(taker_value)
                maker_bps = self._rate(maker_value if maker_value is not None else taker_value)
                c.execute(
                    'INSERT INTO account_pair_fees(symbol,maker_bps,taker_bps,source,'
                    'effective_at,snapshot_id,payload_json) VALUES(?,?,?,?,?,?,?) '
                    'ON CONFLICT(symbol) DO UPDATE SET maker_bps=excluded.maker_bps,'
                    'taker_bps=excluded.taker_bps,source=excluded.source,'
                    'effective_at=excluded.effective_at,snapshot_id=excluded.snapshot_id,'
                    'payload_json=excluded.payload_json',
                    (mapping['symbol'], maker_bps, taker, 'KRAKEN_TRADE_VOLUME',
                     stamp, snapshot_id, json.dumps({'mapping': mapping,
                     'taker': item, 'maker': maker}, sort_keys=True)))
                saved += 1
        if errors and status == 'VALID':
            status = 'PARTIAL'
        self.db.audit('ACCOUNT_FEE_REFRESHED', json.dumps({
            'status': status, 'pairs_saved': saved, 'resolved': len(valid),
            'skipped': skipped, 'errors': errors,
            'volume_30d': str(payload.get('volume') or '')}, ensure_ascii=False))
        return {'status': status, 'saved': saved, 'skipped': skipped,
                'errors': errors, 'volume_30d': payload.get('volume'),
                'currency': payload.get('currency')}

    def _save_failure(self, stamp, error, skipped):
        with self.db.con() as c:
            c.execute('INSERT INTO account_fee_snapshots(created_at,status,source,'
                      'error_reason,payload_json) VALUES(?,?,?,?,?)',
                      (stamp, 'FALLBACK', 'CONFIG', error,
                       json.dumps({'skipped': skipped}, ensure_ascii=False)))
        self.db.audit('ACCOUNT_FEE_REFRESH_FAILED', error, 'warning')

    def rate_bps(self, symbol, side='taker', fallback=None):
        rows = self.db.rows('SELECT maker_bps,taker_bps,source,effective_at '
                            'FROM account_pair_fees WHERE symbol=?', (symbol,))
        if rows:
            key = 'maker_bps' if side == 'maker' else 'taker_bps'
            return D(rows[0][key]), rows[0]['source'], rows[0]['effective_at']
        value = fallback if fallback is not None else self.db.value('paper_fee_bps', '40')
        return D(value), 'CONFIG', None

    def rows(self):
        return self.db.rows('SELECT * FROM account_pair_fees ORDER BY symbol')

    def latest(self):
        rows = self.db.rows('SELECT * FROM account_fee_snapshots ORDER BY id DESC LIMIT 1')
        return rows[0] if rows else None
