"""Calendar systems and conversions to/from the (proleptic) Gregorian calendar.

The original C# implementation relied on ``System.Globalization`` calendars.
This module provides the subset actually used by the country configuration
files, implemented with well known arithmetic algorithms and no third-party
dependency:

* ``Gregorian`` (and ``Default``)
* ``Julian``
* ``Hijri`` / ``UmAlQura`` -- tabular (civil) Islamic calendar, the same
  arithmetic family as .NET's ``HijriCalendar`` (adjustment 0).  For
  ``UmAlQura`` this is an approximation of the Saudi lookup-table calendar
  (observed dates may differ by one day).
* ``Hebrew`` -- arithmetic Hebrew calendar (Dershowitz & Reingold), used for
  Jewish observances such as Passover.
* ``Persian`` -- arithmetic Jalaali calendar (jalaali-js algorithm).
* ``ThaiBuddhist`` / ``Taiwan`` / ``Korean`` -- Gregorian with a year offset.

Calendars that no configuration file uses (``Japanese`` and the lunisolar
variants) raise :class:`UnsupportedCalendarError`.
"""

from __future__ import annotations

from datetime import date


class UnsupportedCalendarError(NotImplementedError):
    """Raised when a configuration requires a calendar that is not implemented."""


# ---------------------------------------------------------------------------
# Julian day number helpers
# ---------------------------------------------------------------------------

def gregorian_to_jdn(year: int, month: int, day: int) -> int:
    a = (14 - month) // 12
    y = year + 4800 - a
    m = month + 12 * a - 3
    return day + (153 * m + 2) // 5 + 365 * y + y // 4 - y // 100 + y // 400 - 32045


def jdn_to_gregorian(jdn: int) -> date:
    a = jdn + 32044
    b = (4 * a + 3) // 146097
    c = a - 146097 * b // 4
    d = (4 * c + 3) // 1461
    e = c - 1461 * d // 4
    m = (5 * e + 2) // 153
    day = e - (153 * m + 2) // 5 + 1
    month = m + 3 - 12 * (m // 10)
    year = 100 * b + d - 4800 + m // 10
    return date(year, month, day)


def julian_to_jdn(year: int, month: int, day: int) -> int:
    a = (14 - month) // 12
    y = year + 4800 - a
    m = month + 12 * a - 3
    return day + (153 * m + 2) // 5 + 365 * y + y // 4 - 32083


def jdn_to_julian(jdn: int) -> tuple[int, int, int]:
    b = 0
    c = jdn + 32082
    d = (4 * c + 3) // 1461
    e = c - 1461 * d // 4
    m = (5 * e + 2) // 153
    day = e - (153 * m + 2) // 5 + 1
    month = m + 3 - 12 * (m // 10)
    year = 100 * b + d - 4800 + m // 10
    return year, month, day


def julian_to_gregorian(year: int, month: int, day: int) -> date:
    """Convert a Julian-calendar date to the equivalent Gregorian date."""
    return jdn_to_gregorian(julian_to_jdn(year, month, day))


# ---------------------------------------------------------------------------
# Tabular (civil) Islamic calendar
# ---------------------------------------------------------------------------

_ISLAMIC_EPOCH_JDN = 1948440  # civil epoch: 1 Muharram 1 AH = 16 July 622 (Julian)


def islamic_to_jdn(year: int, month: int, day: int) -> int:
    return (
        day
        + 29 * (month - 1)
        + month // 2
        + 354 * (year - 1)
        + (3 + 11 * year) // 30
        + _ISLAMIC_EPOCH_JDN
        - 1
    )


def jdn_to_islamic(jdn: int) -> tuple[int, int, int]:
    year = (30 * (jdn - _ISLAMIC_EPOCH_JDN) + 10646) // 10631
    month = 1
    for m in range(12, 0, -1):
        if jdn >= islamic_to_jdn(year, m, 1):
            month = m
            break
    day = jdn - islamic_to_jdn(year, month, 1) + 1
    return year, month, day


# ---------------------------------------------------------------------------
# Hebrew calendar (arithmetic, Dershowitz & Reingold)
#
# Months are numbered in the biblical convention used by Calendrical
# Calculations: 1 = Nisan ... 7 = Tishri ... 12 = Adar (13 = Adar II in leap
# years).  The year begins on 1 Tishri.
# ---------------------------------------------------------------------------

_HEBREW_EPOCH_JDN = 347998  # 1 Tishri, A.M. 1 (7 October 3761 BCE, Julian)


def hebrew_leap_year(year: int) -> bool:
    return (7 * year + 1) % 19 < 7


def hebrew_months_in_year(year: int) -> int:
    return 13 if hebrew_leap_year(year) else 12


def _hebrew_elapsed_days(year: int) -> int:
    months_elapsed = (235 * year - 234) // 19
    parts_elapsed = 12084 + 13753 * months_elapsed
    days = 29 * months_elapsed + parts_elapsed // 25920
    if (3 * (days + 1)) % 7 < 3:
        days += 1
    return days


def _hebrew_new_year_delay(year: int) -> int:
    ny0 = _hebrew_elapsed_days(year - 1)
    ny1 = _hebrew_elapsed_days(year)
    ny2 = _hebrew_elapsed_days(year + 1)
    if ny2 - ny1 == 356:
        return 2
    if ny1 - ny0 == 382:
        return 1
    return 0


def _hebrew_new_year_jdn(year: int) -> int:
    return _HEBREW_EPOCH_JDN + _hebrew_elapsed_days(year) + _hebrew_new_year_delay(year)


def _days_in_hebrew_year(year: int) -> int:
    return _hebrew_new_year_jdn(year + 1) - _hebrew_new_year_jdn(year)


def _last_day_of_hebrew_month(year: int, month: int) -> int:
    if month in (2, 4, 6, 10, 13):
        return 29
    if month == 12 and not hebrew_leap_year(year):
        return 29
    if month == 8 and _days_in_hebrew_year(year) % 10 != 5:  # Heshvan
        return 29
    if month == 9 and _days_in_hebrew_year(year) % 10 == 3:  # Kislev
        return 29
    return 30


def hebrew_to_jdn(year: int, month: int, day: int) -> int:
    jdn = _hebrew_new_year_jdn(year) + day - 1
    if month < 7:
        for m in range(7, hebrew_months_in_year(year) + 1):
            jdn += _last_day_of_hebrew_month(year, m)
        for m in range(1, month):
            jdn += _last_day_of_hebrew_month(year, m)
    else:
        for m in range(7, month):
            jdn += _last_day_of_hebrew_month(year, m)
    return jdn


def jdn_to_hebrew(jdn: int) -> tuple[int, int, int]:
    approx = (jdn - _HEBREW_EPOCH_JDN) * 98496 // 35975351 + 1
    year = approx - 1
    while _hebrew_new_year_jdn(year + 1) <= jdn:
        year += 1
    month = 7 if jdn < hebrew_to_jdn(year, 1, 1) else 1
    while jdn > hebrew_to_jdn(year, month, _last_day_of_hebrew_month(year, month)):
        month += 1
    day = jdn - hebrew_to_jdn(year, month, 1) + 1
    return year, month, day


# ---------------------------------------------------------------------------
# Arithmetic Persian (Jalaali) calendar -- jalaali-js algorithm
# ---------------------------------------------------------------------------

_JALAALI_BREAKS = (
    -61, 9, 38, 199, 426, 686, 756, 818, 1111, 1181, 1210,
    1635, 2060, 2097, 2192, 2262, 2324, 2394, 2456, 3178,
)


def _jal_cal(jy: int) -> tuple[int, int, int]:
    """Return (leap, gregorian_year, march_day) for Persian year ``jy``."""
    if not (_JALAALI_BREAKS[0] <= jy < _JALAALI_BREAKS[-1]):
        raise ValueError(f"Persian year {jy} out of supported range")

    gy = jy + 621
    leap_j = -14
    jp = _JALAALI_BREAKS[0]
    jump = 0
    for jm in _JALAALI_BREAKS[1:]:
        jump = jm - jp
        if jy < jm:
            break
        leap_j += (jump // 33) * 8 + (jump % 33) // 4
        jp = jm
    n = jy - jp
    leap_j += (n // 33) * 8 + ((n % 33) + 3) // 4
    if jump % 33 == 4 and jump - n == 4:
        leap_j += 1
    leap_g = gy // 4 - ((gy // 100 + 1) * 3) // 4 - 150
    march = 20 + leap_j - leap_g
    if jump - n < 6:
        n = n - jump + ((jump + 4) // 33) * 33
    leap = (((n + 1) % 33) - 1) % 4
    if leap == -1:
        leap = 4
    return leap, gy, march


def jalaali_to_jdn(jy: int, jm: int, jd: int) -> int:
    _, gy, march = _jal_cal(jy)
    return (
        gregorian_to_jdn(gy, 3, march)
        + (jm - 1) * 31
        - (jm // 7) * (jm - 7)
        + jd
        - 1
    )


def jdn_to_jalaali(jdn: int) -> tuple[int, int, int]:
    gy = jdn_to_gregorian(jdn).year
    jy = gy - 621
    leap, _, march = _jal_cal(jy)
    k = jdn - gregorian_to_jdn(gy, 3, march)
    if k >= 0:
        if k <= 185:
            return jy, 1 + k // 31, (k % 31) + 1
        k -= 186
    else:
        jy -= 1
        k += 179
        if leap == 1:
            k += 1
    return jy, 7 + k // 30, (k % 30) + 1


# ---------------------------------------------------------------------------
# Calendar objects
# ---------------------------------------------------------------------------

class CalendarBase:
    """Conversion interface between a calendar system and Gregorian dates."""

    name = "Base"

    def to_gregorian(self, year: int, month: int, day: int) -> date:
        raise NotImplementedError

    def from_gregorian(self, d: date) -> tuple[int, int, int]:
        raise NotImplementedError

    def year_of(self, d: date) -> int:
        """Year of this calendar containing the Gregorian date ``d``."""
        return self.from_gregorian(d)[0]

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Calendar {self.name}>"


class GregorianCalendar(CalendarBase):
    name = "Gregorian"

    def to_gregorian(self, year: int, month: int, day: int) -> date:
        return date(year, month, day)

    def from_gregorian(self, d: date) -> tuple[int, int, int]:
        return d.year, d.month, d.day


class _OffsetCalendar(CalendarBase):
    """Gregorian months/days with an offset applied to the year."""

    offset = 0

    def to_gregorian(self, year: int, month: int, day: int) -> date:
        return date(year - self.offset, month, day)

    def from_gregorian(self, d: date) -> tuple[int, int, int]:
        return d.year + self.offset, d.month, d.day


class ThaiBuddhistCalendar(_OffsetCalendar):
    name = "ThaiBuddhist"
    offset = 543


class TaiwanCalendar(_OffsetCalendar):
    name = "Taiwan"
    offset = -1911


class KoreanCalendar(_OffsetCalendar):
    name = "Korean"
    offset = 2333


class JulianCalendar(CalendarBase):
    name = "Julian"

    def to_gregorian(self, year: int, month: int, day: int) -> date:
        return julian_to_gregorian(year, month, day)

    def from_gregorian(self, d: date) -> tuple[int, int, int]:
        return jdn_to_julian(gregorian_to_jdn(d.year, d.month, d.day))


class HijriCalendar(CalendarBase):
    name = "Hijri"

    def to_gregorian(self, year: int, month: int, day: int) -> date:
        return jdn_to_gregorian(islamic_to_jdn(year, month, day))

    def from_gregorian(self, d: date) -> tuple[int, int, int]:
        return jdn_to_islamic(gregorian_to_jdn(d.year, d.month, d.day))


class UmAlQuraCalendar(HijriCalendar):
    name = "UmAlQura"


class HebrewCalendar(CalendarBase):
    """Arithmetic Hebrew calendar.

    Months use the biblical numbering (1 = Nisan ... 7 = Tishri, 13 = Adar II
    in leap years), which is stable across leap years for the spring months.
    """

    name = "Hebrew"

    def to_gregorian(self, year: int, month: int, day: int) -> date:
        return jdn_to_gregorian(hebrew_to_jdn(year, month, day))

    def from_gregorian(self, d: date) -> tuple[int, int, int]:
        return jdn_to_hebrew(gregorian_to_jdn(d.year, d.month, d.day))


class PersianCalendar(CalendarBase):
    name = "Persian"

    def to_gregorian(self, year: int, month: int, day: int) -> date:
        return jdn_to_gregorian(jalaali_to_jdn(year, month, day))

    def from_gregorian(self, d: date) -> tuple[int, int, int]:
        return jdn_to_jalaali(gregorian_to_jdn(d.year, d.month, d.day))


_CALENDARS = {
    "default": GregorianCalendar(),
    "gregorian": GregorianCalendar(),
    "julian": JulianCalendar(),
    "hebrew": HebrewCalendar(),
    "hijri": HijriCalendar(),
    "umalqura": UmAlQuraCalendar(),
    "persian": PersianCalendar(),
    "thaibuddhist": ThaiBuddhistCalendar(),
    "taiwan": TaiwanCalendar(),
    "korean": KoreanCalendar(),
}

#: Calendars recognized by the configuration schema but not implemented.
_KNOWN_UNSUPPORTED = {
    "japanese", "japaneselunisolar", "koreanlunisolar", "taiwanlunisolar",
}


def get_calendar(name: str) -> CalendarBase:
    """Return the calendar named in a configuration file (case-insensitive).

    ``None`` or an empty name maps to the Gregorian calendar (``Default``).
    """
    key = (name or "Default").strip().lower()
    cal = _CALENDARS.get(key)
    if cal is not None:
        return cal
    if key in _KNOWN_UNSUPPORTED:
        raise UnsupportedCalendarError(
            f"calendar {name!r} is not implemented in the Python port"
        )
    raise ValueError(f"unknown calendar {name!r}")
