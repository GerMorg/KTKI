"""v68 runtime wrapper: stable v67 runtime + tax ledger output."""
from flask import Response, request

import v67_main as base
from at_income_tax_v68 import AustrianTaxV68, tax_year

app = base.app
service = AustrianTaxV68(base.db)

_TAX_PAGE = '''
<h1>Steuerinfo Österreich – v68</h1>
<p class="lead">Realhandel-Jahresarbeitsmappe für Kraken: Rohdaten, Ledger-Abstimmung, historische EUR/USD-Bewertung, Anschaffungsbestand, Veräußerungsergebnisse, Prüffälle und E1kv-Arbeitswerte.</p>
<div class="card"><form method="post"><label>Steuerjahr<input name="year" type="number" min="2009" value="{{year}}"></label><label>Kraken-Daten<select name="refresh"><option value="yes">aktualisieren</option><option value="no">nur vorhandene Daten rechnen</option></select></label><button>Steuerbericht erstellen</button></form></div>
{% if error %}<div class="card error">{{error}}</div>{% endif %}
{% if report %}<div class="card"><h2>{{report.summary.status}}</h2><p>{{report.summary.disclaimer}}</p><div class="grid"><div><b>Positive Ergebnisse</b><br>{{report.summary.realized_positive_eur}} EUR</div><div><b>Negative Ergebnisse</b><br>{{report.summary.realized_negative_eur}} EUR</div><div><b>Netto</b><br>{{report.summary.net_realized_eur}} EUR</div><div><b>Steuerwert</b><br>{{report.summary.estimated_tax_eur}} EUR</div><div><b>Prüffälle</b><br>{{report.summary.review_count}}</div><div><b>Report-Hash</b><br><small>{{report.summary.content_sha256}}</small></div></div></div>
{% if report.warnings %}<div class="card warning"><h2>Prüffälle</h2><ul>{% for x in report.warnings %}<li>{{x}}</li>{% endfor %}</ul></div>{% endif %}
<div class="card"><h2>Ausgaben</h2><p><a class="button" href="/tax-info-v68.zip?year={{year}}">Komplettpaket ZIP</a> <a class="button" href="/tax-info-v68.csv?year={{year}}">Realisierte Geschäfte CSV</a></p><p>Das ZIP enthält Summary, realisierte Geschäfte, offenen Bestand, Cashflow/Ledger, Prüfliste, E1kv-Arbeitsblatt und Manifest mit Hashes.</p></div>
<div class="card"><h2>E1kv-Arbeitsblatt</h2><div class="tablewrap"><table><tr><th>Kategorie</th><th>EUR</th><th>Status</th></tr>{% for x in report.e1kv_summary %}<tr><td>{{x.category}}</td><td>{{x.amount_eur}}</td><td>{{x.status}}</td></tr>{% endfor %}</table></div></div>
<div class="card"><h2>Realisierte Geschäfte und Anschaffungen</h2><div class="tablewrap"><table><tr><th>Datum</th><th>Paar</th><th>Seite</th><th>Menge</th><th>Erlös</th><th>Anschaffung</th><th>Ergebnis</th><th>Prüfung</th></tr>{% for x in report.realized %}<tr><td>{{x.date}}</td><td>{{x.pair}}</td><td>{{x.side}}</td><td>{{x.quantity}}</td><td>{{x.proceeds_eur}}</td><td>{{x.acquisition_basis_eur}}</td><td>{{x.gain_loss_eur}}</td><td>{{x.review_required}}</td></tr>{% endfor %}</table></div></div>
{% else %}{% if latest %}<div class="card"><h2>Letzter Bericht</h2><p>{{latest.status}} · {{latest.trade_count}} Trades · {{latest.review_count}} Prüffälle · {{latest.content_sha256}}</p><a class="button" href="/tax-info-v68.zip?year={{year}}">ZIP exportieren</a></div>{% endif %}{% endif %}
<div class="card"><small>Arbeits- und Prüfhilfe; keine Steuer- oder Rechtsberatung. Die steuerliche Einordnung einzelner Produkte, Transaktionen, Verluste und Anschaffungszeitpunkte muss anhand der vollständigen Unterlagen geprüft werden.</small></div>
'''


def _tax_page():
    year = tax_year(request.values.get('year'))
    report = None
    error = None
    if request.method == 'POST':
        try:
            report = service.generate(year, refresh=request.form.get('refresh', 'yes') == 'yes')
        except Exception as exc:
            base.db.audit('AT68_TAX_GUI_FAILED', type(exc).__name__ + ': ' + str(exc)[:300], 'error')
            error = type(exc).__name__ + ': ' + str(exc)[:300]
    latest = service.latest(year) if report is None else None
    return base.legacy.page(_TAX_PAGE, year=year, report=report, latest=latest, error=error)


def _tax_zip():
    year = tax_year(request.args.get('year'))
    data = service.export_zip(year)
    if data is None:
        return Response('Kein v68-Steuerbericht vorhanden', 404, mimetype='text/plain')
    return Response(data, mimetype='application/zip', headers={'Content-Disposition': f'attachment; filename=steuer-at-{year}-v68.zip'})


def _tax_csv():
    year = tax_year(request.args.get('year'))
    row = service.latest(year)
    if row is None:
        return Response('Kein v68-Steuerbericht vorhanden', 404, mimetype='text/plain')
    return Response(row['realized_csv'], mimetype='text/csv', headers={'Content-Disposition': f'attachment; filename=steuer-at-{year}-realized-v68.csv'})


# Replace legacy tax routes without changing the stable v67 process/automation code.
app.view_functions['at_tax_v63.tax_info'] = _tax_page
app.view_functions['at_tax_v63.tax_info_generate'] = _tax_page
app.view_functions['at_tax_v63.tax_csv_export'] = _tax_csv
app.add_url_rule('/tax-info-v68.zip', endpoint='tax_v68_zip_wrapper', view_func=_tax_zip, methods=['GET'])
app.add_url_rule('/tax-info-v68.csv', endpoint='tax_v68_csv_wrapper', view_func=_tax_csv, methods=['GET'])
