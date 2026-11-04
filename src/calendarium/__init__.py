"""Calendarium -- referential of computed dates (public holidays and observances).

Python port of https://github.com/Black-Beard-Sdk/Calendarium : every country
is described by a JSON configuration file whose date rules are written in a
small DSL (``"12-25"``, ``"[EASTER] + 39"``, ``"? (SATURDAY | SUNDAY) : >> MONDAY"``).

Quick start::

    from calendarium import Calendarium

    cal = Calendarium.bundled()
    dates = cal.get_dates(2024, "France")
    for d, identified in dates.items():
        for event in identified.events:
            print(d, event.name, event.observed, event.free)
"""

from .calendars import (
    CalendarBase,
    UnsupportedCalendarError,
    get_calendar,
    julian_to_gregorian,
)
from .core import Calendarium
from .easter import easter_date, orthodox_easter_date
from .loader import (
    bundled_data_path,
    load_bundled,
    load_directory,
    load_file,
)
from .models import (
    CountryConfiguration,
    EventDate,
    IdentifiedDate,
    Period,
    Region,
    Translation,
)
from .rules import (
    DateRule,
    ObservedRule,
    RuleSyntaxError,
    gazetted_coverage,
    parse_date_rule,
    parse_observed_rule,
    register_function,
    registered_functions,
)
from .toc import DEFAULT_TOC_URL, Toc, TocEntry, load_toc

__version__ = "0.3.0"

__all__ = [
    "Calendarium",
    "CalendarBase",
    "CountryConfiguration",
    "DEFAULT_TOC_URL",
    "DateRule",
    "EventDate",
    "IdentifiedDate",
    "ObservedRule",
    "Period",
    "Region",
    "RuleSyntaxError",
    "Toc",
    "TocEntry",
    "Translation",
    "UnsupportedCalendarError",
    "__version__",
    "bundled_data_path",
    "easter_date",
    "gazetted_coverage",
    "get_calendar",
    "julian_to_gregorian",
    "load_bundled",
    "load_directory",
    "load_file",
    "load_toc",
    "orthodox_easter_date",
    "parse_date_rule",
    "parse_observed_rule",
    "register_function",
    "registered_functions",
]
