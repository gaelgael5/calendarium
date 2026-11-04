"""Validation of every country configuration file shipped with the package.

Each file is a parametrized test case (``checked/France``,
``not_checked/Japan``, ...), validated in layers:

1. **structure** -- metadata invariants (strict for the verified tier,
   lenient for ``not_checked``);
2. **compilation** -- every rule parses, calendars resolve, region
   references exist;
3. **evaluation** -- the file evaluates over ``YEARS`` without error and
   respects the engine invariants (dates clipped to the requested year,
   observed day within a week of the actual day, every period produces its
   dates).

Business correctness -- are these the *right* holidays for the country? --
cannot be asserted by code alone: it is covered by the human-reviewed golden
snapshots under ``tests/golden/`` (see ``test_golden.py``).
"""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest

from calendarium import Calendarium, get_calendar
from calendarium.calendars import GregorianCalendar, JulianCalendar, _OffsetCalendar
from calendarium.loader import bundled_data_path, load_directory
from calendarium.rules import parse_date_rule, parse_observed_rule

YEARS = range(2000, 2031)

CHECKED = load_directory(bundled_data_path())
NOT_CHECKED = load_directory(bundled_data_path() / "not_checked")

ALL = [("checked", c) for c in CHECKED] + [("not_checked", c) for c in NOT_CHECKED]
ALL_IDS = [f"{tier}/{c.country}" for tier, c in ALL]
CHECKED_IDS = [f"checked/{c.country}" for c in CHECKED]

_ENGINES: dict = {}
_EVENTS: dict = {}


def _engine(tier, configuration) -> Calendarium:
    key = (tier, configuration.country)
    if key not in _ENGINES:
        _ENGINES[key] = Calendarium([configuration])
    return _ENGINES[key]


def _events_by_year(tier, configuration) -> dict:
    """``{(region, year): [events]}`` for the whole ``YEARS`` window."""
    key = (tier, configuration.country)
    if key not in _EVENTS:
        cal = _engine(tier, configuration)
        regions = [""] + cal.regions(configuration.country)
        _EVENTS[key] = {
            (region, year): [
                event
                for identified in cal.get_dates(year, configuration.country, region).values()
                for event in identified.events
            ]
            for region in regions
            for year in YEARS
        }
    return _EVENTS[key]


def _period_calendar(configuration, period) -> object:
    name = period.calendar
    if name in (None, "", "Default"):
        name = configuration.calendar
    return get_calendar(name)


def _is_year_stable(calendar) -> bool:
    """Calendars whose dates recur exactly once per Gregorian year."""
    return isinstance(calendar, (GregorianCalendar, JulianCalendar, _OffsetCalendar))


# ---------------------------------------------------------------------------
# layer 1: structure
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("tier,configuration", ALL, ids=ALL_IDS)
def test_file_name_matches_country(tier, configuration):
    assert Path(configuration.source_file).name == f"date_{configuration.country}.json"


@pytest.mark.parametrize("tier,configuration", ALL, ids=ALL_IDS)
def test_has_periods(tier, configuration):
    assert configuration.periods, "a country configuration must define periods"


@pytest.mark.parametrize("configuration", CHECKED, ids=CHECKED_IDS)
def test_checked_metadata_is_strict(configuration):
    """The verified tier must carry complete metadata."""
    assert configuration.culture, "verified configurations must declare a Culture"
    for period in configuration.periods:
        assert period.name and period.name.strip(), "period without a name"
        assert period.rule_date and period.rule_date.strip(), f"{period.name}: empty RuleDate"
        for translation in period.translations:
            assert translation.name, f"{period.name}: translation without a name"
        if period.year_start is not None and period.year_end is not None:
            assert period.year_start <= period.year_end, period.name


# ---------------------------------------------------------------------------
# layer 2: compilation
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("tier,configuration", ALL, ids=ALL_IDS)
def test_calendars_resolve(tier, configuration):
    get_calendar(configuration.calendar)
    for period in configuration.periods:
        _period_calendar(configuration, period)
    for region in configuration.regions:
        for period in region.periods:
            _period_calendar(configuration, period)


@pytest.mark.parametrize("tier,configuration", ALL, ids=ALL_IDS)
def test_rules_compile(tier, configuration):
    periods = list(configuration.periods)
    for region in configuration.regions:
        periods.extend(region.periods)
    for period in periods:
        parse_date_rule(period.rule_date)
        if period.rule_observed:
            parse_observed_rule(period.rule_observed)
        if period.rule_duration:
            parse_observed_rule(period.rule_duration)


@pytest.mark.parametrize("tier,configuration", ALL, ids=ALL_IDS)
def test_function_rules_run_on_a_year_stable_calendar(tier, configuration):
    """A ``[FUNCTION]`` rule receives the calendar year, and the named
    functions (Easter, Passover, ...) are defined for Gregorian years: the
    period's effective calendar must therefore be year-stable.  Catches
    copy-paste mistakes such as a Gregorian country declared ``UmAlQura``.
    """
    periods = list(configuration.periods)
    for region in configuration.regions:
        periods.extend(region.periods)
    for period in periods:
        if "[" in period.rule_date:
            calendar = _period_calendar(configuration, period)
            assert _is_year_stable(calendar), (
                f"{period.name}: rule {period.rule_date!r} uses a computed date "
                f"but runs on the {calendar.name} calendar"
            )


def test_gazetted_period_bounds_match_the_tables():
    """A period computed from a gazetted table must be year-bounded to
    exactly what the table covers: extending a table without raising the
    YearEnd bounds would silently stop producing the holiday."""
    from calendarium.rules import gazetted_coverage

    coverage = gazetted_coverage()
    found = 0
    for configuration in CHECKED:
        for period in configuration.periods:
            for name, (first, last) in coverage.items():
                if f"[{name}]" in period.rule_date.upper():
                    found += 1
                    assert period.year_start is not None and period.year_start >= first, (
                        f"{configuration.country}/{period.name}: YearStart must be >= {first}"
                    )
                    assert period.year_end == last, (
                        f"{configuration.country}/{period.name}: YearEnd {period.year_end} "
                        f"!= table end {last} ([{name}])"
                    )
    assert found >= 6  # NZ Matariki, SG/MY/TT Deepavali, TH Buchas


@pytest.mark.parametrize("tier,configuration", ALL, ids=ALL_IDS)
def test_regions_are_consistent(tier, configuration):
    keys = [region.key for region in configuration.regions]
    assert len(keys) == len(set(keys)), f"duplicated region keys: {keys}"
    for region in configuration.regions:
        if region.from_region:
            assert region.from_region in keys, (
                f"region {region.key!r} copies unknown region {region.from_region!r}"
            )
            assert region.from_region != region.key, f"region {region.key!r} copies itself"


# ---------------------------------------------------------------------------
# layer 3: evaluation
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("tier,configuration", ALL, ids=ALL_IDS)
def test_evaluation_invariants(tier, configuration):
    """Every rule set evaluates over the whole window and yields sane events."""
    for (region, year), events in _events_by_year(tier, configuration).items():
        for event in events:
            assert event.date.year == year, (
                f"{event.name} ({region or 'country'}): {event.date} outside {year}"
            )
            shift = abs((event.observed - event.date).days)
            assert shift <= 7, (
                f"{event.name}: observed {event.observed} is {shift} days from {event.date}"
            )
            if event.date_end is not None:
                assert event.date_end >= event.date, event.name


@pytest.mark.parametrize("tier,configuration", ALL, ids=ALL_IDS)
def test_every_period_produces_its_dates(tier, configuration):
    """No dead rule: each period yields events in the years it applies to.

    Periods on a year-stable calendar must appear in every applicable year;
    lunar-calendar periods (Hijri, Hebrew, Persian) may skip around the
    Gregorian year boundary, so they are required at least once in every
    two-year window.
    """
    events = _events_by_year(tier, configuration)
    names_per_year = {
        year: {event.name for (_, y), evs in events.items() if y == year for event in evs}
        for year in YEARS
    }

    periods = list(configuration.periods)
    for region in configuration.regions:
        periods.extend(region.periods)

    for period in periods:
        stable = _is_year_stable(_period_calendar(configuration, period))
        applicable = [year for year in YEARS if period.applies_to(year)]
        for index, year in enumerate(applicable):
            if stable:
                assert period.name in names_per_year[year], (
                    f"{period.name}: no event in {year}"
                )
            else:
                following = applicable[index + 1] if index + 1 < len(applicable) else None
                found = period.name in names_per_year[year] or (
                    following is not None and period.name in names_per_year[following]
                )
                assert found, f"{period.name}: no event in {year}-{following}"
