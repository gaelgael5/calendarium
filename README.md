# Calendarium

Referential of computed dates: public holidays and observances, driven by one
JSON configuration file per country whose date rules are written in a small
DSL.

Python port of [Black-Beard-Sdk/Calendarium](https://github.com/Black-Beard-Sdk/Calendarium)
(C#). The JSON configuration format is **unchanged**: the per-country files of
the original project are reused as-is and shipped with the package. The ANTLR
grammar of the original has been replaced by a small hand-written parser
(no code generation, no runtime dependency — the package only uses the
standard library).

## Installation

```bash
pip install .
```

Development install with tests:

```bash
pip install -e .[dev]
pytest
```

## Use by code

```python
from datetime import date
from calendarium import Calendarium

# engine over the referential shipped with the package
cal = Calendarium.bundled()

# all dates of a year for a country
dates = cal.get_dates(2024, "France")
for d, identified in dates.items():
    for event in identified.events:
        print(d, event.name, event.observed, event.free)

# a specific region (region rules include the country-level ones)
cal.get_dates(2024, "France", region="67")

# every region of the country merged
cal.get_all_dates(2024, "France")

# one date
cal.get_date(date(2024, 7, 14), "France")
cal.is_free(date(2024, 7, 14), "France")      # True

# a sliding window
cal.get_next_dates(date(2024, 12, 1), "France", count_days=60)

# index by observed date instead of actual date
cal.get_dates(2024, "France", key="observed")
```

Custom configuration folders are supported:

```python
cal = Calendarium.from_directory("path/to/countries")
```

## Command line

```bash
# list the available country configurations
calendarium countries

# compute the dates of a year (table output)
calendarium compute 2024 France

# CSV output, same format as the original C# console
calendarium compute 2024 France --csv output.csv

# several years, one region only
calendarium compute 2024 France --years 2 --region 67

# festivities of one date
calendarium show 2024-07-14 France

# list the computed-date functions usable as [NAME] in rules
calendarium functions
```

Add `--all` to also load the unverified configurations (see
[Data tiers](#data-tiers)), or `--data DIR` to load your own folder.

## Configuration format

One JSON file per country, named `date_<Country>.json` (`//` comments and
trailing commas are tolerated, as with the original Json.NET loader):

```json
{
  "Country": "Poland",
  "Culture": "pl",
  "Calendar": "Gregorian",
  "Regions": [ { "Key": "", "Periods": [], "From": null } ],
  "Periods": [
    {
      "Name": "Fat Thursday",
      "RuleDate": "([EASTER]) - 51",
      "RuleObserved": null,
      "RuleDuration": null,
      "Free": false,
      "Translations": [ { "Language": "French", "Name": "Mardi gras" } ],
      "Tags": [],
      "YearStart": 2014
    }
  ]
}
```

* **Country** – key used to query the engine.
* **Calendar** – default calendar of the file; can be overridden per period.
* **Regions** – sub-country rule sets. A region inherits every country-level
  period, plus its own; `From` additionally copies the periods of another
  region of the same country (France: region `68` copies region `67`).
* **Periods** – the date rules:
  * **Name** – English name (by convention);
  * **RuleDate** – rule computing the date (see below);
  * **RuleObserved** – rule computing the *observed* date when it differs
    from the actual date (e.g. a holiday falling on a weekend);
  * **RuleDuration** – rule computing the end date of a multi-day festivity;
  * **Free** – whether the day is non-worked;
  * **YearStart** / **YearEnd** – inclusive year bounds of the festivity
    (`YearFrom` is accepted as an alias of `YearStart`);
  * **Translations**, **Tags**, **Culture** – metadata carried to the events.
* **Defaults** – comma-separated names of shared `date_<Name>.Default.json`
  configurations whose periods are imported (tagged with the default's name).

## Rules

A `RuleDate` is evaluated for a calendar year and produces one or more dates:

| Rule | Meaning |
|---|---|
| `"12-25"` | month 12, day 25, in the period's calendar |
| `"[EASTER]"` | a named computed date (see below) |
| `"([EASTER]) + 39"` | 39 days after Easter Sunday (Ascension) |
| `"([EASTER]) - 2"` | 2 days before Easter Sunday (Good Friday) |
| `"((11-23) - 1) << WEDNESDAY"` | first Wednesday on or before 22 November |
| `"(1-1) >> MONDAY"` | first Monday on or after 1 January |
| `"*MONDAY"` | every Monday of the year |

`>>` / `<<` move forward / backward to the given weekday and **stay in
place** when the date already falls on it.

A `RuleObserved` transforms a single date, usually behind a weekday
condition:

| Rule | Meaning |
|---|---|
| `"? (SATURDAY \| SUNDAY) : >> MONDAY"` | moved to next Monday when on a weekend |
| `"? SUNDAY : >> MONDAY"` | moved to next Monday when on a Sunday |
| `"? (FRIDAY \| SATURDAY) : >> SUNDAY"` | for Friday–Saturday weekends |

### Named computed dates

Available in any rule as `[NAME]`:

| Function | Computes |
|---|---|
| `[EASTER]` | Western Easter Sunday (Meeus/Jones/Butcher) |
| `[ORTHODOX_EASTER]` | Orthodox Easter Sunday (Julian computus, Gregorian date) |
| `[PASSOVER]` | Pesach I — 15 Nisan |
| `[ROSH_HASHANAH]` | 1 Tishri |
| `[YOM_KIPPUR]` | 10 Tishri |
| `[HANUKKAH]` | first day — 25 Kislev |

The registry is extensible:

```python
from calendarium import register_function
register_function("MIDSUMMER", lambda year: [date(year, 6, 24)])
```

## Calendars

Rules can be expressed in a non-Gregorian calendar (`"Calendar"` at file or
period level); results are always returned as Gregorian dates. Supported:

* `Gregorian` (and `Default`), `Julian`;
* `Hebrew` — arithmetic Hebrew calendar (months numbered 1 = Nisan,
  7 = Tishri, 13 = Adar II in leap years);
* `Hijri` and `UmAlQura` — tabular (civil) Islamic calendar, the same
  arithmetic family as .NET's `HijriCalendar`. For `UmAlQura` this
  approximates the Saudi lookup-table calendar: observed dates may differ by
  one day;
* `Persian` — arithmetic Jalaali calendar;
* `ThaiBuddhist`, `Taiwan`, `Korean` — Gregorian with a year offset.

For a non-Gregorian period, the engine evaluates the rule for **every**
calendar year overlapping the requested Gregorian year and clips the results
to that year, so festivities near both ends of the Gregorian year are
produced exactly once.

## Observed day vs. public holiday

Each computed event carries both dates:

* `event.date` — the actual (legal) date of the festivity;
* `event.observed` — the date it is observed (`RuleObserved`), equal to
  `event.date` when no rule applies;
* `event.free` — whether the festivity grants a non-working day;
* `event.is_shifted` — `True` when the two differ.

**Rule: the non-working day of a free festivity is its observed date.**
When nothing shifts the observance, observed and actual dates are the same
day and the distinction is invisible. When a `RuleObserved` shifts it (a
holiday falling on a weekend observed the following Monday), the actual date
keeps the identity of the festivity — name, translations, tags — but the day
off is the observed date. This matches the referential's documented intent
("the observed date is the free day") and the legal practice of the
countries using such rules.

Concretely:

* `event.is_free_on(d)` — `True` only when `d` is the event's observed date
  and the festivity is free;
* `identified.free` and `Calendarium.is_free(d, country)` follow the same
  rule (a festivity shifted away from `d` does not make `d` free);
* `get_dates(..., key="observed")` / `get_date(..., key="observed")` index
  events by observed day, including observances shifted in from an adjacent
  year (a 31 December holiday observed the following Monday appears in
  January of the next year);
* weekends themselves are not modelled: `is_free` only reflects
  festivity-driven days off.

## Data tiers

* `data/countries/` — verified configurations (France, Germany, Italy,
  Saudi Arabia, …);
* `data/countries/not_checked/` — configurations imported from the original
  project but not yet verified. Load them with
  `Calendarium.bundled(include_not_checked=True)` or the CLI flag `--all`.

## Differences from the C# version

* The ANTLR lexer/parser is replaced by a hand-written recursive-descent
  parser (`calendarium.rules`); the accepted language is unchanged.
* `YearStart` / `YearEnd` are inclusive, as documented in the original
  README (the C# engine skipped the boundary years).
* Non-Gregorian rules are evaluated over every calendar year overlapping the
  requested Gregorian year (the C# engine evaluated a single one, missing
  end-of-year festivities).
* New named dates: `[PASSOVER]`, `[ROSH_HASHANAH]`, `[YOM_KIPPUR]`,
  `[HANUKKAH]`; the registry is user-extensible.
* The NuGet distribution commands of the console are gone: the referential
  ships with the package.

## License

MIT — see [LICENSE](LICENSE).
