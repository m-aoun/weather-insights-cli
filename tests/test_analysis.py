"""Unit tests for the pandas-based analysis helpers. No network access."""
import json
from pathlib import Path

import pandas as pd
import pytest

from weather_insights.analysis import (
    comparison_table,
    daily_to_dataframe,
    summarize_history,
)

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def history_daily():
    with open(FIXTURES / "history_daily.json", encoding="utf-8") as fh:
        return json.load(fh)


def test_daily_to_dataframe_sets_datetime_index(history_daily):
    df = daily_to_dataframe(history_daily)
    assert isinstance(df.index, pd.DatetimeIndex)
    assert len(df) == 5
    assert "temperature_2m_max" in df.columns


def test_summarize_history_computes_expected_stats(history_daily):
    df = daily_to_dataframe(history_daily)
    summary = summarize_history(df)

    assert summary.days == 5
    assert summary.min_temp == 12.9
    assert summary.max_temp == 24.5
    assert summary.total_precipitation == 6.0
    # mean of [18.2, 19.0, 16.5, 17.1, 20.3] == 18.22 -> rounded to 18.2
    assert summary.avg_temp == pytest.approx(18.2, abs=0.05)


def test_summarize_history_falls_back_without_mean_column(history_daily):
    data = dict(history_daily)
    data.pop("temperature_2m_mean")
    df = daily_to_dataframe(data)
    summary = summarize_history(df)

    # fallback average of (max+min)/2 per day, then averaged
    expected_avg = sum(
        (mx + mn) / 2
        for mx, mn in zip(data["temperature_2m_max"], data["temperature_2m_min"])
    ) / len(data["temperature_2m_max"])
    assert summary.avg_temp == pytest.approx(round(expected_avg, 1), abs=0.05)


def test_summarize_history_raises_on_empty_dataframe():
    empty_df = pd.DataFrame()
    with pytest.raises(ValueError):
        summarize_history(empty_df)


def test_comparison_table_has_both_cities_as_columns(history_daily):
    df1 = daily_to_dataframe(history_daily)
    # Second city: same shape but shifted values so the two summaries differ.
    shifted = {
        "time": history_daily["time"],
        "temperature_2m_max": [t + 5 for t in history_daily["temperature_2m_max"]],
        "temperature_2m_min": [t + 5 for t in history_daily["temperature_2m_min"]],
        "temperature_2m_mean": [t + 5 for t in history_daily["temperature_2m_mean"]],
        "precipitation_sum": history_daily["precipitation_sum"],
    }
    df2 = daily_to_dataframe(shifted)

    table = comparison_table(df1, df2, "CityA", "CityB")

    assert list(table.columns) == ["CityA", "CityB"]
    assert "Avg Temp (C)" in table.index
    # CityB should be warmer than CityA by ~5 degrees since we shifted it up.
    assert table.loc["Avg Temp (C)", "CityB"] > table.loc["Avg Temp (C)", "CityA"]
