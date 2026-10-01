"""KTKI v102 runtime.

One active runtime owns the current GUI, canonical decision pipeline, shared execution intent and unified Real-Handel status.
"""
VERSION = "0.1.0-dev.102"

import json
import os
from flask import Response, jsonify, redirect, request, url_for
import core_runtime as base
from automation_v67 import AutomationControllerV67
from controlled_learning import ControlledLearning
from news_learning import NewsLearning
from at_income_tax_v68 import AustrianTaxV68, tax_year
from decision_pipeline_v98 import CanonicalDecisionPlannerV98
from decision_engine_v98 import DecisionEngineV98
from v98_paper_engine import PaperEngineV98
from v98_real_allocator import RealPortfolioAllocatorV98
from decision_runtime_v98 import DecisionRuntimeV98
from portfolio_sync import build_rows,normalize_asset
from real_state_v102 import build_real_state

app=base.app
legacy=base.legacy
options=getattr(base,"options",{})

planner=CanonicalDecisionPlannerV98(legacy.db)
runtime=DecisionRuntimeV98(legacy.db, refresh_market=legacy.refresh_allowed_prices, evaluate_forecasts=legacy.forecasts.evaluate_due)

def _load_options():
    path=os.environ.get("APP_OPTIONS","/data/options.json")
    try:
        with open(path,encoding="utf-8") as fh:return json.load(fh) or {}
    except Exception:
        return {}

def _sync_settings():
    opts=_load_options()
    defaults=planner.settings()
    for key,default in defaults.items():
        value=opts.get(key,default)
        normalized=("true" if value else "false") if isinstance(value,bool) else str(value)
        legacy.db.set_setting(key,normalized)
    return opts

options=_sync_settings()

def _sync_runtime_options(opts):
    # The HA UI exposes a small stable set of operational switches; the legacy
    # subsystems keep their internal keys so older database state remains usable.
    automation=bool(opts.get("automation_enabled",True))
    interval=max(1,int(opts.get("automation_interval_minutes",15)))
    real_enabled=bool(opts.get("real_trading_enabled",False))
    real_execute=bool(opts.get("real_execute_enabled",False))
    legacy.db.set_setting("automation_master_enabled","true" if automation else "false")
    for subsystem,cadence in (("analysis",60),("news",30),("learning",60),("paper",15)):
        legacy.db.set_setting("automation_"+subsystem+"_enabled","true" if automation else "false")
        legacy.db.set_setting("automation_"+subsystem+"_interval_minutes",str(cadence))
    legacy.db.set_setting("automation_real_enabled","true" if automation and real_enabled else "false")
    legacy.db.set_setting("automation_real_execute_enabled","true" if automation and real_execute else "false")
    legacy.db.set_setting("automation_tick_minutes",str(min(60,interval)))
    legacy.db.set_setting("automation_learning_auto_approve_enabled","false")
    legacy.db.set_setting("real_trading_enabled","true" if real_enabled else "false")
    legacy.db.set_setting("real_kill_switch","true" if bool(opts.get("real_kill_switch",True)) else "false")
    legacy.db.set_setting("real_allowed_symbols",str(opts.get("real_allowed_symbols","") or ""))
    # Canonical risk settings are shared by Paper and Real.
    for key in ("decision_max_position_pct","decision_cash_reserve_pct","decision_min_trade_eur","decision_max_trade_eur"):
        if key in opts:
            legacy.db.set_setting(key,str(opts[key]))
    return {
        "automation_enabled":automation,"automation_interval_minutes":interval,
        "real_trading_enabled":real_enabled,"real_execute_enabled":real_execute
    }

runtime_options=_sync_runtime_options(options)

try:
    base.controller.stop()
except Exception:
    pass

real_allocator=RealPortfolioAllocatorV98(legacy.db,legacy.real_trade_engine,runtime=runtime)

class RealAllocatorV99:
    """Delegate canonical trading while keeping the persisted real portfolio in sync."""
    def __init__(self,delegate):
        self.delegate=delegate
    def _sync_portfolio(self):
        try:
            client=legacy.real_trade_engine.client
            balances=client.balance()
            assets=client.assets()
            pairs=client.pairs()
            held_names={normalize_asset(code,assets) for code,value in balances.items() if str(value) not in ("0","0.0","0.00")}
            relevant=[]
            for pair_id,pair in pairs.items():
                base_name=normalize_asset(pair.get("base",""),assets)
                quote_name=normalize_asset(pair.get("quote",""),assets)
                if base_name in held_names and quote_name=="EUR":
                    relevant.append(pair.get("altname",pair_id))
            tickers=client.ticker(relevant) if relevant else {}
            rows,total,quality=build_rows(balances,set(),assets,pairs,tickers)
            legacy.db.replace_balances(balances)
            sid=legacy.db.store_portfolio(rows,total,quality)
            return {"snapshot_id":sid,"assets":len(rows),"held_assets":sum(1 for row in rows if row["classification"]=="HELD"),"total_eur":total,"quality":quality}
        except Exception as exc:
            detail=type(exc).__name__+":"+str(exc)[:300]
            legacy.db.audit("REAL_PORTFOLIO_AUTO_SYNC_FAILED",detail,"warning")
            return {"status":"FAILED","error":detail}
    def run(self,*args,**kwargs):
        result=self.delegate.run(*args,**kwargs)
        sync=self._sync_portfolio()
        if isinstance(result,dict):
            result=dict(result)
            result["portfolio_sync"]=sync
        return result
    def __getattr__(self,name):
        return getattr(self.delegate,name)

legacy.real_allocator=RealAllocatorV99(real_allocator)
real_allocator=legacy.real_allocator

def run_paper_cycle():
    engine=PaperEngineV98(
        legacy.db,
        start_eur=legacy.db.value("paper_start_eur","1000"),
        fee_bps=float(planner.settings()["decision_fee_bps"]),
        slippage_bps=float(planner.settings()["decision_slippage_bps"]),
        max_position_pct=float(planner.settings()["decision_max_position_pct"]),
        trade_eur=float(planner.settings()["decision_min_trade_eur"]),
        runtime=runtime,
    )
    return engine.run()

controller=AutomationControllerV67(
    legacy.db,
    legacy.pipeline,
    legacy.news_prefilter,
    ControlledLearning(legacy.db),
    NewsLearning(legacy.db),
    run_paper_cycle,
    real_allocator,
)
controller.start_background()
base.controller=controller
legacy.controller=controller

from market_feed_v102 import PublicMarketServiceV102

# Public Kraken market data is independent from private credentials.
market_service=PublicMarketServiceV102(
    legacy.db, legacy.client, legacy.universe, legacy.stream,
    max_symbols=int(legacy.db.value("v102_market_symbol_limit","30"))
)
legacy.stream.enabled=True
legacy.private_stream.enabled=bool(
    getattr(legacy.client,"key","") and getattr(legacy.client,"secret","")
)
runtime.refresh_market=market_service.refresh_for_process
market_service.start_background()
if legacy.private_stream.enabled:
    legacy.private_stream.start()

legacy.NAV_ITEMS=[
    ("/","Übersicht"),
    ("/markt","Markt & Daten"),
    ("/analyse","Analyse"),
    ("/portfolio","Portfolio"),
    ("/handel","Handel"),
    ("/lernen","Lernen"),
    ("/real-trading","Realhandel"),
    ("/system","System"),
]

tax_service=AustrianTaxV68(legacy.db)

def _tax_page():
    year=tax_year(request.values.get("year"))
    report=None
    latest=None
    error=None
    if request.method=="POST":
        try:
            report=tax_service.generate(year,refresh=request.form.get("refresh","yes")=="yes")
        except Exception as exc:
            legacy.db.audit("V102_TAX_GUI_FAILED",type(exc).__name__+":"+str(exc)[:300],"error")
            error=type(exc).__name__+":"+str(exc)[:300]
    else:
        latest=tax_service.latest(year)
    return legacy.page(
        '''<span class="eyebrow">Österreich · Einkommensteuer</span>
<h1>Einkommensteuer / KESt – Trading</h1>
<p class="lead">Nachweis- und Prüfhilfe für reale Kraken-Geschäfte mit Anschaffungsbestand, EUR/USD-Bewertung, Ledger-Abgleich und E1kv-Arbeitswerten.</p>
<div class="card"><h2>Rechts-/Steuerrahmen</h2>
<p>Für die meisten Einkünfte aus Kapitalvermögen gilt in Österreich der besondere Steuersatz von 27,5 %. Kryptowährungen fallen grundsätzlich ebenfalls unter den besonderen Steuersatz von 27,5 %. Die Seite verwendet 27,5 % nur als Berechnungsparameter für entsprechend eingeordnete Fälle; sie ersetzt keine steuerliche Einordnung.</p>
<p>Ausländische Kapitalerträge ohne inländischen KESt-Abzug können grundsätzlich im Rahmen der Veranlagung zu erfassen sein. Bestimmte Einkünfte unterliegen statt des Sondersteuersatzes dem allgemeinen Tarif und werden deshalb hier als Prüffall behandelt.</p>
<p><a href="https://www.bmf.gv.at/themen/steuern/sparen-veranlagen/besteuerung-kapitalertraege-inland.html" target="_blank" rel="noopener">BMF: Besteuerung von Kapitalerträgen</a> ·
<a href="https://www.bmf.gv.at/themen/steuern/sparen-veranlagen/steuerliche-behandlung-von-kryptowaehrungen.html" target="_blank" rel="noopener">BMF: Kryptowährungen</a></p></div>
<div class="card"><form method="post">
<label>Steuerjahr<input name="year" type="number" min="2009" value="{{year}}"></label>
<label>Kraken-Daten<select name="refresh"><option value="yes">aktualisieren</option><option value="no">nur vorhandene Daten rechnen</option></select></label>
<button>Steuerbericht erstellen</button></form></div>
{% if error %}<div class="card error">{{error}}</div>{% endif %}
{% if report %}
<div class="grid"><div class="card"><b>Ergebnisstatus</b><div class="metric">{{report.summary.status}}</div></div>
<div class="card"><b>Positive Ergebnisse</b><div class="metric">{{report.summary.realized_positive_eur}} €</div></div>
<div class="card"><b>Negative Ergebnisse</b><div class="metric">{{report.summary.realized_negative_eur}} €</div></div>
<div class="card"><b>Rechnerischer Steuerwert</b><div class="metric">{{report.summary.estimated_tax_eur}} €</div></div></div>
{% if report.warnings %}<div class="card warning"><h2>Prüffälle</h2><ul>{% for x in report.warnings %}<li>{{x}}</li>{% endfor %}</ul></div>{% endif %}
<div class="card"><h2>Exporte</h2><p><a class="button" href="/tax-info.zip?year={{year}}">Komplettpaket ZIP</a> <a class="button" href="/tax-info.csv?year={{year}}">Realisierte Geschäfte CSV</a></p>
<p>Das Paket enthält Summary, realisierte Geschäfte, offenen Bestand, Cashflow/Ledger, Prüfliste und E1kv-Arbeitswerte.</p></div>
<div class="card"><h2>E1kv-Arbeitswerte</h2><div class="tablewrap"><table><tr><th>Kategorie</th><th>EUR</th><th>Status</th></tr>{% for x in report.e1kv_summary %}<tr><td>{{x.category}}</td><td>{{x.amount_eur}}</td><td>{{x.status}}</td></tr>{% endfor %}</table></div></div>
<div class="card"><h2>Realisierte Geschäfte</h2><div class="tablewrap"><table><tr><th>Datum</th><th>Paar</th><th>Seite</th><th>Erlös</th><th>Anschaffung</th><th>Gewinn/Verlust</th><th>Prüfung</th></tr>{% for x in report.realized %}<tr><td>{{x.date}}</td><td>{{x.pair}}</td><td>{{x.side}}</td><td>{{x.proceeds_eur}}</td><td>{{x.acquisition_basis_eur}}</td><td>{{x.gain_loss_eur}}</td><td>{{x.review_required}}</td></tr>{% endfor %}</table></div></div>
{% elif latest %}
<div class="card"><h2>Letzter Bericht</h2><p>{{latest.status}} · {{latest.trade_count}} Trades · {{latest.review_count}} Prüffälle · {{latest.content_sha256}}</p><a class="button" href="/tax-info.zip?year={{year}}">ZIP exportieren</a></div>
{% endif %}
<div class="card"><small>Arbeits- und Prüfhilfe; keine Steuer- oder Rechtsberatung. Bei fehlender Anschaffungsbasis, Fremdwährung, Sonderprodukten oder nicht eindeutig einordenbaren Einkünften bleibt der Report auf REVIEW_REQUIRED.</small></div>''',
        year=year,report=report,latest=latest,error=error
    )

for endpoint in ("at_tax_v63.tax_info","at_tax_v63.tax_info_generate"):
    if endpoint in app.view_functions:
        app.view_functions[endpoint]=_tax_page
if "at_tax_v63.tax_csv_export" in app.view_functions:
    app.view_functions["at_tax_v63.tax_csv_export"]=lambda: redirect(url_for("tax_csv",year=request.args.get("year")))

@app.post("/steuerinfo-at")
def tax_info_alias():
    return _tax_page()

@app.get("/steuerinfo-at")
def tax_info_alias_get():
    return _tax_page()

@app.get("/tax-info.zip")
def tax_zip():
    year=tax_year(request.args.get("year"))
    try:
        data=tax_service.export_zip(year)
    except Exception as exc:
        return ("Steuerbericht konnte nicht exportiert werden: "+type(exc).__name__,500)
    if not data:
        return ("Kein Steuerbericht vorhanden",404)
    return Response(data,mimetype="application/zip",headers={"Content-Disposition":f"attachment; filename=steuer-at-{year}.zip"})

@app.get("/tax-info.csv")
def tax_csv():
    row=tax_service.latest(request.args.get("year"))
    if not row:
        return ("Kein Steuerbericht vorhanden",404)
    from flask import Response
    return Response(row["realized_csv"],mimetype="text/csv",headers={"Content-Disposition":f"attachment; filename=steuer-at-{row['tax_year']}-realized.csv"})

def _latest_plan():
    rows=legacy.db.rows("SELECT * FROM decision_plan_runs_v98 ORDER BY id DESC LIMIT 1")
    if not rows:return None
    row=dict(rows[0])
    try:row["settings"]=json.loads(row.get("settings_json") or "{}")
    except Exception:row["settings"]={}
    return row

def _decision_rows(limit=50):
    cols={x["name"] for x in legacy.db.rows("PRAGMA table_info(decision_snapshots)")}
    select="*" if "action_type" in cols else "*"
    rows=legacy.db.rows(f"SELECT {select} FROM decision_snapshots ORDER BY id DESC LIMIT ?",(max(1,min(200,int(limit))),))
    return rows

def _health_snapshot():
    result={}
    for family in ("crypto_spot","xstocks","forex"):
        row=legacy.db.rows("SELECT details_json FROM model_health_snapshots WHERE family=? ORDER BY id DESC LIMIT 1",(family,))
        if row:
            try:result[family]=json.loads(row[0]["details_json"]);continue
            except Exception:pass
        result[family]={}
    return result

def _dashboard():
    plan=_latest_plan()
    decisions=_decision_rows(15)
    health=_health_snapshot()
    public=legacy.stream.status()
    private=legacy.private_stream.status()
    news_count=legacy.db.rows("SELECT COUNT(*) AS n FROM news_items")
    news_links=legacy.db.rows("SELECT COUNT(*) AS n FROM news_market_links")
    auto=controller.settings()
    real_state=build_real_state(legacy.db,controller)
    real_ready=real_state["automatic_execution_ready"]
    return legacy.page(
        '''<section class="hero"><div><span class="eyebrow">KTKI v102</span><h1>Kraken Trader</h1>
<p class="lead">Ein gemeinsamer Daten-, Lern-, Bewertungs-, Ziel- und Orderprozess für Paper und Real.</p></div>
<strong class="hero-state">{{real_state["status_label"]}}</strong></section>
<div class="process-strip">{% for x in ["Kraken","News","Analyse","Lernen","Edge","Target","Order"] %}<div class="process-node"><span>{{loop.index}}</span><b>{{x}}</b></div>{% if not loop.last %}<i>→</i>{% endif %}{% endfor %}</div>
<div class="summary-grid">
<div class="summary"><span>Marktdaten</span><b>{{public.effective_state or "—"}}</b><small>{{public.symbol_count or 0}} Ticker · Frischegate {{fresh_market_seconds|int}}s</small></div>
<div class="summary"><span>News</span><b>{{news_count[0].n if news_count else 0}}</b><small>{{news_links[0].n if news_links else 0}} signierte Marktverknüpfungen</small></div>
<div class="summary"><span>Plan</span><b>{{plan.plan_hash[:10] if plan else "—"}}</b><small>{{plan.decision_count if plan else 0}} Entscheidungen</small></div>
<div class="summary"><span>Steuer</span><b>AT / 27,5 %</b><small>Einkommensteuer-/KESt-Prüfhilfe</small></div>
</div>
<div class="card"><h2>Letzte Entscheidungen</h2><div class="tablewrap"><table><tr><th>Zeit</th><th>Umgebung</th><th>Symbol</th><th>Typ</th><th>Aktion</th><th>Edge nach Kosten</th><th>Target</th><th>Delta</th><th>Ausführung</th><th>Status</th></tr>{% for x in decisions %}<tr><td>{{x.created_at}}</td><td>{{x.environment}}</td><td>{{x.symbol}}</td><td>{{x.action_type or "—"}}</td><td>{{x.action}}</td><td>{{x.expected_edge_after_costs_pct or "—"}}%</td><td>{{x.target_exposure_eur}} €</td><td>{{x.delta_eur}} €</td><td>{{x.execution_symbol or "—"}} · {{x.execution_mode or "—"}} · {{x.leverage or "1"}}x</td><td>{{x.status}}</td></tr>{% else %}<tr><td colspan="10">Noch keine Entscheidung.</td></tr>{% endfor %}</table></div></div>
<div class="split"><div class="card"><h2>Modellqualität je Richtung</h2>{% for f,h in health.items() %}<div class="allocation"><div><b>{{f}}</b><small>UP {{h.quality_score_by_direction.UP if h.quality_score_by_direction else "—"}} · DOWN {{h.quality_score_by_direction.DOWN if h.quality_score_by_direction else "—"}}</small></div><strong>{{h.status or "—"}}</strong></div>{% endfor %}</div>
<div class="card"><h2>Portfolio-/Orderlogik</h2><p>Neue Risiken benötigen positive erwartete Rendite nach aktuellen Routekosten. Rebalancing/Exit darf bestehendes Risiko reduzieren, auch bei negativer Neueinstiegs-Edge.</p><p><a href="/prozess">Ablauf und Diagnose →</a> · <a href="/steuerinfo-at">Einkommensteuer AT →</a></p></div></div>''',
        plan=plan,decisions=decisions,health=health,public=public,private=private,
        news_count=news_count,news_links=news_links,auto=auto,real_state=real_state,fresh_market_seconds=planner.settings()["decision_market_data_max_age_seconds"]
    )

def _analysis():
    rows=legacy.db.rows("""SELECT s.symbol,s.signal,s.score,s.momentum_pct,s.trend_pct,s.volatility_pct,
                                 s.spread_pct,s.news_score,s.quality,s.scanned_at,
                                 u.category,u.canonical_id
                          FROM scanner_results s
                          LEFT JOIN market_universe u ON u.symbol=s.symbol
                          WHERE s.quality IN ('VALID','CACHED')
                          ORDER BY CAST(s.score AS REAL) DESC LIMIT 80""")
    return legacy.page(
        '''<span class="eyebrow">Analyse</span><h1>Aktuelle Kandidaten</h1>
<p class="lead">Nur frische Kandidaten mit verwertbaren Marktdaten gehen in den gemeinsamen kanonischen Plan.</p>
<div class="card"><div class="tablewrap"><table><tr><th>Symbol</th><th>Familie</th><th>Signal</th><th>Score</th><th>Momentum</th><th>Trend</th><th>Volatilität</th><th>Spread</th><th>News</th><th>Alter</th></tr>{% for x in rows %}<tr><td>{{x.symbol}}</td><td>{{x.category}}</td><td>{{x.signal}}</td><td>{{x.score}}</td><td>{{x.momentum_pct}}%</td><td>{{x.trend_pct}}%</td><td>{{x.volatility_pct}}%</td><td>{{x.spread_pct}}%</td><td>{{x.news_score}}</td><td>{{x.scanned_at}}</td></tr>{% endfor %}</table></div></div>''',
        rows=rows
    )

def _v102_chart(values):
    vals=[]
    for value in values or []:
        try: vals.append(float(value))
        except (TypeError,ValueError): pass
    if not vals:
        return '<svg viewBox="0 0 800 220" class="chart"><text x="24" y="115">Noch keine Historie</text></svg>'
    lo,hi=min(vals),max(vals)
    if hi==lo: lo-=1; hi+=1
    pts=[]
    for i,v in enumerate(vals):
        x=28+744*i/max(1,len(vals)-1); y=24+170*(1-(v-lo)/(hi-lo)); pts.append(f"{x:.1f},{y:.1f}")
    return f'<svg viewBox="0 0 800 220" class="chart" role="img" aria-label="Portfolioverlauf"><line x1="28" y1="194" x2="772" y2="194" class="chart-axis"/><polyline points="{" ".join(pts)}" class="chart-line" fill="none"/><circle cx="{pts[-1].split(",")[0]}" cy="{pts[-1].split(",")[1]}" r="4" class="chart-dot"/><text x="28" y="16" class="chart-label">Min {lo:.2f} €</text><text x="772" y="16" text-anchor="end" class="chart-label">Max {hi:.2f} €</text><text x="772" y="214" text-anchor="end" class="chart-value">Aktuell {vals[-1]:.2f} €</text></svg>'

def _portfolio():
    try:
        paper=legacy.db.rows("SELECT created_at,total_eur,quality FROM paper_snapshots ORDER BY id DESC LIMIT 120")
    except Exception:
        paper=[]
    try:
        real=legacy.db.rows("SELECT created_at,total_eur,quality FROM portfolio_snapshots ORDER BY id DESC LIMIT 120")
    except Exception:
        real=[]
    try:
        raw_paper=legacy.db.rows("SELECT symbol,quantity,avg_cost_eur FROM paper_positions WHERE CAST(quantity AS REAL)<>0 ORDER BY symbol")
    except Exception:
        raw_paper=[]
    paper_positions=[]
    for row in raw_paper:
        item=dict(row)
        try:
            px=legacy.db.rows("SELECT last FROM live_prices WHERE symbol=? LIMIT 1",(row["symbol"],))
            price=float(px[0]["last"]) if px and float(px[0]["last"])>0 else None
            if price is not None and str(row["symbol"]).upper().endswith("/USD"):
                fx=legacy.db.rows("SELECT last FROM live_prices WHERE UPPER(symbol)='EUR/USD' LIMIT 1")
                rate=float(fx[0]["last"]) if fx and float(fx[0]["last"])>0 else None
                price=price/rate if rate else None
            value=float(row["quantity"])*price if price is not None else None
            cost=float(row["quantity"])*float(row["avg_cost_eur"])
            item["current_eur"]=f"{value:.4f}" if value is not None else None
            item["pnl_eur"]=f"{value-cost:.4f}" if value is not None else None
            item["price_eur"]=f"{price:.8f}" if price is not None else None
        except Exception:
            item["current_eur"]=item["pnl_eur"]=item["price_eur"]=None
        paper_positions.append(item)
    try:
        real_positions=legacy.db.rows(
            "SELECT asset,display_name,amount,eur_price,eur_value,classification "
            "FROM portfolio_assets WHERE classification='HELD' AND CAST(amount AS REAL)<>0 ORDER BY display_name"
        )
    except Exception:
        real_positions=[]
    try:
        margin_positions=legacy.db.rows(
            "SELECT symbol,side,volume,current_value,unrealized_pnl,leverage "
            "FROM real_margin_positions ORDER BY symbol"
        )
    except Exception:
        margin_positions=[]
    decisions=_decision_rows(30)
    return legacy.page(
        '''<span class="eyebrow">Portfolio</span><h1>Portfolio & Rebalancing</h1>
<div class="chart-grid"><div class="chart-card"><b>Paper Equity</b>{{paper_chart|safe}}</div><div class="chart-card"><b>Real Equity</b>{{real_chart|safe}}</div></div>
<div class="split">
<div class="card"><h2>Paper-Depot · Positionen</h2><div class="tablewrap"><table><tr><th>Symbol</th><th>Menge</th><th>Einstand</th><th>Aktuell</th><th>U/L</th></tr>{% for x in paper_positions %}<tr><td>{{x.symbol}}</td><td>{{x.quantity}}</td><td>{{x.avg_cost_eur}} €</td><td>{{x.current_eur if x.current_eur else "—"}} €</td><td>{{x.pnl_eur if x.pnl_eur else "—"}} €</td></tr>{% else %}<tr><td colspan="5">Keine Paper-Positionen.</td></tr>{% endfor %}</table></div></div>
<div class="card"><h2>Reales Depot · Positionen</h2><div class="tablewrap"><table><tr><th>Asset</th><th>Menge</th><th>EUR-Kurs</th><th>EUR-Wert</th><th>Status</th></tr>{% for x in real_positions %}<tr><td>{{x.display_name or x.asset}}</td><td>{{x.amount}}</td><td>{{x.eur_price or "—"}}</td><td>{{x.eur_value or "—"}} €</td><td>{{x.classification}}</td></tr>{% else %}<tr><td colspan="5">Keine realen Positionen im Portfolio-Snapshot.</td></tr>{% endfor %}</table></div>{% if margin_positions %}<h3>Offene Margin-Positionen</h3><div class="tablewrap"><table><tr><th>Symbol</th><th>Seite</th><th>Menge</th><th>Wert</th><th>U/L</th><th>Hebel</th></tr>{% for x in margin_positions %}<tr><td>{{x.symbol}}</td><td>{{x.side}}</td><td>{{x.volume}}</td><td>{{x.current_value or "—"}} €</td><td>{{x.unrealized_pnl or "—"}} €</td><td>{{x.leverage or "1"}}x</td></tr>{% endfor %}</table></div>{% endif %}</div></div>
<div class="card"><h2>Target vs. Current</h2>{% for x in decisions[:20] %}<div class="allocation"><div><b>{{x.symbol}}</b><small>{{x.action_type}} · {{x.execution_symbol or "—"}} · {{x.status}}</small></div><strong>{{x.target_exposure_eur}} €</strong></div>{% else %}<span class="muted">Noch kein Plan.</span>{% endfor %}</div>
</div>''',
        paper_chart=_v102_chart([x["total_eur"] for x in reversed(paper)]),
        real_chart=_v102_chart([x["total_eur"] for x in reversed(real)]),
        paper_positions=paper_positions,real_positions=real_positions,margin_positions=margin_positions,decisions=decisions
    )

def _handel():
    decisions=_decision_rows(100)
    return legacy.page(
        '''<span class="eyebrow">Ordersteuerung</span><h1>Decision Ledger</h1>
<p class="lead">Jede Paper- und Realorder erhält dieselbe Plan-ID, denselben Zielwert, dieselbe Edge- und Risikobasis und eine explizite Ausführungsbegründung.</p>
<div class="card"><div class="tablewrap"><table><tr><th>Zeit</th><th>Umgebung</th><th>Symbol</th><th>Typ</th><th>Aktion</th><th>Brutto-Edge</th><th>Netto-Edge</th><th>Current</th><th>Target</th><th>Delta</th><th>Nutzen</th><th>Route</th><th>Modus</th><th>Status</th></tr>{% for x in decisions %}<tr><td>{{x.created_at}}</td><td>{{x.environment}}</td><td>{{x.symbol}}</td><td>{{x.action_type or "—"}}</td><td>{{x.action}}</td><td>{{x.expected_edge_gross_pct or "—"}}%</td><td>{{x.expected_edge_after_costs_pct or "—"}}%</td><td>{{x.current_exposure_eur}} €</td><td>{{x.target_exposure_eur}} €</td><td>{{x.delta_eur}} €</td><td>{{x.marginal_benefit_eur or "0"}} €</td><td>{{x.execution_symbol or "—"}}</td><td>{{x.execution_mode or "—"}} / {{x.leverage or "1"}}x</td><td>{{x.status}}</td></tr>{% endfor %}</table></div></div>''',
        decisions=decisions
    )

def _lernen():
    cl=ControlledLearning(legacy.db);nl=NewsLearning(legacy.db)
    families=cl.family_overview()
    candidates=cl.candidates()
    news_candidates=nl.candidates()
    try: news_status=nl.data_status()
    except Exception: news_status={"status":"UNAVAILABLE","news_items":0,"ai_valid":0,"sample_count":0,"required":0,"missing":0,"ready":False}
    try: health=_health_snapshot()
    except Exception: health={}
    research=legacy.pipeline.latest() or {}
    return legacy.page(
        '''<span class="eyebrow">Lernen</span><h1>Lernen & Freigaben</h1>
<p class="lead">Learning verändert aktive Parameter nicht ohne bestandenen Zeit-/Holdout-Vergleich. H24 ist operativ; H168 bleibt zusätzliche Validierung.</p>
<div class="learning-grid">{% for x in families %}<div class="learning-card"><span class="eyebrow">{{x.family}}</span><h3>Aktiv v{{x.active_version or "—"}}</h3><b>{{x.pending_count}} offen</b><small>{{x.latest_status}}</small></div>{% endfor %}</div>
<div class="grid"><div class="card"><h2>Forecast-Basis</h2><p>Research: <b>{{research.stage or "—"}}</b> · {{research.status or "—"}}</p><p>H24/H168 werden für die Modellbewertung getrennt erfasst.</p></div>
<div class="card"><h2>Nachrichten-Lernen</h2><p>Status: <b>{{news_status.status}}</b></p><p>{{news_status.sample_count}} gültige Trainingsbeobachtungen · {{news_status.missing}} fehlen für den Vergleich.</p><p>Externe News-AI ist optional; ohne gültige AI-Auswertungen bleibt dieser Lernpfad bewusst ohne neuen Kandidaten.</p></div></div>
<div class="card"><h2>Strategie-Kandidaten</h2><div class="tablewrap"><table><tr><th>ID</th><th>Familie</th><th>Status</th><th>Samples</th><th>Verbesserung</th><th>Grund</th></tr>{% for x in candidates[:60] %}<tr><td>{{x.id}}</td><td>{{x.family}}</td><td>{{x.status}}</td><td>{{x.sample_count}}</td><td>{{x.improvement}}</td><td>{{x.reason}}</td></tr>{% endfor %}</table></div></div>
<div class="card"><h2>Richtungsevidenz für den Handel</h2><div class="tablewrap"><table><tr><th>Familie</th><th>H24 Samples</th><th>UP Edge</th><th>DOWN Edge</th><th>Risk State</th></tr>{% for family,h in health.items() %}<tr><td>{{family}}</td><td>{{h.horizons["24"].samples if h.horizons else "—"}}</td><td>{{h.directions.UP.mean_edge_after_costs_pct if h.directions and h.directions.UP else "—"}}</td><td>{{h.directions.DOWN.mean_edge_after_costs_pct if h.directions and h.directions.DOWN else "—"}}</td><td>{{h.risk_state or "—"}}</td></tr>{% endfor %}</table></div></div>
<div class="card"><h2>Nachrichten-Lernen</h2><div class="tablewrap"><table><tr><th>ID</th><th>Status</th><th>Samples</th><th>Verbesserung</th><th>Grund</th></tr>{% for x in news_candidates[:50] %}<tr><td>{{x.id}}</td><td>{{x.status}}</td><td>{{x.sample_count}}</td><td>{{x.improvement}}</td><td>{{x.reason}}</td></tr>{% endfor %}</table></div></div>''',
        families=families,candidates=candidates,news_candidates=news_candidates,news_status=news_status,health=health,research=research
    )

def _diagnose():
    plan=_latest_plan();public=legacy.stream.status();private=legacy.private_stream.status();health=_health_snapshot();decisions=_decision_rows(30)
    blocked=legacy.db.rows("SELECT created_at,symbol,action,rule_key,reason FROM decision_rule_evaluations WHERE passed=0 ORDER BY id DESC LIMIT 120")
    real_run=legacy.db.rows("SELECT created_at,status,details_json FROM real_allocation_runs ORDER BY id DESC LIMIT 1")
    real_summary={"status":"—","evaluated_candidates":0,"skipped_count":0,"execution_capacity":0,"total_eur":"—","skips":[]}
    if real_run:
        real_summary["status"]=real_run[0].get("status","—")
        try:
            raw=json.loads(real_run[0].get("details_json") or "{}")
            real_summary.update({
                "evaluated_candidates":raw.get("evaluated_candidates",len(raw.get("decisions",[]))),
                "skipped_count":raw.get("skipped_count",len(raw.get("skips",[]))),
                "execution_capacity":raw.get("execution_capacity",0),
                "skips":raw.get("skips",[])[:12],
            })
            if plan: real_summary["total_eur"]=plan.get("total_eur","—")
        except Exception:
            pass
    return legacy.page(
        '''<span class="eyebrow">Diagnose</span><h1>Warum wurde gehandelt?</h1>
<p class="lead">Datenfrische → Modell-/Richtungsevidenz → Edge nach Kosten → Target → Guard → Order.</p>
<div class="grid"><div class="card"><b>Public Kraken</b><div class="metric">{{public.effective_state}}</div><small>{{public.last_message_at or "—"}}</small></div><div class="card"><b>Private Kraken</b><div class="metric">{{private.effective_state}}</div><small>{{private.last_message_at or "—"}}</small></div><div class="card"><b>Letzter Plan</b><div class="metric">{{plan.plan_hash[:12] if plan else "—"}}</div><small>{{plan.environment if plan else "—"}}</small></div><div class="card"><b>Blockierungen</b><div class="metric">{{blocked|length}}</div><small>letzte 120</small></div></div>
<div class="card"><h2>Directional Model Health</h2>{% for f,h in health.items() %}<div class="allocation"><div><b>{{f}}</b><small>UP {{h.quality_score_by_direction.UP if h.quality_score_by_direction else "—"}} · DOWN {{h.quality_score_by_direction.DOWN if h.quality_score_by_direction else "—"}} · H24 {{h.horizons["24"].samples if h.horizons else "—"}}</small></div><strong>{{h.status or "—"}}</strong></div>{% endfor %}</div>
<div class="card"><h2>Blockierte Regeln</h2><div class="tablewrap"><table><tr><th>Zeit</th><th>Symbol</th><th>Aktion</th><th>Regel</th><th>Grund</th></tr>{% for x in blocked %}<tr><td>{{x.created_at}}</td><td>{{x.symbol}}</td><td>{{x.action}}</td><td>{{x.rule_key}}</td><td>{{x.reason}}</td></tr>{% else %}<tr><td colspan="5">Keine gespeicherte Blockierung.</td></tr>{% endfor %}</table></div></div>
<div class="card"><h2>Letzter Real-Automatiklauf</h2><div class="grid"><div><b>Status</b><div class="metric">{{real_summary.status}}</div></div><div><b>Bewertete Kandidaten</b><div class="metric">{{real_summary.evaluated_candidates}}</div></div><div><b>Übersprungen</b><div class="metric">{{real_summary.skipped_count}}</div></div><div><b>Kapazität</b><div class="metric">{{real_summary.execution_capacity}}</div></div></div><p>Letzte Ziel-/Depotbasis: {{real_summary.total_eur}} € · Mindestorder: {{min_trade_eur}} € · Entry-No-Trade-Band gilt nicht für Neukäufe.</p>{% for x in real_summary.skips %}<div class="allocation"><div><b>{{x.symbol}}</b><small>{{x.reason}}</small></div><strong>{{x.delta_eur or "—"}} €</strong></div>{% else %}<span class="muted">Keine gespeicherten Skip-Gründe gespeichert.</span>{% endfor %}</div>
<div class="card"><h2>Prozessstatus</h2><pre>{{{"plan_hash":plan.plan_hash if plan else None,"public":public,"private":private}|tojson(indent=2)}}</pre></div>''',
        plan=plan,public=public,private=private,health=health,decisions=decisions,blocked=blocked,real_summary=real_summary,min_trade_eur=planner.settings()["decision_min_trade_eur"]
    )

def _prozess():
    return legacy.page(
        '''<span class="eyebrow">Prozess</span><h1>Verbindlicher v102-Ablauf</h1><div class="flow">{% for s in steps %}<div class="card"><div class="flowstep"><span class="num">{{loop.index}}</span><div><h3>{{s.t}}</h3><p>{{s.d}}</p></div></div></div>{% endfor %}</div>''',
        steps=[
            {"t":"Kraken Market Data","d":"Public WebSocket/REST liefern Ticker und abgeschlossene OHLC-Daten. Frische und Datenqualität sind harte Vorbedingungen."},
            {"t":"Nachrichten","d":"News werden gesammelt, klassifiziert, lokal/extern bewertet und als zeitlich abklingendes signiertes Feature in den Scanner gegeben."},
            {"t":"Analyse","d":"Momentum, Trend, Volatilität, Spread, Liquidität und News bilden je Produktfamilie einen Kandidatenscore."},
            {"t":"Forecast","d":"H24/H168 werden gegen abgeschlossene Zielkerzen bewertet; Kosten, Timing und Richtung werden gespeichert."},
            {"t":"Learning","d":"Zeitlich getrenntes Training/Validation plus Walk-Forward prüfen Parameter gegen die aktive Version."},
            {"t":"Canonical Planner","d":"Ein Plan für Paper und Real: Kandidaten, Health, Regime, historische H24-Edge, aktuelle Routekosten, Targets und Ranking."},
            {"t":"Rebalancing","d":"Target minus Current bestimmt die einzelne Aktion; neue Risiken benötigen positive Net-Edge, Reduktionen sind risikoreduzierend."},
            {"t":"Execution Intent","d":"Ein gemeinsamer Intent bestimmt Symbol, Seite, EUR-Notional, Leverage/Mode und Reduce-only. Erst danach trennt sich Paper von Real."},
            {"t":"Paper / Real","d":"Paper simuliert den Fill; Real prüft dieselben Regeln plus Kontosaldo, Kill-Switch, Freigabe und Kraken-Preflight."},
            {"t":"Nachweis / Einkommensteuer AT","d":"Decision Ledger, Audit, Portfolio-Historie und die separate österreichische Steuer-/E1kv-Arbeitsmappe bleiben nachvollziehbar."},
        ]
    )

@app.get("/analyse")
def analyse_v102():return _analysis()
@app.get("/portfolio")
def portfolio_v102():return _portfolio()
@app.get("/handel")
def handel_v102():return _handel()
@app.get("/lernen")
def lernen_v102():return _lernen()
@app.get("/diagnose")
def diagnose_v102():return _diagnose()
@app.get("/prozess")
def prozess_v102():return _prozess()


def _automatik():
    cfg=controller.settings()
    real_state=build_real_state(legacy.db,controller)
    return legacy.page(
        """<span class="eyebrow">Automatik</span><h1>Automatik</h1>
<p class="lead">Die Home-Assistant-Konfiguration ist die einzige Benutzerquelle für Betriebs- und Realhandels-Schalter. Diese Seite zeigt ausschließlich den aktuellen Laufzeitstatus.</p>
<div class="automation-grid">{% for k,n in items %}<div class="automation-card"><b>{{n}}</b><span class="status {{'on' if cfg["automation_"+k+"_enabled"]=="true" else "off"}}">{{"AN" if cfg["automation_"+k+"_enabled"]=="true" else "AUS"}}</span><small>{{cfg["automation_"+k+"_interval_minutes"]}} min</small></div>{% endfor %}</div>
<div class="card"><h2>Realhandelsstatus</h2><p><b>{{real_state.status_label}}</b></p><p>{{real_state.summary}}</p><p><a href="/real-trading">Realhandel & konkrete Blockierungen →</a></p></div>""",
        cfg=cfg,items=[("news","Nachrichten"),("analysis","Analyse"),("learning","Lernen"),("paper","Paper"),("real","Real")],real_state=real_state)

@app.get("/automatik")
def automatik_v102():
    return _automatik()

def _real_trading():
    engine=legacy.real_trade_engine
    real_state=build_real_state(legacy.db,controller)
    result=error=token=None
    if request.method=="POST":
        try:
            if request.form.get("action")=="arm":
                token=engine.arm(request.form.get("phrase"))
            else:
                result=engine.submit(request.form.get("symbol"),request.form.get("side"),request.form.get("volume"),request.form.get("order_type"),request.form.get("limit_price"),request.form.get("client_order_id") or None,request.form.get("approval_token"),request.form.get("live")!="yes",None,request.form.get("leverage") or None,request.form.get("margin")=="yes",request.form.get("reduce_only")=="yes")
        except Exception as exc:
            error=type(exc).__name__+":"+str(exc)
    rows=legacy.db.rows("SELECT id,created_at,client_order_id,symbol,side,order_type,volume,limit_price,status,validate_only,error FROM real_trade_intents ORDER BY id DESC LIMIT 50")
    blocked=legacy.db.rows("SELECT created_at,symbol,action,rule_key,reason FROM decision_rule_evaluations ORDER BY id DESC LIMIT 100")
    return legacy.page(
        """<span class="eyebrow">Realhandel</span><h1>Realhandel</h1>
<div class="grid">
<div class="card"><b>Globaler Realhandelsstatus</b><div class="metric">{{real_state.status_label}}</div><p>{{real_state.summary}}</p></div>
<div class="card"><b>Automatische Real-Ausführung</b><div class="metric">{{"AKTIV" if real_state.automatic_execution_ready else "BLOCKIERT"}}</div><p>{{real_state.automatic_summary}}</p></div>
<div class="card"><b>Manuelle Realorder</b><div class="metric">{{"VERFÜGBAR" if real_state.manual_order_available else "BLOCKIERT"}}</div><p>Eine Live-Order benötigt zusätzlich das zeitlich begrenzte Freigabetoken.</p></div></div>
{% if error %}<div class="card error">{{error}}</div>{% endif %}
{% if result %}<div class="card"><h2>Ergebnis</h2><pre>{{result|tojson(indent=2)}}</pre></div>{% endif %}
{% if token %}<div class="card warning"><b>Einmaliges Freigabetoken · 5 Minuten gültig</b><pre>{{token}}</pre></div>{% endif %}
<div class="card"><h2>Globale Blockierungen</h2>{% if real_state.blockers %}<table><tr><th>Code</th><th>Grund</th></tr>{% for x in real_state.blockers %}<tr><td><code>{{x.code}}</code></td><td>{{x.reason}}</td></tr>{% endfor %}</table>{% else %}<p class="ok">Keine globale Blockierung.</p>{% endif %}</div>
<div class="card"><h2>Konkrete Regelblockierungen</h2>{% if blocked %}<table><tr><th>Zeit</th><th>Symbol</th><th>Aktion</th><th>Regel</th><th>Grund</th></tr>{% for x in blocked %}<tr><td>{{x.created_at}}</td><td>{{x.symbol}}</td><td>{{x.action}}</td><td>{{x.rule_key}}</td><td>{{x.reason}}</td></tr>{% endfor %}</table>{% else %}<p>Noch keine gespeicherte Blockierung.</p>{% endif %}</div>
<div class="card"><h2>Manuelle Order</h2><p>Standardmäßig wird nur gegen Kraken validiert. Eine echte Order wird ausschließlich nach expliziter Live-Auswahl und erfolgreicher Freigabe übermittelt.</p>
<form method="post">
<input type="hidden" name="action" value="submit">
<label>Symbol<input name="symbol" value="BTC/EUR"></label>
<label>Seite<select name="side"><option>buy</option><option>sell</option></select></label>
<label>Typ<select name="order_type"><option>limit</option><option>market</option></select></label>
<label>Volumen<input name="volume" required></label>
<label>Limitpreis<input name="limit_price"></label>
<label>Margin/Leverage<select name="margin"><option value="no">Spot</option><option value="yes">Margin</option></select></label>
<label>Hebel<input name="leverage" value="2"></label>
<label>Reduce-only<select name="reduce_only"><option value="no">Nein</option><option value="yes">Ja</option></select></label>
<label>Idempotenz-ID<input name="client_order_id"></label>
<label>Freigabetoken<input name="approval_token"></label>
<label>Live<select name="live"><option value="no">Nein, nur validieren</option><option value="yes">Ja</option></select></label>
<button>Absenden</button>
</form></div>
<div class="card"><h2>Manuelle Livefreigabe</h2><form method="post"><input type="hidden" name="action" value="arm"><label>Bestätigungsphrase<input name="phrase"></label><button>5 Minuten aktiv bestätigen</button></form></div>
<div class="card"><h2>Letzte Realorder-Intents</h2><div class="tablewrap"><table><tr><th>Zeit</th><th>ID</th><th>Symbol</th><th>Seite</th><th>Volumen</th><th>Status</th><th>Validierung</th></tr>{% for x in rows %}<tr><td>{{x.created_at}}</td><td>{{x.client_order_id}}</td><td>{{x.symbol}}</td><td>{{x.side}}</td><td>{{x.volume}}</td><td>{{x.status}}</td><td>{{x.validate_only}}</td></tr>{% endfor %}</table></div></div>""",
        real_state=real_state,error=error,result=result,token=token,rows=rows,blocked=blocked)

app.view_functions["real_trade.view"]=_real_trading

def _health_current():
    real_state=build_real_state(legacy.db,controller)
    return {
        "status":"ok",
        "version":"0.1.0-dev.100",
        "runtime":"v102_main",
        "real_state":real_state,
        "real_trading":real_state["manual_order_available"],
        "automatic_real_execution":real_state["automatic_execution_ready"],
        "market_stream":legacy.stream.status(),
        "private_stream":legacy.private_stream.status(),
    }

app.view_functions["health"]=_health_current

@app.get("/v102-health")
def v102_health():
    plan=_latest_plan()
    real_state=build_real_state(legacy.db,controller)
    return jsonify({
        "version":"0.1.0-dev.100",
        "runtime":"v102_main",
        "architecture":"CANONICAL_PLANNER_PLUS_SHARED_EXECUTION_INTENT",
        "paper_real_same_plan":True,
        "plan_hash":plan.get("plan_hash") if plan else None,
        "economic_gate":"POSITIVE_EXPECTED_H24_EDGE_AFTER_CURRENT_ENTRY_EXIT_ROUTE_COST_FOR_NEW_RISK",
        "risk_reduction":"ALLOWED_WITHOUT_NEW_ENTRY_EDGE",
        "existing_position_exit":"TARGET_ZERO_RISK_REDUCTION",
        "margin":"ACCOUNT_CAPABILITY_GATED",
        "news":"SIGNED_AND_TIME_DECAYED",
        "tax_ui":"/steuerinfo-at",
        "real_enabled":real_state["manual_order_available"],
        "real_automatic_execution":real_state["automatic_execution_ready"],
        "real_state":real_state,
    })

app.view_functions["index"]=_dashboard


# ---------------------------------------------------------------------------
# v102 canonical GUI/API layer
# ---------------------------------------------------------------------------

def _safe_rows(query, params=()):
    try:
        return legacy.db.rows(query, params)
    except Exception as exc:
        legacy.db.audit("V102_GUI_QUERY_FAILED", type(exc).__name__+":"+str(exc)[:300], "error")
        return []

def _latest_research_v102():
    try:
        return legacy.pipeline.latest() or {}
    except Exception:
        return {}

def _latest_paper_v102():
    rows=_safe_rows("SELECT created_at,total_eur,quality FROM paper_snapshots ORDER BY id DESC LIMIT 1")
    return rows[0] if rows else None

def _latest_real_v102():
    rows=_safe_rows("SELECT created_at,total_eur,quality FROM portfolio_snapshots ORDER BY id DESC LIMIT 1")
    return rows[0] if rows else None

def _current_process_status_v102():
    plan=_latest_plan()
    research=_latest_research_v102()
    paper=_latest_paper_v102()
    real=_latest_real_v102()
    real_run=_safe_rows("SELECT created_at,status,details_json FROM real_allocation_runs ORDER BY id DESC LIMIT 1")
    return {
        "market":market_service.status(),
        "private":legacy.private_stream.status(),
        "research":research,
        "plan":plan,
        "paper":paper,
        "real":real,
        "real_run":real_run[0] if real_run else None,
        "real_state":build_real_state(legacy.db,controller),
    }

def _render_v102(title, eyebrow, lead, body, **ctx):
    return legacy.page(
        f'<span class="eyebrow">{eyebrow}</span><h1>{title}</h1><p class="lead">{lead}</p>'+body,
        **ctx
    )

def _dashboard_v102():
    st=_current_process_status_v102()
    news=_safe_rows("SELECT COUNT(*) AS n FROM news_items")
    links=_safe_rows("SELECT COUNT(*) AS n FROM news_market_links")
    decisions=_decision_rows(10)
    return legacy.page(
        '''<span class="eyebrow">KTKI v102</span><h1>Kraken Trader</h1>
<p class="lead">Ein klarer End-to-End-Prozess: Marktdaten → News → Analyse → Lernen → Ziel → Order.</p>
<div class="summary-grid">
<div class="summary"><span>Public Market</span><b>{{market.effective_state}}</b><small>{{market.symbol_count}} WS-Symbole · {{market.live_price_count_10m}} Preise / 10 min</small></div>
<div class="summary"><span>News</span><b>{{news_count}}</b><small>{{news_links}} Marktverknüpfungen</small></div>
<div class="summary"><span>Analyse</span><b>{{research.stage or "—"}}</b><small>{{research.status or "Noch kein Lauf"}}</small></div>
<div class="summary"><span>Realhandel</span><b>{{real_state.status_label}}</b><small>{{"Automatik bereit" if real_state.automatic_execution_ready else "Nicht vollständig freigegeben"}}</small></div>
</div>
<div class="card"><h2>Prozess</h2><div class="process-strip">{% for x in steps %}<div class="process-node"><span>{{loop.index}}</span><b>{{x}}</b></div>{% if not loop.last %}<i>→</i>{% endif %}{% endfor %}</div>
<p><a class="button" href="/markt">Marktdaten</a> <a class="button secondary" href="/analyse">Analyse</a> <a class="button secondary" href="/system">System</a></p></div>
<div class="card"><h2>Letzte Entscheidungen</h2><div class="tablewrap"><table>
<tr><th>Zeit</th><th>Umgebung</th><th>Symbol</th><th>Aktion</th><th>Target</th><th>Delta</th><th>Status</th></tr>
{% for x in decisions %}<tr><td>{{x.created_at}}</td><td>{{x.environment}}</td><td>{{x.symbol}}</td><td>{{x.action_type or x.action}}</td><td>{{x.target_exposure_eur}} €</td><td>{{x.delta_eur}} €</td><td>{{x.status}}</td></tr>{% else %}<tr><td colspan="7">Noch keine Entscheidungen.</td></tr>{% endfor %}
</table></div></div>''',
        market=st["market"],real_state=st["real_state"],research=st["research"],
        news_count=(news[0]["n"] if news else 0),news_links=(links[0]["n"] if links else 0),
        decisions=decisions,steps=["Kraken","News","Analyse","Lernen","Plan","Order"]
    )

def _market_page_v102(message=None, message_level=""):
    status=market_service.status()
    prices=_safe_rows("SELECT symbol,last,bid,ask,change_pct,received_at FROM live_prices ORDER BY symbol LIMIT 80")
    universe_rows=_safe_rows("SELECT symbol,asset_class,category,status FROM market_universe ORDER BY category,symbol LIMIT 60")
    return _render_v102(
        "Markt & Daten","Kraken Market","Öffentliche Marktdaten benötigen keinen API-Schlüssel. REST-Snapshot und WebSocket werden gemeinsam überwacht.",
        '''{% if message %}<div class="card {{message_level}}">{{message}}</div>{% endif %}
<div class="summary-grid">
<div class="summary"><span>Public WebSocket</span><b>{{status.effective_state}}</b><small>{{status.system_status or "—"}} · {{status.last_message_at or "Noch keine Nachricht"}}</small></div>
<div class="summary"><span>Livepreise</span><b>{{status.live_price_count_10m}}</b><small>letzte 10 Minuten</small></div>
<div class="summary"><span>Abonnements</span><b>{{status.symbol_count}}</b><small>{{status.blocked_symbol_count}} abgewiesene Symbole</small></div>
<div class="summary"><span>REST Snapshot</span><b>{{status.last_rest_refresh or "—"}}</b><small>{{status.last_refresh_result.get("saved",0) if status.last_refresh_result else 0}} gespeichert</small></div>
</div>
<div class="card"><h2>Public Market Interface</h2><p>{{status.last_error or "Keine aktuelle Stream-Fehlermeldung."}}</p><form method="post" action="/markt/refresh"><button>Marktdaten jetzt aktualisieren</button></form></div>
<div class="card"><h2>Aktuelle Preise</h2><div class="tablewrap"><table><tr><th>Symbol</th><th>Last</th><th>Bid</th><th>Ask</th><th>Änderung</th><th>Zeit</th></tr>
{% for x in prices %}<tr><td>{{x.symbol}}</td><td>{{x.last}}</td><td>{{x.bid or "—"}}</td><td>{{x.ask or "—"}}</td><td>{{x.change_pct or "—"}} %</td><td>{{x.received_at}}</td></tr>{% else %}<tr><td colspan="6">Noch keine Preise verfügbar.</td></tr>{% endfor %}
</table></div></div>
<div class="card"><h2>Kraken Market Universe</h2><div class="tablewrap"><table><tr><th>Symbol</th><th>Asset Class</th><th>Kategorie</th><th>Status</th></tr>
{% for x in universe_rows %}<tr><td>{{x.symbol}}</td><td>{{x.asset_class}}</td><td>{{x.category}}</td><td>{{x.status}}</td></tr>{% else %}<tr><td colspan="4">Universe wird noch synchronisiert.</td></tr>{% endfor %}
</table></div></div>''',
        status=status,prices=prices,universe_rows=universe_rows,message=message,message_level=message_level
    )

@app.get("/markt")
def markt_v102():
    return _market_page_v102()

@app.post("/markt/refresh")
def markt_refresh_v102():
    try:
        result=market_service.bootstrap(force=True)
        message="Marktdaten aktualisiert: {} Preise gespeichert; WS auf {} Symbole gesetzt.".format(result.get("saved",0),len(result.get("symbols",[])))
        level="ok" if result.get("saved") else "warning"
    except Exception as exc:
        message="Marktdaten konnten nicht aktualisiert werden: "+type(exc).__name__+": "+str(exc)[:300]
        level="error"
    return _market_page_v102(message,level)

def _analysis_v102_clean(message=None,message_level=""):
    research=_latest_research_v102()
    rows=_safe_rows("""SELECT s.symbol,s.signal,s.score,s.momentum_pct,s.trend_pct,s.volatility_pct,
                              s.spread_pct,s.news_score,s.quality,s.scanned_at,u.category
                       FROM scanner_results s LEFT JOIN market_universe u ON u.symbol=s.symbol
                       WHERE s.quality IN ('VALID','CACHED')
                       ORDER BY CAST(s.score AS REAL) DESC LIMIT 80""")
    return _render_v102(
        "Analyse","Analyse","Der Analysebutton startet den vollständigen aktuellen Forschungsprozess. Ergebnisse werden anschließend gemeinsam von Paper und Real verwendet.",
        '''{% if message %}<div class="card {{message_level}}">{{message}}</div>{% endif %}
<div class="card"><form method="post" action="/analyse/start"><button>Analyseprozess starten</button></form>
<p><b>Letzter Lauf:</b> {{research.stage or "—"}} · {{research.status or "Noch kein Lauf"}} · {{research.progress_current or 0}}/{{research.progress_total or 0}}</p></div>
<div class="card"><h2>Aktuelle Kandidaten</h2><div class="tablewrap"><table><tr><th>Symbol</th><th>Familie</th><th>Signal</th><th>Score</th><th>Momentum</th><th>Trend</th><th>Volatilität</th><th>Spread</th><th>News</th></tr>
{% for x in rows %}<tr><td>{{x.symbol}}</td><td>{{x.category or "—"}}</td><td>{{x.signal}}</td><td>{{x.score}}</td><td>{{x.momentum_pct}}%</td><td>{{x.trend_pct}}%</td><td>{{x.volatility_pct}}%</td><td>{{x.spread_pct}}%</td><td>{{x.news_score}}</td></tr>{% else %}<tr><td colspan="9">Noch keine analysierten Kandidaten.</td></tr>{% endfor %}
</table></div></div>''',
        research=research,rows=rows,message=message,message_level=message_level
    )

@app.get("/analyse")
def analyse_v102_clean():
    return _analysis_v102_clean()

@app.post("/analyse/start")
def analyse_start_v102():
    try:
        result=legacy.pipeline.start()
        status=str(result.get("status","")).upper() if isinstance(result,dict) else "QUEUED"
        message="Analyseprozess gestartet." if status=="QUEUED" else "Analyseprozess meldet: "+str(result)
        level="ok" if status in ("QUEUED","BUSY","COMPLETED") else "warning"
    except Exception as exc:
        message="Analyseprozess konnte nicht gestartet werden: "+type(exc).__name__+": "+str(exc)[:300]
        level="error"
    return _analysis_v102_clean(message,level)

def _portfolio_v102_clean(message=None,message_level=""):
    paper=_safe_rows("SELECT created_at,total_eur,quality FROM paper_snapshots ORDER BY id DESC LIMIT 120")
    real=_safe_rows("SELECT created_at,total_eur,quality FROM portfolio_snapshots ORDER BY id DESC LIMIT 120")
    paper_pos=_safe_rows("SELECT symbol,quantity,avg_cost_eur FROM paper_positions WHERE CAST(quantity AS REAL)<>0 ORDER BY symbol")
    real_pos=_safe_rows("SELECT asset,display_name,amount,eur_price,eur_value,classification FROM portfolio_assets WHERE classification='HELD' AND CAST(amount AS REAL)<>0 ORDER BY display_name")
    margin=_safe_rows("SELECT symbol,side,volume,current_value,unrealized_pnl,leverage FROM real_margin_positions ORDER BY symbol")
    decisions=_decision_rows(20)
    for row in paper_pos:
        item=dict(row)
        try:
            px=_safe_rows("SELECT last FROM live_prices WHERE symbol=? LIMIT 1",(row["symbol"],))
            price=float(px[0]["last"]) if px and float(px[0]["last"])>0 else None
            if price is not None and str(row["symbol"]).upper().endswith("/USD"):
                fx=_safe_rows("SELECT last FROM live_prices WHERE UPPER(symbol)='EUR/USD' LIMIT 1")
                rate=float(fx[0]["last"]) if fx and float(fx[0]["last"])>0 else None
                price=price/rate if rate else None
            value=float(row["quantity"])*price if price is not None else None
            cost=float(row["quantity"])*float(row["avg_cost_eur"])
            item["current_eur"]=f"{value:.4f}" if value is not None else None
            item["pnl_eur"]=f"{value-cost:.4f}" if value is not None else None
        except Exception:
            item["current_eur"]=item["pnl_eur"]=None
        # Jinja cannot mutate sqlite rows; stash enriched copy.
        row=dict(row)
        row.update(item)
    paper_pos=[dict(x) for x in paper_pos]
    for item in paper_pos:
        try:
            px=_safe_rows("SELECT last FROM live_prices WHERE symbol=? LIMIT 1",(item["symbol"],))
            price=float(px[0]["last"]) if px and float(px[0]["last"])>0 else None
            if price is not None and str(item["symbol"]).upper().endswith("/USD"):
                fx=_safe_rows("SELECT last FROM live_prices WHERE UPPER(symbol)='EUR/USD' LIMIT 1")
                rate=float(fx[0]["last"]) if fx and float(fx[0]["last"])>0 else None
                price=price/rate if rate else None
            value=float(item["quantity"])*price if price is not None else None
            cost=float(item["quantity"])*float(item["avg_cost_eur"])
            item["current_eur"]=f"{value:.4f}" if value is not None else None
            item["pnl_eur"]=f"{value-cost:.4f}" if value is not None else None
        except Exception:
            item["current_eur"]=item["pnl_eur"]=None
    return _render_v102(
        "Portfolio","Portfolio","Paper- und Realpositionen bleiben getrennt sichtbar; Ziel und Entscheidung werden separat nachvollzogen.",
        '''{% if message %}<div class="card {{message_level}}">{{message}}</div>{% endif %}
<div class="chart-grid"><div class="chart-card"><b>Paper Equity</b>{{paper_chart|safe}}</div><div class="chart-card"><b>Real Equity</b>{{real_chart|safe}}</div></div>
<div class="card"><h2>Paper-Depot · Positionen</h2><div class="tablewrap"><table><tr><th>Symbol</th><th>Menge</th><th>Einstand</th><th>Aktuell</th><th>U/L</th></tr>
{% for x in paper_pos %}<tr><td>{{x.symbol}}</td><td>{{x.quantity}}</td><td>{{x.avg_cost_eur}} €</td><td>{{x.current_eur or "—"}} €</td><td>{{x.pnl_eur or "—"}} €</td></tr>{% else %}<tr><td colspan="5">Keine Paper-Positionen.</td></tr>{% endfor %}
</table></div></div>
<div class="card"><h2>Reales Depot · Positionen</h2><div class="tablewrap"><table><tr><th>Asset</th><th>Menge</th><th>EUR-Kurs</th><th>EUR-Wert</th><th>Status</th></tr>
{% for x in real_pos %}<tr><td>{{x.display_name or x.asset}}</td><td>{{x.amount}}</td><td>{{x.eur_price or "—"}}</td><td>{{x.eur_value or "—"}} €</td><td>{{x.classification}}</td></tr>{% else %}<tr><td colspan="5">Keine realen Positionen im Snapshot.</td></tr>{% endfor %}
</table></div>{% if margin %}<h3>Offene Margin-Positionen</h3><div class="tablewrap"><table><tr><th>Symbol</th><th>Seite</th><th>Menge</th><th>Wert</th><th>U/L</th><th>Hebel</th></tr>{% for x in margin %}<tr><td>{{x.symbol}}</td><td>{{x.side}}</td><td>{{x.volume}}</td><td>{{x.current_value or "—"}} €</td><td>{{x.unrealized_pnl or "—"}} €</td><td>{{x.leverage or "1"}}x</td></tr>{% endfor %}</table></div>{% endif %}</div>
<div class="card"><h2>Target vs Current</h2>{% for x in decisions %}<div class="allocation"><div><b>{{x.symbol}}</b><small>{{x.environment}} · {{x.action_type}} · {{x.status}}</small></div><strong>{{x.target_exposure_eur}} €</strong></div>{% else %}<span class="muted">Noch kein Plan.</span>{% endfor %}</div>
{% if api_ready %}<div class="card"><form method="post" action="/portfolio/sync"><button>Reales Depot synchronisieren</button></form><small>Nur mit konfigurierten Private-API-Daten sichtbar.</small></div>{% endif %}''',
        paper_chart=_v100_chart([x["total_eur"] for x in reversed(paper)]),
        real_chart=_v100_chart([x["total_eur"] for x in reversed(real)]),
        paper_pos=paper_pos,real_pos=real_pos,margin=margin,decisions=decisions,
        api_ready=bool(getattr(legacy.client,"key","") and getattr(legacy.client,"secret","")),
        message=message,message_level=message_level
    )

@app.get("/portfolio")
def portfolio_v102_clean():
    return _portfolio_v102_clean()

@app.post("/portfolio/sync")
def portfolio_sync_v102():
    if not (getattr(legacy.client,"key","") and getattr(legacy.client,"secret","")):
        return _portfolio_v102_clean("Keine Kraken Private API-Zugangsdaten konfiguriert.","warning")
    try:
        sync_portfolio()
        return _portfolio_v102_clean("Reales Depot erfolgreich synchronisiert.","ok")
    except Exception as exc:
        legacy.db.audit("V102_PORTFOLIO_SYNC_FAILED",type(exc).__name__+":"+str(exc)[:300],"warning")
        return _portfolio_v102_clean("Depot-Synchronisierung fehlgeschlagen: "+type(exc).__name__+": "+str(exc)[:300],"error")

def _handel_v102_clean():
    decisions=_decision_rows(120)
    plan=_latest_plan()
    return _render_v102(
        "Handel","Entscheidungen","Gemeinsamer Plan für Paper und Real. Erst die letzte Ausführungsschicht trennt die Umgebungen.",
        '''<div class="summary-grid"><div class="summary"><span>Letzter Plan</span><b>{{plan.plan_hash[:12] if plan else "—"}}</b><small>{{plan.environment if plan else "—"}}</small></div><div class="summary"><span>Entscheidungen</span><b>{{decisions|length}}</b><small>letzte 120</small></div></div>
<div class="card"><div class="tablewrap"><table><tr><th>Zeit</th><th>Umgebung</th><th>Symbol</th><th>Typ</th><th>Aktion</th><th>Edge</th><th>Current</th><th>Target</th><th>Delta</th><th>Route</th><th>Status</th></tr>
{% for x in decisions %}<tr><td>{{x.created_at}}</td><td>{{x.environment}}</td><td>{{x.symbol}}</td><td>{{x.action_type or "—"}}</td><td>{{x.action}}</td><td>{{x.expected_edge_after_costs_pct or "—"}}%</td><td>{{x.current_exposure_eur}} €</td><td>{{x.target_exposure_eur}} €</td><td>{{x.delta_eur}} €</td><td>{{x.execution_symbol or "—"}}</td><td>{{x.status}}</td></tr>{% else %}<tr><td colspan="11">Noch keine Entscheidungen.</td></tr>{% endfor %}</table></div></div>''',
        decisions=decisions,plan=plan
    )

@app.get("/handel")
def handel_v102_clean():
    return _handel_v102_clean()

def _lernen_v102_clean(message=None,message_level=""):
    cl=ControlledLearning(legacy.db)
    nl=NewsLearning(legacy.db)
    families=cl.family_overview()
    candidates=cl.candidates()
    news_candidates=nl.candidates()
    try: news_status=nl.data_status()
    except Exception: news_status={"status":"UNAVAILABLE","sample_count":0,"missing":0,"ready":False}
    return _render_v102(
        "Lernen & Freigaben","Lernen","Neue Parameter werden nur nach Prüfung und ausdrücklicher Freigabe aktiv.",
        '''{% if message %}<div class="card {{message_level}}">{{message}}</div>{% endif %}
<div class="learning-grid">{% for x in families %}<div class="learning-card"><span class="eyebrow">{{x.family}}</span><h3>Aktiv v{{x.active_version or "—"}}</h3><b>{{x.pending_count}} offen</b><small>{{x.latest_status}}</small></div>{% endfor %}</div>
<div class="card"><h2>Strategie-Kandidaten</h2><div class="tablewrap"><table><tr><th>ID</th><th>Familie</th><th>Status</th><th>Samples</th><th>Verbesserung</th><th>Grund</th><th>Aktion</th></tr>
{% for x in candidates[:60] %}<tr><td>{{x.id}}</td><td>{{x.family}}</td><td>{{x.status}}</td><td>{{x.sample_count}}</td><td>{{x.improvement}}</td><td>{{x.reason}}</td><td>{% if x.status=="PENDING" %}<form method="post" action="/lernen/decision"><input type="hidden" name="kind" value="strategy"><input type="hidden" name="candidate_id" value="{{x.id}}"><button name="action" value="approve">Freigeben</button> <button class="secondary" name="action" value="reject">Ablehnen</button></form>{% else %}—{% endif %}</td></tr>
{% else %}<tr><td colspan="7">Keine Kandidaten vorhanden.</td></tr>{% endfor %}</table></div></div>
<div class="card"><h2>Nachrichten-Lernen</h2><p>Status: <b>{{news_status.status}}</b> · {{news_status.sample_count}} gültige Beobachtungen · {{news_status.missing}} fehlen.</p>
<div class="tablewrap"><table><tr><th>ID</th><th>Status</th><th>Samples</th><th>Verbesserung</th><th>Grund</th><th>Aktion</th></tr>
{% for x in news_candidates[:50] %}<tr><td>{{x.id}}</td><td>{{x.status}}</td><td>{{x.sample_count}}</td><td>{{x.improvement}}</td><td>{{x.reason}}</td><td>{% if x.status=="PENDING" %}<form method="post" action="/lernen/decision"><input type="hidden" name="kind" value="news"><input type="hidden" name="candidate_id" value="{{x.id}}"><button name="action" value="approve">Freigeben</button> <button class="secondary" name="action" value="reject">Ablehnen</button></form>{% else %}—{% endif %}</td></tr>
{% else %}<tr><td colspan="6">Keine Nachrichten-Lernkandidaten vorhanden.</td></tr>{% endfor %}</table></div></div>''',
        families=families,candidates=candidates,news_candidates=news_candidates,news_status=news_status,
        message=message,message_level=message_level
    )

@app.get("/lernen")
def lernen_v102_clean():
    return _lernen_v102_clean()

@app.post("/lernen/decision")
def lernen_decision_v102():
    kind=request.form.get("kind")
    action=request.form.get("action")
    try:
        candidate_id=int(request.form.get("candidate_id","0"))
        if action not in ("approve","reject") or kind not in ("strategy","news"):
            raise ValueError("Ungültige Lernaktion")
        result=(ControlledLearning(legacy.db).decide(candidate_id,action)
                if kind=="strategy" else NewsLearning(legacy.db).decide(candidate_id,action))
        return _lernen_v102_clean("Lernkandidat verarbeitet: "+str(result),"ok")
    except Exception as exc:
        legacy.db.audit("V102_LEARNING_DECISION_FAILED",type(exc).__name__+":"+str(exc)[:300],"warning")
        return _lernen_v102_clean("Lernkandidat konnte nicht verarbeitet werden: "+type(exc).__name__+": "+str(exc)[:300],"error")

def _real_trading_v102_clean():
    engine=legacy.real_trade_engine
    real_state=build_real_state(legacy.db,controller)
    result=error=token=None
    if request.method=="POST":
        try:
            if request.form.get("action")=="arm":
                token=engine.arm(request.form.get("phrase"))
            else:
                result=engine.submit(
                    request.form.get("symbol"),request.form.get("side"),request.form.get("volume"),
                    request.form.get("order_type"),request.form.get("limit_price"),
                    request.form.get("client_order_id") or None,request.form.get("approval_token"),
                    request.form.get("live")!="yes",None,request.form.get("leverage") or None,
                    request.form.get("margin")=="yes",request.form.get("reduce_only")=="yes"
                )
        except Exception as exc:
            error=type(exc).__name__+":"+str(exc)[:500]
    rows=_safe_rows("SELECT id,created_at,client_order_id,symbol,side,order_type,volume,limit_price,status,validate_only,error FROM real_trade_intents ORDER BY id DESC LIMIT 50")
    return _render_v102(
        "Realhandel","Realhandel","Reale Orders bleiben separat sichtbar und benötigen globale Freigabe sowie ein zeitlich begrenztes Freigabetoken.",
        '''<div class="summary-grid"><div class="summary"><span>Global</span><b>{{real_state.status_label}}</b><small>{{real_state.summary}}</small></div><div class="summary"><span>Automatik</span><b>{{"BEREIT" if real_state.automatic_execution_ready else "BLOCKIERT"}}</b><small>{{real_state.automatic_summary}}</small></div><div class="summary"><span>Manuell</span><b>{{"VERFÜGBAR" if real_state.manual_order_available else "BLOCKIERT"}}</b><small>zusätzliche Live-Freigabe erforderlich</small></div></div>
{% if error %}<div class="card error">{{error}}</div>{% endif %}{% if result %}<div class="card"><h2>Ergebnis</h2><pre>{{result|tojson(indent=2)}}</pre></div>{% endif %}{% if token %}<div class="card warning"><b>Freigabetoken · 5 Minuten gültig</b><pre>{{token}}</pre></div>{% endif %}
<div class="card"><h2>Blockierungen</h2>{% if real_state.blockers %}<table><tr><th>Code</th><th>Grund</th></tr>{% for x in real_state.blockers %}<tr><td><code>{{x.code}}</code></td><td>{{x.reason}}</td></tr>{% endfor %}</table>{% else %}<p class="ok">Keine globale Blockierung.</p>{% endif %}</div>
<div class="card"><h2>Manuelle Order</h2><form method="post"><input type="hidden" name="action" value="submit">
<label>Symbol<input name="symbol" value="BTC/EUR" required></label><label>Seite<select name="side"><option value="buy">Buy</option><option value="sell">Sell</option></select></label>
<label>Typ<select name="order_type"><option value="limit">Limit</option><option value="market">Market</option></select></label><label>Volumen<input name="volume" required></label><label>Limitpreis<input name="limit_price"></label>
<details><summary>Erweiterte Orderoptionen</summary><label>Margin/Leverage<select name="margin"><option value="no">Spot</option><option value="yes">Margin</option></select></label><label>Hebel<input name="leverage" value="2"></label><label>Reduce-only<select name="reduce_only"><option value="no">Nein</option><option value="yes">Ja</option></select></label><label>Idempotenz-ID<input name="client_order_id"></label></details>
<label>Freigabetoken<input name="approval_token"></label><label>Ausführung<select name="live"><option value="no">Nur validieren</option><option value="yes">Live senden</option></select></label>
<button>Order prüfen / ausführen</button></form></div>
<div class="card"><h2>Live-Freigabe</h2><form method="post"><input type="hidden" name="action" value="arm"><label>Bestätigungsphrase<input name="phrase" required></label><button>Live für 5 Minuten freigeben</button></form></div>
<div class="card"><h2>Letzte Realorder-Intents</h2><div class="tablewrap"><table><tr><th>Zeit</th><th>ID</th><th>Symbol</th><th>Seite</th><th>Volumen</th><th>Status</th><th>Validierung</th></tr>{% for x in rows %}<tr><td>{{x.created_at}}</td><td>{{x.client_order_id}}</td><td>{{x.symbol}}</td><td>{{x.side}}</td><td>{{x.volume}}</td><td>{{x.status}}</td><td>{{x.validate_only}}</td></tr>{% else %}<tr><td colspan="7">Noch keine Realorder-Intents.</td></tr>{% endfor %}</table></div></div>''',
        real_state=real_state,error=error,result=result,token=token,rows=rows
    )

app.view_functions["real_trade.view"]=_real_trading_v102_clean

def _system_v102_clean(message=None,message_level=""):
    st=_current_process_status_v102()
    research=st["research"] or {}
    plan=st["plan"]
    paper=st["paper"]
    real=st["real"]
    real_run=st["real_run"]
    news=_safe_rows("SELECT COUNT(*) AS n FROM news_items")
    links=_safe_rows("SELECT COUNT(*) AS n FROM news_market_links")
    return _render_v102(
        "Systemstatus","System","Schnittstellen, Automatik und Ende-zu-Ende-Zustand an einer Stelle.",
        '''{% if message %}<div class="card {{message_level}}">{{message}}</div>{% endif %}
<div class="summary-grid"><div class="summary"><span>Public Kraken</span><b>{{market.effective_state}}</b><small>{{market.last_error or "keine Fehlermeldung"}}</small></div>
<div class="summary"><span>Private Kraken</span><b>{{private.effective_state}}</b><small>{{private.last_error or "nicht aktiviert / keine Daten"}}</small></div>
<div class="summary"><span>Research</span><b>{{research.stage or "—"}}</b><small>{{research.status or "Noch kein Lauf"}}</small></div>
<div class="summary"><span>Realhandel</span><b>{{real_state.status_label}}</b><small>{{real_state.automatic_summary}}</small></div></div>
<div class="card"><h2>End-to-End-Prozess</h2><div class="process-strip">{% for x in steps %}<div class="process-node"><span>{{loop.index}}</span><b>{{x}}</b></div>{% if not loop.last %}<i>→</i>{% endif %}{% endfor %}</div>
<div class="tablewrap"><table><tr><th>Stufe</th><th>Zustand</th><th>Nachweis</th></tr>
<tr><td>Market</td><td>{{market.effective_state}}</td><td>{{market.live_price_count_10m}} Livepreise / 10 min</td></tr>
<tr><td>News</td><td>{{news_count}}</td><td>{{news_links}} Marktverknüpfungen</td></tr>
<tr><td>Analyse</td><td>{{research.stage or "—"}}</td><td>{{research.progress_current or 0}}/{{research.progress_total or 0}}</td></tr>
<tr><td>Plan</td><td>{{"vorhanden" if plan else "noch keiner"}}</td><td>{{plan.plan_hash[:12] if plan else "—"}}</td></tr>
<tr><td>Paper</td><td>{{paper.quality if paper else "noch kein Snapshot"}}</td><td>{{paper.total_eur if paper else "—"}} €</td></tr>
<tr><td>Real</td><td>{{real.quality if real else "noch kein Snapshot"}}</td><td>{{real_run.status if real_run else "noch kein Lauf"}}</td></tr>
</table></div></div>
<div class="card"><h2>Wartung</h2><p>Netzwerk- und Prozessfehler werden innerhalb der GUI abgefangen. Es gibt nur noch wenige explizite Aktionen.</p>
<div class="section-actions"><form method="post" action="/markt/refresh"><button>Marktdaten aktualisieren</button></form><form method="post" action="/analyse/start"><button class="secondary">Analyse starten</button></form></div>
<p><a href="/steuerinfo-at">Einkommensteuer AT</a> · <a href="/health">Health JSON</a> · <a href="/api/market">Market JSON</a></p></div>''',
        market=st["market"],private=st["private"],real_state=st["real_state"],research=research,plan=plan,
        paper=paper,real=real,real_run=real_run,
        news_count=(news[0]["n"] if news else 0),news_links=(links[0]["n"] if links else 0),
        steps=["Kraken","News","Analyse","Lernen","Plan","Order","Nachweis"]
    )

@app.get("/system")
def system_v102_clean():
    return _system_v102_clean()

@app.get("/api/market")
def api_market_v102():
    return {"status":"ok","runtime":"v102","market":market_service.status(),
            "prices":_safe_rows("SELECT symbol,last,bid,ask,change_pct,received_at FROM live_prices ORDER BY symbol LIMIT 100")}

@app.get("/api/process")
def api_process_v102():
    return {"status":"ok","runtime":"v102","process":_current_process_status_v102()}

def _health_v102():
    st=_current_process_status_v102()
    return {"status":"ok","version":"0.1.0-dev.102","runtime":"v102_main",
            "market_stream":st["market"],"private_stream":st["private"],"real_state":st["real_state"],
            "research":st["research"],"plan_hash":st["plan"].get("plan_hash") if st["plan"] else None,
            "paper":st["paper"],"real":st["real"],"real_run":st["real_run"],
            "interfaces":{"public_market":"REST + WebSocket","private_account":"WebSocket when API credentials are configured",
                         "decision_pipeline":"canonical v98 planner / shared runtime","real_execution":"common guards + Kraken preflight"}}

app.view_functions["health"]=_health_v102

@app.get("/v102-health")
def v102_health():
    return jsonify(_health_v102())

LEGACY_GUI_REDIRECTS={
    "/api":"/system","/products":"/markt","/news-learning":"/lernen","/fees":"/markt","/data-quality":"/markt",
    "/decision-matrix":"/handel","/forex-shadow":"/system","/backtests":"/system","/audit":"/system",
    "/exports":"/system","/event-dashboard":"/system","/tax-info":"/steuerinfo-at","/scanner":"/analyse",
    "/paper":"/portfolio","/controlled-learning":"/lernen","/process":"/system","/settings":"/system",
    "/portfolio-modern":"/portfolio",
}
for path,target in LEGACY_GUI_REDIRECTS.items():
    for rule in list(app.url_map.iter_rules()):
        if rule.rule==path:
            endpoint=rule.endpoint
            def redirect_legacy(target=target):
                return redirect(target,code=302)
            app.view_functions[endpoint]=redirect_legacy

# Make all current same-path GUI routes canonical.
app.view_functions["index"]=_dashboard_v102
app.view_functions["analyse_v100"]=_analysis_v102_clean
app.view_functions["portfolio_v100"]=_portfolio_v102_clean
app.view_functions["handel_v100"]=_handel_v102_clean
app.view_functions["lernen_v100"]=_lernen_v102_clean
app.view_functions["diagnose_v100"]=_system_v102_clean
app.view_functions["prozess_v100"]=_system_v102_clean
app.view_functions["automatik_v100"]=_system_v102_clean

for endpoint in ("v100_health","v101_health"):
    if endpoint in app.view_functions:
        app.view_functions[endpoint]=lambda: redirect("/health",code=302)
