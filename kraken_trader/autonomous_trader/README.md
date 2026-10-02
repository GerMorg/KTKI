# Autonomous Kraken Trader v1

This package is the new independent trading runtime defined by the Autonomous Trader specifications.

## Runtime boundary

TradingAuthority is the only component that can:
- start a trading cycle,
- create the final decision,
- pass deterministic risk checks,
- create an order intent,
- submit an order,
- reconcile an ambiguous order.

News, Gemini, market transport, learning, calibration and sensors are data/analysis services only.

## Operational safety

Live trading is disabled by default:
- trading_enabled: false
- live_enabled: false
- kill_switch: true

Immutable safety ceilings are implemented in config.py. Learning can tune model/strategy parameters only inside those ceilings.

## Kraken

The runtime discovers current spot and derivatives instruments dynamically from Kraken metadata instead of maintaining a symbol whitelist. The Kraken instrument identifiers, precision, minimums and leverage levels are stored in the instrument registry.

## Research and learning

Prediction records are created at analysis time with a baseline price. Later cycles evaluate realized outcomes against completed market snapshots. Calibration stores predicted-versus-realized direction probability quality. Candidate validation is separated from the live active model and applies chronological multi-window and multiple-testing controls.

## Recovery

Ambiguous private REST results never trigger a blind retry. They enter UNKNOWN_RECONCILING, require reconciliation, and trip the no-new-risk circuit breaker. WebSocket sequence gaps emit recovery events.

## Persistence

SQLite is a historical materialization/audit store. Kraken remains account/order/position truth. Financial values are stored as Decimal strings.

No GUI is shipped by this package. Home Assistant configuration is provided through the add-on config.yaml; status snapshots are published by SensorPublisher.
