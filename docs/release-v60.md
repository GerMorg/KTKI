# v60 – Autonomous Trading Readiness

## Scope

v60 is a process and execution architecture release. It is intentionally not a live-trading activation release.

### Research/model
- `AVOID` is no longer interpreted as a bearish price forecast.
- Forecasts use historical target candles and frozen cost snapshots.
- Flat forecasts are evaluated relative to the stored round-trip cost envelope.
- Model-health snapshots require sufficient 24h/168h evidence, positive net performance after costs, bounded drawdown and positive performance against the no-position baseline.
- Scanner scores remain conviction/ranking values, not probabilities.
- Portfolio targets are normalized by conviction/volatility and include cost penalties, cash reserve and max-position limits.

### Execution
- EUR and USD alternatives are compared using absolute EUR all-in cost.
- USD routes include the EUR/USD conversion spread and fee.
- USD buys can create an explicit EUR->USD funding leg before the product order.
- The funding leg is followed by a fresh private-balance read before product execution.
- Real order validation uses EUR-equivalent notional, Kraken minimum order/cost rules, quote/base balances and a live-price deviation guard.
- Real decision gates include model health, route cost, quote funding, portfolio risk and order constraints.

## Safety

Real trading remains disabled by default. Automatic rebalancing remains disabled and dry-run by default. Enabling live execution is an operational decision that must only be made after the model-health gates have accumulated sufficient out-of-sample evidence.

## External API reference

Kraken's current API documentation describes REST and WebSocket interfaces and supports client order identifiers for idempotent order management. The implementation keeps client-order identifiers and persists order intents for reconciliation. See the official Kraken API Center: https://docs.kraken.com/
