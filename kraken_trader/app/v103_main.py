"""KTKI v103 runtime.

Single current GUI around the canonical decision process:
Market -> News -> Analysis -> Learning -> Plan -> Paper/Real -> Evidence.
"""
VERSION="0.1.0-dev.103"

import json
import os
from flask import Response, jsonify, redirect, request

import core_runtime as base
from automation_v67 import AutomationControllerV67
from controlled_learning import ControlledLearning
from news_learning import NewsLearning
from at_income_tax_v68 import AustrianTaxV68, tax_year, BMF_CAPITAL_URL, BMF_CRYPTO_URL, BMF_REPORTING_URL
from decision_pipeline_v98 import CanonicalDecisionPlannerV98
from decision_runtime_v98 import DecisionRuntimeV98
from v103_paper_engine import PaperEngineV103
from v98_real_allocator import RealPortfolioAllocatorV98
from portfolio_sync import build_rows, normalize_asset
from real_state_v102 import build_real_state
from market_feed_v102 import PublicMarketServiceV102

app=base.app
legacy=base.legacy

def _load_options():
    path=os.environ.get("APP_OPTIONS","/data/options.json")
    try:
        with open(path,encoding="utf-8") as fh:
            return json.load(fh) or {}
    except Exception:
        return {}

options=_load_options()
planner=CanonicalDecisionPlannerV98(legacy.db)

for key,default in planner.settings().items():
    value=options.get(key,default)
    normalized=("true" if value else "false") if isinstance(value,bool) else str(value)
    legacy.db.set_setting(key,normalized)

def _sync_runtime_options(opts):
    automation=bool(opts.get("automation_enabled",True))
    paper_enabled=bool(opts.get("paper_enabled",True))
    interval=max(1,int(opts.get("automation_interval_minutes",5)))
    real_enabled=bool(opts.get("real_trading_enabled",False))
    real_execute=bool(opts.get("real_execute_enabled",False))
    legacy.db.set_setting("automation_master_enabled","true" if automation else "false")
    for subsystem,cadence in (("analysis",60),("news",30),("learning",60)):
        legacy.db.set_setting("automation_"+subsystem+"_enabled","true" if automation else "false")
        legacy.db.set_setting("automation_"+subsystem+"_interval_minutes",str(cadence))
    legacy.db.set_setting("automation_paper_enabled","true" if automation and paper_enabled else "false")
    legacy.db.set_setting("automation_paper_interval_minutes","15")
    legacy.db.set_setting("automation_real_enabled","true" if automation and real_enabled else "false")
    legacy.db.set_setting("automation_real_execute_enabled","true" if automation and real_execute else "false")
    legacy.db.set_setting("automation_tick_minutes",str(interval))
    legacy.db.set_setting("automation_learning_auto_approve_enabled","false")
    legacy.db.set_setting("real_trading_enabled","true" if real_enabled else "false")
    legacy.db.set_setting("real_kill_switch","true" if bool(opts.get("real_kill_switch",True)) else "false")
    legacy.db.set_setting("real_allowed_symbols",str(opts.get("real_allowed_symbols","") or ""))
    for key in ("decision_max_position_pct","decision_cash_reserve_pct","decision_min_trade_eur","decision_max_trade_eur"):
        if key in opts:
            legacy.db.set_setting(key,str(opts[key]))

_sync_runtime_options(options)
if bool(options.get("real_execute_enabled",False)):
    legacy.real_trade_engine.ensure_automation_secret()

runtime=DecisionRuntimeV98(
    legacy.db,
    refresh_market=None,
    evaluate_forecasts=legacy.forecasts.evaluate_due,
)

paper_engine=PaperEngineV103(
    legacy.db,
    start_eur=legacy.db.value("paper_start_eur","1000"),
    fee_bps=float(planner.settings()["decision_fee_bps"]),
    slippage_bps=float(planner.settings()["decision_slippage_bps"]),
    max_position_pct=float(planner.settings()["decision_max_position_pct"]),
    trade_eur=float(planner.settings()["decision_min_trade_eur"]),
    runtime=runtime,
)

real_delegate=RealPortfolioAllocatorV98(legacy.db,legacy.real_trade_engine,runtime=runtime)

class RealAllocatorV102:
    def __init__(self,delegate):
        self.delegate=delegate

    def _sync_portfolio(self):
        try:
            client=legacy.real_trade_engine.client
            balances=client.balance()
            assets=client.assets()
            pairs=client.pairs()
            held_names={
                normalize_asset(code,assets)
                for code,value in balances.items()
                if str(value) not in ("0","0.0","0.00")
            }
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
            return {"snapshot_id":sid,"assets":len(rows),"quality":quality,"total_eur":total}
        except Exception as exc:
            detail=type(exc).__name__+":"+str(exc)[:300]
            legacy.db.audit("V102_REAL_PORTFOLIO_SYNC_FAILED",detail,"warning")
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

real_allocator=RealAllocatorV102(real_delegate)

controller=AutomationControllerV67(
    legacy.db,
    legacy.pipeline,
    legacy.news_prefilter,
    ControlledLearning(legacy.db),
    NewsLearning(legacy.db),
    lambda: paper_engine.run(),
    real_allocator,
)
legacy.controller=controller
base.controller=controller

market_service=PublicMarketServiceV102(
    legacy.db,
    legacy.client,
    legacy.universe,
    legacy.stream,
    max_symbols=int(legacy.db.value("v102_market_symbol_limit","30")),
)
legacy.refresh_allowed_prices=market_service.refresh_for_process
runtime.refresh_market=market_service.refresh_for_process

# Public market data never depends on private API credentials.
legacy.stream.enabled=True
legacy.private_stream.enabled=bool(
    getattr(legacy.client,"key","") and getattr(legacy.client,"secret","")
)

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

controller.start_background()
market_service.start_background()
if legacy.private_stream.enabled:
    legacy.private_stream.start()

def _safe_rows(query,params=()):
    try:
        return legacy.db.rows(query,params)
    except Exception as exc:
        legacy.db.audit("V102_GUI_QUERY_FAILED",type(exc).__name__+":"+str(exc)[:300],"error")
        return []

def _latest_plan():
    rows=_safe_rows("SELECT * FROM decision_plan_runs_v98 ORDER BY id DESC LIMIT 1")
    if not rows:
        return None
    row=dict(rows[0])
    try:
        row["settings"]=json.loads(row.get("settings_json") or "{}")
    except Exception:
        row["settings"]={}
    return row

def _latest_research():
    try:
        return legacy.pipeline.latest() or {}
    except Exception:
        return {}

def _decision_rows(limit=80):
    return _safe_rows(
        "SELECT * FROM decision_snapshots ORDER BY id DESC LIMIT ?",
        (max(1,min(200,int(limit))),),
    )

def _latest_snapshot(table):
    rows=_safe_rows(f"SELECT created_at,total_eur,quality FROM {table} ORDER BY id DESC LIMIT 1")
    return rows[0] if rows else None

def _chart(values):
    vals=[]
    for value in values or []:
        try:
            vals.append(float(value))
        except (TypeError,ValueError):
            pass
    if not vals:
        return '<svg viewBox="0 0 800 170" class="chart"><text x="24" y="90">Noch keine Historie</text></svg>'
    lo,hi=min(vals),max(vals)
    if lo==hi:
        lo-=1
        hi+=1
    points=[]
    for i,value in enumerate(vals):
        x=24+752*i/max(1,len(vals)-1)
        y=22+120*(1-(value-lo)/(hi-lo))
        points.append(f"{x:.1f},{y:.1f}")
    return f'<svg viewBox="0 0 800 170" class="chart" role="img" aria-label="Portfolioverlauf"><line x1="24" y1="145" x2="776" y2="145" class="chart-axis"/><polyline points="{" ".join(points)}" class="chart-line" fill="none"/><text x="24" y="13" class="chart-label">Max {hi:.2f} €</text><text x="24" y="166" class="chart-label">Min {lo:.2f} €</text><text x="776" y="13" text-anchor="end" class="chart-value">Aktuell {vals[-1]:.2f} €</text></svg>'

def _state():
    news=_safe_rows("SELECT COUNT(*) AS n FROM news_items")
    links=_safe_rows("SELECT COUNT(*) AS n FROM news_market_links")
    real_run=_safe_rows("SELECT created_at,status,details_json FROM real_allocation_runs ORDER BY id DESC LIMIT 1")
    return {
        "market":market_service.status(),
        "private":legacy.private_stream.status(),
        "news_count":int(news[0]["n"]) if news else 0,
        "news_links":int(links[0]["n"]) if links else 0,
        "research":_latest_research(),
        "plan":_latest_plan(),
        "paper":_latest_snapshot("paper_snapshots"),
        "real":_latest_snapshot("portfolio_snapshots"),
        "real_run":real_run[0] if real_run else None,
        "real_state":build_real_state(legacy.db,controller),
    }

def _dashboard():
    st=_state()
    return legacy.page(
        '''<span class="eyebrow">KTKI v102</span><h1>Kraken Trader</h1>
<p class="lead">Marktdaten → News → Analyse → Lernen → Plan → Order.</p>
<div class="summary-grid">
<div class="summary"><span>Public Market</span><b>{{market.effective_state}}</b><small>{{market.symbol_count}} WS-Symbole · {{market.live_price_count_10m}} Livepreise</small></div>
<div class="summary"><span>News</span><b>{{news_count}}</b><small>{{news_links}} Marktverknüpfungen</small></div>
<div class="summary"><span>Analyse</span><b>{{research.stage or "—"}}</b><small>{{research.status or "Noch kein Lauf"}}</small></div>
<div class="summary"><span>Realhandel</span><b>{{real_state.status_label}}</b><small>{{"Automatik bereit" if real_state.automatic_execution_ready else "nicht vollständig freigegeben"}}</small></div>
</div>
<div class="card"><h2>Prozess</h2><div class="process-strip">{% for x in steps %}<div class="process-node"><span>{{loop.index}}</span><b>{{x}}</b></div>{% if not loop.last %}<i>→</i>{% endif %}{% endfor %}</div>
<p><a class="button" href="/markt">Marktdaten</a> <a class="button secondary" href="/analyse">Analyse</a> <a class="button secondary" href="/system">System</a></p></div>
<div class="card"><h2>Letzte Entscheidungen</h2><div class="tablewrap"><table><tr><th>Zeit</th><th>Umgebung</th><th>Symbol</th><th>Aktion</th><th>Target</th><th>Delta</th><th>Status</th></tr>{% for x in decisions %}<tr><td>{{x.created_at}}</td><td>{{x.environment}}</td><td>{{x.symbol}}</td><td>{{x.action_type or x.action}}</td><td>{{x.target_exposure_eur}} €</td><td>{{x.delta_eur}} €</td><td>{{x.status}}</td></tr>{% else %}<tr><td colspan="7">Noch keine Entscheidungen.</td></tr>{% endfor %}</table></div></div>''',
        market=st["market"],news_count=st["news_count"],news_links=st["news_links"],
        research=st["research"],real_state=st["real_state"],decisions=_decision_rows(10),
        steps=["Kraken","News","Analyse","Lernen","Plan","Order"],
    )

app.view_functions["index"]=_dashboard

def _market_page(message=None,level=""):
    status=market_service.status()
    all_prices=_safe_rows("SELECT symbol,last,bid,ask,change_pct,received_at FROM live_prices ORDER BY symbol LIMIT 200")
    wanted=set(status.get("symbols") or [])
    prices=[row for row in all_prices if row.get("symbol") in wanted] if wanted else all_prices[:30]
    universe=_safe_rows("SELECT symbol,asset_class,category,status FROM market_universe ORDER BY category,symbol LIMIT 60")
    return legacy.page(
        '''<span class="eyebrow">Kraken Market</span><h1>Markt & Daten</h1>
<p class="lead">Public Market ist unabhängig von den privaten API-Zugangsdaten. REST-Snapshot und WebSocket werden gemeinsam dargestellt.</p>
{% if message %}<div class="card {{level}}">{{message}}</div>{% endif %}
<div class="summary-grid"><div class="summary"><span>WebSocket</span><b>{{status.effective_state}}</b><small>{{status.system_status or "—"}} · {{status.last_message_at or "noch keine Nachricht"}}</small></div>
<div class="summary"><span>Livepreise</span><b>{{status.live_price_count_10m}}</b><small>letzte 10 Minuten</small></div>
<div class="summary"><span>Symbole</span><b>{{status.symbol_count}}</b><small>{{status.blocked_symbol_count}} abgewiesen</small></div>
<div class="summary"><span>REST</span><b>{{status.last_rest_refresh or "—"}}</b><small>{{status.last_refresh_result.get("saved",0) if status.last_refresh_result else 0}} gespeichert</small></div></div>
<div class="card"><h2>Verbindung</h2><p>{{status.last_error or "Keine aktuelle Stream-Fehlermeldung."}}</p><form method="post" action="/markt/refresh"><button>Marktdaten aktualisieren</button></form></div>
<div class="card"><h2>Aktuelle Preise</h2><div class="tablewrap"><table><tr><th>Symbol</th><th>Last</th><th>Bid</th><th>Ask</th><th>Änderung</th><th>Zeit</th></tr>{% for x in prices %}<tr><td>{{x.symbol}}</td><td>{{x.last}}</td><td>{{x.bid or "—"}}</td><td>{{x.ask or "—"}}</td><td>{{x.change_pct or "—"}}%</td><td>{{x.received_at}}</td></tr>{% else %}<tr><td colspan="6">Noch keine Preise verfügbar.</td></tr>{% endfor %}</table></div></div>
<div class="card"><h2>Marktuniversum</h2><div class="tablewrap"><table><tr><th>Symbol</th><th>Klasse</th><th>Kategorie</th><th>Status</th></tr>{% for x in universe %}<tr><td>{{x.symbol}}</td><td>{{x.asset_class}}</td><td>{{x.category}}</td><td>{{x.status}}</td></tr>{% else %}<tr><td colspan="4">Universe wird noch synchronisiert.</td></tr>{% endfor %}</table></div></div>''',
        status=status,prices=prices,universe=universe,message=message,level=level,
    )

@app.get("/markt")
def markt():
    return _market_page()

@app.post("/markt/refresh")
def markt_refresh():
    try:
        result=market_service.bootstrap(force=True)
        return _market_page(
            "Marktdaten aktualisiert: {} Preise gespeichert; {} WS-Symbole aktiv.".format(
                result.get("saved",0),len(result.get("symbols",[]))
            ),
            "ok" if result.get("saved") else "warning",
        )
    except Exception as exc:
        return _market_page(
            "Marktdaten konnten nicht aktualisiert werden: "+type(exc).__name__+": "+str(exc)[:300],
            "error",
        )

def _analyse(message=None,level=""):
    research=_latest_research()
    rows=_safe_rows("""SELECT s.symbol,s.signal,s.score,s.momentum_pct,s.trend_pct,s.volatility_pct,s.spread_pct,s.news_score,s.quality,s.scanned_at,u.category
                       FROM scanner_results s LEFT JOIN market_universe u ON u.symbol=s.symbol
                       WHERE s.quality IN ('VALID','CACHED')
                       ORDER BY CAST(s.score AS REAL) DESC LIMIT 80""")
    return legacy.page(
        '''<span class="eyebrow">Analyse</span><h1>Analyse</h1>
<p class="lead">Eine Aktion startet den vollständigen Forschungsprozess. Das Ergebnis wird später vom gemeinsamen Plan verwendet.</p>
{% if message %}<div class="card {{level}}">{{message}}</div>{% endif %}
<div class="card"><form method="post" action="/analyse/start"><button>Analyseprozess starten</button></form><p><b>Letzter Lauf:</b> {{research.stage or "—"}} · {{research.status or "Noch kein Lauf"}} · {{research.progress_current or 0}}/{{research.progress_total or 0}}</p></div>
<div class="card"><h2>Kandidaten</h2><div class="tablewrap"><table><tr><th>Symbol</th><th>Klasse</th><th>Signal</th><th>Score</th><th>Momentum</th><th>Trend</th><th>Volatilität</th><th>Spread</th><th>News</th></tr>{% for x in rows %}<tr><td>{{x.symbol}}</td><td>{{x.category or "—"}}</td><td>{{x.signal}}</td><td>{{x.score}}</td><td>{{x.momentum_pct}}%</td><td>{{x.trend_pct}}%</td><td>{{x.volatility_pct}}%</td><td>{{x.spread_pct}}%</td><td>{{x.news_score}}</td></tr>{% else %}<tr><td colspan="9">Noch keine Kandidaten.</td></tr>{% endfor %}</table></div></div>''',
        research=research,rows=rows,message=message,level=level,
    )

@app.get("/analyse")
def analyse():
    return _analyse()

@app.post("/analyse/start")
def analyse_start():
    try:
        result=legacy.pipeline.start()
        status=str(result.get("status","")).upper() if isinstance(result,dict) else "QUEUED"
        return _analyse(
            "Analyseprozess gestartet." if status=="QUEUED" else "Analyseprozess meldet: "+str(result),
            "ok" if status in ("QUEUED","BUSY","COMPLETED") else "warning",
        )
    except Exception as exc:
        legacy.db.audit("V102_ANALYSE_START_FAILED",type(exc).__name__+":"+str(exc)[:300],"warning")
        return _analyse("Analyseprozess konnte nicht gestartet werden: "+type(exc).__name__+": "+str(exc)[:300],"error")

def _portfolio(message=None,level=""):
    paper=_safe_rows("SELECT created_at,total_eur,quality FROM paper_snapshots ORDER BY id DESC LIMIT 120")
    real=_safe_rows("SELECT created_at,total_eur,quality FROM portfolio_snapshots ORDER BY id DESC LIMIT 120")
    paper_pos=[dict(x) for x in _safe_rows("SELECT symbol,quantity,avg_cost_eur FROM paper_positions WHERE CAST(quantity AS REAL)<>0 ORDER BY symbol")]
    real_pos=_safe_rows("SELECT asset,display_name,amount,eur_price,eur_value,classification FROM portfolio_assets WHERE classification='HELD' AND CAST(amount AS REAL)<>0 ORDER BY display_name")
    margin=_safe_rows("SELECT symbol,side,volume,current_value,unrealized_pnl,leverage FROM real_margin_positions ORDER BY symbol")
    decisions=_decision_rows(20)
    for item in paper_pos:
        try:
            prices=_safe_rows("SELECT last FROM live_prices WHERE symbol=? LIMIT 1",(item["symbol"],))
            px=float(prices[0]["last"]) if prices and float(prices[0]["last"])>0 else None
            if px is not None and str(item["symbol"]).upper().endswith("/USD"):
                fx=_safe_rows("SELECT last FROM live_prices WHERE UPPER(symbol)='EUR/USD' LIMIT 1")
                rate=float(fx[0]["last"]) if fx and float(fx[0]["last"])>0 else None
                px=px/rate if rate else None
            value=float(item["quantity"])*px if px is not None else None
            cost=float(item["quantity"])*float(item["avg_cost_eur"])
            item["current_eur"]=f"{value:.4f}" if value is not None else None
            item["pnl_eur"]=f"{value-cost:.4f}" if value is not None else None
        except Exception:
            item["current_eur"]=item["pnl_eur"]=None
    return legacy.page(
        '''<span class="eyebrow">Portfolio</span><h1>Portfolio</h1>
<p class="lead">Paper- und Realpositionen, Equity und Zielpositionen auf einer Seite.</p>
{% if message %}<div class="card {{level}}">{{message}}</div>{% endif %}
<div class="chart-grid"><div class="chart-card"><b>Paper Equity</b>{{paper_chart|safe}}</div><div class="chart-card"><b>Real Equity</b>{{real_chart|safe}}</div></div>
<div class="card"><h2>Paper-Depot</h2><div class="tablewrap"><table><tr><th>Symbol</th><th>Menge</th><th>Einstand</th><th>Aktuell</th><th>U/L</th></tr>{% for x in paper_pos %}<tr><td>{{x.symbol}}</td><td>{{x.quantity}}</td><td>{{x.avg_cost_eur}} €</td><td>{{x.current_eur or "—"}} €</td><td>{{x.pnl_eur or "—"}} €</td></tr>{% else %}<tr><td colspan="5">Keine Paper-Positionen.</td></tr>{% endfor %}</table></div></div>
<div class="card"><h2>Reales Depot</h2><div class="tablewrap"><table><tr><th>Asset</th><th>Menge</th><th>EUR-Kurs</th><th>EUR-Wert</th><th>Status</th></tr>{% for x in real_pos %}<tr><td>{{x.display_name or x.asset}}</td><td>{{x.amount}}</td><td>{{x.eur_price or "—"}}</td><td>{{x.eur_value or "—"}} €</td><td>{{x.classification}}</td></tr>{% else %}<tr><td colspan="5">Keine realen Positionen im Snapshot.</td></tr>{% endfor %}</table></div>{% if margin %}<h3>Offene Margin-Positionen</h3><div class="tablewrap"><table><tr><th>Symbol</th><th>Seite</th><th>Menge</th><th>Wert</th><th>U/L</th><th>Hebel</th></tr>{% for x in margin %}<tr><td>{{x.symbol}}</td><td>{{x.side}}</td><td>{{x.volume}}</td><td>{{x.current_value or "—"}} €</td><td>{{x.unrealized_pnl or "—"}} €</td><td>{{x.leverage or "1"}}x</td></tr>{% endfor %}</table></div>{% endif %}</div>
<div class="card"><h2>Target vs. Current</h2>{% for x in decisions %}<div class="allocation"><div><b>{{x.symbol}}</b><small>{{x.environment}} · {{x.action_type or x.action}} · {{x.status}}</small></div><strong>{{x.target_exposure_eur}} €</strong></div>{% else %}<span class="muted">Noch kein Plan.</span>{% endfor %}</div>
{% if api_ready %}<div class="card"><form method="post" action="/portfolio/sync"><button>Reales Depot synchronisieren</button></form></div>{% endif %}''',
        paper_chart=_chart([x["total_eur"] for x in reversed(paper)]),
        real_chart=_chart([x["total_eur"] for x in reversed(real)]),
        paper_pos=paper_pos,real_pos=real_pos,margin=margin,decisions=decisions,
        api_ready=bool(getattr(legacy.client,"key","") and getattr(legacy.client,"secret","")),
        message=message,level=level,
    )

@app.get("/portfolio")
def portfolio():
    return _portfolio()

@app.post("/portfolio/sync")
def portfolio_sync():
    if not (getattr(legacy.client,"key","") and getattr(legacy.client,"secret","")):
        return _portfolio("Keine Kraken Private API-Zugangsdaten konfiguriert.","warning")
    try:
        legacy.client.balance()
        balances=legacy.client.balance()
        assets=legacy.client.assets()
        pairs=legacy.client.pairs()
        names={normalize_asset(x,assets) for x in balances}
        relevant=[pair.get("altname",pid) for pid,pair in pairs.items()
                  if normalize_asset(pair.get("base",""),assets) in names
                  and normalize_asset(pair.get("quote",""),assets)=="EUR"]
        tickers=legacy.client.ticker(relevant) if relevant else {}
        rows,total,quality=build_rows(balances,set(),assets,pairs,tickers)
        legacy.db.replace_balances(balances)
        legacy.db.store_portfolio(rows,total,quality)
        return _portfolio("Reales Depot erfolgreich synchronisiert.","ok")
    except Exception as exc:
        legacy.db.audit("V102_PORTFOLIO_SYNC_FAILED",type(exc).__name__+":"+str(exc)[:300],"warning")
        return _portfolio("Depot-Synchronisierung fehlgeschlagen: "+type(exc).__name__+": "+str(exc)[:300],"error")

def _handel():
    plan=_latest_plan()
    return legacy.page(
        '''<span class="eyebrow">Entscheidungen</span><h1>Handel</h1>
<p class="lead">Der gemeinsame Plan für Paper und Real. Hier wird nichts separat neu berechnet.</p>
<div class="summary-grid"><div class="summary"><span>Plan</span><b>{{plan.plan_hash[:12] if plan else "—"}}</b><small>{{plan.environment if plan else "—"}}</small></div><div class="summary"><span>Entscheidungen</span><b>{{decisions|length}}</b><small>letzte 120</small></div></div>
<div class="card"><div class="tablewrap"><table><tr><th>Zeit</th><th>Umgebung</th><th>Symbol</th><th>Typ</th><th>Aktion</th><th>Netto-Edge</th><th>Current</th><th>Target</th><th>Delta</th><th>Route</th><th>Status</th></tr>{% for x in decisions %}<tr><td>{{x.created_at}}</td><td>{{x.environment}}</td><td>{{x.symbol}}</td><td>{{x.action_type or "—"}}</td><td>{{x.action}}</td><td>{{x.expected_edge_after_costs_pct or "—"}}%</td><td>{{x.current_exposure_eur}} €</td><td>{{x.target_exposure_eur}} €</td><td>{{x.delta_eur}} €</td><td>{{x.execution_symbol or "—"}}</td><td>{{x.status}}</td></tr>{% else %}<tr><td colspan="11">Noch keine Entscheidungen.</td></tr>{% endfor %}</table></div></div>''',
        plan=plan,decisions=_decision_rows(120),
    )

@app.get("/handel")
def handel():
    return _handel()

def _lernen(message=None,level=""):
    cl=ControlledLearning(legacy.db)
    nl=NewsLearning(legacy.db)
    families=cl.family_overview()
    candidates=cl.candidates()
    news_candidates=nl.candidates()
    try:
        news_status=nl.data_status()
    except Exception:
        news_status={"status":"UNAVAILABLE","sample_count":0,"missing":0}
    return legacy.page(
        '''<span class="eyebrow">Lernen</span><h1>Lernen</h1>
<p class="lead">Neue Parameter werden niemals automatisch aktiv. Nur explizit freigegebene Kandidaten dürfen die aktive Version ersetzen.</p>
{% if message %}<div class="card {{level}}">{{message}}</div>{% endif %}
<div class="learning-grid">{% for x in families %}<div class="learning-card"><span class="eyebrow">{{x.family}}</span><h3>Aktiv v{{x.active_version or "—"}}</h3><b>{{x.pending_count}} offen</b><small>{{x.latest_status}}</small></div>{% endfor %}</div>
<div class="card"><h2>Strategie-Kandidaten</h2><div class="tablewrap"><table><tr><th>ID</th><th>Familie</th><th>Status</th><th>Samples</th><th>Verbesserung</th><th>Aktion</th></tr>{% for x in candidates[:60] %}<tr><td>{{x.id}}</td><td>{{x.family}}</td><td>{{x.status}}</td><td>{{x.sample_count}}</td><td>{{x.improvement}}</td><td>{% if x.status=="PENDING" %}<form method="post" action="/lernen/decision"><input type="hidden" name="kind" value="strategy"><input type="hidden" name="candidate_id" value="{{x.id}}"><button name="action" value="approve">Freigeben</button> <button class="secondary" name="action" value="reject">Ablehnen</button></form>{% else %}—{% endif %}</td></tr>{% else %}<tr><td colspan="6">Keine Kandidaten vorhanden.</td></tr>{% endfor %}</table></div></div>
<div class="card"><h2>Nachrichten-Lernen</h2><p>Status: <b>{{news_status.status}}</b> · {{news_status.sample_count}} gültige Beobachtungen · {{news_status.missing}} fehlen.</p><div class="tablewrap"><table><tr><th>ID</th><th>Status</th><th>Samples</th><th>Verbesserung</th><th>Aktion</th></tr>{% for x in news_candidates[:50] %}<tr><td>{{x.id}}</td><td>{{x.status}}</td><td>{{x.sample_count}}</td><td>{{x.improvement}}</td><td>{% if x.status=="PENDING" %}<form method="post" action="/lernen/decision"><input type="hidden" name="kind" value="news"><input type="hidden" name="candidate_id" value="{{x.id}}"><button name="action" value="approve">Freigeben</button> <button class="secondary" name="action" value="reject">Ablehnen</button></form>{% else %}—{% endif %}</td></tr>{% else %}<tr><td colspan="5">Keine Nachrichten-Lernkandidaten vorhanden.</td></tr>{% endfor %}</table></div></div>''',
        families=families,candidates=candidates,news_candidates=news_candidates,news_status=news_status,message=message,level=level,
    )

@app.get("/lernen")
def lernen():
    return _lernen()

@app.post("/lernen/decision")
def lernen_decision():
    kind=request.form.get("kind")
    action=request.form.get("action")
    try:
        candidate_id=int(request.form.get("candidate_id","0"))
        if kind not in ("strategy","news") or action not in ("approve","reject"):
            raise ValueError("Ungültige Lernaktion")
        result=(ControlledLearning(legacy.db).decide(candidate_id,action)
                if kind=="strategy" else NewsLearning(legacy.db).decide(candidate_id,action))
        return _lernen("Lernkandidat verarbeitet.","ok")
    except Exception as exc:
        legacy.db.audit("V102_LEARNING_DECISION_FAILED",type(exc).__name__+":"+str(exc)[:300],"warning")
        return _lernen("Lernkandidat konnte nicht verarbeitet werden: "+type(exc).__name__+": "+str(exc)[:300],"error")

def _real_trading():
    engine=legacy.real_trade_engine
    real_state=build_real_state(legacy.db,controller)
    result=error=token=None
    if request.method=="POST":
        try:
            if request.form.get("action")=="arm":
                token=engine.arm(request.form.get("phrase"))
            else:
                live=request.form.get("live")=="yes"
                if live and not real_state["manual_order_available"]:
                    raise ValueError("Manuelle Realorder ist global blockiert.")
                result=engine.submit(
                    request.form.get("symbol"),request.form.get("side"),request.form.get("volume"),
                    request.form.get("order_type"),request.form.get("limit_price"),
                    request.form.get("client_order_id") or None,request.form.get("approval_token"),
                    not live,None,request.form.get("leverage") or None,
                    request.form.get("margin")=="yes",request.form.get("reduce_only")=="yes",
                )
        except Exception as exc:
            error=type(exc).__name__+":"+str(exc)[:500]
    rows=_safe_rows("SELECT id,created_at,client_order_id,symbol,side,order_type,volume,status,validate_only,error FROM real_trade_intents ORDER BY id DESC LIMIT 40")
    return legacy.page(
        '''<span class="eyebrow">Realhandel</span><h1>Realhandel</h1>
<p class="lead">Reale Orders bleiben getrennt und werden nur nach globaler Freigabe und zusätzlicher Live-Bestätigung übermittelt.</p>
<div class="summary-grid"><div class="summary"><span>Global</span><b>{{real_state.status_label}}</b><small>{{real_state.summary}}</small></div><div class="summary"><span>Automatik</span><b>{{"BEREIT" if real_state.automatic_execution_ready else "BLOCKIERT"}}</b><small>{{real_state.automatic_summary}}</small></div><div class="summary"><span>Manuell</span><b>{{"VERFÜGBAR" if real_state.manual_order_available else "BLOCKIERT"}}</b><small>Live erfordert Freigabetoken</small></div></div>
{% if error %}<div class="card error">{{error}}</div>{% endif %}{% if result %}<div class="card"><h2>Ergebnis</h2><pre>{{result|tojson(indent=2)}}</pre></div>{% endif %}{% if token %}<div class="card warning"><b>Freigabetoken · 5 Minuten gültig</b><pre>{{token}}</pre></div>{% endif %}
<div class="card"><h2>Manuelle Order</h2><form method="post"><input type="hidden" name="action" value="submit">
<label>Symbol<input name="symbol" value="BTC/EUR" required></label><label>Seite<select name="side"><option value="buy">Buy</option><option value="sell">Sell</option></select></label>
<label>Typ<select name="order_type"><option value="limit">Limit</option><option value="market">Market</option></select></label><label>Volumen<input name="volume" required></label><label>Limitpreis<input name="limit_price"></label>
<details><summary>Erweiterte Optionen</summary><label>Margin<select name="margin"><option value="no">Spot</option><option value="yes">Margin</option></select></label><label>Hebel<input name="leverage" value="2"></label><label>Reduce-only<select name="reduce_only"><option value="no">Nein</option><option value="yes">Ja</option></select></label><label>Idempotenz-ID<input name="client_order_id"></label></details>
<label>Freigabetoken<input name="approval_token"></label><label>Ausführung<select name="live"><option value="no">Nur validieren</option>{% if real_state.manual_order_available %}<option value="yes">Live senden</option>{% endif %}</select></label>
<button>Order prüfen / ausführen</button></form></div>
<div class="card"><h2>Live-Freigabe</h2><form method="post"><input type="hidden" name="action" value="arm"><label>Bestätigungsphrase<input name="phrase" required></label><button>Live für 5 Minuten freigeben</button></form></div>
<div class="card"><h2>Letzte Realorder-Intents</h2><div class="tablewrap"><table><tr><th>Zeit</th><th>ID</th><th>Symbol</th><th>Seite</th><th>Volumen</th><th>Status</th><th>Validierung</th></tr>{% for x in rows %}<tr><td>{{x.created_at}}</td><td>{{x.client_order_id}}</td><td>{{x.symbol}}</td><td>{{x.side}}</td><td>{{x.volume}}</td><td>{{x.status}}</td><td>{{x.validate_only}}</td></tr>{% else %}<tr><td colspan="7">Noch keine Realorder-Intents.</td></tr>{% endfor %}</table></div></div>''',
        real_state=real_state,error=error,result=result,token=token,rows=rows,
    )

app.view_functions["real_trade.view"]=_real_trading

def _system():
    st=_state()
    research=st["research"] or {}
    plan=st["plan"]
    paper=st["paper"]
    real=st["real"]
    real_run=st["real_run"]
    return legacy.page(
        '''<span class="eyebrow">System</span><h1>Systemstatus</h1>
<p class="lead">Schnittstellen, Automatik und Ende-zu-Ende-Zustand. Keine eigenständigen Fachseiten mehr.</p>
<div class="summary-grid"><div class="summary"><span>Public Kraken</span><b>{{market.effective_state}}</b><small>{{market.last_error or "keine Fehlermeldung"}}</small></div><div class="summary"><span>Private Kraken</span><b>{{private.effective_state}}</b><small>{{private.last_error or "nicht aktiviert / keine Daten"}}</small></div><div class="summary"><span>Research</span><b>{{research.stage or "—"}}</b><small>{{research.status or "Noch kein Lauf"}}</small></div><div class="summary"><span>Realhandel</span><b>{{real_state.status_label}}</b><small>{{real_state.automatic_summary}}</small></div></div>
<div class="card"><h2>End-to-End</h2><div class="process-strip">{% for x in steps %}<div class="process-node"><span>{{loop.index}}</span><b>{{x}}</b></div>{% if not loop.last %}<i>→</i>{% endif %}{% endfor %}</div>
<div class="tablewrap"><table><tr><th>Stufe</th><th>Zustand</th><th>Nachweis</th></tr><tr><td>Market</td><td>{{market.effective_state}}</td><td>{{market.live_price_count_10m}} Livepreise / 10 min</td></tr><tr><td>News</td><td>{{news_count}}</td><td>{{news_links}} Marktverknüpfungen</td></tr><tr><td>Analyse</td><td>{{research.stage or "—"}}</td><td>{{research.progress_current or 0}}/{{research.progress_total or 0}}</td></tr><tr><td>Plan</td><td>{{"vorhanden" if plan else "noch keiner"}}</td><td>{{plan.plan_hash[:12] if plan else "—"}}</td></tr><tr><td>Paper</td><td>{{paper.quality if paper else "noch kein Snapshot"}}</td><td>{{paper.total_eur if paper else "—"}} €</td></tr><tr><td>Real</td><td>{{real.quality if real else "noch kein Snapshot"}}</td><td>{{real_run.status if real_run else "noch kein Lauf"}}</td></tr></table></div></div>
<div class="card"><h2>Systemaktionen</h2><form method="post" action="/system/refresh"><button>Systemdaten aktualisieren</button></form><p><a href="/steuerinfo-at">Einkommensteuer AT</a></p></div>''',
        market=st["market"],private=st["private"],real_state=st["real_state"],research=research,plan=plan,
        paper=paper,real=real,real_run=real_run,news_count=st["news_count"],news_links=st["news_links"],
        steps=["Kraken","News","Analyse","Lernen","Plan","Order","Nachweis"],
    )

@app.get("/system")
def system():
    return _system()

@app.post("/system/refresh")
def system_refresh():
    try:
        market_service.bootstrap(force=True)
        return _system()
    except Exception as exc:
        return _system()

tax_service=AustrianTaxV68(legacy.db)

def _tax_page():
    year=tax_year(request.values.get("year"))
    report=latest=error=None
    if request.method=="POST":
        try:
            report=tax_service.generate(year,refresh=request.form.get("refresh","yes")=="yes")
        except Exception as exc:
            legacy.db.audit("V103_TAX_GUI_FAILED",type(exc).__name__+":"+str(exc)[:300],"error")
            error=type(exc).__name__+":"+str(exc)[:300]
    else:
        latest=tax_service.latest(year)
    latest_summary={}
    if latest:
        try:
            latest_summary=json.loads(latest.get("summary_json") or "{}")
        except Exception:
            latest_summary={}
    return legacy.page(
        '''<span class="eyebrow">Österreich · Einkommensteuer</span><h1>Einkommensteuer / KESt</h1>
<p class="lead">Arbeits- und Prüfhilfe für den österreichischen Trading-Steuerbericht.</p>
<div class="card"><h2>Steuerrahmen und offizielle Quellen</h2>
<p>{{(latest_summary.get("tax_scope") or "Kapitalvermögens- und Kryptofälle werden mit dokumentierten Prüffeldern ausgewertet. Fälle außerhalb des hier verwendeten Arbeitsrahmens bleiben ausdrücklich Prüffälle.")}}</p>
<p><b>Berechnungsparameter:</b> {{(latest_summary.get("tax_rate_reference") or "27,5 % als Rechenparameter für entsprechend eingeordnete Kapital-/Kryptofälle; die konkrete steuerliche Einordnung ist zu prüfen.")}}</p>
<p><a href="{{bmf_capital}}" target="_blank" rel="noopener">BMF · Besteuerung von Kapitalerträgen</a> ·
<a href="{{bmf_crypto}}" target="_blank" rel="noopener">BMF · Steuerliche Behandlung von Kryptowährungen</a> ·
<a href="{{bmf_reporting}}" target="_blank" rel="noopener">BMF · Informationen zu Einkünften aus Kapitalvermögen</a></p>
<p>{{(latest_summary.get("loss_offset_note") or "Verlustausgleich und Sonderfälle werden nicht automatisch abschließend beurteilt und müssen anhand der vollständigen Unterlagen geprüft werden.")}}</p></div>
{% if error %}<div class="card error">{{error}}</div>{% endif %}
<div class="card"><form method="post"><label>Steuerjahr<input name="year" type="number" min="2009" value="{{year}}"></label><label>Kraken-Daten<select name="refresh"><option value="yes">aktualisieren</option><option value="no">nur vorhandene Daten rechnen</option></select></label><button>Steuerbericht erstellen</button></form></div>
{% if report %}<div class="summary-grid"><div class="summary"><span>Status</span><b>{{report.summary.status}}</b></div><div class="summary"><span>Positive Ergebnisse</span><b>{{report.summary.realized_positive_eur}} €</b></div><div class="summary"><span>Negative Ergebnisse</span><b>{{report.summary.realized_negative_eur}} €</b></div><div class="summary"><span>Steuerwert</span><b>{{report.summary.estimated_tax_eur}} €</b></div><div class="summary"><span>Prüffälle</span><b>{{report.summary.review_count}}</b></div></div>
<div class="card"><h2>E1kv-Arbeitswerte</h2><div class="tablewrap"><table><tr><th>Kategorie</th><th>EUR</th><th>Status</th></tr>{% for x in report.e1kv_summary %}<tr><td>{{x.category}}</td><td>{{x.amount_eur}}</td><td>{{x.status}}</td></tr>{% endfor %}</table></div></div>
{% if report.warnings %}<div class="card warning"><h2>Prüfhinweise</h2><ul>{% for x in report.warnings %}<li>{{x}}</li>{% endfor %}</ul></div>{% endif %}
<div class="card"><h2>Exporte</h2><p><a class="button" href="/tax-info.zip?year={{year}}">Komplettpaket ZIP</a> <a class="button secondary" href="/tax-info.csv?year={{year}}">Realisierte Geschäfte CSV</a></p></div>
{% elif latest %}<div class="card"><h2>Letzter Bericht</h2><p>{{latest.status}} · {{latest.trade_count}} Trades · {{latest.review_count}} Prüffälle</p><a class="button" href="/tax-info.zip?year={{year}}">ZIP exportieren</a> <a class="button secondary" href="/tax-info.csv?year={{year}}">CSV exportieren</a></div>{% endif %}
<div class="card"><small>Arbeits- und Prüfhilfe; keine Steuer- oder Rechtsberatung. Die endgültige steuerliche Beurteilung muss anhand der vollständigen Unterlagen erfolgen.</small></div>''',
        year=year,report=report,latest=latest,error=error,latest_summary=latest_summary,
        bmf_capital=BMF_CAPITAL_URL,bmf_crypto=BMF_CRYPTO_URL,bmf_reporting=BMF_REPORTING_URL,
    )

@app.route("/steuerinfo-at",methods=["GET","POST"])
def steuerinfo():
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
    return Response(row["realized_csv"],mimetype="text/csv",headers={"Content-Disposition":f"attachment; filename=steuer-at-{row['tax_year']}-realized.csv"})

def _health():
    st=_state()
    return {
        "status":"ok",
        "version":VERSION,
        "runtime":"v103_main",
        "market":st["market"],
        "private_stream":st["private"],
        "news":{"items":st["news_count"],"market_links":st["news_links"]},
        "research":st["research"],
        "plan":st["plan"],
        "paper":st["paper"],
        "real":st["real"],
        "real_run":st["real_run"],
        "real_state":st["real_state"],
        "interfaces":{
            "public_market":"REST + WebSocket",
            "private_account":"read-only WebSocket when credentials exist",
            "process":"Market -> News -> Analysis -> Learning -> Plan -> Execution",
        },
    }

app.view_functions["health"]=_health

@app.get("/v103-health")
def v103_health():
    return jsonify(_health())

@app.get("/api/market")
def api_market():
    return _health()["market"]

@app.get("/api/process")
def api_process():
    st=_state()
    return {
        "status":"ok",
        "runtime":"v103",
        "stages":{
            "market":st["market"],
            "news":{"items":st["news_count"],"market_links":st["news_links"]},
            "analysis":st["research"],
            "plan":st["plan"],
            "paper":st["paper"],
            "real":st["real"],
        },
    }

# Legacy GUI paths become redirects, so old bookmarks cannot open independent
# stale pages. Machine-facing CSV/JSON endpoints are deliberately separate.
LEGACY_GUI_REDIRECTS={
    "/api":"/system",
    "/products":"/markt",
    "/news-learning":"/lernen",
    "/fees":"/markt",
    "/data-quality":"/markt",
    "/decision-matrix":"/handel",
    "/forex-shadow":"/system",
    "/backtests":"/system",
    "/audit":"/system",
    "/exports":"/system",
    "/event-dashboard":"/system",
    "/tax-info":"/steuerinfo-at",
    "/scanner":"/analyse",
    "/paper":"/portfolio",
    "/controlled-learning":"/lernen",
    "/process":"/system",
    "/settings":"/system",
    "/portfolio-modern":"/portfolio",
    "/diagnose":"/system",
    "/prozess":"/system",
    "/automatik":"/system",
    "/analyse-v98":"/analyse",
    "/portfolio-v98":"/portfolio",
    "/handel-v98":"/handel",
    "/lernen-v98":"/lernen",
    "/diagnose-v98":"/system",
    "/prozess-v98":"/system",
    "/automatik-v98":"/system",
    "/v100-health":"/health",
    "/v101-health":"/health",
    "/v102-health":"/health",
    "/tax-info-v68":"/steuerinfo-at",
    "/tax-info-v68.zip":"/steuerinfo-at",
    "/tax-info-v68.csv":"/steuerinfo-at",
}
for path,target in LEGACY_GUI_REDIRECTS.items():
    existing=[rule for rule in list(app.url_map.iter_rules()) if rule.rule==path]
    if existing:
        for rule in existing:
            app.view_functions[rule.endpoint]=(lambda target=target: redirect(target,code=302))
    else:
        endpoint="v102_legacy_"+path.strip("/").replace("/","_").replace("-","_")
        app.add_url_rule(path,endpoint=endpoint,view_func=(lambda target=target: redirect(target,code=302)),methods=["GET","POST"])

# Replace same-path legacy GUI handlers with the one current implementation.
