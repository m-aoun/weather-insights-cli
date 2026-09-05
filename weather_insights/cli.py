"""Click-based command line interface for WeatherInsights."""
from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

import click
import pandas as pd

from .analysis import daily_to_dataframe, summarize_history, comparison_table
from .api import WeatherAPIError, WeatherClient, describe_weather_code
from .viz import plot_comparison, plot_history

OUTPUT_DIR = Path("output")


@click.group()
@click.option("--no-cache", is_flag=True, default=False, help="Bypass the local response cache.")
@click.pass_context
def main(ctx: click.Context, no_cache: bool) -> None:
    """WeatherInsights: fetch, analyze, and visualize weather/climate data.

    Powered by the free, keyless Open-Meteo API — no account or API key needed.
    """
    ctx.ensure_object(dict)
    ctx.obj["client"] = WeatherClient(use_cache=not no_cache)


def _fail(message: str) -> "click.exceptions.Exit":
    click.secho(f"Error: {message}", fg="red", err=True)
    sys.exit(1)


@main.command()
@click.argument("city")
@click.pass_context
def current(ctx: click.Context, city: str) -> None:
    """Show current weather conditions for CITY."""
    client: WeatherClient = ctx.obj["client"]
    try:
        location = client.geocode(city)
        weather = client.current_weather(location)
    except WeatherAPIError as exc:
        _fail(str(exc))
        return

    condition = describe_weather_code(weather.get("weather_code"))
    click.secho(f"Current weather in {location.display_name}", bold=True)
    click.echo(f"  Condition:   {condition}")
    click.echo(f"  Temperature: {weather.get('temperature_2m')} C")
    click.echo(f"  Feels like:  {weather.get('apparent_temperature')} C")
    click.echo(f"  Humidity:    {weather.get('relative_humidity_2m')}%")
    click.echo(f"  Wind speed:  {weather.get('wind_speed_10m')} km/h")


@main.command()
@click.argument("city")
@click.option("--days", default=5, show_default=True, help="Number of forecast days (1-16).")
@click.pass_context
def forecast(ctx: click.Context, city: str, days: int) -> None:
    """Show an N-day forecast for CITY."""
    if not 1 <= days <= 16:
        _fail("--days must be between 1 and 16 (Open-Meteo forecast limit).")
        return

    client: WeatherClient = ctx.obj["client"]
    try:
        location = client.geocode(city)
        daily = client.forecast(location, days)
    except WeatherAPIError as exc:
        _fail(str(exc))
        return

    df = daily_to_dataframe(daily)
    click.secho(f"{days}-day forecast for {location.display_name}", bold=True)
    header = f"{'Date':<12}{'High (C)':<10}{'Low (C)':<10}{'Precip %':<10}Condition"
    click.echo(header)
    click.echo("-" * len(header))
    for ts, row in df.iterrows():
        condition = describe_weather_code(row.get("weather_code"))
        click.echo(
            f"{ts.date().isoformat():<12}"
            f"{row.get('temperature_2m_max'):<10}"
            f"{row.get('temperature_2m_min'):<10}"
            f"{row.get('precipitation_probability_max', 'n/a'):<10}"
            f"{condition}"
        )


@main.command()
@click.argument("city")
@click.option("--days", default=14, show_default=True, help="Number of past days of history to fetch.")
@click.pass_context
def history(ctx: click.Context, city: str, days: int) -> None:
    """Fetch DAYS of history for CITY, save a chart, and print summary stats."""
    if days < 1:
        _fail("--days must be at least 1.")
        return

    client: WeatherClient = ctx.obj["client"]
    end = date.today() - timedelta(days=1)  # archive API lags ~1-2 days behind today
    start = end - timedelta(days=days - 1)

    try:
        location = client.geocode(city)
        daily = client.history(location, start.isoformat(), end.isoformat())
    except WeatherAPIError as exc:
        _fail(str(exc))
        return

    df = daily_to_dataframe(daily)
    try:
        summary = summarize_history(df)
    except ValueError as exc:
        _fail(str(exc))
        return

    safe_name = location.name.lower().replace(" ", "_")
    output_path = OUTPUT_DIR / f"history_{safe_name}_{days}d.png"
    plot_history(df, location.display_name, output_path)

    click.secho(f"History for {location.display_name} ({start} to {end})", bold=True)
    click.echo(f"  Days analyzed:      {summary.days}")
    click.echo(f"  Average temp:       {summary.avg_temp} C")
    click.echo(f"  Min temp:           {summary.min_temp} C")
    click.echo(f"  Max temp:           {summary.max_temp} C")
    click.echo(f"  Total precipitation:{summary.total_precipitation} mm")
    click.secho(f"  Chart saved to:     {output_path}", fg="green")


@main.command()
@click.argument("city1")
@click.argument("city2")
@click.option("--days", default=14, show_default=True, help="Number of past days of history to compare.")
@click.pass_context
def compare(ctx: click.Context, city1: str, city2: str, days: int) -> None:
    """Compare DAYS of history between CITY1 and CITY2."""
    if days < 1:
        _fail("--days must be at least 1.")
        return

    client: WeatherClient = ctx.obj["client"]
    end = date.today() - timedelta(days=1)
    start = end - timedelta(days=days - 1)

    try:
        loc1 = client.geocode(city1)
        loc2 = client.geocode(city2)
        daily1 = client.history(loc1, start.isoformat(), end.isoformat())
        daily2 = client.history(loc2, start.isoformat(), end.isoformat())
    except WeatherAPIError as exc:
        _fail(str(exc))
        return

    df1 = daily_to_dataframe(daily1)
    df2 = daily_to_dataframe(daily2)

    safe1 = loc1.name.lower().replace(" ", "_")
    safe2 = loc2.name.lower().replace(" ", "_")
    output_path = OUTPUT_DIR / f"compare_{safe1}_vs_{safe2}_{days}d.png"
    plot_comparison(df1, df2, loc1.display_name, loc2.display_name, output_path)

    table = comparison_table(df1, df2, loc1.display_name, loc2.display_name)

    click.secho(f"Comparing {loc1.display_name} vs {loc2.display_name} ({start} to {end})", bold=True)
    with pd.option_context("display.float_format", "{:.1f}".format):
        click.echo(table.to_string())
    click.secho(f"Chart saved to: {output_path}", fg="green")


if __name__ == "__main__":
    main()
