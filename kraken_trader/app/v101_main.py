"""KTKI v101 runtime.

One active runtime owns the current GUI, canonical decision pipeline, shared execution intent and unified Real-Handel status.
"""
VERSION = "0.1.0-dev.101"

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
from real_state_v100 import build_real_state

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

legacy.NAV_ITEMS=[("/","Übersicht"),("/analyse","Analyse"),("/portfolio","Portfolio"),("/handel","Handel"),("/lernen","Lernen"),("/diagnose","Diagnose"),("/prozess","Prozess"),("/automatik","Automatik"),("/real-trading","Realhandel"),("/steuerinfo-at","Einkommensteuer AT"),("/products","Produkte"),("/news-learning","Nachrichten-Lernen"),("/fees","Gebühren"),("/data-quality","Datenqualität"),("/backtests","Backtests"),("/decision-matrix","Regelmatrix"),("/audit","Audit"),("/exports","Export")]

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
            legacy.db.audit("V100_TAX_GUI_FAILED",type(exc).__name__+":"+str(exc)[:300],"error")
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
        '''<section class="hero"><div><span class="eyebrow">KTKI v101</span><h1>Kraken Trader</h1>
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

def _v100_chart(values):
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
        paper_chart=_v100_chart([x["total_eur"] for x in reversed(paper)]),
        real_chart=_v100_chart([x["total_eur"] for x in reversed(real)]),
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
        '''<span class="eyebrow">Prozess</span><h1>Verbindlicher v100-Ablauf</h1><div class="flow">{% for s in steps %}<div class="card"><div class="flowstep"><span class="num">{{loop.index}}</span><div><h3>{{s.t}}</h3><p>{{s.d}}</p></div></div></div>{% endfor %}</div>''',
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
def analyse_v100():return _analysis()
@app.get("/portfolio")
def portfolio_v100():return _portfolio()
@app.get("/handel")
def handel_v100():return _handel()
@app.get("/lernen")
def lernen_v100():return _lernen()
@app.get("/diagnose")
def diagnose_v100():return _diagnose()
@app.get("/prozess")
def prozess_v100():return _prozess()


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
def automatik_v100():
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
        "runtime":"v100_main",
        "real_state":real_state,
        "real_trading":real_state["manual_order_available"],
        "automatic_real_execution":real_state["automatic_execution_ready"],
        "market_stream":legacy.stream.status(),
        "private_stream":legacy.private_stream.status(),
    }

app.view_functions["health"]=_health_current

@app.get("/v100-health")
def v100_health():
    plan=_latest_plan()
    real_state=build_real_state(legacy.db,controller)
    return jsonify({
        "version":"0.1.0-dev.100",
        "runtime":"v100_main",
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
