import csv
import hashlib
import io
import json
import os
import zipfile
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from db import now

RATE = Decimal('0.275')
DISCLAIMER = ('Arbeits- und Prüfhilfe für die österreichische Einkommensteuer. '
              'Keine Steuer- oder Rechtsberatung und kein Ersatz für die Prüfung durch '
              'Steuerberatung bzw. Finanzverwaltung. Die steuerliche Einordnung einzelner '
              'Produkte, Transaktionen, Verluste und Anschaffungszeitpunkte muss anhand der '
              'vollständigen Unterlagen geprüft werden.')


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
    """Reproducible Austrian real-trading tax working set.

    Raw Kraken trade/ledger evidence is stored separately from the derived
    calculation. EUR/USD rates are cached by day and every persisted report
    contains hashes plus machine-readable exports.
    """

    def __init__(self, db):
        self.db = db
        self.ensure()

    def ensure(self):
        with self.db.con() as c:
            c.executescript('''
                CREATE TABLE IF NOT EXISTS at68_reports(
                    id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT NOT NULL,
                    tax_year INTEGER NOT NULL, status TEXT NOT NULL,
                    trade_count INTEGER NOT NULL, ledger_count INTEGER NOT NULL,
                    gain_eur TEXT NOT NULL, loss_eur TEXT NOT NULL,
                    tax_estimate_eur TEXT NOT NULL, review_count INTEGER NOT NULL,
                    content_sha256 TEXT NOT NULL, summary_json TEXT NOT NULL,
                    realized_csv TEXT NOT NULL, inventory_csv TEXT NOT NULL,
                    cashflow_csv TEXT NOT NULL, audit_csv TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS idx_at68_reports_year ON at68_reports(tax_year,id DESC);
                CREATE TABLE IF NOT EXISTS at68_real_trades(
                    txid TEXT PRIMARY KEY, trade_time REAL NOT NULL, pair TEXT NOT NULL,
                    side TEXT NOT NULL, price TEXT NOT NULL, volume TEXT NOT NULL,
                    cost TEXT NOT NULL, fee TEXT NOT NULL, ordertxid TEXT,
                    raw_json TEXT NOT NULL, imported_at TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS idx_at68_real_trades_time ON at68_real_trades(trade_time,txid);
                CREATE TABLE IF NOT EXISTS at68_ledgers(
                    ledger_id TEXT PRIMARY KEY, ledger_time REAL NOT NULL, asset TEXT NOT NULL,
                    amount TEXT NOT NULL, fee TEXT NOT NULL, ledger_type TEXT NOT NULL,
                    subtype TEXT, refid TEXT, raw_json TEXT NOT NULL, imported_at TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS idx_at68_ledgers_time ON at68_ledgers(ledger_time,ledger_id);
                CREATE TABLE IF NOT EXISTS at68_fx_daily(
                    day TEXT PRIMARY KEY, rate_eurusd TEXT NOT NULL,
                    source TEXT NOT NULL, fetched_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS at68_basis_opening(
                    asset TEXT PRIMARY KEY, quantity TEXT NOT NULL, basis_eur TEXT NOT NULL,
                    source TEXT NOT NULL, updated_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS at68_report_audit(
                    report_id INTEGER PRIMARY KEY, created_at TEXT NOT NULL,
                    tax_year INTEGER NOT NULL, source_sha256 TEXT NOT NULL,
                    report_sha256 TEXT NOT NULL, details_json TEXT NOT NULL);
            ''')

    def _client(self):
        try:
            with open(os.getenv('APP_OPTIONS', '/data/options.json'), encoding='utf-8') as handle:
                options = json.load(handle)
            key, secret = options.get('kraken_api_key', ''), options.get('kraken_api_secret', '')
            if key and secret:
                from kraken import KrakenClient
                return KrakenClient(key, secret)
        except Exception:
            pass
        return None

    @staticmethod
    def _pair_parts(pair):
        compact = str(pair or '').upper().replace('/', '').replace('-', '')
        compact = compact.replace('XXBT', 'XBT').replace('XETH', 'ETH')
        for quote in ('EUR', 'USD'):
            if compact.endswith(quote):
                return compact[:-3], quote
        return compact, ''

    def _is_supported_market(self, pair):
        base, quote = self._pair_parts(pair)
        return bool(base and quote in ('EUR', 'USD') and base not in ('EUR', 'USD'))

    def _fetch_trades(self):
        client = self._client()
        if not client:
            return {'status': 'NO_API_CREDENTIALS', 'imported': 0, 'pages': 0}
        imported = pages = offset = 0
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
                        c.execute('''INSERT OR REPLACE INTO at68_real_trades
                                     (txid,trade_time,pair,side,price,volume,cost,fee,ordertxid,raw_json,imported_at)
                                     VALUES(?,?,?,?,?,?,?,?,?,?,?)''',
                                  (str(txid), float(item.get('time') or 0), str(item.get('pair') or ''),
                                   str(item.get('type') or '').lower(), str(item.get('price') or 0),
                                   str(item.get('vol') or 0), str(item.get('cost') or 0),
                                   str(item.get('fee') or 0), str(item.get('ordertxid') or ''),
                                   json.dumps(item, sort_keys=True, ensure_ascii=False), now()))
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
        imported = pages = offset = 0
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
                        c.execute('''INSERT OR REPLACE INTO at68_ledgers
                                     (ledger_id,ledger_time,asset,amount,fee,ledger_type,subtype,refid,raw_json,imported_at)
                                     VALUES(?,?,?,?,?,?,?,?,?,?)''',
                                  (str(ledger_id), float(item.get('time') or 0), str(item.get('asset') or ''),
                                   str(item.get('amount') or 0), str(item.get('fee') or 0),
                                   str(item.get('type') or ''), str(item.get('subtype') or ''),
                                   str(item.get('refid') or ''), json.dumps(item, sort_keys=True, ensure_ascii=False), now()))
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
        days = {iso_day(x['trade_time']) for x in self.db.rows('SELECT trade_time FROM at68_real_trades WHERE trade_time>0')}
        days |= {iso_day(x['ledger_time']) for x in self.db.rows('SELECT ledger_time FROM at68_ledgers WHERE ledger_time>0')}
        missing = sorted(x for x in days if x.startswith(str(year)) and x not in existing)
        client = self._client()
        if missing and not client:
            return existing, {'status': 'NO_API_CREDENTIALS', 'fetched_days': 0, 'missing_days': missing, 'errors': []}
        fetched, errors = 0, []
        if missing and client:
            try:
                since = int(datetime(year, 1, 1, tzinfo=timezone.utc).timestamp())
                candles = client.ohlc('EUR/USD', interval=1440, since=since)
                if not isinstance(candles, dict):
                    raise TypeError('OHLC result is not a dictionary')
                series = next((v for k, v in candles.items() if k != 'last' and isinstance(v, list)), [])
                for candle in series:
                    if not isinstance(candle, (list, tuple)) or len(candle) < 5:
                        continue
                    day = datetime.fromtimestamp(float(candle[0]), timezone.utc).date().isoformat()
                    close = D(candle[4])
                    if close <= 0 or not day.startswith(str(year)):
                        continue
                    with self.db.con() as c:
                        c.execute('INSERT OR REPLACE INTO at68_fx_daily VALUES(?,?,?,?)', (day, str(close), 'KRAKEN_OHLC_D1_CLOSE', now()))
                    existing[day] = close
                    fetched += 1
            except Exception as exc:
                errors.append(type(exc).__name__)
        return existing, {'status': 'VALID' if not (set(missing) - set(existing)) else 'PARTIAL',
                           'fetched_days': fetched, 'missing_days': sorted(set(missing) - set(existing)), 'errors': errors}

    def _external_basis(self):
        return {x['asset']: [D(x['quantity']), D(x['basis_eur']), x['source']]
                for x in self.db.rows('SELECT asset,quantity,basis_eur,source FROM at68_basis_opening')}

    def _eur_value(self, pair, quote_amount, day, fx):
        _, quote = self._pair_parts(pair)
        amount = D(quote_amount)
        if quote == 'EUR':
            return amount, 'EUR_NATIVE'
        if quote == 'USD':
            rate = D(fx.get(day, 0))
            return (amount / rate, 'KRAKEN_OHLC_D1_CLOSE') if rate > 0 else (Decimal(0), 'MISSING_FX')
        return Decimal(0), 'UNSUPPORTED_QUOTE'

    def build_realized(self, year, fx):
        inventory = self._external_basis()
        rows, warnings = [], []
        for trade in self.db.rows('SELECT * FROM at68_real_trades ORDER BY trade_time,txid'):
            timestamp = float(trade['trade_time'] or 0)
            if timestamp <= 0:
                warnings.append(f"Trade {trade['txid']}: ungültiger Zeitstempel")
                continue
            moment = datetime.fromtimestamp(timestamp, timezone.utc)
            pair = trade['pair']
            base, quote = self._pair_parts(pair)
            qty, cost_quote, fee_quote = D(trade['volume']), D(trade['cost']), D(trade['fee'])
            if not self._is_supported_market(pair) or qty <= 0:
                continue
            gross_eur, fx_source = self._eur_value(pair, cost_quote, moment.date().isoformat(), fx)
            fee_eur, _ = self._eur_value(pair, fee_quote, moment.date().isoformat(), fx)
            state = inventory.setdefault(base, [Decimal(0), Decimal(0), 'derived'])
            side = str(trade['side']).lower()
            review = []
            if quote == 'USD' and gross_eur <= 0:
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
                rows.append({'trade_id': trade['txid'], 'date': moment.isoformat(), 'day': moment.date().isoformat(),
                             'pair': pair, 'asset': base, 'side': 'BUY', 'quantity': money(qty),
                             'quote_amount': money(cost_quote), 'quote_currency': quote,
                             'gross_value_eur': money(gross_eur), 'fee_eur': money(fee_eur),
                             'acquisition_basis_eur': money(acquisition), 'proceeds_eur': '0.00',
                             'gain_loss_eur': '0.00', 'estimated_tax_eur': '0.00',
                             'fx_rate_source': fx_source, 'review_required': 'yes' if review else 'no',
                             'review_reasons': '|'.join(sorted(set(review)))})
                continue
            if side != 'sell':
                warnings.append(f"Trade {trade['txid']}: nicht auswertbare Seite")
                continue
            if state[0] < qty:
                basis = Decimal(0)
                review.append('ANSCHAFFUNGSBESTAND_FEHLT_ODER_WIRD_EXTERN_GEHALTEN')
                warnings.append(f"Trade {trade['txid']}: Anschaffungsbestand nicht vollständig vorhanden")
            else:
                basis = state[1] / state[0] * qty if state[0] > 0 else Decimal(0)
                state[0] -= qty
                state[1] -= basis
            proceeds = gross_eur - fee_eur if gross_eur > 0 else Decimal(0)
            if proceeds <= 0:
                review.append('ERLOES_NICHT_EUR_BEWERTET')
            gain = proceeds - basis if not review else Decimal(0)
            if moment.year != year:
                continue
            rows.append({'trade_id': trade['txid'], 'date': moment.isoformat(), 'day': moment.date().isoformat(),
                         'pair': pair, 'asset': base, 'side': 'SELL', 'quantity': money(qty),
                         'quote_amount': money(cost_quote), 'quote_currency': quote,
                         'gross_value_eur': money(gross_eur), 'fee_eur': money(fee_eur),
                         'acquisition_basis_eur': money(basis), 'proceeds_eur': money(proceeds),
                         'gain_loss_eur': money(gain), 'estimated_tax_eur': money(max(Decimal(0), gain) * RATE) if not review else '0.00',
                         'fx_rate_source': fx_source, 'review_required': 'yes' if review else 'no',
                         'review_reasons': '|'.join(sorted(set(review)))})
        return rows, inventory, warnings

    def build_inventory(self, inventory, year):
        rows = []
        for asset in sorted(inventory):
            qty, basis, source = inventory[asset]
            if qty <= 0:
                continue
            rows.append({'tax_year': str(year), 'asset': asset, 'quantity': money(qty), 'basis_eur': money(basis),
                         'unit_basis_eur': money(basis / qty if qty else 0), 'basis_source': source,
                         'review_required': 'yes' if source != 'derived' else 'no'})
        return rows

    def build_cashflow(self, year):
        rows = []
        for ledger in self.db.rows('SELECT * FROM at68_ledgers ORDER BY ledger_time,ledger_id'):
            if not ledger['ledger_time'] or datetime.fromtimestamp(float(ledger['ledger_time']), timezone.utc).year != year:
                continue
            amount, fee = D(ledger['amount']), D(ledger['fee'])
            kind = str(ledger['ledger_type']).lower()
            if kind == 'deposit':
                classification, review = 'EINLAGE/TRANSFER', 'no'
            elif kind in ('withdrawal', 'transfer'):
                classification, review = 'AUSZAHLUNG/TRANSFER', 'no'
            elif kind in ('staking', 'earn', 'reward'):
                classification, review = 'EINGANG_MANUELL_EINORDNEN', 'yes'
            elif kind == 'trade':
                classification, review = 'TRADE_LEDGER_NICHT_SEPARAT_VERSTEUERN', 'no'
            else:
                classification, review = 'SONSTIGER_LEDGER', 'yes'
            rows.append({'ledger_id': ledger['ledger_id'], 'date': datetime.fromtimestamp(float(ledger['ledger_time']), timezone.utc).isoformat(),
                         'asset': ledger['asset'], 'amount': money(amount), 'fee': money(fee), 'type': ledger['ledger_type'],
                         'subtype': ledger['subtype'], 'refid': ledger['refid'], 'classification': classification,
                         'review_required': review})
        return rows

    @staticmethod
    def _csv(rows, fields):
        stream = io.StringIO(newline='')
        writer = csv.DictWriter(stream, fieldnames=fields, delimiter=';')
        writer.writeheader()
        writer.writerows(rows)
        return stream.getvalue()

    def _e1kv_summary(self, summary):
        return [
            {'tax_year': str(summary['tax_year']), 'category': 'Realisierte positive Ergebnisse', 'amount_eur': summary['realized_positive_eur'], 'tax_rate_parameter': '27,5 %', 'status': 'Arbeitswert'},
            {'tax_year': str(summary['tax_year']), 'category': 'Realisierte negative Ergebnisse', 'amount_eur': summary['realized_negative_eur'], 'tax_rate_parameter': '27,5 %', 'status': 'Arbeitswert'},
            {'tax_year': str(summary['tax_year']), 'category': 'Nettoergebnis ausgewerteter Real-Veräußerungen', 'amount_eur': summary['net_realized_eur'], 'tax_rate_parameter': '27,5 %', 'status': 'Arbeitswert'},
            {'tax_year': str(summary['tax_year']), 'category': 'Rechnerischer Steuerwert', 'amount_eur': summary['estimated_tax_eur'], 'tax_rate_parameter': '27,5 %', 'status': 'Nur bei READY_FOR_REVIEW'},
        ]

    def analyze(self, year, refresh=True):
        year = tax_year(year)
        imports = {'trades': self._fetch_trades() if refresh else {'status': 'NOT_REQUESTED', 'imported': 0},
                   'ledgers': self._fetch_ledgers() if refresh else {'status': 'NOT_REQUESTED', 'imported': 0}}
        fx, fx_status = self._fx_rates(year)
        realized, inventory, warnings = self.build_realized(year, fx)
        cashflow = self.build_cashflow(year)
        inventory_rows = self.build_inventory(inventory, year)
        valid_sells = [x for x in realized if x['side'] == 'SELL' and x['review_required'] == 'no']
        gains = sum((max(Decimal(0), D(x['gain_loss_eur'])) for x in valid_sells), Decimal(0))
        losses = sum((min(Decimal(0), D(x['gain_loss_eur'])) for x in valid_sells), Decimal(0))
        fees = sum((D(x['fee_eur']) for x in realized), Decimal(0))
        warnings = sorted(set(warnings + [f"Bestand {x['asset']}: Anschaffungsbasis prüfen" for x in inventory_rows if x['review_required'] == 'yes']))
        if fx_status['missing_days']:
            warnings.append(f"Für {len(fx_status['missing_days'])} Handelstage fehlt eine EUR/USD-Bewertung")
        if imports['trades'].get('status') not in ('VALID', 'NOT_REQUESTED'):
            warnings.append('Real-Trade-Historie konnte nicht vollständig aktualisiert werden')
        status = 'READY_FOR_REVIEW' if not warnings and all(x['review_required'] == 'no' for x in realized) else 'REVIEW_REQUIRED'
        summary = {'tax_year': year, 'status': status,
                   'calculation_method': 'Durchschnittliche Anschaffungskosten je Asset aus dem importierten Real-Trade-Bestand; Sonderfälle und Abweichungen prüfen.',
                   'tax_rate_reference': '27,5 % als Berechnungsparameter; steuerliche Einordnung und anwendbarer Satz prüfen.',
                   'realized_positive_eur': money(gains), 'realized_negative_eur': money(losses),
                   'net_realized_eur': money(gains + losses),
                   'estimated_tax_eur': money(max(Decimal(0), gains + losses) * RATE) if status == 'READY_FOR_REVIEW' else '0.00',
                   'trade_fees_eur': money(fees), 'real_trade_count': imports['trades'].get('imported', 0),
                   'year_realized_rows': len(realized), 'review_count': len(warnings) + sum(x['review_required'] == 'yes' for x in realized),
                   'fx_status': fx_status, 'imports': imports, 'year_end_open_positions': len(inventory_rows),
                   'disclaimer': DISCLAIMER}
        return {'summary': summary, 'realized': realized, 'inventory': inventory_rows, 'cashflow': cashflow, 'warnings': warnings, 'fx': fx}

    def persist(self, year, report):
        realized_fields = ['trade_id','date','day','pair','asset','side','quantity','quote_amount','quote_currency','gross_value_eur','fee_eur','acquisition_basis_eur','proceeds_eur','gain_loss_eur','estimated_tax_eur','fx_rate_source','review_required','review_reasons']
        inventory_fields = ['tax_year','asset','quantity','basis_eur','unit_basis_eur','basis_source','review_required']
        cashflow_fields = ['ledger_id','date','asset','amount','fee','type','subtype','refid','classification','review_required']
        audit_fields = ['tax_year','record_type','record_id','status','reason']
        e1kv_fields = ['tax_year','category','amount_eur','tax_rate_parameter','status']
        realized_csv = self._csv(report['realized'], realized_fields)
        inventory_csv = self._csv(report['inventory'], inventory_fields)
        cashflow_csv = self._csv(report['cashflow'], cashflow_fields)
        e1kv_csv = self._csv(self._e1kv_summary(report['summary']), e1kv_fields)
        audit_rows = [{'tax_year': str(year), 'record_type': 'REAL_TRADE', 'record_id': x['trade_id'], 'status': x['review_required'], 'reason': x['review_reasons']} for x in report['realized']]
        audit_rows += [{'tax_year': str(year), 'record_type': 'REPORT', 'record_id': '', 'status': 'yes', 'reason': x} for x in report['warnings']]
        audit_csv = self._csv(audit_rows, audit_fields)
        source = realized_csv + inventory_csv + cashflow_csv + audit_csv + e1kv_csv
        source_sha = hashlib.sha256(source.encode('utf-8')).hexdigest()
        summary = dict(report['summary'])
        summary['source_sha256'] = source_sha
        details = json.dumps(summary, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
        report_sha = hashlib.sha256((details + source).encode('utf-8')).hexdigest()
        summary['content_sha256'] = report_sha
        details = json.dumps(summary, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
        with self.db.con() as c:
            cur = c.execute('''INSERT INTO at68_reports(created_at,tax_year,status,trade_count,ledger_count,gain_eur,loss_eur,tax_estimate_eur,review_count,content_sha256,summary_json,realized_csv,inventory_csv,cashflow_csv,audit_csv)
                               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                            (now(), year, summary['status'], len(report['realized']), len(report['cashflow']), summary['realized_positive_eur'], summary['realized_negative_eur'], summary['estimated_tax_eur'], summary['review_count'], report_sha, details, realized_csv, inventory_csv, cashflow_csv, audit_csv))
            report_id = cur.lastrowid
            c.execute('INSERT OR REPLACE INTO at68_report_audit VALUES(?,?,?,?,?,?)',
                      (report_id, now(), year, source_sha, report_sha, json.dumps({'e1kv_rows': 4, 'warning_count': len(report['warnings'])}, ensure_ascii=False)))
        report['summary'] = summary
        report['report_id'] = report_id
        report['e1kv_summary'] = self._e1kv_summary(summary)
        report['csv'] = {'realized': realized_csv, 'inventory': inventory_csv, 'cashflow': cashflow_csv, 'audit': audit_csv, 'e1kv': e1kv_csv}
        return report

    def generate(self, year, refresh=True):
        report = self.analyze(year, refresh=refresh)
        return self.persist(tax_year(year), report)

    def latest(self, year):
        rows = self.db.rows('SELECT * FROM at68_reports WHERE tax_year=? ORDER BY id DESC LIMIT 1', (tax_year(year),))
        return rows[0] if rows else None

    def export_zip(self, year):
        row = self.latest(year)
        if not row:
            return None
        summary = json.loads(row['summary_json'])
        e1kv = self._csv(self._e1kv_summary(summary), ['tax_year','category','amount_eur','tax_rate_parameter','status'])
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
            prefix = f'steuer-at-{row["tax_year"]}'
            archive.writestr(prefix + '-summary.json', row['summary_json'])
            archive.writestr(prefix + '-realized.csv', row['realized_csv'])
            archive.writestr(prefix + '-inventory.csv', row['inventory_csv'])
            archive.writestr(prefix + '-cashflow.csv', row['cashflow_csv'])
            archive.writestr(prefix + '-audit.csv', row['audit_csv'])
            archive.writestr(prefix + '-e1kv-arbeitsblatt.csv', e1kv)
            archive.writestr(prefix + '-manifest.json', json.dumps({'report_id': row['id'], 'tax_year': row['tax_year'], 'report_sha256': summary.get('content_sha256'), 'source_sha256': summary.get('source_sha256'), 'disclaimer': DISCLAIMER}, ensure_ascii=False, indent=2))
        return stream.getvalue()


_TEMPLATE = '''
<h1>Steuerinfo Österreich – v68</h1>
<p class="lead">Realhandel-Jahresarbeitsmappe für Kraken: Rohdaten, Ledger-Abstimmung, historische EUR/USD-Bewertung, Anschaffungsbestand, Veräußerungsergebnisse, Prüffälle und E1kv-Arbeitswerte.</p>
<div class="card"><form method="post"><label>Steuerjahr<input name="year" type="number" min="2009" value="{{year}}"></label><label>Kraken-Daten<select name="refresh"><option value="yes">aktualisieren</option><option value="no">nur vorhandene Daten rechnen</option></select></label><button>Steuerbericht erstellen</button></form></div>
{% if error %}<div class="card error">{{error}}</div>{% endif %}
{% if report %}<div class="card"><h2>{{report.summary.status}}</h2><p>{{report.summary.disclaimer}}</p><div class="grid"><div><b>Positive Ergebnisse</b><br>{{report.summary.realized_positive_eur}} EUR</div><div><b>Negative Ergebnisse</b><br>{{report.summary.realized_negative_eur}} EUR</div><div><b>Netto</b><br>{{report.summary.net_realized_eur}} EUR</div><div><b>Steuerwert</b><br>{{report.summary.estimated_tax_eur}} EUR</div><div><b>Prüffälle</b><br>{{report.summary.review_count}}</div><div><b>Report-Hash</b><br><small>{{report.summary.content_sha256}}</small></div></div></div>
{% if report.warnings %}<div class="card warning"><h2>Prüffälle</h2><ul>{% for x in report.warnings %}<li>{{x}}</li>{% endfor %}</ul></div>{% endif %}
<div class="card"><h2>Ausgaben</h2><p><a class="button" href="/tax-info-v68.zip?year={{year}}">Komplettpaket ZIP</a> <a class="button" href="/tax-info-v68.csv?year={{year}}">Realisierte Geschäfte CSV</a></p><p>Das ZIP enthält Summary, realisierte Geschäfte, offenen Bestand, Cashflow/Ledger, Prüfliste, E1kv-Arbeitsblatt und Manifest/Hashes.</p></div>
<div class="card"><h2>E1kv-Arbeitsblatt</h2><div class="tablewrap"><table><tr><th>Kategorie</th><th>EUR</th><th>Status</th></tr>{% for x in report.e1kv_summary %}<tr><td>{{x.category}}</td><td>{{x.amount_eur}}</td><td>{{x.status}}</td></tr>{% endfor %}</table></div></div>
<div class="card"><h2>Realisierte Geschäfte und Anschaffungen</h2><div class="tablewrap"><table><tr><th>Datum</th><th>Paar</th><th>Seite</th><th>Menge</th><th>Erlös</th><th>Anschaffung</th><th>Ergebnis</th><th>Prüfung</th></tr>{% for x in report.realized %}<tr><td>{{x.date}}</td><td>{{x.pair}}</td><td>{{x.side}}</td><td>{{x.quantity}}</td><td>{{x.proceeds_eur}}</td><td>{{x.acquisition_basis_eur}}</td><td>{{x.gain_loss_eur}}</td><td>{{x.review_required}}</td></tr>{% endfor %}</table></div></div>
{% else %}{% if latest %}<div class="card"><h2>Letzter Bericht</h2><p>{{latest.status}} · {{latest.trade_count}} Trades · {{latest.review_count}} Prüffälle · {{latest.content_sha256}}</p><a class="button" href="/tax-info-v68.zip?year={{year}}">ZIP exportieren</a></div>{% endif %}{% endif %}
<div class="card"><small>{{'Arbeits- und Prüfhilfe für die österreichische Einkommensteuer. Keine Steuer- oder Rechtsberatung und kein Ersatz für die Prüfung durch Steuerberatung bzw. Finanzverwaltung. Die steuerliche Einordnung einzelner Produkte, Transaktionen, Verluste und Anschaffungszeitpunkte muss anhand der vollständigen Unterlagen geprüft werden.'}}</small></div>
'''
