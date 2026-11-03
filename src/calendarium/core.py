"""The Calendarium engine.

Port of the C# ``CalendariumConfiguration`` / ``ConfigurationEvaluatorVisitor``:
compiles the rule strings of every loaded configuration, then computes, with
caching, the festivities of a (Gregorian) year for a country and optional
region.

Differences with the C# engine, on purpose:

* ``YearStart`` / ``YearEnd`` bounds are inclusive, as documented in the
  original README (the C# code skipped the boundary years);
* for a non-Gregorian period calendar, the rule is evaluated for **every**
  calendar year overlapping the requested Gregorian year and the results are
  clipped to that Gregorian year (the C# engine evaluated a single calendar
  year, missing festivities at the end of the Gregorian year and leaking
  dates of the previous one).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple, Union

from .calendars import CalendarBase, GregorianCalendar, get_calendar
from .loader import load_bundled, load_directory, split_defaults
from .models import CountryConfiguration, EventDate, IdentifiedDate, Period
from .rules import DateRule, ObservedRule, parse_date_rule, parse_observed_rule


@dataclass
class _CompiledPeriod:
    period: Period
    culture: Optional[str]
    calendar: CalendarBase
    date_rule: DateRule
    observed_rule: Optional[ObservedRule] = None
    duration_rule: Optional[ObservedRule] = None
    extra_tags: List[str] = field(default_factory=list)


class Calendarium:
    """Computes the identified dates of the loaded country configurations.

    >>> cal = Calendarium.bundled()
    >>> dates = cal.get_dates(2024, "France")
    >>> dates[date(2024, 7, 14)].events[0].name
    'Bastille Day'
    """

    def __init__(self, configurations: Iterable[CountryConfiguration]):
        countries, defaults = split_defaults(configurations)
        self._configurations = countries
        self._defaults = {d.country: d for d in defaults}
        self._rules: Dict[Tuple[str, str], List[_CompiledPeriod]] = {}
        self._cache: Dict[Tuple[int, str, str], Dict[date, IdentifiedDate]] = {}
        for configuration in countries:
            self._register(configuration)

    # -- constructors ------------------------------------------------------

    @classmethod
    def bundled(cls, include_not_checked: bool = False) -> "Calendarium":
        """Engine over the referential shipped with the package."""
        return cls(load_bundled(include_not_checked=include_not_checked))

    @classmethod
    def from_directory(cls, path: Union[str, Path], recursive: bool = False) -> "Calendarium":
        """Engine over the ``date_*.json`` files of a directory."""
        return cls(load_directory(path, recursive=recursive))

    # -- registration ------------------------------------------------------

    def _register(self, configuration: CountryConfiguration) -> None:
        country = configuration.country
        culture = configuration.culture

        country_periods: List[_CompiledPeriod] = []

        # shared defaults imported through the `Defaults` property
        if configuration.defaults:
            for name in (n.strip() for n in configuration.defaults.split(",")):
                if not name:
                    continue
                if name not in self._defaults:
                    raise KeyError(
                        f"{country}: unknown default configuration {name!r} "
                        f"(loaded: {sorted(self._defaults)})"
                    )
                shared = self._defaults[name]
                country_periods.extend(
                    self._compile(
                        shared.periods,
                        shared.culture or culture,
                        configuration.calendar,
                        extra_tags=[name],
                    )
                )

        country_periods.extend(
            self._compile(configuration.periods, culture, configuration.calendar)
        )
        self._rules[(country, "")] = country_periods

        # regions: own periods + country periods (+ periods copied with `From`)
        by_key = {region.key: region for region in configuration.regions}
        for region in configuration.regions:
            compiled = self._compile(region.periods, culture, configuration.calendar)
            if region.from_region:
                if region.from_region not in by_key:
                    raise KeyError(
                        f"{country}: region {region.key!r} copies unknown region "
                        f"{region.from_region!r}"
                    )
                source = by_key[region.from_region]
                compiled.extend(
                    self._compile(source.periods, culture, configuration.calendar)
                )
            compiled.extend(country_periods)
            self._rules[(country, region.key)] = compiled

    def _compile(
        self,
        periods: List[Period],
        culture: Optional[str],
        country_calendar: str,
        extra_tags: Optional[List[str]] = None,
    ) -> List[_CompiledPeriod]:
        compiled = []
        for period in periods:
            calendar_name = period.calendar
            if calendar_name in (None, "", "Default"):
                calendar_name = country_calendar
            compiled.append(
                _CompiledPeriod(
                    period=period,
                    culture=culture,
                    calendar=get_calendar(calendar_name),
                    date_rule=parse_date_rule(period.rule_date),
                    observed_rule=(
                        parse_observed_rule(period.rule_observed)
                        if period.rule_observed
                        else None
                    ),
                    duration_rule=(
                        parse_observed_rule(period.rule_duration)
                        if period.rule_duration
                        else None
                    ),
                    extra_tags=list(extra_tags or []),
                )
            )
        return compiled

    # -- queries -----------------------------------------------------------

    def countries(self) -> List[str]:
        """Registered country names."""
        return sorted({country for country, _ in self._rules})

    def regions(self, country: str) -> List[str]:
        """Region keys of a country (empty list when it has none)."""
        return sorted(region for c, region in self._rules if c == country and region)

    def configuration(self, country: str) -> Optional[CountryConfiguration]:
        for configuration in self._configurations:
            if configuration.country == country:
                return configuration
        return None

    def get_dates(
        self,
        year: int,
        country: str,
        region: str = "",
        key: str = "date",
    ) -> Dict[date, IdentifiedDate]:
        """Identified dates of a Gregorian year for a country.

        ``region`` selects a region rule set (region rules include the
        country-level ones).  ``key`` selects the index: ``"date"`` (actual
        festivity date, default) or ``"observed"`` (date the festivity is
        observed -- the non-working day for free festivities).
        """
        self._check_key(key)
        if key == "observed":
            return self._observed(year, country, region)
        return self._build(year, country, region)

    def get_all_dates(
        self,
        year: int,
        country: str,
        key: str = "date",
    ) -> Dict[date, IdentifiedDate]:
        """Identified dates of a year with every region of the country merged."""
        self._check_key(key)
        merged: Dict[date, IdentifiedDate] = {}
        for _, region in self._keys(country):
            for d, identified in self.get_dates(year, country, region, key).items():
                if d in merged:
                    merged[d].merge(identified)
                else:
                    merged[d] = identified.clone()
        return dict(sorted(merged.items()))

    def get_date(
        self,
        d: date,
        country: str,
        region: Optional[str] = None,
        key: str = "date",
    ) -> Optional[IdentifiedDate]:
        """Festivities on one date, or ``None``.

        With ``region=None`` every region of the country is searched.
        ``key="observed"`` looks the date up as an observed day instead of an
        actual festivity date.
        """
        self._check_key(key)
        regions = [region] if region is not None else [r for _, r in self._keys(country)]
        result: Optional[IdentifiedDate] = None
        for reg in regions:
            identified = self.get_dates(d.year, country, reg, key).get(d)
            if identified is not None:
                if result is None:
                    result = identified.clone()
                else:
                    result.merge(identified)
        return result

    def is_free(self, d: date, country: str, region: str = "") -> bool:
        """True when the date is a non-working day for the country.

        Follows the observed-date rule: a free festivity counts on its
        observed date (which is its actual date when nothing shifts it).
        Weekends themselves are not modelled here.
        """
        identified = self._observed(d.year, country, region).get(d)
        return identified.free if identified else False

    def get_next_dates(
        self,
        start: date,
        country: str,
        count_days: int = 365,
        regions: Iterable[str] = (),
    ) -> Dict[date, IdentifiedDate]:
        """Identified dates in the window ``[start, start + count_days]``."""
        regions = list(regions) or [""]
        end = start + timedelta(days=count_days)
        result: Dict[date, IdentifiedDate] = {}
        for region in regions:
            for year in range(start.year, end.year + 1):
                for d, identified in self._build(year, country, region).items():
                    if start <= d <= end:
                        if d in result:
                            result[d].merge(identified)
                        else:
                            result[d] = identified.clone()
        return dict(sorted(result.items()))

    # -- internals ----------------------------------------------------------

    def _keys(self, country: str) -> List[Tuple[str, str]]:
        keys = [key for key in self._rules if key[0] == country]
        if not keys:
            raise KeyError(
                f"unknown country {country!r} (loaded: {', '.join(self.countries())})"
            )
        return sorted(keys)

    @staticmethod
    def _check_key(key: str) -> None:
        if key not in ("date", "observed"):
            raise ValueError(f"key must be 'date' or 'observed', got {key!r}")

    def _observed(self, year: int, country: str, region: str) -> Dict[date, IdentifiedDate]:
        """Events of a year indexed by observed date.

        An observed rule can shift a festivity into the next year (e.g. a
        31 December holiday observed the following Monday), so the adjacent
        years are scanned and the result is clipped to observed dates of
        ``year``.
        """
        result: Dict[date, IdentifiedDate] = {}
        for source_year in (year - 1, year, year + 1):
            for identified in self._build(source_year, country, region).values():
                for event in identified.events:
                    if event.observed.year == year:
                        target = result.setdefault(
                            event.observed, IdentifiedDate(date=event.observed)
                        )
                        target.events.append(event)
        return dict(sorted(result.items()))

    def _build(self, year: int, country: str, region: str) -> Dict[date, IdentifiedDate]:
        rules = self._rules.get((country, region or ""))
        if rules is None:
            self._keys(country)  # raises for unknown country
            raise KeyError(
                f"unknown region {region!r} for {country} "
                f"(regions: {', '.join(self.regions(country)) or 'none'})"
            )

        cache_key = (year, country, region or "")
        cached = self._cache.get(cache_key)
        if cached is None:
            cached = {}
            for compiled in rules:
                if compiled.period.applies_to(year):
                    self._apply(cached, compiled, year, country, region or "")
            self._cache[cache_key] = dict(sorted(cached.items()))

        # hand out copies so callers can merge/mutate freely
        return {d: identified.clone() for d, identified in self._cache[cache_key].items()}

    def _apply(
        self,
        result: Dict[date, IdentifiedDate],
        compiled: _CompiledPeriod,
        year: int,
        country: str,
        region: str,
    ) -> None:
        calendar = compiled.calendar
        gregorian = isinstance(calendar, GregorianCalendar)

        if gregorian:
            calendar_years = [year]
        else:
            # every calendar year overlapping the Gregorian year
            first = calendar.year_of(date(year, 1, 1))
            last = calendar.year_of(date(year, 12, 31))
            calendar_years = range(first, last + 1)

        for calendar_year in calendar_years:
            for d in compiled.date_rule.evaluate(calendar_year, calendar):

                if not gregorian and d.year != year:
                    continue  # clip to the requested Gregorian year

                observed = (
                    compiled.observed_rule.evaluate(d)
                    if compiled.observed_rule
                    else d
                )
                date_end = (
                    compiled.duration_rule.evaluate(d)
                    if compiled.duration_rule
                    else None
                )

                event = EventDate(
                    name=compiled.period.name,
                    date=d,
                    observed=observed,
                    free=compiled.period.free,
                    country=country,
                    region=region,
                    culture=compiled.culture,
                    calendar=calendar.name,
                    date_end=date_end,
                    translations=list(compiled.period.translations),
                    tags=list(compiled.period.tags) + list(compiled.extra_tags),
                )

                identified = result.get(d)
                if identified is None:
                    result[d] = identified = IdentifiedDate(date=d)
                identified.events.append(event)
