# v38 Repair Release

This is the complete repair pass requested for the Kraken Trader application. The repository's historical semantic development version `0.1.0-dev.38` already exists, so this repair uses the next monotonic runtime version `0.1.0-dev.58` while retaining the user-facing repair designation `v38`.

## Fixed

- Numeric GUI values remain real numeric objects during template rendering, so localized German output no longer corrupts arithmetic, comparisons, or Jinja float filters.
- Raw JSON/text values are preserved exactly.
- Controlled learning performs exactly one time-ordered training/validation split; the optimizer never re-splits its supplied training set.
- Validation size is large enough to satisfy all required horizon gates instead of allowing a 24h/168h gate configuration with too few validation observations.
- Active-vs-candidate comparisons persist per-horizon coverage, decision count, raw accuracy, Wilson lower bounds, net return and drawdown, making the shadow result auditable and meaningful.
- Approval re-runs the shadow evaluation against the exact persisted validation forecast IDs and blocks activation if the sample changed, the active version changed, parameters are invalid, or any gate fails.
- Legacy xStock learning is now a compatibility facade over `parameter_family_versions`; it no longer maintains a second independent activation/version system.
- Legacy xStock migration runs only once against the default version and cannot overwrite an already evolved active version on application restart.
- News-learning candidate identity includes the full comparison sample content as well as the active base version, preventing stale deduplication after data or model changes.
- News-learning approval rechecks the exact time-split sample and walk-forward gates before activating a new version.
- Regression coverage was expanded for all of the above.
- A GitHub Actions regression workflow was added for every branch push and pull request. The workflow invokes `sh run_tests.sh`, so it does not depend on the repository executable bit.

## Safety

Real trading remains disabled by default. No learning path activates a new parameter set automatically.

## Verification

The release branch contains automated regression tests and CI configuration. The final merge should be accepted only with a green GitHub Actions test job.
