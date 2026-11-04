#!/usr/bin/env python3
"""Regenerate the TOC of the verified countries.

Writes ``src/calendarium/data/countries/toc.txt`` with one line per
verified configuration: ``country;culture;relative-uri``.  The URIs are
relative to the TOC location, so the file works wherever the directory is
served from (raw GitHub, a mirror, a local clone).
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from calendarium.loader import bundled_data_path, load_directory  # noqa: E402


def main() -> int:
    directory = bundled_data_path()
    configurations = load_directory(directory)
    lines = [
        "# Calendarium table of contents -- verified country configurations.",
        "# Format: country;culture;uri  (relative URIs resolve against this file)",
        "# Regenerate with: python scripts/update_toc.py",
    ]
    for configuration in sorted(configurations, key=lambda c: c.country):
        uri = Path(configuration.source_file).name
        lines.append(f"{configuration.country};{configuration.culture or ''};{uri}")
    target = directory / "toc.txt"
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {target} ({len(configurations)} countries)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
