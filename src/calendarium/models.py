"""Data model of the Calendarium referential.

The JSON schema is unchanged from the original C# project (PascalCase keys),
so the existing per-country configuration files are reused as-is.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional


@dataclass
class Translation:
    """A translated name of a period (``NameConfiguration`` in C#)."""

    language: str
    name: str

    @classmethod
    def from_dict(cls, data: dict) -> "Translation":
        return cls(language=data.get("Language") or "Undefined", name=data.get("Name") or "")


@dataclass
class Period:
    """A computed date rule (``PeriodConfiguration`` in C#)."""

    name: str
    rule_date: str
    rule_observed: Optional[str] = None
    rule_duration: Optional[str] = None
    free: bool = False
    calendar: str = "Default"
    translations: List[Translation] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    year_start: Optional[int] = None
    year_end: Optional[int] = None

    @classmethod
    def from_dict(cls, data: dict) -> "Period":
        return cls(
            name=data["Name"],
            rule_date=data["RuleDate"],
            rule_observed=data.get("RuleObserved") or None,
            rule_duration=data.get("RuleDuration") or None,
            free=bool(data.get("Free", False)),
            calendar=data.get("Calendar") or "Default",
            translations=[Translation.from_dict(t) for t in data.get("Translations") or []],
            tags=list(data.get("Tags") or []),
            # the original schema documented "YearFrom"; the C# model used
            # "YearStart" -- data files contain both, accept both
            year_start=data.get("YearStart", data.get("YearFrom")),
            year_end=data.get("YearEnd"),
        )

    def applies_to(self, year: int) -> bool:
        """Inclusive year bounds: the festivity exists from ``year_start``
        up to ``year_end``."""
        if self.year_start is not None and year < self.year_start:
            return False
        if self.year_end is not None and year > self.year_end:
            return False
        return True


@dataclass
class Region:
    """A sub-country rule set (``RegionConfiguration`` in C#).

    ``from_region`` copies the periods of another region of the same country
    (JSON key ``From``).
    """

    key: str
    periods: List[Period] = field(default_factory=list)
    from_region: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict) -> "Region":
        return cls(
            key=data.get("Key") or "",
            periods=[Period.from_dict(p) for p in data.get("Periods") or []],
            from_region=data.get("From") or None,
        )


@dataclass
class CountryConfiguration:
    """A country (or shared *default*) configuration file."""

    country: str
    culture: Optional[str] = None
    calendar: str = "Default"
    periods: List[Period] = field(default_factory=list)
    regions: List[Region] = field(default_factory=list)
    defaults: Optional[str] = None  # comma-separated names of default configs
    url: Optional[str] = None
    is_default: bool = False  # True for *.Default.json files
    source_file: Optional[str] = None

    @classmethod
    def from_dict(
        cls,
        data: dict,
        is_default: bool = False,
        source_file: Optional[str] = None,
    ) -> "CountryConfiguration":
        return cls(
            country=data["Country"],
            culture=data.get("Culture") or None,
            calendar=data.get("Calendar") or "Default",
            periods=[Period.from_dict(p) for p in data.get("Periods") or []],
            regions=[Region.from_dict(r) for r in data.get("Regions") or []],
            defaults=data.get("Defaults") or None,
            url=data.get("Url") or None,
            is_default=is_default,
            source_file=source_file,
        )


@dataclass
class EventDate:
    """One computed festivity on a given date.

    ``date`` is the actual (legal) date of the festivity; ``observed`` is the
    date it is observed when a ``RuleObserved`` shifts it (for instance a
    holiday falling on a weekend observed the following Monday).  When no
    rule applies, ``observed == date``.

    ``free`` qualifies the festivity; the day actually non-worked is the
    **observed** date.  When the observance is shifted, the actual date keeps
    the identity of the festivity but does not count as a day off.
    """

    name: str
    date: date
    observed: date
    free: bool
    country: str
    region: str = ""
    culture: Optional[str] = None
    calendar: str = "Gregorian"
    date_end: Optional[date] = None
    translations: List[Translation] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)

    @property
    def is_shifted(self) -> bool:
        """True when the observed date differs from the actual date."""
        return self.observed != self.date

    def is_free_on(self, d: date) -> bool:
        """True when this event makes ``d`` a non-working day.

        A free festivity is non-worked on its observed date only.
        """
        return self.free and self.observed == d

    def translation(self, language: str) -> Optional[str]:
        for t in self.translations:
            if t.language.lower() == language.lower():
                return t.name
        return None

    def _identity(self) -> tuple:
        return (self.name, self.country, self.region, self.date, self.observed)


@dataclass
class IdentifiedDate:
    """All festivities attached to one calendar date (``IdentifiedDate`` in C#)."""

    date: date
    events: List[EventDate] = field(default_factory=list)

    @property
    def free(self) -> bool:
        """True when at least one event makes this day a non-working day.

        Follows the observed-date rule: a free festivity whose observance is
        shifted away from this date does not make this date free.
        """
        return any(e.is_free_on(self.date) for e in self.events)

    def merge(self, other: "IdentifiedDate") -> None:
        known = {e._identity() for e in self.events}
        for event in other.events:
            if event._identity() not in known:
                self.events.append(event)
                known.add(event._identity())

    def clone(self) -> "IdentifiedDate":
        return IdentifiedDate(date=self.date, events=list(self.events))
