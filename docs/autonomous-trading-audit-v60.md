# Kraken Trader v60 – End-to-end process and autonomous-trading audit

## Executive conclusion

The repository has a solid research/paper-trading foundation, but the previous scoring and execution chain was **not yet suitable for autonomous real trading**. The main reasons were not one isolated bug; they were semantic gaps between research, forecasting, allocation and execution.

v60 therefore defines the following contract:

1. Research may generate candidates, but it never implies an order.
2. A scanner score is a ranking/conviction score, **not a probability** and not an expected return.
3. `BUY` is a long-entry signal. `AVOID` means no long position; it is not a bearish price forecast.
4. Forecasts are evaluated against the actual future candle and against the stored all-in round-trip cost.
5. Model health must pass before an autonomous real decision is allowed.
6. Portfolio targets are normalized across the whole portfolio, with a cash reserve and per-position cap.
7. EUR and USD product routes are compared in EUR using product spread, trade fee, slippage, and the EUR/USD conversion leg.
8. A USD product is executable automatically only after sufficient USD is available. The funding leg is an explicit EUR/USD conversion step, followed by a fresh balance check.
9. Real orders remain disabled by default. Enabling automation does not bypass decision, model, balance, market-quality, idempotency or kill-switch gates.

## Process audit

### 1. Universe

**Purpose:** identify tradable Kraken products and their canonical identity.

Required output: canonical product, all executable alternatives, quote currency, market constraints, asset class and current metadata.

No value is added by repeatedly carrying multiple alternatives through the decision chain. The selected route is therefore a derived execution decision; alternatives remain metadata for cost comparison and audit.

### 2. News and external AI

External AI is a teacher/data enrichment source, never a direct trading authority. AI output must be schema-valid, versioned and frozen in the learning sample.

A news item can change the research score but cannot bypass the market-data, model-health or execution gates.

### 3. Prefilter

The prefilter should remove obviously unusable markets and rank candidates. Its score is not a trading probability. Missing ticker data is not silently treated as a good market.

### 4. Deep scanner

The scanner currently uses momentum, trend, volatility and spread. These are useful features, but they are not sufficient as a standalone alpha model. In particular:

- momentum/trend are correlated and can double-count the same information;
- volatility is a risk feature, not a directional edge;
- spread is an execution-cost feature, not alpha;
- the current 0–100 score is not calibrated as a probability;
- a raw score must not be multiplied directly into portfolio weights as if it were expected return.

v60 treats the score as conviction/ranking input and adds an explicit model-health gate.

### 5. Forecasting

The old `AVOID -> DOWN` mapping was semantically wrong. AVOID means that the strategy does not want a long position; it does not assert a negative future return. v60 uses `UP` for BUY and `FLAT` for AVOID/HOLD.

Forecast evaluation now uses the actual historical target candle and treats a flat outcome as correct only when the move is within the stored round-trip cost envelope.

### 6. Controlled learning

Parameter learning remains candidate-based and explicit-approval based. It must compare active and candidate models on the same frozen validation rows and preserve horizon-specific results.

For autonomous activation, learning must additionally prove out-of-sample net performance after costs, stable results across multiple time windows, bounded drawdown and sufficient decision coverage. A parameter set that only improves hit rate while destroying net return is not acceptable.

### 7. Portfolio allocation

The old allocator could assign the same maximum exposure to many candidates independently, allowing the sum to exceed the intended portfolio risk budget.

v60 uses normalized risk-adjusted conviction:

`target weight ∝ max(score - buy_threshold, 0) / volatility`

then enforces cash reserve, maximum position size and minimum trade size. This is deliberately a risk-weighting heuristic, not a claim that the score is a return forecast.

### 8. Execution routing

For every canonical product the system compares all available execution pairs in EUR terms.

EUR route cost:

`product spread + trade fee + slippage`

USD route cost:

`product spread + trade fee + slippage + EUR/USD conversion spread + EUR/USD conversion fee`

The comparison is made for the actual planned EUR notional. A USD route is not considered cheaper merely because its product spread is smaller.

### 9. USD funding

If the selected product is quoted in USD and the account lacks sufficient USD:

1. calculate the required USD amount plus execution-cost buffer;
2. determine the EUR amount required at the current EUR/USD executable side;
3. create a separate EUR/USD funding intent;
4. verify that the funding order is accepted;
5. refresh/confirm the USD balance;
6. only then submit the product order;
7. persist both legs under one rebalance/run identifier.

If any step fails, the product order is not submitted.

### 10. Real execution

Every live order must pass:

- real trading enabled;
- kill switch clear;
- automation authorization valid;
- model health ready;
- current market data fresh;
- selected route still valid and cheaper than alternatives;
- balance sufficient;
- pair/order quantity constraints satisfied;
- notional limits satisfied in EUR;
- portfolio/risk limits satisfied;
- idempotency check;
- one order/funding workflow at a time.

A successful HTTP response is not equivalent to a completed trade. The execution state must subsequently be reconciled from Kraken execution/order data.

## Model suitability for future autonomous trading

| Model/component | Current role | Autonomous suitability |
|---|---|---|
| Liquidity/spread prefilter | Market-quality filter | Suitable as a gate, not alpha |
| Momentum | Directional feature | Potentially useful, must be validated out-of-sample |
| SMA10/SMA30 trend | Directional feature | Potentially useful, but correlated with momentum |
| Volatility | Risk feature | Useful for sizing/risk, not direction |
| News local model | Feature/teacher | Research only until stable out-of-sample edge is demonstrated |
| External AI | Data enrichment | Never direct order authority |
| Forex v1/v2 shadow models | Research | Require independent walk-forward validation before live use |
| Scanner 0–100 score | Ranking | Not a probability; cannot directly size positions |
| Controlled learning | Parameter optimization | Useful with strict walk-forward and frozen-sample gates |
| Current simple SMA backtest | Sanity benchmark | Not sufficient for production model validation |

## Required production validation before automatic real trading

A model family must demonstrate, on unseen time periods:

- sufficient sample size for both 24h and 168h horizons;
- positive net return after actual fees, spread, slippage and FX conversion;
- no material drawdown regression versus the active model;
- stability across multiple walk-forward windows;
- acceptable turnover and concentration;
- no dependence on one asset or one news event;
- comparison against buy-and-hold and no-position baselines;
- realistic order constraints and minimum sizes;
- no look-ahead leakage;
- calibrated confidence if confidence is used for sizing.

Until those conditions are met, automatic real execution must remain blocked even when the raw model score is high.

## Automatic portfolio rebalancing contract

The rebalancer should run from current real balances, not from a paper wallet or stale snapshot. It computes current EUR equity, target exposures, route costs and required trades. It then minimizes unnecessary turnover: trades inside the no-trade band are skipped, but a small apparent edge must never be used to justify a trade whose all-in expected benefit does not exceed all-in execution cost plus a safety margin.

The default operating mode remains dry-run. Live automation is an explicit operational decision after the complete model-health and execution tests pass.
