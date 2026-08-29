# Release v58 — Learning/UI repair

## Scope

This release repairs the GUI numeric-display regression and hardens the learning UI around candidate review.

## Fixed

- Localized numeric values remain numeric inside Jinja templates, so arithmetic and `float` formatting keep their original semantics.
- German comma formatting is applied only when values are rendered as text; persisted JSON and raw strings remain unchanged.
- Release metadata is synchronized across runtime, add-on configuration and repository metadata.
- Regression coverage verifies localized display values can still be subtracted/formatted numerically.
- Existing controlled-learning and news-learning approval gates remain fail-closed; no automatic parameter activation is introduced.

## Verification

The repository's existing regression suite could not be executed in this environment because the runtime has no outbound network access for cloning/installing dependencies. The new regression tests are included in `tests/test_v58_regressions.py` and the existing repository-quality checks are updated to v58.

Real trading remains disabled by default.
