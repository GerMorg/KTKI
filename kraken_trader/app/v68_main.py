"""v68 runtime wrapper.

Builds on the stable v67 runtime and replaces the old tax view with the
reproducible Austrian Real-Kraken tax ledger. The v67 research/ticker and
Paper-payload fixes remain untouched and therefore stay part of the runtime.
"""

from flask import request, Response

import v67_main as base
from at_income_tax_v68 import AustrianTaxV68, tax_year, _TEMPLATE

app = base.app
service = AustrianTaxV68(base.db)


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
    return base.legacy.page(_TEMPLATE, year=year, report=report, latest=latest, error=error)


def _tax_zip():
    year = tax_year(request.args.get('year'))
    data = service.export_zip(year)
    if data is None:
        return Response('Kein v68-Steuerbericht vorhanden', 404, mimetype='text/plain')
    return Response(
        data,
        mimetype='application/zip',
        headers={'Content-Disposition': f'attachment; filename=steuer-at-{year}-v68.zip'},
    )


def _tax_csv():
    year = tax_year(request.args.get('year'))
    row = service.latest(year)
    if row is None:
        return Response('Kein v68-Steuerbericht vorhanden', 404, mimetype='text/plain')
    return Response(
        row['realized_csv'],
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename=steuer-at-{year}-realized-v68.csv'},
    )


# Replace both GET and POST handlers registered by the legacy v63 blueprint.
app.view_functions['at_tax_v63.tax_info'] = _tax_page
app.view_functions['at_tax_v63.tax_info_generate'] = _tax_page
app.view_functions['at_tax_v63.tax_csv_export'] = _tax_csv
app.add_url_rule('/tax-info-v68.zip', endpoint='tax_v68_zip_wrapper', view_func=_tax_zip, methods=['GET'])
app.add_url_rule('/tax-info-v68.csv', endpoint='tax_v68_csv_wrapper', view_func=_tax_csv, methods=['GET'])
