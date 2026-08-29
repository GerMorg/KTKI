# v38 Repair Release

This is the complete repair pass requested for the Kraken Trader application. The repository already contains a historical `0.1.0-dev.38`; the repaired runtime is therefore versioned monotonically as `0.1.0-dev.59` while retaining the repair designation `v38`.

## Fixed

- Active/candidate learning displays are no longer self-comparisons after promotion. Actionable candidate views show only pending candidates; promoted versions remain in version history.
- Numeric GUI values remain arithmetic-safe while German output uses fewer unnecessary decimal places.
- Controlled learning performs exactly one time-ordered train/validation split and persists the validation sample for approval rechecks.
- Per-horizon active-vs-candidate metrics include coverage, decisions, raw/robust accuracy, net return, improvement and drawdown.
- News-learning approval validates the frozen validation sample instead of fingerprinting the continuously changing full news set, preventing false `REJECTED_RECHECK` results caused by newly arriving news.
- News candidate identity still includes the full teacher/sample content and active base version for correct automatic deduplication.
- Austrian tax reporting is now real-trading first: Kraken trade history is imported when private API credentials are available, with Realhandel / Paper / Beide as explicit sources.
- Real-trade tax calculations use EUR acquisition/proceeds with average cost inventory handling and explicitly flag non-EUR pairs or incomplete holdings for manual review rather than inventing FX/basis values.
- Regression tests cover all newly reported defects.
- GitHub Actions runs the complete regression suite with `sh run_tests.sh`.

## Austrian tax basis

For private crypto assets, the BMF states a special rate of 27.5% and describes the moving-average method for crypto of the same type held in the same wallet/address for realizations after 31 December 2022. Foreign capital income and other capital gains can likewise be subject to the 27.5% special rate depending on their classification. The application therefore presents the report as a verification aid, not as a filing decision. citeturn984252search0turn984252search1turn984252search8

## Safety

Real trading remains disabled by default. No learning path activates a new parameter set automatically.

## Verification

The final repair must only be merged from a branch whose GitHub Actions test job is green.
