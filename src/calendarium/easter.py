"""Easter computation.

Port of the original C# ``EasterHelper`` (Black.Beard.Calendarium).
"""

from __future__ import annotations

from datetime import date

from .calendars import julian_to_gregorian


def easter_date(year: int) -> date:
    """Gregorian (western) Easter Sunday.

    Meeus/Jones/Butcher Gregorian algorithm,
    https://en.wikipedia.org/wiki/Computus
    """
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def orthodox_easter_date(year: int) -> date:
    """Orthodox (eastern) Easter Sunday, as a Gregorian calendar date.

    Meeus Julian algorithm: the result is computed in the Julian calendar
    and converted to the Gregorian calendar.
    """
    a = year % 4
    b = year % 7
    c = year % 19
    d = ((19 * c) + 15) % 30
    e = (((2 * a) + (4 * b)) - d + 34) % 7
    month = (d + e + 114) // 31
    day = ((d + e + 114) % 31) + 1
    return julian_to_gregorian(year, month, day)
