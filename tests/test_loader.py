from calendarium import load_bundled, load_file, bundled_data_path
from calendarium.loader import _strip_json_comments, loads


def test_strip_comments():
    text = """
    // leading comment
    {
      "Country": "X", /* block */
      "Url": "https://example.org/a//b",  // not a comment inside the string
      "Periods": [],
    }
    """
    configuration = loads(text)
    assert configuration.country == "X"
    assert configuration.url == "https://example.org/a//b"


def test_strip_trailing_commas():
    cleaned = _strip_json_comments('{"a": [1, 2,], "b": {"c": 1,},}')
    import json

    assert json.loads(cleaned) == {"a": [1, 2], "b": {"c": 1}}


def test_load_bundled_checked():
    configurations = load_bundled()
    countries = {c.country for c in configurations}
    assert "France" in countries
    assert "Germany" in countries
    assert "Saudi_Arabia" in countries
    assert len(configurations) >= 28


def test_load_bundled_with_not_checked():
    configurations = load_bundled(include_not_checked=True)
    countries = [c.country for c in configurations]
    assert len(countries) == len(set(countries)), "no duplicated country"
    assert len(configurations) > 100


def test_load_file_france():
    configuration = load_file(bundled_data_path() / "date_France.json")
    assert configuration.country == "France"
    assert configuration.culture == "fr-FR"
    assert len(configuration.periods) == 14
    assert [r.key for r in configuration.regions] == ["67", "68"]
    assert configuration.regions[1].from_region == "67"
