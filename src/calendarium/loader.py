"""Loading of country configuration files (``ConfigurationLoader`` in C#).

Files follow the original naming convention:

* ``date_<Country>.json`` -- a country configuration;
* ``date_<Name>.Default.json`` -- a shared *default* configuration that
  countries can import through their ``Defaults`` property;
* ``_schema*.json`` -- JSON schemas, ignored.

The files may contain ``//`` and ``/* */`` comments (they were parsed with
Json.NET in the original project), so comments are stripped before parsing.
"""

from __future__ import annotations

import json
import re
from importlib.resources import files as _package_files
from pathlib import Path
from typing import Iterable, List, Union

from .models import CountryConfiguration

_COMMENT_RE = re.compile(
    r'("(?:[^"\\]|\\.)*")'      # a JSON string (kept)
    r"|(/\*.*?\*/)"             # a /* block comment */
    r"|(//[^\r\n]*)",           # a // line comment
    re.DOTALL,
)

_TRAILING_COMMA_RE = re.compile(
    r'("(?:[^"\\]|\\.)*")'      # a JSON string (kept)
    r"|,(\s*[}\]])",            # a trailing comma before } or ]
    re.DOTALL,
)


def _strip_json_comments(text: str) -> str:
    """Strip Json.NET tolerances (comments, trailing commas) to strict JSON."""
    text = _COMMENT_RE.sub(lambda m: m.group(1) or "", text)
    return _TRAILING_COMMA_RE.sub(lambda m: m.group(1) or m.group(2), text)


def loads(text: str, is_default: bool = False, source_file: str = None) -> CountryConfiguration:
    """Parse one configuration document."""
    data = json.loads(_strip_json_comments(text))
    return CountryConfiguration.from_dict(data, is_default=is_default, source_file=source_file)


def load_file(path: Union[str, Path]) -> CountryConfiguration:
    """Load one ``date_*.json`` configuration file."""
    path = Path(path)
    is_default = path.name.lower().endswith("default.json")
    return loads(path.read_text(encoding="utf-8-sig"), is_default=is_default, source_file=str(path))


def load_directory(path: Union[str, Path], recursive: bool = False) -> List[CountryConfiguration]:
    """Load every configuration file of a directory."""
    path = Path(path)
    if not path.is_dir():
        raise FileNotFoundError(f"configuration directory not found: {path}")
    pattern = "**/date_*.json" if recursive else "date_*.json"
    return [load_file(f) for f in sorted(path.glob(pattern))]


def bundled_data_path() -> Path:
    """Directory of the country files shipped with the package."""
    return Path(str(_package_files("calendarium") / "data" / "countries"))


def load_bundled(include_not_checked: bool = False) -> List[CountryConfiguration]:
    """Load the referential shipped with the package.

    By default only the verified configurations are loaded.  With
    ``include_not_checked=True`` the unverified ones (``not_checked/``) are
    added for the countries that have no verified configuration.
    """
    root = bundled_data_path()
    configurations = load_directory(root)

    if include_not_checked:
        known = {c.country for c in configurations}
        for extra in load_directory(root / "not_checked"):
            if extra.country not in known:
                configurations.append(extra)
                known.add(extra.country)

    return configurations


def split_defaults(
    configurations: Iterable[CountryConfiguration],
) -> tuple[List[CountryConfiguration], List[CountryConfiguration]]:
    """Separate country configurations from shared *default* configurations."""
    countries, defaults = [], []
    for configuration in configurations:
        (defaults if configuration.is_default else countries).append(configuration)
    return countries, defaults
