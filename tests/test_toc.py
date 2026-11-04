from pathlib import Path

import pytest

from calendarium import Calendarium, Toc, load_bundled
from calendarium.loader import bundled_data_path

TOC_PATH = bundled_data_path() / "toc.txt"


def test_bundled_toc_parses():
    toc = Toc.load(TOC_PATH)
    assert "France" in toc.countries()
    assert len(toc.countries()) >= 100


def test_bundled_toc_is_in_sync_with_the_data_directory():
    """toc.txt must list exactly the verified configurations."""
    toc = Toc.load(TOC_PATH)
    configurations = {c.country: c for c in load_bundled()}
    assert sorted(toc.countries()) == sorted(configurations)
    for entry in toc.entries:
        configuration = configurations[entry.country]
        assert entry.culture == (configuration.culture or ""), entry.country
        assert Path(entry.uri).name == Path(configuration.source_file).name


def test_full_toc_matches_relative_toc():
    """toc.full.txt lists the same countries with absolute GitHub URLs."""
    relative = Toc.load(TOC_PATH)
    full = Toc.load(bundled_data_path() / "toc.full.txt")
    assert full.countries() == relative.countries()
    for entry, rel_entry in zip(full.entries, relative.entries):
        assert entry.culture == rel_entry.culture
        assert entry.uri.startswith(
            "https://raw.githubusercontent.com/gaelgael5/calendarium/main/"
        )
        assert entry.uri.endswith(Path(rel_entry.uri).name)


def test_relative_uris_resolve_against_the_toc():
    toc = Toc.load(TOC_PATH)
    entry = toc.find("France")
    assert Path(entry.uri).is_file()
    assert Path(entry.uri).parent == Path(str(TOC_PATH)).parent.resolve()


def test_file_uri():
    toc = Toc.load(Path(TOC_PATH).resolve().as_uri())
    assert "Germany" in toc.countries()
    configuration = toc.load_country("Germany")
    assert configuration.country == "Germany"


def test_find_by_country_or_culture():
    toc = Toc.load(TOC_PATH)
    assert toc.find("france").country == "France"
    assert toc.find("fr-FR").country == "France"
    assert toc.find("FR-fr").country == "France"
    assert toc.find("Atlantis") is None


def test_load_country_unknown():
    toc = Toc.load(TOC_PATH)
    with pytest.raises(KeyError):
        toc.load_country("Atlantis")


def test_parse_errors_and_comments():
    toc = Toc.parse("# comment\n\nX;xx;date_X.json\n", Path("/tmp/toc.txt"))
    assert toc.countries() == ["X"]
    with pytest.raises(ValueError):
        Toc.parse("not-a-toc-line\n", Path("/tmp/toc.txt"))


def test_absolute_uris_kept():
    toc = Toc.parse("X;xx;https://example.org/date_X.json\n", Path("/tmp/toc.txt"))
    assert toc.entries[0].uri == "https://example.org/date_X.json"
    toc2 = Toc.parse("X;xx;sub/date_X.json\n", "https://example.org/data/toc.txt")
    assert toc2.entries[0].uri == "https://example.org/data/sub/date_X.json"


def test_calendarium_from_toc_subset():
    from datetime import date

    cal = Calendarium.from_toc(TOC_PATH, countries=["fr-FR", "Germany"])
    assert sorted(cal.countries()) == ["France", "Germany"]
    assert cal.is_free(date(2025, 7, 14), "France")


def test_add_configuration():
    from datetime import date

    cal = Calendarium.from_toc(TOC_PATH, countries=["France"])
    toc = Toc.load(TOC_PATH)
    cal.add_configuration(toc.load_country("Belgium"))
    assert sorted(cal.countries()) == ["Belgium", "France"]
    assert cal.is_free(date(2025, 7, 21), "Belgium")  # Belgian National Day
    # replacing an existing country drops its caches
    cal.add_configuration(toc.load_country("France"))
    assert cal.is_free(date(2025, 7, 14), "France")
