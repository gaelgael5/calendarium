#!/usr/bin/env python3
"""Print a country's rules and computed dates, for verification review.

Usage: python scripts/review_country.py Canada [years...]
Default years: 2024 2025 2026.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from calendarium import Calendarium  # noqa: E402
from calendarium.snapshot import snapshot_rows  # noqa: E402


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print(__doc__)
        return 2
    country = argv[0]
    years = [int(y) for y in argv[1:]] or [2024, 2025, 2026]

    cal = Calendarium.bundled(include_not_checked=True)
    configuration = cal.configuration(country)
    if configuration is None:
        print(f"unknown country {country!r}")
        return 2

    print(f"# {configuration.country}  culture={configuration.culture}  "
          f"calendar={configuration.calendar}  file={configuration.source_file}")
    print("## periods")
    for p in configuration.periods:
        bounds = ""
        if p.year_start or p.year_end:
            bounds = f"  [{p.year_start or ''}..{p.year_end or ''}]"
        cal_note = f"  cal={p.calendar}" if p.calendar not in ("Default", None, "") else ""
        obs = f"  obs={p.rule_observed!r}" if p.rule_observed else ""
        free = "free" if p.free else "WORKED"
        print(f"  {p.name:42} {p.rule_date:28} {free}{cal_note}{obs}{bounds}")
    print("## computed")
    for row in snapshot_rows(cal, country, years):
        print("  " + row)
    return 0


if __name__ == "__main__":
    sys.exit(main())
