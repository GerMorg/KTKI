import csv
import hashlib
import io
import json
import os
import zipfile
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from flask import Blueprint, Response, request

from db import now
from kraken import KrakenClient

RATE = Decimal('0.275')
DISCLAIMER = (
    'Arbeits- und Prüfhilfe für die österreichische Einkommensteuer. '
    'Keine Steuer- oder Rechtsberatung und kein Ersatz für die Prüfung durch '
    'Steuerberatung bzw. Finanzverwaltung. Die steuerliche Einordnung einzelner '
    'Produkte, Transaktionen, Verluste und Anschaffungszeitpunkte muss anhand der '
    'vollständigen Unterlagen geprüft werden.'
)


def D(value):
    try:
        return Decimal(str(value if value not in (None, '') else 0))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal(0)


def money(value):
    return str(D(value).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))


def tax_year(value):
    try:
        year = int(value)
    except (TypeError, ValueError):
        year = datetime.now(timezone.utc).year - 1
    return max(2009, min(datetime.now(timezone.utc).year, year))


def iso_day(timestamp):
    return datetime.fromtimestamp(float(timestamp), timezone.utc).date().isoformat()


class AustrianTaxV68:
    """Builds a reproducible Real-Kraken tax working set.

    The engine intentionally separates raw imported evidence from the derived
    calculation. Raw TradesHistory and Ledgers are stored unchanged, FX rates
    are cached by day, and every generated report carries a content hash.
    """

    def __init__(self, db):
        self.db = db
        self.ensure()

    def ensure(self):
        with self.db.con() as c:
            c.executescript(
                '''
                CREATE TABLE IF NOT EXISTS at68_reports(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    tax_year INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    trade_count INTEGER NOT NULL,
                    ledger_count INTEGER NOT NULL,
                    gain_eur TEXT NOT NULL,
                    loss_eur TEXT NOT NULL,
                    tax_estimate_eur TEXT NOT NULL,
                    review_count INTEGER NOT NULL,
                    content_sha256 TEXT NOT NULL,
                    summary_json TEXT NOT NULL,
                    realized_csv TEXT NOT NULL,
                    inventory_csv TEXT NOT NULL,
                    cashflow_csv TEXT NOT NULL,
                    audit_csv TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_at68_reports_year ON at68_reports(tax_year,id DESC);
                CREATE TABLE IF NOT EXISTS at68_real_trades(
                    txid TEXT PRIMARY KEY,
                    trade_time REAL NOT NULL,
                    pair TEXT NOT NULL,
                    side TEXT NOT NULL,
                    price TEXT NOT NULL,
                    volume TEXT NOT NULL,
                    cost TEXT NOT NULL,
                    fee TEXT NOT NULL,
                    ordertxid TEXT,
                    raw_json TEXT NOT NULL,
                    imported_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_at68_real_trades_time ON at68_real_trades(trade_time,txid);
                CREATE TABLE IF NOT EXISTS at68_ledgers(
                    ledger_id TEXT PRIMARY KEY,
                    ledger_time REAL NOT NULL,
                    asset TEXT NOT NULL,
                    amount TEXT NOT NULL,
                    fee TEXT NOT NULL,
                    ledger_type TEXT NOT NULL,
                    subtype TEXT,
                    refid TEXT,
                    raw_json TEXT NOT NULL,
                    imported_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_at68_ledgers_time ON at68_ledgers(ledger_time,ledger_id);
                CREATE TABLE IF NOT EXISTS at68_fx_daily(
                    day TEXT PRIMARY KEY,
                    rate_eurusd TEXT NOT NULL,
                    source TEXT NOT NULL,
                    fetched_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS at68_basis_opening(
                    asset TEXT PRIMARY KEY,
                    quantity TEXT NOT NULL,
                    basis_eur TEXT NOT NULL,
                    source TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS at68_report_audit(
                    report_id INTEGER PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    tax_year INTEGER NOT NULL,
                    source_sha256 TEXT NOT NULL,
                    report_sha256 TEXT NOT NULL,
                    details_json TEXT NOT NULL
                );
                '''
            )

    def _client(self):
        try:
            with open(os.getenv('APP_OPTIONS', '/data/options.json'), encoding='utf-8') as handle:
                options = json.load(handle)
            key = options.get('kraken_api_key', '')
            secret = options.get('kraken_api_secret', '')
            return KrakenClient(key, secret) if key and secret else None
        except Exception:
            return None

    @staticmethod
    def _pair_parts(pair):
        compact = str(pair or '').upper().replace('/', '').replace('-', '')
        compact = compact.replace('XXBT', 'XBT').replace('XETH', 'ETH')
        if compact.endswith('EUR'):
            return compact[:-3], 'EUR'
        if compact.endswith('USD'):
            return compact[:-3], 'USD'
        return compact, ''

    def _pair_is_crypto_or_token(self, pair):
        base, quote = self._pair_parts(pair)
        return bool(base and quote in ('EUR', 'USD') and base not in ('EUR', 'USD'))

    def _fetch_trades(self):
        client = self._client()
        if not client:
            return {'status': 'NO_API_CREDENTIALS', 'imported': 0, 'pages': 0}
        imported = 0
        pages = 0
        offset = 0
        try:
            while True:
                result = client.call('/0/private/TradesHistory', {'type': 'all', 'ofs': offset}, private=True)
                if not isinstance(result, dict):
                    raise TypeError('TradesHistory result is not a dictionary')
                trades = result.get('trades') or {}
                if not isinstance(trades, dict):
                    raise TypeError('TradesHistory trades is not a dictionary')
                pages += 1
                if not trades:
                    break
                with self.db.con() as c:
                    for txid, item in trades.items():
                        if not isinstance(item, dict):
                            continue
                        c.execute(
                            '''INSERT OR REPLACE INTO at68_real_trades
                               (txid,trade_time,pair,side,price,volume,cost,fee,ordertxid,raw_json,imported_at)
                               VALUES(?,?,?,?,?,?,?,?,?,?,?)''',
                            (
                                str(txid), float(item.get('time') or 0), str(item.get('pair') or ''),
                                str(item.get('type') or '').lower(), str(item.get('price') or 0),
                                str(item.get('vol') or 0), str(item.get('cost') or 0),
                                str(item.get('fee') or 0), str(item.get('ordertxid') or ''),
                                json.dumps(item, sort_keys=True, ensure_ascii=False), now(),
                            ),
                        )
                        imported += 1
                if len(trades) < 50:
                    break
                offset += len(trades)
            return {'status': 'VALID', 'imported': imported, 'pages': pages}
        except Exception as exc:
            self.db.audit('AT68_TRADES_IMPORT_FAILED', type(exc).__name__ + ': ' + str(exc)[:300], 'warning')
            return {'status': 'ERROR', 'imported': imported, 'pages': pages, 'error': type(exc).__name__}

    def _fetch_ledgers(self):
        client = self._client()
        if not client:
            return {'status': 'NO_API_CREDENTIALS', 'imported': 0, 'pages': 0}
        imported = 0
        pages = 0
        offset = 0
        try:
            while True:
                result = client.call('/0/private/Ledgers', {'aclass': 'currency', 'type': 'all', 'ofs': offset}, private=True)
                if not isinstance(result, dict):
                    raise TypeError('Ledgers result is not a dictionary')
                ledgers = result.get('ledger') or {}
                if not isinstance(ledgers, dict):
                    raise TypeError('Ledgers ledger is not a dictionary')
                pages += 1
                if not ledgers:
                    break
                with self.db.con() as c:
                    for ledger_id, item in ledgers.items():
                        if not isinstance(item, dict):
                            continue
                        c.execute(
                            '''INSERT OR REPLACE INTO at68_ledgers
                               (ledger_id,ledger_time,asset,amount,fee,ledger_type,subtype,refid,raw_json,imported_at)
                               VALUES(?,?,?,?,?,?,?,?,?,?)''',
                            (
                                str(ledger_id), float(item.get('time') or 0), str(item.get('asset') or ''),
                                str(item.get('amount') or 0), str(item.get('fee') or 0),
                                str(item.get('type') or ''), str(item.get('subtype') or ''),
                                str(item.get('refid') or ''), json.dumps(item, sort_keys=True, ensure_ascii=False), now(),
                            ),
                        )
                        imported += 1
                if len(ledgers) < 50:
                    break
                offset += len(ledgers)
            return {'status': 'VALID', 'imported': imported, 'pages': pages}
        except Exception as exc:
            self.db.audit('AT68_LEDGERS_IMPORT_FAILED', type(exc).__name__ + ': ' + str(exc)[:300], 'warning')
            return {'status': 'ERROR', 'imported': imported, 'pages': pages, 'error': type(exc).__name__}

    def _fx_rates(self, year):
        existing = {x['day']: D(x['rate_eurusd']) for x in self.db.rows('SELECT day,rate_eurusd FROM at68_fx_daily')}
        wanted_days = {iso_day(x['trade_time']) for x in self.db.rows('SELECT trade_time FROM at68_real_trades WHERE trade_time>0')}
        wanted_days |= {iso_day(x['ledger_time']) for x in self.db.rows('SELECT ledger_time FROM at68_ledgers WHERE ledger_time>0')}
        wanted_days = {x for x in wanted_days if x.startswith(str(year))}
        missing = sorted(x for x in wanted_days if x not in existing)
        client = self._client()
        if missing and not client:
            return existing, {'status': 'NO_API_CREDENTIALS', 'fetched_days': 0, 'missing_days': missing}
        fetched = 0
        errors = []
        # Daily candles provide one stable, cached conversion point for a trade day.
        # If a day is not returned by Kraken, the transaction stays REVIEW_REQUIRED.
        if missing and client:
            try:
                since = int(datetime.fromisoformat(f'{year}-01-01T00:00:00+00:00').timestamp())
                candles = client.ohlc('EUR/USD', interval=1440, since=since)
                if not isinstance(candles, dict):
                    raise TypeError('OHLC result is not a dictionary')
                series = candles.get('XXEURZUSD') or candles.get('EUR/USD') or next((v for k, v in candles.items() if k != 'last' and isinstance(v, list)), [])
                if not isinstance(series, list):
                    series = []
                for candle in series:
                    if not isinstance(candle, (list, tuple)) or len(candle) < 5:
                        continue
                    day = datetime.fromtimestamp(float(candle[0]), timezone.utc).date().isoformat()
                    close = D(candle[4])
                    if close <= 0 or not day.startswith(str(year)):
                        continue
                    with self.db.con() as c:
                        c.execute('INSERT OR REPLACE INTO at68_fx_daily(day,rate_eurusd,source,fetched_at) VALUES(?,?,?,?)', (day, str(close), 'KRAKEN_OHLC_D1_CLOSE', now()))
                    existing[day] = close
                    fetched += 1
            except Exception as exc:
                errors.append(type(exc).__name__)
        result = {'status': 'VALID' if not (set(missing) - set(existing)) else 'PARTIAL', 'fetched_days': fetched, 'missing_days': sorted(set(missing) - set(existing)), 'errors': errors}
        return existing, result

    def _external_basis(self):
        rows = self.db.rows('SELECT asset,quantity,basis_eur,source FROM at68_basis_opening ORDER BY asset')
        return {x['asset']: [D(x['quantity']), D(x['basis_eur']), x['source']] for x in rows}

    def _eur_value(self, pair, quote_amount, day, fx):
        base, quote = self._pair_parts(pair)
        if quote == 'EUR':
            return D(quote_amount), 'EUR_NATIVE'
        if quote == 'USD':
            rate = D(fx.get(day, 0))
            if rate > 0:
                return D(quote_amount) / rate, 'KRAKEN_OHLC_D1_CLOSE'
            return Decimal(0), 'MISSING_FX'
        return Decimal(0), 'UNSUPPORTED_QUOTE'

    def build_realized(self, year, fx):
        inventory = self._external_basis()
        rows = []
        warnings = []
        trades = self.db.rows('SELECT * FROM at68_real_trades ORDER BY trade_time,txid')
        for trade in trades:
            timestamp = float(trade['trade_time'] or 0)
            if timestamp <= 0:
                warnings.append(f"Trade {trade['txid']}: ungültiger Zeitstempel")
                continue
            day = iso_day(timestamp)
            moment = datetime.fromtimestamp(timestamp, timezone.utc)
            pair = trade['pair']
            base, quote = self._pair_parts(pair)
            qty = D(trade['volume'])
            cost_quote = D(trade['cost'])
            fee_quote = D(trade['fee'])
            if not base or quote not in ('EUR', 'USD') or not self._pair_is_crypto_or_token(pair):
                continue
            gross_eur, fx_source = self._eur_value(pair, cost_quote, day, fx)
            fee_eur, fee_fx_source = self._eur_value(pair, fee_quote, day, fx)
            state = inventory.setdefault(base, [Decimal(0), Decimal(0), 'derived'])
            side = str(trade['side']).lower()
            review = []
            if gross_eur <= 0 and quote == 'USD':
                review.append('HISTORISCHE_EUR_USD_RATE_FEHLT')
            if side == 'buy':
                acquisition = gross_eur + fee_eur if gross_eur > 0 else Decimal(0)
                if gross_eur > 0:
                    state[0] += qty
                    state[1] += acquisition
                else:
                    review.append('ANSCHAFFUNGSKOSTEN_NICHT_EUR_BEWERTET')
                if moment.year != year:
                    continue
                # Käufe werden als Bestands-/Belegposition ausgegeben, nicht als Veräußerung.
                rows.append({
                    'trade_id': trade['txid'], 'date': moment.isoformat(), 'day': day,
                    'pair': pair, 'asset': base, 'side': 'BUY', 'quantity': money(qty),
                    'quote_amount': money(cost_quote), 'quote_currency': quote,
                    'gross_value_eur': money(gross_eur), 'fee_eur': money(fee_eur),
                    'acquisition_basis_eur': money(acquisition), 'proceeds_eur': '0.00',
                    'gain_loss_eur': '0.00', 'estimated_tax_eur': '0.00',
                    'fx_rate_source': fx_source if fx_source != 'MISSING_FX' else fee_fx_source,
                    'review_required': 'yes' if review else 'no', 'review_reasons': '|'.join(sorted(set(review))),
                })
                continue
            if side != 'sell' or qty <= 0:
                warnings.append(f"Trade {trade['txid']}: nicht auswertbarer Side/Quantity")
                continue
            if state[0] < qty:
                review.append('ANSCHAFFUNGSBESTAND_FEHLT_ODER_WIRD_EXTERN_GEHALTEN')
                basis = Decimal(0)
            else:
                basis = (state[1] / state[0] * qty) if state[0] > 0 else Decimal(0)
                state[0] -= qty
                state[1] -= basis
            proceeds = gross_eur - fee_eur if gross_eur > 0 else Decimal(0)
            if proceeds <= 0:
                review.append('ERLOES_NICHT_EUR_BEWERTET')
            gain = proceeds - basis if not review or 'HISTORISCHE_EUR_USD_RATE_FEHLT' not in review else Decimal(0)
            if moment.year != year:
                continue
            estimated = max(Decimal(0), gain) * RATE if not review else Decimal(0)
            rows.append({
                'trade_id': trade['txid'], 'date': moment.isoformat(), 'day': day,
                'pair': pair, 'asset': base, 'side': 'SELL', 'quantity': money(qty),
                'quote_amount': money(cost_quote), 'quote_currency': quote,
                'gross_value_eur': money(gross_eur), 'fee_eur': money(fee_eur),
                'acquisition_basis_eur': money(basis), 'proceeds_eur': money(proceeds),
                'gain_loss_eur': money(gain), 'estimated_tax_eur': money(estimated),
                'fx_rate_source': fx_source, 'review_required': 'yes' if review else 'no',
                'review_reasons': '|'.join(sorted(set(review))),
            })
        return rows, inventory, warnings

    def build_inventory(self, inventory, year):
        rows = []
        for asset in sorted(inventory):
            qty, basis, source = inventory[asset]
            if qty <= 0:
                continue
            rows.append({
                'tax_year': str(year), 'asset': asset, 'quantity': money(qty),
                'basis_eur': money(basis), 'unit_basis_eur': money(basis / qty if qty else 0),
                'basis_source': source, 'review_required': 'yes' if source != 'derived' else 'no',
            })
        return rows

    def build_cashflow(self, year):
        rows = []
        for ledger in self.db.rows('SELECT * FROM at68_ledgers ORDER BY ledger_time,ledger_id'):
            if not ledger['ledger_time'] or datetime.fromtimestamp(float(ledger['ledger_time']), timezone.utc).year != year:
                continue
            amount = D(ledger['amount'])
            fee = D(ledger['fee'])
            ltype = str(ledger['ledger_type']).lower()
            classification = 'SONSTIGER_LEDGER'
            review = 'no'
            if ltype in ('deposit', 'staking', 'earn'):
                classification = 'EINGANG_MANUELL_EINORDNEN' if ltype != 'deposit' else 'EINLAGE/TRANSFER'
                review = 'yes' if ltype != 'deposit' else 'no'
            elif ltype in ('withdrawal', 'transfer'):
                classification = 'AUSZAHLUNG/TRANSFER'
            elif ltype == 'trade':
                classification = 'TRADE_LEDGER_NICHT_SEPARAT_VERSTEUERN'
            rows.append({
                'ledger_id': ledger['ledger_id'],
                'date': datetime.fromtimestamp(float(ledger['ledger_time']), timezone.utc).isoformat(),
                'asset': ledger['asset'], 'amount': money(amount), 'fee': money(fee),
                'type': ledger['ledger_type'], 'subtype': ledger['subtype'], 'refid': ledger['refid'],
                'classification': classification, 'review_required': review,
            })
        return rows

    def analyze(self, year, refresh=True):
        year = tax_year(year)
        imports = {'trades': {'status': 'NOT_REQUESTED'}, 'ledgers': {'status': 'NOT_REQUESTED'}}
        if refresh:
            imports['trades'] = self._fetch_trades()
            imports['ledgers'] = self._fetch_ledgers()
        fx, fx_status = self._fx_rates(year)
        realized, inventory, warnings = self.build_realized(year, fx)
        cashflow = self.build_cashflow(year)
        inventory_rows = self.build_inventory(inventory, year)
        for row in inventory_rows:
            if row['review_required'] == 'yes':
                warnings.append(f"Bestand {row['asset']}: Anschaffungsbasis stammt nicht vollständig aus Real-Kraken-Trades")
        if fx_status['missing_days']:
            warnings.append(f"Für {len(fx_status['missing_days'])} Handelstage fehlt eine EUR/USD-Bewertung")
        review_rows = [x for x in realized if x['review_required'] == 'yes']
        valid_sells = [x for x in realized if x['side'] == 'SELL' and x['review_required'] == 'no']
        gains = sum((max(Decimal(0), D(x['gain_loss_eur'])) for x in valid_sells), Decimal(0))
        losses = sum((min(Decimal(0), D(x['gain_loss_eur'])) for x in valid_sells), Decimal(0))
        fees = sum((D(x['fee_eur']) for x in realized), Decimal(0))
        net = gains + losses
        status = 'READY_FOR_REVIEW' if not warnings and not review_rows and imports['trades'].get('status') == 'VALID' else 'REVIEW_REQUIRED'
        summary = {
            'tax_year': year,
            'status': status,
            'calculation_method': 'Durchschnittliche Anschaffungskosten je Asset aus dem importierten Real-Trade-Bestand; Sonderfälle/Abweichungen müssen geprüft werden.',
            'tax_rate_reference': '27,5 % als Berechnungsparameter; steuerliche Einordnung und anwendbarer Satz prüfen.',
            'realized_positive_eur': money(gains),
            'realized_negative_eur': money(losses),
            'net_realized_eur': money(net),
            'estimated_tax_eur': money(max(Decimal(0), net) * RATE) if status == 'READY_FOR_REVIEW' else '0.00',
            'trade_fees_eur': money(fees),
            'real_trade_count': len(self.db.rows('SELECT txid FROM at68_real_trades')),
            'year_realized_rows': len(realized),
            'review_count': len(review_rows) + len(warnings),
            'fx_status': fx_status,
            'imports': imports,
            'year_end_open_positions': len(inventory_rows),
            'disclaimer': DISCLAIMER,
        }
        return {
            'summary': summary, 'realized': realized, 'inventory': inventory_rows,
            'cashflow': cashflow, 'warnings': sorted(set(warnings)), 'fx': fx,
        }

    @staticmethod
    def _csv(rows, fields):
        stream = io.StringIO(newline='')
        writer = csv.DictWriter(stream, fieldnames=fields, delimiter=';')
        writer.writeheader()
        writer.writerows(rows)
        return stream.getvalue()

    def _e1kv_summary(self, report):
        s = report['summary']
        net = D(s['net_realized_eur'])
        return [
            {'tax_year': str(s['tax_year']), 'category': 'Realisierte positive Ergebnisse', 'amount_eur': s['realized_positive_eur'], 'tax_rate_parameter': '27,5 %', 'status': 'Arbeitswert'},
            {'tax_year': str(s['tax_year']), 'category': 'Realisierte negative Ergebnisse', 'amount_eur': s['realized_negative_eur'], 'tax_rate_parameter': '27,5 %', 'status': 'Arbeitswert'},
            {'tax_year': str(s['tax_year']), 'category': 'Nettoergebnis aus ausgewerteten Real-Veräußerungen', 'amount_eur': money(net), 'tax_rate_parameter': '27,5 %', 'status': 'Arbeitswert'},
            {'tax_year': str(s['tax_year']), 'category': 'Rechnerischer Steuerwert', 'amount_eur': s['estimated_tax_eur'], 'tax_rate_parameter': '27,5 %', 'status': 'Nur bei READY_FOR_REVIEW'},
        ]

    def persist(self, year, report):
        realized_fields = ['trade_id','date','day','pair','asset','side','quantity','quote_amount','quote_currency','gross_value_eur','fee_eur','acquisition_basis_eur','proceeds_eur','gain_loss_eur','estimated_tax_eur','fx_rate_source','review_required','review_reasons']
        inventory_fields = ['tax_year','asset','quantity','basis_eur','unit_basis_eur','basis_source','review_required']
        cashflow_fields = ['ledger_id','date','asset','amount','fee','type','subtype','refid','classification','review_required']
        audit_fields = ['tax_year','record_type','record_id','status','reason']
        realized_csv = self._csv(report['realized'], realized_fields)
        inventory_csv = self._csv(report['inventory'], inventory_fields)
        cashflow_csv = self._csv(report['cashflow'], cashflow_fields)
        audit_rows = []
        for x in report['realized']:
            audit_rows.append({'tax_year': str(year), 'record_type': 'REAL_TRADE', 'record_id': x['trade_id'], 'status': x['review_required'], 'reason': x['review_reasons']})
        for warning in report['warnings']:
            audit_rows.append({'tax_year': str(year), 'record_type': 'REPORT', 'record_id': '', 'status': 'yes', 'reason': warning})
        audit_csv = self._csv(audit_rows, audit_fields)
        e1kv_csv = self._csv(self._e1kv_summary(report), ['tax_year','category','amount_eur','tax_rate_parameter','status'])
        source_material = realized_csv + inventory_csv + cashflow_csv + e1kv_csv
        source_sha = hashlib.sha256(source_material.encode('utf-8')).hexdigest()
        summary = dict(report['summary'])
        summary['source_sha256'] = source_sha
        details = json.dumps(report['summary'], sort_keys=True, ensure_ascii=False, separators=(',', ':'))
        report_sha = hashlib.sha256((details + source_material).encode('utf-8')).hexdigest()
        with self.db.con() as c:
            cur = c.execute(
                '''INSERT INTO at68_reports(created_at,tax_year,status,trade_count,ledger_count,gain_eur,loss_eur,tax_estimate_eur,review_count,content_sha256,summary_json,realized_csv,inventory_csv,cashflow_csv,audit_csv)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                (
                    now(), year, summary['status'], len(report['realized']), len(report['cashflow']),
                    summary['realized_positive_eur'], summary['realized_negative_eur'], summary['estimated_tax_eur'],
                    summary['review_count'], report_sha, json.dumps(summary, ensure_ascii=False), realized_csv,
                    inventory_csv, cashflow_csv, audit_csv,
                ),
            )
            report_id = cur.lastrowid
            c.execute(
                'INSERT OR REPLACE INTO at68_report_audit(report_id,created_at,tax_year,source_sha256,report_sha256,details_json) VALUES(?,?,?,?,?,?)',
                (report_id, now(), year, source_sha, report_sha, json.dumps({'warning_count': len(report['warnings']), 'e1kv_rows': len(self._e1kv_summary(report))}, ensure_ascii=False)),
            )
        report['summary']['content_sha256'] = report_sha
        report['summary']['source_sha256'] = source_sha
        report['report_id'] = report_id
        report['e1kv_summary'] = self._e1kv_summary(report)
        report['csv'] = {'realized': realized_csv, 'inventory': inventory_csv, 'cashflow': cashflow_csv, 'audit': audit_csv, 'e1kv': e1kv_csv}
        return report

    def generate(self, year, refresh=True):
        report = self.analyze(year, refresh=refresh)
        return self.persist(tax_year(year), report)

    def latest(self, year):
        row = self.db.rows('SELECT * FROM at68_reports WHERE tax_year=? ORDER BY id DESC LIMIT 1', (tax_year(year),))
        return row[0] if row else None

    def export_zip(self, year):
        row = self.latest(year)
        if not row:
            return None
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(f'steuer-at-{row["tax_year"]}-summary.json', row['summary_json'])
            archive.writestr(f'steuer-at-{row["tax_year"]}-realized.csv', row['realized_csv'])
            archive.writestr(f'steuer-at-{row["tax_year"]}-inventory.csv', row['inventory_csv'])
            archive.writestr(f'steuer-at-{row["tax_year"]}-cashflow.csv', row['cashflow_csv'])
            archive.writestr(f'steuer-at-{row["tax_year"]}-audit.csv', row['audit_csv'])
            summary = json.loads(row['summary_json'])
            e1kv = self._csv([
                {'tax_year': str(row['tax_year']), 'category': 'Realisierte positive Ergebnisse', 'amount_eur': summary['realized_positive_eur'], 'tax_rate_parameter': '27,5 %', 'status': 'Arbeitswert'},
                {'tax_year': str(row['tax_year']), 'category': 'Realisierte negative Ergebnisse', 'amount_eur': summary['realized_negative_eur'], 'tax_rate_parameter': '27,5 %', 'status': 'Arbeitswert'},
                {'tax_year': str(row['tax_year']), 'category': 'Nettoergebnis aus ausgewerteten Real-Veräußerungen', 'amount_eur': money(D(summary['net_realized_eur'])), 'tax_rate_parameter': '27,5 %', 'status': 'Arbeitswert'},
                {'tax_year': str(row['tax_year']), 'category': 'Rechnerischer Steuerwert', 'amount_eur': summary['estimated_tax_eur'], 'tax_rate_parameter': '27,5 %', 'status': 'Nur bei READY_FOR_REVIEW'},
            ], ['tax_year','category','amount_eur','tax_rate_parameter','status'])
            archive.writestr(f'steuer-at-{row["tax_year"]}-e1kv-arbeitsblatt.csv', e1kv)
            manifest = json.dumps({'report_id': row['id'], 'tax_year': row['tax_year'], 'report_sha256': json.loads(row['summary_json']).get('content_sha256'), 'disclaimer': DISCLAIMER}, ensure_ascii=False, indent=2)
            archive.writestr(f'steuer-at-{row["tax_year"]}-manifest.json', manifest)
        return stream.getvalue()


def create_tax_v68_blueprint(db, page):
    service = AustrianTaxV68(db)
    bp = Blueprint('at_tax_v68', __name__)

    @bp.route('/tax-info', methods=['GET', 'POST'], endpoint='tax_info_v68')
    def tax_info():
        year = tax_year(request.values.get('year'))
        report = None
        error = None
        if request.method == 'POST':
            try:
                refresh = request.form.get('refresh', 'yes') == 'yes'
                report = service.generate(year, refresh=refresh)
            except Exception as exc:
                db.audit('AT68_TAX_GUI_FAILED', type(exc).__name__ + ': ' + str(exc)[:300], 'error')
                error = type(exc).__name__ + ': ' + str(exc)[:300]
        latest = service.latest(year) if report is None else None
        return page(_TEMPLATE, year=year, report=report, latest=latest, error=error)

    @bp.get('/tax-info-v68.zip', endpoint='tax_v68_zip')
    def tax_zip():
        year = tax_year(request.args.get('year'))
        data = service.export_zip(year)
        if data is None:
            return Response('Kein v68-Steuerbericht vorhanden', 404, mimetype='text/plain')
        return Response(data, mimetype='application/zip', headers={'Content-Disposition': f'attachment; filename=steuer-at-{year}-v68.zip'})

    @bp.get('/tax-info-v68.csv', endpoint='tax_v68_csv')
    def tax_csv():
        year = tax_year(request.args.get('year'))
        report = service.latest(year)
        if report is None:
            return Response('Kein v68-Steuerbericht vorhanden', 404, mimetype='text/plain')
        return Response(report['realized_csv'], mimetype='text/csv', headers={'Content-Disposition': f'attachment; filename=steuer-at-{year}-realized-v68.csv'})

    return bp


_TEMPLATE = '''
<h1>Steuerinfo Österreich – v68</h1>
<p class="lead">Realhandel-Jahresarbeitsmappe: Kraken-Trades, Ledger, historische FX-Bewertung, Anschaffungsbestand, Veräußerungsgewinne/-verluste und E1kv-Arbeitswerte.</p>
<div class="card"><form method="post">
<label>Steuerjahr<input name="year" type="number" min="2009" value="{{year}}"></label>
<label>Realhandel von Kraken aktualisieren?<select name="refresh"><option value="yes">Ja</option><option value="no">Nur lokal rechnen</option></select></label>
<button>Steuerdaten erstellen / aktualisieren</button>
</form></div>
{% if error %}<div class="card error">{{error}}</div>{% endif %}
{% if report %}<div class="card"><h2>{{report.summary.status}}</h2><p>{{report.summary.disclaimer}}</p><div class="grid">
<div><b>Positive Ergebnisse</b><br>{{report.summary.realized_positive_eur}} EUR</div>
<div><b>Negative Ergebnisse</b><br>{{report.summary.realized_negative_eur}} EUR</div>
<div><b>Netto</b><br>{{report.summary.net_realized_eur}} EUR</div>
<div><b>Rechnerische Steuer</b><br>{{report.summary.estimated_tax_eur}} EUR</div>
<div><b>Prüffälle</b><br>{{report.summary.review_count}}</div>
<div><b>Report-Hash</b><br><small>{{report.summary.content_sha256}}</small></div>
</div></div>
{% if report.warnings %}<div class="card warning"><h2>Prüfhilfen</h2><ul>{% for x in report.warnings %}<li>{{x}}</li>{% endfor %}</ul></div>{% endif %}
<div class="card"><h2>Ausgaben für die Steuerunterlagen</h2><p><a class="button" href="{{url_for('at_tax_v68.tax_v68_zip',year=year)}}">Komplettpaket ZIP</a> <a class="button" href="{{url_for('at_tax_v68.tax_v68_csv',year=year)}}">Realisierte Geschäfte CSV</a></p><p>Das ZIP enthält Summary, realisierte Geschäfte, offenen Bestand, Ledger-/Cashflow-Abstimmung, Prüfliste, E1kv-Arbeitsblatt und Manifest mit Hash.</p></div>
<div class="card"><h2>E1kv-Arbeitsblatt</h2><div class="tablewrap"><table><tr><th>Kategorie</th><th>EUR</th><th>Status</th></tr>{% for x in report.e1kv_summary %}<tr><td>{{x.category}}</td><td>{{x.amount_eur}}</td><td>{{x.status}}</td></tr>{% endfor %}</table></div></div>
<div class="card"><h2>Realisierte Geschäfte</h2><div class="tablewrap"><table><tr><th>Datum</th><th>Paar</th><th>Seite</th><th>Menge</th><th>Erlös</th><th>Anschaffung</th><th>Ergebnis</th><th>Prüfung</th></tr>{% for x in report.realized %}<tr><td>{{x.date}}</td><td>{{x.pair}}</td><td>{{x.side}}</td><td>{{x.quantity}}</td><td>{{x.proceeds_eur}}</td><td>{{x.acquisition_basis_eur}}</td><td>{{x.gain_loss_eur}}</td><td>{{x.review_required}}</td></tr>{% endfor %}</table></div></div>
{% else %}{% if latest %}<div class="card"><h2>Letzter Bericht</h2><p>{{latest.status}} · {{latest.row_count}} Realisierungs-/Kaufzeilen · {{latest.review_count}} Prüffälle · Hash {{latest.content_sha256}}</p><a class="button" href="{{url_for('at_tax_v68.tax_v68_zip',year=year)}}">ZIP exportieren</a></div>{% endif %}{% endif %}
<div class="card"><small>{{'Arbeits- und Prüfhilfe für die österreichische Einkommensteuer. Keine Steuer- oder Rechtsberatung und kein Ersatz für die Prüfung durch Steuerberatung bzw. Finanzverwaltung. Die steuerliche Einordnung einzelner Produkte, Transaktionen, Verluste und Anschaffungszeitpunkte muss anhand der vollständigen Unterlagen geprüft werden.'}}</small></div>
'''
