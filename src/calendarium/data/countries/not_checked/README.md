# Unverified configurations

These country files are imported from the original project and are **not
verified**. They load only with `Calendarium.bundled(include_not_checked=True)`
or the CLI flag `--all`.

Everything else has been verified and promoted to `data/countries/` (see
the per-country git history and `tests/golden/`). One country remains:

| Country | Blocking reason |
|---|---|
| Syria | No stable full-year official list yet. Known state (November 2026): Presidential Decree 188 of 2025 frames the official holidays (Liberation Day 8 December; Friday-Saturday public-sector weekend), Decree 13 of 2026 added Newroz (21 March), and multi-day closures are announced ad hoc by the Presidency (March 2026 block, Prophet's Birthday). Verification needs the full text of Decree 188/2025 or a complete yearly list from SANA/the Presidency. |
