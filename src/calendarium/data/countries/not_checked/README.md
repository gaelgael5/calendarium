# Unverified configurations

**This folder is empty: every country of the referential has been
verified** and lives in `data/countries/`, pinned by the golden snapshots
in `tests/golden/` (see the per-country git history for what each
verification changed).

The folder is kept for the promotion workflow: a newly imported or
contributed configuration starts here (loaded only with
`Calendarium.bundled(include_not_checked=True)` or the CLI flag `--all`)
until it has been reviewed against official sources, moved to
`data/countries/`, and given a golden file.
