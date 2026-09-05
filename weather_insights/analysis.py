"""Pandas-based analysis helpers for forecast/history payloads returned by the API.

Kept separate from api.py and cli.py so it can be unit tested with plain
dict/DataFrame fixtures and no network access.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


def daily_to_dataframe(daily: dict) -> pd.DataFrame:
    """Convert an Open-Meteo 'daily' block (dict of parallel lists) into a DataFrame."""
    df = pd.DataFrame(daily)
    if "time" in df.columns:
        df["time"] = pd.to_datetime(df["time"])
        df = df.set_index("time")
    return df


@dataclass
class HistorySummary:
    avg_temp: float
    min_temp: float
    max_temp: float
    total_precipitation: float
    days: int

    def as_dict(self) -> dict:
        return {
            "avg_temp": self.avg_temp,
            "min_temp": self.min_temp,
            "max_temp": self.max_temp,
            "total_precipitation": self.total_precipitation,
            "days": self.days,
        }


def summarize_history(df: pd.DataFrame) -> HistorySummary:
    """Compute avg/min/max temp and total precipitation from a history DataFrame.

    Expects columns temperature_2m_mean (or falls back to max/min average) and
    precipitation_sum, as produced by daily_to_dataframe() on archive data.
    """
    if df.empty:
        raise ValueError("Cannot summarize an empty history DataFrame.")

    if "temperature_2m_mean" in df.columns and df["temperature_2m_mean"].notna().any():
        mean_series = df["temperature_2m_mean"]
    else:
        mean_series = (df["temperature_2m_max"] + df["temperature_2m_min"]) / 2

    avg_temp = float(mean_series.mean())
    min_temp = float(df["temperature_2m_min"].min())
    max_temp = float(df["temperature_2m_max"].max())
    total_precip = float(df.get("precipitation_sum", pd.Series(dtype=float)).sum())

    return HistorySummary(
        avg_temp=round(avg_temp, 1),
        min_temp=round(min_temp, 1),
        max_temp=round(max_temp, 1),
        total_precipitation=round(total_precip, 1),
        days=len(df),
    )


def comparison_table(df1: pd.DataFrame, df2: pd.DataFrame, name1: str, name2: str) -> pd.DataFrame:
    """Build a side-by-side comparison table of summary stats for two locations."""
    s1 = summarize_history(df1)
    s2 = summarize_history(df2)
    table = pd.DataFrame(
        {
            name1: s1.as_dict(),
            name2: s2.as_dict(),
        }
    )
    table.index = ["Avg Temp (C)", "Min Temp (C)", "Max Temp (C)", "Total Precip (mm)", "Days"]
    return table
