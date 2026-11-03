from datetime import date

from calendarium import easter_date, orthodox_easter_date


def test_gregorian_easter_anchors():
    assert easter_date(2019) == date(2019, 4, 21)
    assert easter_date(2020) == date(2020, 4, 12)
    assert easter_date(2021) == date(2021, 4, 4)
    assert easter_date(2022) == date(2022, 4, 17)
    assert easter_date(2024) == date(2024, 3, 31)
    assert easter_date(2025) == date(2025, 4, 20)
    assert easter_date(2038) == date(2038, 4, 25)  # latest possible Easter


def test_orthodox_easter_anchors():
    # Gregorian calendar dates of the orthodox Easter
    assert orthodox_easter_date(2019) == date(2019, 4, 28)
    assert orthodox_easter_date(2020) == date(2020, 4, 19)
    assert orthodox_easter_date(2021) == date(2021, 5, 2)
    assert orthodox_easter_date(2024) == date(2024, 5, 5)
    assert orthodox_easter_date(2025) == date(2025, 4, 20)  # same day as western


def test_easter_is_always_a_sunday():
    for year in range(1990, 2050):
        assert easter_date(year).weekday() == 6
        assert orthodox_easter_date(year).weekday() == 6
