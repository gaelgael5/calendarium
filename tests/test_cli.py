import csv

from calendarium.cli import main


def test_countries(capsys):
    assert main(["countries"]) == 0
    out = capsys.readouterr().out
    assert "France" in out
    assert "regions=67,68" in out


def test_compute_table(capsys):
    assert main(["compute", "2024", "France"]) == 0
    out = capsys.readouterr().out
    assert "2024-07-14  Bastille Day" in out
    # regional day listed once, tagged with its regions
    assert out.count("Christmas 2nd Day") == 1
    assert "[67,68]" in out


def test_compute_csv(tmp_path, capsys):
    target = tmp_path / "out.csv"
    assert main(["compute", "2020", "France", "--region", "", "--csv", str(target)]) == 0
    with target.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.reader(handle, delimiter=";"))
    assert rows[0] == ["Name", "StartDate", "EndDate", "ObservedDate", "Country", "Culture", "Free", "Calendar"]
    assert len(rows) == 15  # header + 14 dates
    bastille = next(r for r in rows if r[0] == "Bastille Day")
    assert bastille == ["Bastille Day", "14/07/2020 00:00:00", "", "14/07/2020", "France", "fr-FR", "true", "Gregorian"]


def test_show(capsys):
    assert main(["show", "2024-07-14", "France"]) == 0
    assert "Bastille Day" in capsys.readouterr().out
    assert main(["show", "2024-07-15", "France"]) == 1


def test_show_observed_day(tmp_path, capsys):
    (tmp_path / "date_Testland.json").write_text(
        """{
          "Country": "Testland",
          "Culture": "en-US",
          "Periods": [
            {
              "Name": "National Day",
              "RuleDate": "7-4",
              "RuleObserved": "? (SATURDAY | SUNDAY) : >> MONDAY",
              "Free": true
            }
          ]
        }""",
        encoding="utf-8",
    )
    capsys.readouterr()

    # 4 July 2021 (Sunday): festivity present but not the day off
    assert main(["show", "2021-07-04", "Testland", "--data", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "National Day (worked, observed 2021-07-05)" in out

    # 5 July 2021 (Monday): the observed, non-worked day
    assert main(["show", "2021-07-05", "Testland", "--data", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "National Day observed (free, actual date 2021-07-04)" in out


def test_functions(capsys):
    assert main(["functions"]) == 0
    out = capsys.readouterr().out
    assert "[EASTER]" in out
    assert "[PASSOVER]" in out


def test_unknown_country(capsys):
    assert main(["compute", "2024", "Atlantis"]) == 2
    assert "error:" in capsys.readouterr().err
