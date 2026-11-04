"""Golden tests: the engine output must match the human-reviewed snapshots.

Each ``tests/golden/<Country>.csv`` is the reference output of a country for
the years pinned in its header.  A failure here means either a regression in
the engine, or an intentional change to the referential: in the second case
regenerate with ``python scripts/update_golden.py <Country>`` and have the
diff reviewed against official sources.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from calendarium import Calendarium
from calendarium.snapshot import snapshot_rows

GOLDEN_DIR = Path(__file__).parent / "golden"
GOLDEN_FILES = sorted(GOLDEN_DIR.glob("*.csv"))


@pytest.fixture(scope="module")
def cal():
    return Calendarium.bundled(include_not_checked=True)


def _read_golden(path: Path):
    years, rows = None, []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("# years:"):
            years = [int(y) for y in line.split(":", 1)[1].split(",")]
        elif not line or line.startswith("#") or line.startswith("date;"):
            continue
        else:
            rows.append(line)
    if years is None:
        raise AssertionError(f"{path.name}: missing '# years:' header")
    return years, rows


def test_golden_files_exist():
    assert GOLDEN_FILES, "no golden file found under tests/golden/"


@pytest.mark.parametrize("path", GOLDEN_FILES, ids=lambda p: p.stem)
def test_golden(path, cal):
    years, expected = _read_golden(path)
    computed = snapshot_rows(cal, path.stem, years)

    missing = sorted(set(expected) - set(computed))
    unexpected = sorted(set(computed) - set(expected))
    assert computed == expected, (
        f"{path.stem} diverges from its golden snapshot.\n"
        f"  missing rows: {missing}\n"
        f"  unexpected rows: {unexpected}\n"
        f"If the change is intentional, regenerate with "
        f"'python scripts/update_golden.py {path.stem}' and review the diff."
    )
