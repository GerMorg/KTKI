# v94 End-to-End Decision Architecture

v94 uses one deterministic DecisionEngineV94 for Paper and Real portfolio decisions. Only the execution adapter differs after target generation.

Invariants:
- expected edge after current route costs is a hard economic entry condition;
- model health is continuous quality/sizing evidence, not a blanket BUY gate;
- H24 is operational and H168 advisory;
- long and short candidates are discovered from the same scanner universe;
- news is an explicit candidate input when available;
- symbol-specific historical forecast evidence is preferred over family averages;
- target exposure is compared with current exposure for rebalancing;
- held positions without a current thesis receive an explicit zero target;
- bearish held longs are reduced to zero when short opening is disabled;
- forecast cost adjustments are not counted twice;
- Paper and Real calculate the same confidence/leverage routing before their execution adapters;
- unsupported Paper short openings are blocked explicitly rather than silently becoming spot sells.
