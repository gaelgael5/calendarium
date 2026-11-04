# Unverified configurations

These country files are imported from the original project and are **not
verified**. They load only with `Calendarium.bundled(include_not_checked=True)`
or the CLI flag `--all`.

Everything else has been verified and promoted to `data/countries/` (see
the per-country git history and `tests/golden/`). One country remains:

| Country | Blocking reason |
|---|---|
| Syria | Holiday list in flux after the December 2024 change of government; needs a stable official source |
