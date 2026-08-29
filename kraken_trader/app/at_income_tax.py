import csv
import io
import json
import os
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from flask import Blueprint, Response, request

from db import now
from kraken import KrakenClient

RATE = Decimal('0.275')
DISCLAIMER = (
    'Unverbindliche Ausfüll- und Prüfhilfe, keine Steuer- oder Rechtsberatung. '
    'Die endgültige steuerliche Beurteilung muss anhand der vollständigen Unterlagen erfolgen.'
)


def D(value):
    try:
        return Decimal(str(value if value not in (None, '') else 0))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal(0)


def money(value):
    return str(D(value).quantize(Decimal('0.01')))


def tax_year(value):
    try:
        year = int(value)
    except (TypeError, ValueError):
        year = datetime.now(timezone.utc).year - 1
    return max(2009, min(datetime.now(timezone.utc).year, year))


class AustrianTaxInfo:
    def __init__(self, db):
        self.db = db
        self.ensure()

    def ensure(self):
        with self.db.con() as c:
            c.executescript('''
                CREATE TABLE IF NOT EXISTS at_tax_reports(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    tax_year INTEGER NOT NULL,
                    source TEXT NOT NULL,
                    status TEXT NOT NULL,
                    row_count INTEGER NOT NULL,
                    taxable_gain_eur TEXT NOT NULL,
                    deductible_loss_eur TEXT NOT NULL,
                    estimated_tax_eur TEXT NOT NULL,
                    warnings_json TEXT NOT NULL,
                    details_json TEXT NOT NULL,
                    csv_text TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_at_tax_reports_year ON at_tax_reports(tax_year,id);
                CREATE TABLE IF NOT EXISTS real_tax_trades(
                    txid TEXT PRIMARY KEY,
                    trade_time REAL NOT NULL,
                    pair TEXT NOT NULL,
                    side TEXT NOT NULL,
                    price TEXT NOT NULL,
                    volume TEXT NOT NULL,
                    cost TEXT NOT NULL,
                    fee TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    imported_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_real_tax_trades_time ON real_tax_trades(trade_time,txid);
            ''')

    def _client(self):
        try:
            path = os.getenv('APP_OPTIONS', '/data/options.json')
            with open(path, encoding='utf-8') as handle:
                options = json.load(handle)
            key = options.get('kraken_api_key', '')
            secret = options.get('kraken_api_secret', '')
            if key and secret:
                return KrakenClient(key, secret)
        except Exception:
            pass
        return None

    @staticmethod
    def _trade_time(value):
        try:
            return datetime.fromtimestamp(float(value), tz=timezone.utc)
        except (TypeError, ValueError, OSError):
            return None

    @staticmethod
    def _eur_pair(pair):
        compact = str(pair or '').upper().replace('/', '')
        compact = compact.replace('XXBT', 'XBT').replace('XETH', 'ETH').replace('Z', '')
        return compact.endswith('EUR')

    @staticmethod
    def _base_asset(pair):
        compact = str(pair or '').upper().replace('/', '')
        compact = compact.replace('XXBT', 'XBT').replace('XETH', 'ETH')
        if compact.endswith('EUR'):
            return compact[:-3].lstrip('XZ') or 'UNKNOWN'
        if compact.endswith('USD'):
            return compact[:-3].lstrip('XZ') or 'UNKNOWN'
        return compact

    def refresh_real_trades(self):
        client = self._client()
        if not client:
            return {'status': 'NO_API_CREDENTIALS', 'imported': 0}
        imported = 0
        offset = 0
        try:
            while True:
                result = client.call('/0/private/TradesHistory', {'type': 'all', 'ofs': offset}, private=True)
                trades = result.get('trades') or {}
                if not trades:
                    break
                with self.db.con() as c:
                    for txid, item in trades.items():
                        c.execute(
                            '''INSERT OR REPLACE INTO real_tax_trades(
                               txid,trade_time,pair,side,price,volume,cost,fee,payload_json,imported_at)
                               VALUES(?,?,?,?,?,?,?,?,?,?)''',
                            (txid, float(item.get('time') or 0), str(item.get('pair') or ''),
                             str(item.get('type') or '').lower(), str(item.get('price') or 0),
                             str(item.get('vol') or 0), str(item.get('cost') or 0),
                             str(item.get('fee') or 0), json.dumps(item, sort_keys=True), now())
                        )
                        imported += 1
                if len(trades) < 50:
                    break
                offset += len(trades)
            self.db.audit('AT_TAX_REAL_TRADES_REFRESH', json.dumps({'imported': imported}))
            return {'status': 'VALID', 'imported': imported}
        except Exception as exc:
            self.db.audit('AT_TAX_REAL_TRADES_REFRESH_FAILED', type(exc).__name__, 'warning')
            return {'status': 'ERROR', 'imported': imported, 'error': type(exc).__name__}

    def _paper_rows(self, year):
        inventory = {}
        rows = []
        warnings = []
        trades = self.db.rows(
            "SELECT t.*,u.asset_class,u.category FROM paper_trades t "
            "LEFT JOIN market_universe u ON u.symbol=t.symbol "
            "WHERE substr(t.created_at,1,4)<=? ORDER BY t.created_at,t.id",
            (str(year),),
        )
        for trade in trades:
            symbol = trade['symbol']
            side = str(trade['side']).upper()
            qty = D(trade['quantity'])
            state = inventory.setdefault(symbol, [Decimal(0), Decimal(0)])
            if qty <= 0 or side not in ('BUY', 'SELL'):
                warnings.append(f"Paper-Trade {trade['id']}: ungültige Daten")
                continue
            if side == 'BUY':
                state[0] += qty
                state[1] += D(trade['net_eur'])
                continue
            gap = qty > state[0]
            basis = Decimal(0) if gap else state[1] / state[0] * qty
            if not gap:
                state[0] -= qty
                state[1] -= basis
            if str(trade['created_at'])[:4] != str(year):
                continue
            details = {}
            try:
                details = json.loads(trade.get('decision_json') or '{}')
            except Exception:
                pass
            ac = trade.get('asset_class') or details.get('asset_class') or 'unknown'
            cat = trade.get('category') or details.get('category')
            crypto = ac in ('currency', 'crypto', 'crypto_spot') or cat == 'crypto_spot'
            review = gap or not crypto
            proceeds = D(trade['gross_eur']) - D(trade['fee_eur'])
            gain = proceeds - basis
            if review:
                warnings.append(f"Paper-Trade {trade['id']}: Bestand oder Anlageklasse prüfen")
            rows.append({
                'trade_id': str(trade['id']), 'date': trade['created_at'], 'symbol': symbol,
                'source': 'paper', 'asset_class': ac, 'quantity': money(qty),
                'proceeds_eur': money(proceeds), 'acquisition_cost_eur': money(basis),
                'gain_loss_eur': money(gain), 'tax_rate': '27,5 %' if crypto else '',
                'estimated_tax_eur': money(max(Decimal(0), gain) * RATE) if crypto and not review else '',
                'review_required': 'yes' if review else 'no',
                'classification_note': 'Krypto-Neuvermögen, gleitender Durchschnitt' if crypto else 'Anlageklasse prüfen',
            })
        return rows, warnings

    def _real_rows(self, year):
        inventory = {}
        rows = []
        warnings = []
        trades = self.db.rows('SELECT * FROM real_tax_trades ORDER BY trade_time,txid')
        for trade in trades:
            pair = trade['pair']
            side = str(trade['side']).lower()
            qty = D(trade['volume'])
            cost = D(trade['cost'])
            fee = D(trade['fee'])
            moment = self._trade_time(trade['trade_time'])
            if qty <= 0 or side not in ('buy', 'sell') or moment is None:
                warnings.append(f"Real-Trade {trade['txid']}: ungültige Daten")
                continue
            eur_pair = self._eur_pair(pair)
            asset = self._base_asset(pair)
            state = inventory.setdefault(asset, [Decimal(0), Decimal(0)])
            if side == 'buy':
                if eur_pair:
                    state[0] += qty
                    state[1] += cost + fee
                else:
                    warnings.append(f"Real-Trade {trade['txid']}: nicht-EUR-Paar benötigt FX-Bewertung")
                continue
            gap = qty > state[0]
            basis = Decimal(0) if gap or not eur_pair else state[1] / state[0] * qty
            if not gap and eur_pair:
                state[0] -= qty
                state[1] -= basis
            if moment.year != year:
                continue
            proceeds = cost - fee if eur_pair else Decimal(0)
            gain = proceeds - basis if eur_pair and not gap else Decimal(0)
            review = (not eur_pair) or gap
            if review:
                warnings.append(
                    f"Real-Trade {trade['txid']}: {'nicht-EUR-Paar' if not eur_pair else 'Anschaffungsbestand nicht vollständig vorhanden'}; fachlich prüfen"
                )
            rows.append({
                'trade_id': trade['txid'], 'date': moment.isoformat(), 'symbol': pair,
                'source': 'real', 'asset_class': 'unknown', 'quantity': money(qty),
                'proceeds_eur': money(proceeds), 'acquisition_cost_eur': money(basis),
                'gain_loss_eur': money(gain), 'tax_rate': '27,5 %' if not review else '',
                'estimated_tax_eur': money(max(Decimal(0), gain) * RATE) if not review else '',
                'review_required': 'yes' if review else 'no',
                'classification_note': 'Realhandel, EUR-Handel, gleitender Durchschnitt' if not review else 'FX/Bestand/Anlageklasse prüfen',
            })
        return rows, warnings

    def analyze(self, year, source='real'):
        year = tax_year(year)
        source = source if source in ('real', 'paper', 'both') else 'real'
        refresh = {'status': 'NOT_REQUESTED', 'imported': 0}
        if source in ('real', 'both'):
            refresh = self.refresh_real_trades()
        rows = []
        warnings = []
        if source in ('real', 'both'):
            real_rows, real_warnings = self._real_rows(year)
            rows.extend(real_rows)
            warnings.extend(real_warnings)
        if source in ('paper', 'both'):
            paper_rows, paper_warnings = self._paper_rows(year)
            rows.extend(paper_rows)
            warnings.extend(paper_warnings)
        if not rows:
            warnings.append('Keine steuerlich auswertbaren Verkäufe im ausgewählten Steuerjahr gefunden')
        if source in ('real', 'both') and refresh['status'] != 'VALID':
            warnings.append('Realhandelsdaten konnten nicht vollständig aus Kraken importiert werden; Bericht ist nur als Prüfhilfe zu verwenden')
        fields = [
            'trade_id','date','symbol','source','asset_class','quantity','proceeds_eur',
            'acquisition_cost_eur','gain_loss_eur','tax_rate','estimated_tax_eur',
            'review_required','classification_note'
        ]
        buffer = io.StringIO(newline='')
        writer = csv.DictWriter(buffer, fields, delimiter=';')
        writer.writeheader()
        writer.writerows(rows)
        valid_rows = [row for row in rows if row['review_required'] == 'no']
        gains = sum((max(Decimal(0), D(row['gain_loss_eur'])) for row in valid_rows), Decimal(0))
        losses = sum((min(Decimal(0), D(row['gain_loss_eur'])) for row in valid_rows), Decimal(0))
        estimate = max(Decimal(0), gains + losses) * RATE
        status = 'REVIEW_REQUIRED' if warnings or any(row['review_required'] == 'yes' for row in rows) else 'READY_FOR_REVIEW'
        result = {
            'year': year, 'source': source, 'status': status, 'rows': rows,
            'warnings': sorted(set(warnings)), 'taxable_gain_eur': money(gains),
            'deductible_loss_eur': money(losses), 'estimated_tax_eur': money(estimate),
            'disclaimer': DISCLAIMER, 'refresh': refresh, 'rate': '27,5 %', 'csv': buffer.getvalue(),
        }
        with self.db.con() as c:
            c.execute(
                '''INSERT INTO at_tax_reports(created_at,tax_year,source,status,row_count,
                   taxable_gain_eur,deductible_loss_eur,estimated_tax_eur,warnings_json,details_json,csv_text)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?)''',
                (now(), year, source, status, len(rows), result['taxable_gain_eur'], result['deductible_loss_eur'],
                 result['estimated_tax_eur'], json.dumps(result['warnings'], ensure_ascii=False),
                 json.dumps(result, ensure_ascii=False, sort_keys=True), result['csv'])
            )
        self.db.audit('AT_TAX_INFO_REPORT', json.dumps({'year': year, 'source': source, 'status': status, 'rows': len(rows)}))
        return result

    def latest(self, year):
        report = self.db.rows(
            'SELECT * FROM at_tax_reports WHERE tax_year=? ORDER BY id DESC LIMIT 1',
            (tax_year(year),),
        )
        return report[0] if report else None


def create_tax_blueprint(db, page):
    service = AustrianTaxInfo(db)
    bp = Blueprint('at_tax', __name__)

    @bp.route('/tax-info', methods=['GET', 'POST'])
    def view():
        year = tax_year(request.values.get('year'))
        source = request.values.get('source', 'real')
        report = None
        if request.method == 'POST':
            report = service.analyze(year, source)
        return page('''
            <h1>Steuerinfo Österreich</h1>
            <p class=lead>Steuerliche Arbeits- und Prüfhilfe mit <b>Realhandel als Standardquelle</b>. Der Paper-Handel kann separat oder zusätzlich ausgewertet werden.</p>
            <div class=card>
              <form method=post>
                <label>Steuerjahr<input name=year type=number min=2009 value="{{year}}"></label>
                <label>Datenquelle<select name=source>
                  <option value=real {% if source=='real' %}selected{% endif %}>Realhandel – Kraken</option>
                  <option value=paper {% if source=='paper' %}selected{% endif %}>Paper-Handel</option>
                  <option value=both {% if source=='both' %}selected{% endif %}>Realhandel + Paper</option>
                </select></label>
                <button>Steuerbericht erstellen / Realhandel aktualisieren</button>
              </form>
              <p class=muted>Bei Realhandel werden Kraken-Trade-Historie und vorhandene Accountdaten verwendet, sofern die Private-API-Zugangsdaten verfügbar sind.</p>
            </div>
            {% if report %}
              <div class=card>
                <h2>{{report.status}}</h2>
                <p>{{report.disclaimer}}</p>
                <p>Quelle: <b>{{report.source}}</b> · Steuersatz: <b>{{report.rate}}</b></p>
                <p>Positive Einkünfte {{report.taxable_gain_eur}} EUR · Verluste {{report.deductible_loss_eur}} EUR · rechnerische Steuer {{report.estimated_tax_eur}} EUR</p>
                <p>Real-Import: {{report.refresh.status}} · {{report.refresh.imported}} Trades</p>
              </div>
              {% if report.warnings %}<div class=card><b>Prüfhinweise</b><ul>{% for x in report.warnings %}<li>{{x}}</li>{% endfor %}</ul></div>{% endif %}
              <p><a class=button href="{{url_for('at_tax.csv_export',year=year)}}">CSV exportieren</a></p>
              <div class=tablewrap><table><tr><th>Datum</th><th>Quelle</th><th>Symbol</th><th>Erlös</th><th>Anschaffung</th><th>Ergebnis</th><th>Prüfung</th></tr>{% for x in report.rows %}<tr><td>{{x.date}}</td><td>{{x.source}}</td><td>{{x.symbol}}</td><td>{{x.proceeds_eur}}</td><td>{{x.acquisition_cost_eur}}</td><td>{{x.gain_loss_eur}}</td><td>{{x.review_required}}</td></tr>{% endfor %}</table></div>
            {% endif %}
        ''', year=year, source=source, report=report)

    @bp.get('/tax-info.csv')
    def csv_export():
        report = service.latest(request.args.get('year'))
        if not report:
            return Response('Kein Bericht vorhanden', 404, mimetype='text/plain')
        return Response(
            report['csv_text'],
            mimetype='text/csv',
            headers={'Content-Disposition': f"attachment; filename=steuerinfo-at-{report['tax_year']}.csv"},
        )

    return bp
