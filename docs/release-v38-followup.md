# v38 Follow-up Repair

This follow-up corrects issues found after the initial v38 merge.

- Learning no longer presents an approved candidate as an actionable candidate against the newly active version.
- Active/candidate arithmetic remains numeric-safe and display precision is reduced where practical.
- News-learning approval rechecks the frozen validation sample rather than the continuously changing full news sample, preventing false `REJECTED_RECHECK` states caused by newly arriving news.
- Austrian tax reporting is real-trading first and can import Kraken `TradesHistory` when private API credentials are configured, with explicit Paper / Real / Both sources.
- Non-EUR real trades and incomplete acquisition inventory are flagged for manual review instead of inventing FX or cost-basis data.
- Regression tests cover the newly reported defects.

The tax page remains a calculation and verification aid, not tax or legal advice.
