from datetime import date

import pytest

from calendarium import Calendarium, CountryConfiguration, Period

# values published in the original project's README for France 2020/2021
FRANCE_2020 = {
    date(2020, 1, 1): "New Year's Day",
    date(2020, 4, 10): "Good Friday",
    date(2020, 4, 12): "Easter Sunday",
    date(2020, 4, 13): "Easter Monday",
    date(2020, 5, 1): "Labor Day",
    date(2020, 5, 8): "Victory Day",
    date(2020, 5, 21): "Ascension",
    date(2020, 5, 31): "Pentecost",
    date(2020, 6, 1): "Pentecost Monday",
    date(2020, 7, 14): "Bastille Day",
    date(2020, 8, 15): "Assumption",
    date(2020, 11, 1): "All Saints' Day",
    date(2020, 11, 11): "Armistice Day 1918",
    date(2020, 12, 25): "Christmas Day",
}

FRANCE_2021 = {
    date(2021, 1, 1): "New Year's Day",
    date(2021, 4, 2): "Good Friday",
    date(2021, 4, 4): "Easter Sunday",
    date(2021, 4, 5): "Easter Monday",
    date(2021, 5, 8): "Victory Day",
    date(2021, 5, 13): "Ascension",
    date(2021, 5, 23): "Pentecost",
    date(2021, 5, 24): "Pentecost Monday",
    date(2021, 7, 14): "Bastille Day",
}


@pytest.fixture(scope="module")
def cal():
    return Calendarium.bundled()


def test_france_2020_matches_original_readme(cal):
    dates = cal.get_dates(2020, "France")
    assert len(dates) == len(FRANCE_2020)
    for d, name in FRANCE_2020.items():
        assert any(e.name == name for e in dates[d].events), (d, name)


def test_france_2021_anchors(cal):
    dates = cal.get_dates(2021, "France")
    for d, name in FRANCE_2021.items():
        assert any(e.name == name for e in dates[d].events), (d, name)


def test_event_fields(cal):
    event = cal.get_dates(2021, "France")[date(2021, 7, 14)].events[0]
    assert event.name == "Bastille Day"
    assert event.free is True
    assert event.culture == "fr-FR"
    assert event.country == "France"
    assert event.region == ""
    assert event.calendar == "Gregorian"
    assert event.observed == event.date
    assert not event.is_shifted


def test_translations(cal):
    dates = cal.get_dates(2021, "France", region="67")
    event = next(e for e in dates[date(2021, 12, 26)].events if e.name == "Christmas 2nd Day")
    assert event.translation("French") == "St étienne"
    assert event.translation("german") is None


def test_region_includes_country_dates(cal):
    national = cal.get_dates(2021, "France")
    region = cal.get_dates(2021, "France", region="67")
    assert set(national) < set(region)
    extra = set(region) - set(national)
    assert extra == {date(2021, 12, 24), date(2021, 12, 26), date(2021, 12, 31)}


def test_region_from_inheritance(cal):
    """Region 68 has no own periods but copies region 67 through `From`."""
    r67 = cal.get_dates(2021, "France", region="67")
    r68 = cal.get_dates(2021, "France", region="68")
    assert set(r67) == set(r68)


def test_get_all_dates_merges_regions(cal):
    merged = cal.get_all_dates(2021, "France")
    assert set(merged) == set(cal.get_dates(2021, "France", region="67"))
    # a national day carries one event per rule set it appears in, deduplicated
    events = merged[date(2021, 12, 26)].events
    assert sorted(e.region for e in events) == ["67", "68"]


def test_get_date(cal):
    identified = cal.get_date(date(2021, 12, 26), "France")
    assert identified is not None
    assert {e.region for e in identified.events} == {"67", "68"}
    assert cal.get_date(date(2021, 12, 26), "France", region="") is None
    assert cal.get_date(date(2021, 3, 2), "France") is None


def test_is_free(cal):
    assert cal.is_free(date(2021, 7, 14), "France")
    assert not cal.is_free(date(2021, 7, 15), "France")
    assert not cal.is_free(date(2021, 12, 26), "France")
    assert cal.is_free(date(2021, 12, 26), "France", region="67")


def test_get_next_dates_across_years(cal):
    window = cal.get_next_dates(date(2020, 12, 1), "France", count_days=60)
    assert date(2020, 12, 25) in window
    assert date(2021, 1, 1) in window
    assert date(2020, 11, 11) not in window
    assert list(window) == sorted(window)


def test_saudi_arabia_islamic_dates_within_gregorian_year(cal):
    """Hijri rules must cover the whole Gregorian year (two hijri years)."""
    dates = cal.get_dates(2021, "Saudi_Arabia")
    assert date(2021, 5, 13) in dates   # Eid al-Fitr (1 Shawwal 1442)
    assert date(2021, 7, 20) in dates   # Eid al-Adha (10 Dhu al-Hijjah 1442)
    assert date(2021, 9, 23) in dates   # National Day (Gregorian period)
    assert all(d.year == 2021 for d in dates)


def test_unknown_country_and_region(cal):
    with pytest.raises(KeyError):
        cal.get_dates(2021, "Atlantis")
    with pytest.raises(KeyError):
        cal.get_dates(2021, "France", region="99")


def _testland() -> Calendarium:
    return Calendarium(
        [
            CountryConfiguration(
                country="Testland",
                culture="en-US",
                periods=[
                    Period(
                        name="National Day",
                        rule_date="7-4",
                        rule_observed="? (SATURDAY | SUNDAY) : >> MONDAY",
                        free=True,
                    ),
                    Period(
                        name="Year End",
                        rule_date="12-31",
                        rule_observed="? (SATURDAY | SUNDAY) : >> MONDAY",
                        free=True,
                    ),
                ],
            )
        ]
    )


def test_observed_keying():
    cal = _testland()

    # 4 July 2021 is a Sunday -> observed Monday 5 July
    by_date = cal.get_dates(2021, "Testland")
    event = next(e for e in by_date[date(2021, 7, 4)].events if e.name == "National Day")
    assert event.observed == date(2021, 7, 5)
    assert event.is_shifted

    by_observed = cal.get_dates(2021, "Testland", key="observed")
    assert date(2021, 7, 5) in by_observed
    assert date(2021, 7, 4) not in by_observed


def test_free_follows_observed_date():
    """Decided rule: the non-working day of a free festivity is its observed date."""
    cal = _testland()

    # 4 July 2021 (Sunday) is observed Monday 5 July
    assert not cal.is_free(date(2021, 7, 4), "Testland")
    assert cal.is_free(date(2021, 7, 5), "Testland")

    # the actual date keeps the festivity but is not a day off
    by_date = cal.get_dates(2021, "Testland")
    assert not by_date[date(2021, 7, 4)].free
    event = next(e for e in by_date[date(2021, 7, 4)].events if e.name == "National Day")
    assert event.free  # the festivity still grants a day off...
    assert not event.is_free_on(date(2021, 7, 4))  # ...but not on its actual date
    assert event.is_free_on(date(2021, 7, 5))

    # the observed index reports the day as free
    by_observed = cal.get_dates(2021, "Testland", key="observed")
    assert by_observed[date(2021, 7, 5)].free

    # 4 July 2022 is a Monday: nothing shifts, both views agree
    assert cal.is_free(date(2022, 7, 4), "Testland")
    assert cal.get_dates(2022, "Testland")[date(2022, 7, 4)].free


def test_free_unshifted_event_unchanged():
    cal = Calendarium.bundled()
    # France has no observed rules: actual date == observed date == free day
    assert cal.is_free(date(2021, 7, 14), "France")
    assert cal.get_dates(2021, "France")[date(2021, 7, 14)].free


def test_observed_shift_across_year_boundary():
    cal = _testland()

    # 31 December 2022 is a Saturday -> observed Monday 2 January 2023
    assert not cal.is_free(date(2022, 12, 31), "Testland")
    assert cal.is_free(date(2023, 1, 2), "Testland")

    by_observed_2023 = cal.get_dates(2023, "Testland", key="observed")
    event = next(e for e in by_observed_2023[date(2023, 1, 2)].events if e.name == "Year End")
    assert event.date == date(2022, 12, 31)

    # the shifted-away observance does not appear in the 2022 observed index
    by_observed_2022 = cal.get_dates(2022, "Testland", key="observed")
    assert date(2022, 12, 31) not in by_observed_2022

    # get_date also resolves the observed day across the boundary
    identified = cal.get_date(date(2023, 1, 2), "Testland", key="observed")
    assert identified is not None and identified.free


def test_year_bounds_inclusive():
    configuration = CountryConfiguration(
        country="Testland",
        periods=[
            Period(name="Recent Day", rule_date="3-1", free=True, year_start=2014, year_end=2020)
        ],
    )
    cal = Calendarium([configuration])
    assert cal.get_dates(2013, "Testland") == {}
    assert date(2014, 3, 1) in cal.get_dates(2014, "Testland")
    assert date(2020, 3, 1) in cal.get_dates(2020, "Testland")
    assert cal.get_dates(2021, "Testland") == {}


def test_all_not_checked_configurations_evaluate():
    cal = Calendarium.bundled(include_not_checked=True)
    assert len(cal.countries()) > 100
    for country in cal.countries():
        cal.get_all_dates(2024, country)  # must not raise
