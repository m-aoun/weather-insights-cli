"""Thin client around the free, keyless Open-Meteo APIs.

Open-Meteo (https://open-meteo.com) requires no API key and no account
signup, which is exactly why it was chosen for this project: anyone who
clones this repo can run it immediately.

Endpoints used:
  - Geocoding:  https://geocoding-api.open-meteo.com/v1/search
  - Forecast:   https://api.open-meteo.com/v1/forecast
  - Archive:    https://archive-api.open-meteo.com/v1/archive
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import requests

from .cache import Cache

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

REQUEST_TIMEOUT = 15  # seconds

# WMO weather interpretation codes -> human-readable condition text.
# https://open-meteo.com/en/docs (see "WMO Weather interpretation codes")
WEATHER_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snow fall",
    73: "Moderate snow fall",
    75: "Heavy snow fall",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


def describe_weather_code(code: Optional[int]) -> str:
    """Translate a WMO weather code into a human-readable description."""
    if code is None:
        return "Unknown"
    return WEATHER_CODES.get(int(code), f"Unknown (code {code})")


class WeatherAPIError(Exception):
    """Raised for any user-facing failure: bad city name, network error, etc."""


@dataclass
class Location:
    name: str
    country: str
    latitude: float
    longitude: float
    timezone: str = "auto"

    @property
    def display_name(self) -> str:
        if self.country:
            return f"{self.name}, {self.country}"
        return self.name


class WeatherClient:
    """Fetches geocoding/current/forecast/archive data with an optional cache."""

    def __init__(self, use_cache: bool = True, cache: Optional[Cache] = None):
        self.use_cache = use_cache
        self.cache = cache or Cache()

    # -- low-level HTTP with caching -------------------------------------------------
    def _get(self, url: str, params: dict) -> dict:
        if self.use_cache:
            cached = self.cache.get(url, params)
            if cached is not None:
                return cached

        try:
            response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
        except requests.exceptions.ConnectionError as exc:
            raise WeatherAPIError(
                "Could not reach the weather service. Check your internet connection."
            ) from exc
        except requests.exceptions.Timeout as exc:
            raise WeatherAPIError(
                "The weather service took too long to respond. Please try again."
            ) from exc
        except requests.exceptions.RequestException as exc:
            raise WeatherAPIError(f"Network error while contacting the weather service: {exc}") from exc

        if response.status_code != 200:
            raise WeatherAPIError(
                f"Weather service returned an error (HTTP {response.status_code}): {response.text[:200]}"
            )

        try:
            data = response.json()
        except ValueError as exc:
            raise WeatherAPIError("Weather service returned an unreadable response.") from exc

        if self.use_cache:
            self.cache.set(url, params, data)
        return data

    # -- geocoding ---------------------------------------------------------------
    def geocode(self, city: str) -> Location:
        """Resolve a free-text city name to a Location (lat/lon/timezone)."""
        params = {"name": city, "count": 1, "language": "en", "format": "json"}
        data = self._get(GEOCODING_URL, params)
        results = data.get("results") or []
        if not results:
            raise WeatherAPIError(
                f"Could not find a city named '{city}'. Check the spelling and try again."
            )
        top = results[0]
        return Location(
            name=top.get("name", city),
            country=top.get("country", ""),
            latitude=top["latitude"],
            longitude=top["longitude"],
            timezone=top.get("timezone", "auto"),
        )

    # -- current weather -----------------------------------------------------------
    def current_weather(self, location: Location) -> dict:
        params = {
            "latitude": location.latitude,
            "longitude": location.longitude,
            "current": ",".join(
                [
                    "temperature_2m",
                    "apparent_temperature",
                    "relative_humidity_2m",
                    "wind_speed_10m",
                    "weather_code",
                ]
            ),
            "timezone": location.timezone,
        }
        data = self._get(FORECAST_URL, params)
        current = data.get("current")
        if not current:
            raise WeatherAPIError("Weather service response did not include current conditions.")
        return current

    # -- forecast --------------------------------------------------------------
    def forecast(self, location: Location, days: int) -> dict:
        params = {
            "latitude": location.latitude,
            "longitude": location.longitude,
            "daily": ",".join(
                [
                    "temperature_2m_max",
                    "temperature_2m_min",
                    "precipitation_probability_max",
                    "weather_code",
                ]
            ),
            "forecast_days": days,
            "timezone": location.timezone,
        }
        data = self._get(FORECAST_URL, params)
        daily = data.get("daily")
        if not daily:
            raise WeatherAPIError("Weather service response did not include a forecast.")
        return daily

    # -- history (archive) -------------------------------------------------------
    def history(self, location: Location, start_date: str, end_date: str) -> dict:
        params = {
            "latitude": location.latitude,
            "longitude": location.longitude,
            "start_date": start_date,
            "end_date": end_date,
            "daily": ",".join(
                [
                    "temperature_2m_max",
                    "temperature_2m_min",
                    "temperature_2m_mean",
                    "precipitation_sum",
                ]
            ),
            "timezone": location.timezone,
        }
        data = self._get(ARCHIVE_URL, params)
        daily = data.get("daily")
        if not daily:
            raise WeatherAPIError("Weather service response did not include historical data.")
        return daily
