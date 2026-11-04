"""Astronomical Chinese lunisolar calendar.

Months begin on the day of the astronomical new moon in local standard
time; the month containing the December solstice is month 11; in a leap
suì (the solstice-to-solstice span containing 13 month starts) the leap
month is the first one that contains no major solar term (zhōngqì).

The computation is parameterized by a fixed UTC offset, which is what
distinguishes the national calendars built on the same rules:

* ``tz=8``  -- China, Hong Kong, Macao, Singapore, Malaysia (UTC+8);
* ``tz=9``  -- Korea (UTC+9);
* ``tz=7``  -- Vietnam (UTC+7).  Tet occasionally differs from the
  Chinese New Year (e.g. 2007: 17 vs 18 February), which this module
  reproduces.

New moon instants follow Meeus, *Astronomical Algorithms*, ch. 49, and
the apparent solar longitude ch. 25 (low-precision series); both are
accurate to well under a minute, far below the day resolution needed.
"""

from __future__ import annotations

from datetime import date, timedelta
from functools import lru_cache
from math import cos, floor, pi, sin

from .calendars import gregorian_to_jdn, jdn_to_gregorian

_DEG = pi / 180.0


def _delta_t_seconds(year: float) -> float:
    """TT - UT1, Espenak/Meeus polynomial for 2005-2050 (fine nearby)."""
    t = year - 2000.0
    return 62.92 + 0.32217 * t + 0.005589 * t * t


def _jde_to_local_date(jde: float, tz_hours: float) -> date:
    """Calendar date of a TT instant at the given fixed UTC offset."""
    year = 2000.0 + (jde - 2451545.0) / 365.25
    jd_ut = jde - _delta_t_seconds(year) / 86400.0
    local = jd_ut + tz_hours / 24.0
    return jdn_to_gregorian(int(floor(local + 0.5)))


# ---------------------------------------------------------------------------
# New moons (Meeus ch. 49)
# ---------------------------------------------------------------------------

def _new_moon_jde(k: int) -> float:
    t = k / 1236.85
    t2, t3, t4 = t * t, t ** 3, t ** 4

    jde = (2451550.09766 + 29.530588861 * k
           + 0.00015437 * t2 - 0.000000150 * t3 + 0.00000000073 * t4)

    e = 1.0 - 0.002516 * t - 0.0000074 * t2
    m = (2.5534 + 29.10535670 * k - 0.0000014 * t2 - 0.00000011 * t3) * _DEG
    mp = (201.5643 + 385.81693528 * k + 0.0107582 * t2
          + 0.00001238 * t3 - 0.000000058 * t4) * _DEG
    f = (160.7108 + 390.67050284 * k - 0.0016118 * t2
         - 0.00000227 * t3 + 0.000000011 * t4) * _DEG
    om = (124.7746 - 1.56375588 * k + 0.0020672 * t2 + 0.00000215 * t3) * _DEG

    jde += (
        -0.40720 * sin(mp)
        + 0.17241 * e * sin(m)
        + 0.01608 * sin(2 * mp)
        + 0.01039 * sin(2 * f)
        + 0.00739 * e * sin(mp - m)
        - 0.00514 * e * sin(mp + m)
        + 0.00208 * e * e * sin(2 * m)
        - 0.00111 * sin(mp - 2 * f)
        - 0.00057 * sin(mp + 2 * f)
        + 0.00056 * e * sin(2 * mp + m)
        - 0.00042 * sin(3 * mp)
        + 0.00042 * e * sin(m + 2 * f)
        + 0.00038 * e * sin(m - 2 * f)
        - 0.00024 * e * sin(2 * mp - m)
        - 0.00017 * sin(om)
        - 0.00007 * sin(mp + 2 * m)
        + 0.00004 * sin(2 * mp - 2 * f)
        + 0.00004 * sin(3 * m)
        + 0.00003 * sin(mp + m - 2 * f)
        + 0.00003 * sin(2 * mp + 2 * f)
        - 0.00003 * sin(mp + m + 2 * f)
        + 0.00003 * sin(mp - m + 2 * f)
        - 0.00002 * sin(mp - m - 2 * f)
        - 0.00002 * sin(3 * mp + m)
        + 0.00002 * sin(4 * mp)
    )

    # planetary corrections
    a = (
        (299.77 + 0.107408 * k - 0.009173 * t2, 0.000325),
        (251.88 + 0.016321 * k, 0.000165),
        (251.83 + 26.651886 * k, 0.000164),
        (349.42 + 36.412478 * k, 0.000126),
        (84.66 + 18.206239 * k, 0.000110),
        (141.74 + 53.303771 * k, 0.000062),
        (207.14 + 2.453732 * k, 0.000060),
        (154.84 + 7.306860 * k, 0.000056),
        (34.52 + 27.261239 * k, 0.000047),
        (207.19 + 0.121824 * k, 0.000042),
        (291.34 + 1.844379 * k, 0.000040),
        (161.72 + 24.198154 * k, 0.000037),
        (239.56 + 25.513099 * k, 0.000035),
        (331.55 + 3.592518 * k, 0.000023),
    )
    for angle, coeff in a:
        jde += coeff * sin(angle * _DEG)

    return jde


def _new_moon_on_or_before(d: date, tz_hours: float) -> tuple[int, date]:
    """(k, local date) of the last new moon on or before ``d``."""
    approx = d.year + (d.timetuple().tm_yday - 1) / 365.25
    k = int(floor((approx - 2000.0) * 12.3685))
    while _jde_to_local_date(_new_moon_jde(k + 1), tz_hours) <= d:
        k += 1
    while _jde_to_local_date(_new_moon_jde(k), tz_hours) > d:
        k -= 1
    return k, _jde_to_local_date(_new_moon_jde(k), tz_hours)


# ---------------------------------------------------------------------------
# Apparent solar longitude and solar terms (Meeus ch. 25)
# ---------------------------------------------------------------------------

def _sun_apparent_longitude(jde: float) -> float:
    """Apparent longitude of the sun, degrees in [0, 360)."""
    t = (jde - 2451545.0) / 36525.0
    l0 = 280.46646 + 36000.76983 * t + 0.0003032 * t * t
    m = (357.52911 + 35999.05029 * t - 0.0001537 * t * t) * _DEG
    c = ((1.914602 - 0.004817 * t - 0.000014 * t * t) * sin(m)
         + (0.019993 - 0.000101 * t) * sin(2 * m)
         + 0.000289 * sin(3 * m))
    om = (125.04 - 1934.136 * t) * _DEG
    lam = l0 + c - 0.00569 - 0.00478 * sin(om)
    return lam % 360.0


def _solar_term_jde(longitude: float, jde_guess: float) -> float:
    """TT instant near ``jde_guess`` when the sun reaches ``longitude``."""
    jde = jde_guess
    for _ in range(6):
        diff = (longitude - _sun_apparent_longitude(jde) + 180.0) % 360.0 - 180.0
        jde += diff / 0.98565  # mean solar motion, degrees per day
    return jde


def solar_term_date(year: int, longitude: float, tz_hours: float = 8.0) -> date:
    """Local date in ``year`` when the sun reaches ``longitude`` degrees.

    The guess assumes the term named by its longitude in the usual solar
    year (e.g. 15 = Qingming in April, 270 = December solstice).
    """
    # day-of-year estimate: sun at 280 deg around 1 January
    doy = ((longitude - 280.0) % 360.0) / 0.98565
    guess = gregorian_to_jdn(year, 1, 1) + doy
    return _jde_to_local_date(_solar_term_jde(longitude, guess), tz_hours)


def qingming(year: int, tz_hours: float = 8.0) -> date:
    """Qingming festival: the solar term at 15 degrees (early April)."""
    return solar_term_date(year, 15.0, tz_hours)


def december_solstice(year: int, tz_hours: float = 8.0) -> date:
    """Local date of the December solstice (Dongzhi)."""
    return solar_term_date(year, 270.0, tz_hours)


# ---------------------------------------------------------------------------
# Month assembly
# ---------------------------------------------------------------------------

@lru_cache(maxsize=None)
def _sui_months(gyear: int, tz_hours: float) -> tuple:
    """Months of the sui ending at the December solstice of ``gyear``.

    Returns ``((number, is_leap, start_date), ...)`` from month 11 of
    lunar year ``gyear - 1`` through month 10 of lunar year ``gyear``.
    """
    s_prev = december_solstice(gyear - 1, tz_hours)
    s_cur = december_solstice(gyear, tz_hours)

    k0, start0 = _new_moon_on_or_before(s_prev, tz_hours)
    k1, _ = _new_moon_on_or_before(s_cur, tz_hours)

    starts = [_jde_to_local_date(_new_moon_jde(k), tz_hours) for k in range(k0, k1 + 1)]
    count = len(starts) - 1  # months strictly inside the sui span
    leap_sui = count == 13

    # major solar terms (zhongqi) of the sui: 270, 300, ..., 240 degrees
    zhongqi = []
    base = _solar_term_jde(270.0, gregorian_to_jdn(gyear - 1, 12, 21))
    for i in range(13):
        lon = (270.0 + 30.0 * i) % 360.0
        zhongqi.append(_jde_to_local_date(_solar_term_jde(lon, base + i * 30.44), tz_hours))

    def has_zhongqi(start: date, end: date) -> bool:
        return any(start <= z < end for z in zhongqi)

    months = []
    number = 11
    leap_used = False
    for i in range(count):
        start, end = starts[i], starts[i + 1]
        if i == 0:
            months.append((11, False, start))
            continue
        if leap_sui and not leap_used and not has_zhongqi(start, end):
            months.append((number, True, start))  # leap month keeps the number
            leap_used = True
        else:
            number = 1 if number == 12 else number + 1
            months.append((number, False, start))
    return tuple(months)


@lru_cache(maxsize=None)
def _year_months(lyear: int, tz_hours: float) -> tuple:
    """All months of lunar year ``lyear`` (1..12 plus leaps), with the
    exclusive end date of the year appended as ``(None, False, date)``."""
    first = [m for m in _sui_months(lyear, tz_hours) if m[0] < 11]
    second = [m for m in _sui_months(lyear + 1, tz_hours) if m[0] >= 11]
    nxt = [m for m in _sui_months(lyear + 1, tz_hours) if m[0] == 1]
    end = nxt[0][2] if nxt else second[-1][2] + timedelta(days=30)
    return tuple(first + second + [(None, False, end)])


def lunar_new_year(gyear: int, tz_hours: float = 8.0) -> date:
    """Local date of lunar month 1 day 1 of the lunar year ``gyear``."""
    for number, is_leap, start in _sui_months(gyear, tz_hours):
        if number == 1 and not is_leap:
            return start
    raise RuntimeError(f"no month 1 found for {gyear}")  # pragma: no cover


def lunar_to_gregorian(lyear: int, month: int, day: int, tz_hours: float = 8.0) -> date:
    """Gregorian date of a (regular) lunar month/day of lunar year ``lyear``."""
    if not 1 <= month <= 12:
        raise ValueError(f"lunar month must be 1..12, got {month}")
    months = _year_months(lyear, tz_hours)
    for index, (number, is_leap, start) in enumerate(months):
        if number == month and not is_leap:
            length = (months[index + 1][2] - start).days
            if not 1 <= day <= length:
                raise ValueError(
                    f"lunar {lyear}-{month} has {length} days, got day {day}"
                )
            return start + timedelta(days=day - 1)
    raise RuntimeError(f"month {month} not found in lunar year {lyear}")  # pragma: no cover


def gregorian_to_lunar(d: date, tz_hours: float = 8.0) -> tuple[int, int, int]:
    """(lunar year, month, day) containing ``d`` (leap months keep their
    regular month number)."""
    lyear = d.year if d >= lunar_new_year(d.year, tz_hours) else d.year - 1
    months = _year_months(lyear, tz_hours)
    for index in range(len(months) - 1):
        number, _, start = months[index]
        end = months[index + 1][2]
        if start <= d < end:
            return lyear, number, (d - start).days + 1
    raise RuntimeError(f"date {d} not located in lunar year {lyear}")  # pragma: no cover
