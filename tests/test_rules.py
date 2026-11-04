from datetime import date

import pytest

from calendarium import (
    RuleSyntaxError,
    get_calendar,
    parse_date_rule,
    parse_observed_rule,
    register_function,
    registered_functions,
)


def test_mask():
    assert parse_date_rule("12-25").evaluate(2020) == [date(2020, 12, 25)]
    assert parse_date_rule("04-1").evaluate(2021) == [date(2021, 4, 1)]


def test_easter_functions():
    assert parse_date_rule("[EASTER]").evaluate(2020) == [date(2020, 4, 12)]
    assert parse_date_rule("[ORTHODOX_EASTER]").evaluate(2021) == [date(2021, 5, 2)]


def test_jewish_functions():
    assert parse_date_rule("[PASSOVER]").evaluate(2024) == [date(2024, 4, 23)]
    assert parse_date_rule("[ROSH_HASHANAH]").evaluate(2019) == [date(2019, 9, 30)]
    assert parse_date_rule("[YOM_KIPPUR]").evaluate(2024) == [date(2024, 10, 12)]
    assert parse_date_rule("[HANUKKAH]").evaluate(2024) == [date(2024, 12, 26)]


def test_offsets():
    assert parse_date_rule("([EASTER]) + 39").evaluate(2020) == [date(2020, 5, 21)]
    assert parse_date_rule("([EASTER]) - 2").evaluate(2020) == [date(2020, 4, 10)]
    assert parse_date_rule("[EASTER] + 49").evaluate(2020) == [date(2020, 5, 31)]
    assert parse_date_rule("([EASTER]) - 51").evaluate(2020) == [date(2020, 2, 21)]


def test_weekday_shift():
    # Wednesday before 23 November (German Day of Prayer and Repentance)
    rule = parse_date_rule("((11-23) - 1) << Wednesday")
    assert rule.evaluate(2020) == [date(2020, 11, 18)]
    assert rule.evaluate(2021) == [date(2021, 11, 17)]
    assert rule.evaluate(2022) == [date(2022, 11, 16)]
    # >> / << stay in place when already on the weekday
    assert parse_date_rule("(11-18) << WEDNESDAY").evaluate(2020) == [date(2020, 11, 18)]
    assert parse_date_rule("(11-18) >> WEDNESDAY").evaluate(2020) == [date(2020, 11, 18)]


def test_all_weekdays():
    mondays = parse_date_rule("*MONDAY").evaluate(2020)
    assert len(mondays) == 52
    assert all(d.weekday() == 0 and d.year == 2020 for d in mondays)


def test_mask_in_other_calendar():
    hijri = get_calendar("Hijri")
    assert parse_date_rule("10-1").evaluate(1442, hijri) == [date(2021, 5, 13)]


def test_rules_are_case_insensitive():
    assert parse_date_rule("[easter]").evaluate(2020) == [date(2020, 4, 12)]


def test_observed_weekend_to_monday():
    rule = parse_observed_rule("? (SATURDAY | SUNDAY) : >> MONDAY")
    assert rule.evaluate(date(2021, 1, 2)) == date(2021, 1, 4)  # saturday
    assert rule.evaluate(date(2021, 1, 3)) == date(2021, 1, 4)  # sunday
    assert rule.evaluate(date(2021, 1, 5)) == date(2021, 1, 5)  # tuesday, unchanged


def test_observed_single_day():
    rule = parse_observed_rule("? SUNDAY : >> MONDAY")
    assert rule.evaluate(date(2021, 1, 3)) == date(2021, 1, 4)
    assert rule.evaluate(date(2021, 1, 2)) == date(2021, 1, 2)


def test_observed_friday_saturday_weekend():
    rule = parse_observed_rule("? (THURSDAY | FRIDAY) : >> SATURDAY")
    assert rule.evaluate(date(2021, 1, 1)) == date(2021, 1, 2)


def test_observed_multi_clause_us_style():
    """Asymmetric substitute rule: Saturday -> preceding Friday, Sunday -> Monday."""
    rule = parse_observed_rule("? SATURDAY : << FRIDAY ; ? SUNDAY : >> MONDAY")
    assert rule.evaluate(date(2021, 7, 3)) == date(2021, 7, 2)   # saturday -> friday
    assert rule.evaluate(date(2021, 7, 4)) == date(2021, 7, 5)   # sunday -> monday
    assert rule.evaluate(date(2021, 7, 5)) == date(2021, 7, 5)   # monday unchanged


def test_observed_multi_clause_uk_boxing_day():
    """Substitute day skipping the other holiday's substitute."""
    rule = parse_observed_rule("? SATURDAY : >> MONDAY ; ? SUNDAY : >> TUESDAY")
    # Boxing Day 2020: Saturday -> Monday 28 December
    assert rule.evaluate(date(2020, 12, 26)) == date(2020, 12, 28)
    # Boxing Day 2021: Sunday -> Tuesday 28 December
    assert rule.evaluate(date(2021, 12, 26)) == date(2021, 12, 28)
    # Boxing Day 2022: Monday, unchanged
    assert rule.evaluate(date(2022, 12, 26)) == date(2022, 12, 26)


def test_observed_first_matching_clause_wins():
    rule = parse_observed_rule("? SUNDAY : >> MONDAY ; ? SUNDAY : >> TUESDAY")
    assert rule.evaluate(date(2021, 1, 3)) == date(2021, 1, 4)


def test_japanese_equinoxes():
    assert parse_date_rule("[VERNAL_EQUINOX_JAPAN]").evaluate(2024) == [date(2024, 3, 20)]
    assert parse_date_rule("[VERNAL_EQUINOX_JAPAN]").evaluate(2026) == [date(2026, 3, 20)]
    assert parse_date_rule("[AUTUMNAL_EQUINOX_JAPAN]").evaluate(2024) == [date(2024, 9, 22)]
    assert parse_date_rule("[AUTUMNAL_EQUINOX_JAPAN]").evaluate(2025) == [date(2025, 9, 23)]


def test_matariki_gazetted():
    assert parse_date_rule("[MATARIKI]").evaluate(2024) == [date(2024, 6, 28)]
    assert parse_date_rule("[MATARIKI]").evaluate(2025) == [date(2025, 6, 20)]
    assert parse_date_rule("[MATARIKI]").evaluate(2026) == [date(2026, 7, 10)]
    with pytest.raises(ValueError):
        parse_date_rule("[MATARIKI]").evaluate(2060)


def test_june_solstice_chile():
    # dates tabulated by law 21.357
    expected = {2021: 21, 2022: 21, 2023: 21, 2024: 20, 2025: 20,
                2026: 21, 2027: 21, 2028: 20, 2029: 20, 2030: 21}
    for year, day in expected.items():
        assert parse_date_rule("[JUNE_SOLSTICE_CHILE]").evaluate(year) == [date(year, 6, day)], year


def test_register_function():
    register_function("MIDSUMMER", lambda year: [date(year, 6, 24)])
    assert "MIDSUMMER" in registered_functions()
    assert parse_date_rule("[MIDSUMMER] - 1").evaluate(2024) == [date(2024, 6, 23)]


def test_syntax_errors():
    with pytest.raises(RuleSyntaxError):
        parse_date_rule("[UNKNOWN_FUNCTION]")
    with pytest.raises(RuleSyntaxError):
        parse_date_rule("12-25 extra garbage ~~")
    with pytest.raises(RuleSyntaxError):
        parse_date_rule("((12-25)")
    with pytest.raises(RuleSyntaxError):
        parse_observed_rule("? NOTADAY : >> MONDAY")
