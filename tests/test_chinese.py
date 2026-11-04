from datetime import date

import pytest

from calendarium import get_calendar, parse_date_rule
from calendarium.chinese import (
    december_solstice,
    gregorian_to_lunar,
    lunar_new_year,
    lunar_to_gregorian,
    qingming,
)


def test_chinese_new_year_anchors():
    expected = {
        2020: (1, 25), 2021: (2, 12), 2022: (2, 1), 2023: (1, 22),
        2024: (2, 10), 2025: (1, 29), 2026: (2, 17), 2027: (2, 6),
    }
    for year, (month, day) in expected.items():
        assert lunar_new_year(year, 8) == date(year, month, day), year


def test_festival_anchors_utc8():
    assert lunar_to_gregorian(2024, 5, 5, 8) == date(2024, 6, 10)   # Dragon Boat
    assert lunar_to_gregorian(2025, 5, 5, 8) == date(2025, 5, 31)
    assert lunar_to_gregorian(2024, 8, 15, 8) == date(2024, 9, 17)  # Mid-Autumn
    assert lunar_to_gregorian(2025, 8, 15, 8) == date(2025, 10, 6)
    assert lunar_to_gregorian(2026, 8, 15, 8) == date(2026, 9, 25)
    assert lunar_to_gregorian(2025, 4, 8, 8) == date(2025, 5, 5)    # Buddha
    assert lunar_to_gregorian(2025, 4, 15, 8) == date(2025, 5, 12)  # Vesak
    assert lunar_to_gregorian(2025, 9, 9, 8) == date(2025, 10, 29)  # Chung Yeung


def test_leap_months():
    # 2023 has a leap month 2; 2025 a leap month 6: regular masks must
    # land on the regular months.
    assert lunar_to_gregorian(2023, 4, 8, 8) == date(2023, 5, 26)
    assert lunar_to_gregorian(2023, 1, 1, 8) == date(2023, 1, 22)
    assert lunar_to_gregorian(2025, 8, 15, 8) == date(2025, 10, 6)


def test_solar_terms():
    assert qingming(2024) == date(2024, 4, 4)
    assert qingming(2025) == date(2025, 4, 4)
    assert qingming(2026) == date(2026, 4, 5)
    assert december_solstice(2024) == date(2024, 12, 21)
    assert december_solstice(2025) == date(2025, 12, 21)
    assert december_solstice(2026) == date(2026, 12, 22)


def test_national_meridians():
    # Korea (UTC+9): Seollal and Chuseok
    assert lunar_new_year(2025, 9) == date(2025, 1, 29)
    assert lunar_to_gregorian(2024, 8, 15, 9) == date(2024, 9, 17)
    # Vietnam (UTC+7): Tet 2007 famously fell a day before China's CNY
    assert lunar_new_year(2007, 7) == date(2007, 2, 17)
    assert lunar_new_year(2007, 8) == date(2007, 2, 18)
    assert lunar_to_gregorian(2025, 3, 10, 7) == date(2025, 4, 7)   # Hung Kings


def test_roundtrip():
    for year in range(1995, 2051, 3):
        d = lunar_new_year(year, 8)
        assert gregorian_to_lunar(d, 8) == (year, 1, 1), year
        d2 = lunar_to_gregorian(year, 8, 15, 8)
        assert gregorian_to_lunar(d2, 8) == (year, 8, 15), year


def test_calendar_objects():
    chinese = get_calendar("Chinese")
    assert chinese.to_gregorian(2025, 1, 1) == date(2025, 1, 29)
    assert chinese.year_of(date(2025, 1, 15)) == 2024  # before CNY 2025
    assert chinese.year_of(date(2025, 12, 31)) == 2025
    korean = get_calendar("KoreanLunisolar")
    assert korean.to_gregorian(2025, 8, 15) == date(2025, 10, 6)
    viet = get_calendar("VietnameseLunisolar")
    assert viet.to_gregorian(2007, 1, 1) == date(2007, 2, 17)


def test_rule_functions():
    assert parse_date_rule("[QINGMING]").evaluate(2025) == [date(2025, 4, 4)]
    assert parse_date_rule("[DONGZHI]").evaluate(2026) == [date(2026, 12, 22)]
    assert parse_date_rule("[DEEPAVALI]").evaluate(2024) == [date(2024, 10, 31)]
    assert parse_date_rule("[DEEPAVALI]").evaluate(2025) == [date(2025, 10, 20)]
    with pytest.raises(ValueError):
        parse_date_rule("[DEEPAVALI]").evaluate(2060)


def test_chinese_masks_in_rules():
    rule = parse_date_rule("1-1")
    assert rule.evaluate(2025, get_calendar("Chinese")) == [date(2025, 1, 29)]
    eve = parse_date_rule("(1-1) - 1")
    assert eve.evaluate(2025, get_calendar("Chinese")) == [date(2025, 1, 28)]
