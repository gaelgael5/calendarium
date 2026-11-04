"""Command line interface.

Replaces the original C# console application (minus the NuGet distribution
commands, which have no equivalent here: the referential ships with the
package).

Examples::

    calendarium countries
    calendarium compute 2024 France
    calendarium compute 2024 France --region 67 --csv output.csv
    calendarium show 2024-07-14 France
"""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import date, datetime
from typing import List, Optional

from . import __version__
from .core import Calendarium
from .models import EventDate
from .rules import registered_functions
from .snapshot import dedupe_events

_CSV_HEADER = ["Name", "StartDate", "EndDate", "ObservedDate", "Country", "Culture", "Free", "Calendar"]


def _load(args: argparse.Namespace) -> Calendarium:
    if args.data:
        return Calendarium.from_directory(args.data)
    return Calendarium.bundled(include_not_checked=args.all)


def _parse_date(text: str) -> date:
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        raise SystemExit(f"invalid date {text!r}: expected YYYY-MM-DD")


def _event_row(event: EventDate) -> List[str]:
    """One CSV row, in the format of the original C# `compute` command."""
    return [
        event.name,
        event.date.strftime("%d/%m/%Y 00:00:00"),
        event.date_end.strftime("%d/%m/%Y") if event.date_end else "",
        event.observed.strftime("%d/%m/%Y"),
        event.country,
        event.culture or "",
        "true" if event.free else "false",
        event.calendar,
    ]


def _collect(cal: Calendarium, year: int, country: str, region: Optional[str]) -> List[EventDate]:
    if region is not None:
        dates = cal.get_dates(year, country, region=region)
    else:
        dates = cal.get_all_dates(year, country)
    events: List[EventDate] = []
    for identified in dates.values():
        events.extend(identified.events)
    return events


def cmd_countries(args: argparse.Namespace) -> int:
    cal = _load(args)
    for country in cal.countries():
        regions = cal.regions(country)
        configuration = cal.configuration(country)
        parts = [country]
        if configuration and configuration.culture:
            parts.append(f"culture={configuration.culture}")
        if configuration and configuration.calendar not in ("Default", "Gregorian"):
            parts.append(f"calendar={configuration.calendar}")
        if regions:
            parts.append(f"regions={','.join(regions)}")
        print("  ".join(parts))
    return 0


def cmd_compute(args: argparse.Namespace) -> int:
    cal = _load(args)
    countries = args.country or cal.countries()

    events: List[EventDate] = []
    for country in countries:
        for year in range(args.year, args.year + args.years):
            events.extend(_collect(cal, year, country, args.region))

    rows = dedupe_events(events)

    if args.csv:
        with open(args.csv, "w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle, delimiter=";")
            writer.writerow(_CSV_HEADER)
            writer.writerows(_event_row(e) for e, _ in rows)
        print(f"{len(rows)} dates written to {args.csv}")
    else:
        for event, regions in rows:
            observed = f"  observed {event.observed}" if event.is_shifted else ""
            free = "free" if event.free else "worked"
            region = f"  [{','.join(regions)}]" if regions else ""
            print(f"{event.date}  {event.name}{observed}  ({event.country}, {free}){region}")
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    cal = _load(args)
    d = _parse_date(args.date)

    identified = cal.get_date(d, args.country, region=args.region)
    actual_events = identified.events if identified else []

    observed = cal.get_date(d, args.country, region=args.region, key="observed")
    shifted_in = [e for e in (observed.events if observed else []) if e.is_shifted]

    if not actual_events and not shifted_in:
        print(f"{d}: no festivity for {args.country}")
        return 1

    for event in actual_events:
        note = f", observed {event.observed}" if event.is_shifted else ""
        region = f" [{event.region}]" if event.region else ""
        free = "free" if event.is_free_on(d) else "worked"
        print(f"{d}: {event.name} ({free}{note}){region}")
    for event in shifted_in:
        region = f" [{event.region}]" if event.region else ""
        free = "free" if event.is_free_on(d) else "worked"
        print(f"{d}: {event.name} observed ({free}, actual date {event.date}){region}")
    return 0


def cmd_functions(args: argparse.Namespace) -> int:
    for name in registered_functions():
        print(f"[{name}]")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="calendarium",
        description="Referential of computed dates (public holidays and observances).",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--data", metavar="DIR", help="load configurations from DIR instead of the bundled referential")
    common.add_argument("--all", action="store_true", help="also load the unverified (not_checked) configurations")

    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("countries", parents=[common], help="list the available country configurations")
    p.set_defaults(func=cmd_countries)

    p = sub.add_parser("compute", parents=[common], help="compute the dates of one or more years")
    p.add_argument("year", type=int, help="first (Gregorian) year to compute")
    p.add_argument("country", nargs="*", help="countries to compute (default: all)")
    p.add_argument("--years", type=int, default=1, metavar="N", help="number of years to compute (default: 1)")
    p.add_argument("--region", help="restrict to one region key (default: merge all regions)")
    p.add_argument("--csv", metavar="FILE", help="write a CSV file (same format as the C# version)")
    p.set_defaults(func=cmd_compute)

    p = sub.add_parser("show", parents=[common], help="show the festivities of one date")
    p.add_argument("date", help="date, format YYYY-MM-DD")
    p.add_argument("country", help="country name")
    p.add_argument("--region", default=None, help="region key (default: search all regions)")
    p.set_defaults(func=cmd_show)

    p = sub.add_parser("functions", parents=[common], help="list the computed-date functions usable as [NAME]")
    p.set_defaults(func=cmd_functions)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except KeyError as error:
        print(f"error: {error.args[0]}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
