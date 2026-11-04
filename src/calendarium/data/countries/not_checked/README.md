# Unverified configurations

These country files are imported from the original project and are **not
verified**: their holiday lists have not been reviewed against official
sources. They load only with `Calendarium.bundled(include_not_checked=True)`
or the CLI flag `--all`.

Everything that could be verified has been promoted to `data/countries/`
(see the per-country git history and `tests/golden/`), including the
Chinese-lunisolar group since the astronomical calendar was implemented
(`calendarium.chinese`). What remains here is blocked:

| Country | Blocking reason |
|---|---|
| Syria | Holiday list in flux after the December 2024 change of government; needs a stable official source |
| Thailand | The Buddhist holidays (Makha/Visakha/Asarnha Bucha, Khao Phansa) follow the Thai lunar calendar, whose month numbering and intercalation differ from the Chinese calendar (e.g. Visakha Bucha 2025 fell on 11 May where the Chinese 4-15 gives 12 May); needs either the Thai arithmetic calendar or a gazetted table |
