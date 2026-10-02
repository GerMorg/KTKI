# KTKI Read-only audit used for Autonomous Trader v1

The existing KTKI implementation was reviewed only as a reference. The v1 runtime does not import its legacy modules.

## Findings carried into the redesign

1. The legacy code has multiple version-specific runtime and execution modules.
2. The legacy application contains web/GUI runtime surfaces.
3. Real trading has separate execution gates that should not become independent trading authorities.
4. Market handling is distributed across legacy modules.
5. The redesign therefore uses one central TradingAuthority, one execution boundary and explicit state machines.

## Replacement decisions

- Dynamic Kraken product discovery replaces manually curated market lists.
- Kraken metadata is the source for instrument identifiers, precision, minimums and leverage.
- Kraken is account/order/position truth; SQLite is history and materialization.
- News and Gemini enrich decisions but cannot submit orders.
- Risk limits are immutable ceilings outside learning.
- Ambiguous order submission always reconciles before any replacement.
- Research/model promotion is separated from the active production model.
- There is no Flask/Jinja/HTML/Ingress GUI in the new runtime.

## Final audit target

The v1 implementation is considered complete only after CI and end-to-end tests demonstrate dynamic discovery, Long/Short, Spot/Margin/Leverage/available derivatives, cost-aware execution, News/Gemini influence, learning/calibration, model rollback, reconciliation, recovery, sensors, audit logging and absence of hidden order authorities.

The acceptance criteria are derived from AUTONOMOUS_TRADER_SPEC.md.
