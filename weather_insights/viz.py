"""Matplotlib chart generation. Charts are always saved to PNG files (no GUI/display
needed), which is why the Agg backend is forced before pyplot is imported."""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

OUTPUT_DIR = Path("output")


def _ensure_output_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def plot_history(df: pd.DataFrame, city_label: str, output_path: Path) -> Path:
    """Save a temperature-trend line chart (max/min/mean) for one city."""
    _ensure_output_dir(output_path)

    fig, ax = plt.subplots(figsize=(10, 5))
    if "temperature_2m_max" in df.columns:
        ax.plot(df.index, df["temperature_2m_max"], label="Max Temp (C)", color="#d62728")
    if "temperature_2m_min" in df.columns:
        ax.plot(df.index, df["temperature_2m_min"], label="Min Temp (C)", color="#1f77b4")
    if "temperature_2m_mean" in df.columns:
        ax.plot(df.index, df["temperature_2m_mean"], label="Mean Temp (C)", color="#2ca02c", linestyle="--")

    ax.set_title(f"Temperature Trend — {city_label}")
    ax.set_xlabel("Date")
    ax.set_ylabel("Temperature (C)")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    return output_path


def plot_comparison(
    df1: pd.DataFrame, df2: pd.DataFrame, label1: str, label2: str, output_path: Path
) -> Path:
    """Save an overlaid mean-temperature comparison chart for two cities."""
    _ensure_output_dir(output_path)

    def mean_series(df: pd.DataFrame) -> pd.Series:
        if "temperature_2m_mean" in df.columns and df["temperature_2m_mean"].notna().any():
            return df["temperature_2m_mean"]
        return (df["temperature_2m_max"] + df["temperature_2m_min"]) / 2

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(df1.index, mean_series(df1), label=label1, color="#d62728", marker="o", markersize=3)
    ax.plot(df2.index, mean_series(df2), label=label2, color="#1f77b4", marker="o", markersize=3)

    ax.set_title(f"Temperature Comparison — {label1} vs {label2}")
    ax.set_xlabel("Date")
    ax.set_ylabel("Mean Temperature (C)")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    return output_path
