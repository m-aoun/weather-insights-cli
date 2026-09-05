"""Unit tests for WeatherClient using mocked requests calls (no real network access)."""
from unittest.mock import Mock, patch

import pytest
import requests

from weather_insights.api import WeatherAPIError, WeatherClient, describe_weather_code
from weather_insights.cache import Cache


def _mock_response(json_data, status_code=200):
    resp = Mock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.text = str(json_data)
    return resp


@pytest.fixture
def client(tmp_path):
    return WeatherClient(use_cache=True, cache=Cache(cache_dir=tmp_path / "cache"))


def test_describe_weather_code_known_and_unknown():
    assert describe_weather_code(0) == "Clear sky"
    assert describe_weather_code(61) == "Slight rain"
    assert "Unknown" in describe_weather_code(9999)
    assert describe_weather_code(None) == "Unknown"


@patch("weather_insights.api.requests.get")
def test_geocode_success(mock_get, client):
    mock_get.return_value = _mock_response(
        {
            "results": [
                {"name": "London", "country": "United Kingdom", "latitude": 51.5, "longitude": -0.12, "timezone": "Europe/London"}
            ]
        }
    )
    location = client.geocode("London")
    assert location.name == "London"
    assert location.country == "United Kingdom"
    assert location.display_name == "London, United Kingdom"


@patch("weather_insights.api.requests.get")
def test_geocode_unknown_city_raises_clear_error(mock_get, client):
    mock_get.return_value = _mock_response({"results": []})
    with pytest.raises(WeatherAPIError, match="Could not find a city"):
        client.geocode("Zzznotarealplace")


@patch("weather_insights.api.requests.get")
def test_network_failure_raises_clear_error(mock_get, client):
    mock_get.side_effect = requests.exceptions.ConnectionError("boom")
    with pytest.raises(WeatherAPIError, match="Could not reach the weather service"):
        client.geocode("London")


@patch("weather_insights.api.requests.get")
def test_non_200_response_raises_clear_error(mock_get, client):
    mock_get.return_value = _mock_response({"error": True}, status_code=500)
    with pytest.raises(WeatherAPIError, match="HTTP 500"):
        client.geocode("London")


@patch("weather_insights.api.requests.get")
def test_repeated_call_uses_cache_not_second_network_call(mock_get, client):
    mock_get.return_value = _mock_response(
        {
            "results": [
                {"name": "Paris", "country": "France", "latitude": 48.85, "longitude": 2.35, "timezone": "Europe/Paris"}
            ]
        }
    )
    client.geocode("Paris")
    client.geocode("Paris")

    assert mock_get.call_count == 1


@patch("weather_insights.api.requests.get")
def test_no_cache_client_hits_network_every_time(mock_get, tmp_path):
    mock_get.return_value = _mock_response(
        {
            "results": [
                {"name": "Paris", "country": "France", "latitude": 48.85, "longitude": 2.35, "timezone": "Europe/Paris"}
            ]
        }
    )
    no_cache_client = WeatherClient(use_cache=False, cache=Cache(cache_dir=tmp_path / "cache"))
    no_cache_client.geocode("Paris")
    no_cache_client.geocode("Paris")

    assert mock_get.call_count == 2


@patch("weather_insights.api.requests.get")
def test_current_weather_missing_field_raises_clear_error(mock_get, client):
    mock_get.return_value = _mock_response({"not_current": {}})
    with pytest.raises(WeatherAPIError, match="current conditions"):
        from weather_insights.api import Location

        client.current_weather(Location(name="X", country="Y", latitude=0, longitude=0))
