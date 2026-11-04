#!/usr/bin/env python3
"""Regenerate the golden snapshot files under tests/golden/.

A golden file is the human-reviewed reference output of a country: the test
suite recomputes it and compares exactly (see tests/test_golden.py).  After
regenerating, review the diff against official sources before committing --
the review is what makes a country "verified".

Usage:
    python scripts/update_golden.py                 # refresh existing golden files
    python scripts/update_golden.py France Germany  # specific countries
    python scripts/update_golden.py --all-checked   # every verified country
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from calendarium import Calendarium  # noqa: E402
from calendarium.snapshot import snapshot_rows  # noqa: E402

GOLDEN_DIR = ROOT / "tests" / "golden"
GOLDEN_YEARS = (2024, 2025, 2026)
HEADER = "date;name;observed;free;regions"


def write_golden(cal: Calendarium, country: str) -> Path:
    rows = snapshot_rows(cal, country, GOLDEN_YEARS)
    path = GOLDEN_DIR / f"{country}.csv"
    lines = [
        "# Calendarium golden snapshot -- human-reviewed reference output",
        f"# country: {country}",
        f"# years: {','.join(str(y) for y in GOLDEN_YEARS)}",
        f"# regenerate: python scripts/update_golden.py {country}",
        HEADER,
        *rows,
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("countries", nargs="*", help="countries to regenerate")
    parser.add_argument(
        "--all-checked",
        action="store_true",
        help="regenerate every country of the verified tier",
    )
    args = parser.parse_args(argv)

    cal = Calendarium.bundled(include_not_checked=True)

    if args.all_checked:
        from calendarium.loader import bundled_data_path, load_directory

        countries = [c.country for c in load_directory(bundled_data_path())]
    elif args.countries:
        countries = args.countries
    else:
        countries = sorted(p.stem for p in GOLDEN_DIR.glob("*.csv"))
        if not countries:
            parser.error("no golden file to refresh; give country names or --all-checked")

    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    for country in countries:
        path = write_golden(cal, country)
        print(f"wrote {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
