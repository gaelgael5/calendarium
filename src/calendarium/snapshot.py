"""Canonical snapshot of a country's computed dates.

A snapshot is a sorted list of one-line records, stable across runs, used to
compare the engine's output against a human-reviewed reference (the *golden*
files under ``tests/golden/``) and by the CLI table output.
"""

from __future__ import annotations

from typing import Iterable, List, Tuple

from .core import Calendarium
from .models import EventDate


def dedupe_events(events: Iterable[EventDate]) -> List[Tuple[EventDate, List[str]]]:
    """Group identical events found in several region rule sets.

    Returns ``(event, regions)`` pairs where ``regions`` is empty for a
    country-wide event, or lists the region keys the event is specific to.
    """
    groups: dict = {}
    for event in events:
        key = (event.country, event.date, event.name, event.observed, event.free)
        groups.setdefault(key, []).append(event)
    result = []
    for key in sorted(groups):
        group = groups[key]
        national = any(not e.region for e in group)
        regions = [] if national else sorted({e.region for e in group})
        result.append((group[0], regions))
    return result


def snapshot_rows(cal: Calendarium, country: str, years: Iterable[int]) -> List[str]:
    """``date;name;observed;free;regions`` records for the given years.

    Every region of the country is included; an event common to the whole
    country appears once with an empty ``regions`` field, a region-specific
    event once with its region keys joined by ``|``.
    """
    events: List[EventDate] = []
    for year in years:
        for identified in cal.get_all_dates(year, country).values():
            events.extend(identified.events)

    return [
        ";".join(
            [
                event.date.isoformat(),
                event.name,
                event.observed.isoformat(),
                "true" if event.free else "false",
                "|".join(regions),
            ]
        )
        for event, regions in dedupe_events(events)
    ]
