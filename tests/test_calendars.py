from datetime import date, timedelta

import pytest

from calendarium import UnsupportedCalendarError, get_calendar, julian_to_gregorian


def test_julian():
    assert julian_to_gregorian(2020, 12, 25) == date(2021, 1, 7)
    cal = get_calendar("Julian")
    assert cal.from_gregorian(date(2021, 1, 7)) == (2020, 12, 25)


def test_hijri_anchors():
    # match .NET HijriCalendar (tabular, adjustment 0)
    cal = get_calendar("Hijri")
    assert cal.to_gregorian(1442, 1, 1) == date(2020, 8, 20)
    assert cal.to_gregorian(1442, 9, 1) == date(2021, 4, 13)   # 1 Ramadan
    assert cal.to_gregorian(1442, 10, 1) == date(2021, 5, 13)  # Eid al-Fitr
    assert cal.year_of(date(2021, 2, 3)) == 1442


def test_hijri_roundtrip():
    cal = get_calendar("Hijri")
    d = date(2000, 1, 1)
    while d < date(2030, 1, 1):
        y, m, day = cal.from_gregorian(d)
        assert cal.to_gregorian(y, m, day) == d
        assert 1 <= m <= 12 and 1 <= day <= 30
        d += timedelta(days=97)


def test_umalqura_is_tabular_islamic():
    assert get_calendar("UmAlQura").to_gregorian(1442, 10, 1) == date(2021, 5, 13)


def test_hebrew_anchors():
    cal = get_calendar("Hebrew")
    # 1 Tishri 5780 (Rosh Hashanah) = 30 September 2019
    assert cal.to_gregorian(5780, 7, 1) == date(2019, 9, 30)
    # 15 Nisan (Pesach I): 5781 -> 28 March 2021, 5784 -> 23 April 2024
    assert cal.to_gregorian(5781, 1, 15) == date(2021, 3, 28)
    assert cal.to_gregorian(5784, 1, 15) == date(2024, 4, 23)
    assert cal.to_gregorian(5785, 1, 15) == date(2025, 4, 13)
    assert cal.from_gregorian(date(2024, 4, 23)) == (5784, 1, 15)


def test_hebrew_roundtrip():
    cal = get_calendar("Hebrew")
    d = date(2000, 1, 1)
    while d < date(2030, 1, 1):
        y, m, day = cal.from_gregorian(d)
        assert cal.to_gregorian(y, m, day) == d
        d += timedelta(days=61)


def test_persian_anchor():
    cal = get_calendar("Persian")
    assert cal.to_gregorian(1400, 1, 1) == date(2021, 3, 21)
    assert cal.from_gregorian(date(2021, 3, 21)) == (1400, 1, 1)


def test_offset_calendars():
    thai = get_calendar("ThaiBuddhist")
    assert thai.to_gregorian(2563, 4, 6) == date(2020, 4, 6)
    assert thai.year_of(date(2020, 2, 3)) == 2563
    taiwan = get_calendar("Taiwan")
    assert taiwan.to_gregorian(109, 10, 10) == date(2020, 10, 10)


def test_default_is_gregorian():
    assert get_calendar("Default").to_gregorian(2024, 2, 29) == date(2024, 2, 29)
    assert get_calendar(None).name == "Gregorian"


def test_unsupported_and_unknown():
    with pytest.raises(UnsupportedCalendarError):
        get_calendar("Japanese")
    with pytest.raises(ValueError):
        get_calendar("Klingon")
