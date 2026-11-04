#!/usr/bin/env python3
"""Regenerate the TOCs of the verified countries.

Writes two equivalent files under ``src/calendarium/data/countries/``:

* ``toc.txt`` -- relative URIs, resolved against the TOC location, so the
  file works wherever the directory is served from (raw GitHub, a mirror,
  a local clone);
* ``toc.full.txt`` -- absolute raw-GitHub URLs, so the file can be copied
  or served from anywhere and still point at this repository.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from calendarium.loader import bundled_data_path, load_directory  # noqa: E402


BASE_URL = (
    "https://raw.githubusercontent.com/gaelgael5/calendarium/"
    "main/src/calendarium/data/countries/"
)


def main() -> int:
    directory = bundled_data_path()
    configurations = sorted(load_directory(directory), key=lambda c: c.country)

    header = [
        "# Calendarium table of contents -- verified country configurations.",
        "# Format: country;culture;uri",
        "# Regenerate with: python scripts/update_toc.py",
    ]

    relative = header + ["# (relative URIs resolve against this file)"]
    absolute = header + ["# (absolute URLs point at the repository's main branch)"]
    for configuration in configurations:
        name = Path(configuration.source_file).name
        culture = configuration.culture or ""
        relative.append(f"{configuration.country};{culture};{name}")
        absolute.append(f"{configuration.country};{culture};{BASE_URL}{name}")

    for filename, lines in (("toc.txt", relative), ("toc.full.txt", absolute)):
        target = directory / filename
        target.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"wrote {target} ({len(configurations)} countries)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
