#!/usr/bin/env python3
"""Check that the gazetted tables still cover the near future.

The referential embeds hand-maintained tables of officially gazetted
dates (Matariki, Deepavali, the Thai Bucha days). This script exits
non-zero, listing what needs attention, when a table no longer covers
next year -- the margin that leaves time to extend it before users ask
for dates the table cannot produce.

Run monthly by .github/workflows/maintenance.yml, which opens a GitHub
issue on failure; can be run by hand any time:

    python scripts/check_gazetted_tables.py
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from calendarium.rules import gazetted_coverage  # noqa: E402

MARGIN_YEARS = 1  # every table must cover at least current year + margin


def main() -> int:
    horizon = date.today().year + MARGIN_YEARS
    stale = []
    print(f"Gazetted tables coverage (must reach {horizon}):")
    for name, (first, last) in sorted(gazetted_coverage().items()):
        status = "OK" if last >= horizon else "EXTEND"
        print(f"  [{name}] {first}-{last}  {status}")
        if last < horizon:
            stale.append((name, last))

    if not stale:
        print("All gazetted tables cover the horizon.")
        return 0

    print()
    print("Tables to extend with newly gazetted dates:")
    for name, last in stale:
        print(f"  - [{name}] ends in {last}")
    print()
    print("How to extend:")
    print("  1. add the official dates to the table in src/calendarium/rules.py;")
    print("  2. raise the matching YearEnd bounds in the country files")
    print("     (a unit test enforces that they stay in sync);")
    print("  3. regenerate the goldens of the affected countries:")
    print("     python scripts/update_golden.py New_Zealand Singapore Malaysia \\")
    print("         Trinidad_and_Tobago Thailand")
    print()
    print("Also worth a periodic look: Syria (still in not_checked, waiting for")
    print("a stable official holiday list) and the decree-based days that are")
    print("not encoded (China State Council arrangement, Thai Cabinet")
    print("substitutes, Vietnam Tet decree).")
    return 1


if __name__ == "__main__":
    sys.exit(main())
