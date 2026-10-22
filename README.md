# WeatherInsights CLI

A command-line tool that fetches, analyzes, and visualizes weather and
climate data using [Open-Meteo](https://open-meteo.com) — a free weather
API that **requires no API key or account signup**. Clone the repo and it
just works.

Built to demonstrate practical Python skills: HTTP integration, pandas data
wrangling, matplotlib chart generation, a real file-based cache, and a
proper CLI built with `click` — all backed by a real, network-mocked test
suite.

## Why Open-Meteo?

Most weather APIs (OpenWeatherMap, WeatherAPI, etc.) require an account and
an API key, which is friction for anyone trying to just run a project from
GitHub. Open-Meteo's forecast, geocoding, and historical-archive endpoints
are free and keyless, so this tool works immediately for anyone who clones
it — no `.env` file, no signup, no secrets to manage.

## Features

- **`current <city>`** — geocodes a city name and prints current temperature,
  feels-like temperature, humidity, wind speed, and a human-readable
  condition (translated from Open-Meteo's WMO weather codes).
- **`forecast <city> --days N`** — prints an N-day forecast table (high,
  low, precipitation probability, condition) for 1-16 days.
- **`history <city> --days N`** — fetches N days of historical data from
  Open-Meteo's archive API, computes average/min/max temperature and total
  precipitation with pandas, and saves a temperature-trend line chart
  (PNG) to `./output/`.
- **`compare <city1> <city2> --days N`** — fetches history for two cities,
  prints a pandas-computed side-by-side comparison table, and saves an
  overlaid comparison chart (PNG) to `./output/`.
- **Local response cache** — API responses are cached to disk
  (`~/.cache/weather-insights/`, 1 hour TTL) keyed by request URL +
  parameters, so re-running the same command doesn't re-hit the network.
  Pass `--no-cache` on any command to bypass it.
- **Clean error handling** — an unknown city name or a network failure
  prints a one-line error and exits non-zero; it never dumps a stack trace
  at the user.

## Setup

Requires Python 3.11+.

```bash
git clone https://github.com/m-aoun/weather-insights-cli.git
cd weather-insights-cli
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -e .
```

No API key, `.env` file, or account is needed — Open-Meteo is free and
keyless.

## Usage

```bash
weather-insights current London
weather-insights forecast London --days 5
weather-insights history London --days 14
weather-insights compare London Paris --days 14

# bypass the local cache on any command:
weather-insights --no-cache current London
```

### Real example output

Captured directly from running the commands against the live Open-Meteo API:

```
$ weather-insights current London
Current weather in London, United Kingdom
  Condition:   Clear sky
  Temperature: 14.3 C
  Feels like:  12.9 C
  Humidity:    80%
  Wind speed:  12.2 km/h
```

```
$ weather-insights forecast London --days 5
5-day forecast for London, United Kingdom
Date        High (C)  Low (C)   Precip %  Condition
---------------------------------------------------
2026-09-05  21.1      13.6      0.0       Overcast
2026-09-06  24.8      15.9      15.0      Light drizzle
2026-09-07  21.4      18.0      6.0       Overcast
2026-09-08  19.7      15.2      20.0      Light drizzle
2026-09-09  19.4      12.6      3.0       Overcast
```

```
$ weather-insights history London --days 14
History for London, United Kingdom (2026-08-22 to 2026-09-04)
  Days analyzed:      14
  Average temp:       18.8 C
  Min temp:           11.4 C
  Max temp:           26.7 C
  Total precipitation:31.9 mm
  Chart saved to:     output\history_london_14d.png
```

```
$ weather-insights compare London Paris --days 14
Comparing London, United Kingdom vs Paris, France (2026-08-22 to 2026-09-04)
                   London, United Kingdom  Paris, France
Avg Temp (C)                         18.8           20.4
Min Temp (C)                         11.4           12.4
Max Temp (C)                         26.7           29.1
Total Precip (mm)                    31.9           53.1
Days                                 14.0           14.0
Chart saved to: output\compare_london_vs_paris_14d.png
```

Unknown city names fail cleanly instead of crashing:

```
$ weather-insights current Zzznotarealplacexyz
Error: Could not find a city named 'Zzznotarealplacexyz'. Check the spelling and try again.
(exit code 1)
```

## Running tests

The test suite is fully offline — all `requests` calls are mocked with
`unittest.mock`, so `pytest` never touches the network. It covers the
pandas summary-statistics calculations (`analysis.py`), the file-based
cache (`cache.py`, including expiry and corrupted-file handling), and the
API client's error handling and caching behavior (`api.py`).

```bash
pip install -e ".[dev]"
pytest -v
```

```
============================= test session starts =============================
collected 20 items

tests/test_analysis.py::test_daily_to_dataframe_sets_datetime_index PASSED
tests/test_analysis.py::test_summarize_history_computes_expected_stats PASSED
tests/test_analysis.py::test_summarize_history_falls_back_without_mean_column PASSED
tests/test_analysis.py::test_summarize_history_raises_on_empty_dataframe PASSED
tests/test_analysis.py::test_comparison_table_has_both_cities_as_columns PASSED
tests/test_api.py::test_describe_weather_code_known_and_unknown PASSED
tests/test_api.py::test_geocode_success PASSED
tests/test_api.py::test_geocode_unknown_city_raises_clear_error PASSED
tests/test_api.py::test_network_failure_raises_clear_error PASSED
tests/test_api.py::test_non_200_response_raises_clear_error PASSED
tests/test_api.py::test_repeated_call_uses_cache_not_second_network_call PASSED
tests/test_api.py::test_no_cache_client_hits_network_every_time PASSED
tests/test_api.py::test_current_weather_missing_field_raises_clear_error PASSED
tests/test_cache.py::test_cache_miss_returns_none PASSED
tests/test_cache.py::test_cache_set_then_get_returns_same_data PASSED
tests/test_cache.py::test_cache_key_is_sensitive_to_params PASSED
tests/test_cache.py::test_cache_key_is_sensitive_to_url PASSED
tests/test_cache.py::test_expired_entries_are_treated_as_misses PASSED
tests/test_cache.py::test_clear_removes_all_entries PASSED
tests/test_cache.py::test_corrupted_cache_file_is_treated_as_miss PASSED

============================= 20 passed in 0.58s ==============================
```

## Project layout

```
weather_insights/
  api.py         # Open-Meteo HTTP client (geocoding, current, forecast, archive)
  cache.py       # file-based response cache with TTL
  analysis.py    # pandas summary-stat and comparison-table calculations
  viz.py         # matplotlib chart generation (saved as PNG)
  cli.py         # click CLI wiring it all together
tests/
  test_api.py       # mocked-network tests for the API client
  test_analysis.py  # pandas calculation tests
  test_cache.py     # cache behavior tests
```

## Known limitations

- Open-Meteo's historical archive typically lags 1-2 days behind
  real-time, so `history`/`compare` use `yesterday` as the end date rather
  than `today`.
- The geocoding endpoint takes the single top match for a city name; very
  ambiguous names (e.g. a small town sharing a name with a larger one)
  may resolve to the more prominent location.

## License

MIT — see [LICENSE](LICENSE).

## Author

Muhammad Aoun Shabbir — [github.com/m-aoun](https://github.com/m-aoun)
