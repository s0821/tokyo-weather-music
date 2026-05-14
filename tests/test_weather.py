import pytest
from unittest.mock import patch, MagicMock
from src.weather import get_weather, detect_season


def test_detect_season_spring():
    assert detect_season(3) == "春"
    assert detect_season(4) == "春"
    assert detect_season(5) == "春"


def test_detect_season_summer():
    assert detect_season(6) == "夏"
    assert detect_season(8) == "夏"


def test_detect_season_autumn():
    assert detect_season(9) == "秋"
    assert detect_season(11) == "秋"


def test_detect_season_winter():
    assert detect_season(12) == "冬"
    assert detect_season(1) == "冬"
    assert detect_season(2) == "冬"


def test_get_weather_returns_expected_keys():
    mock_response = {
        "current": {
            "weathercode": 61,
            "temperature_2m": 18.2,
            "apparent_temperature": 16.5,
            "relativehumidity_2m": 78,
            "windspeed_10m": 3.2,
            "precipitation": 1.4,
        }
    }
    with patch("src.weather.requests.get") as mock_get:
        mock_get.return_value.json.return_value = mock_response
        mock_get.return_value.raise_for_status = MagicMock()
        result = get_weather(date="2026-05-14")

    assert result["weather_label"] == "小雨"
    assert result["temperature"] == 18.2
    assert result["feels_like"] == 16.5
    assert result["humidity"] == 78
    assert result["wind_speed"] == 3.2
    assert result["precipitation"] == 1.4
    assert result["season"] == "春"
    assert result["date"] == "2026-05-14"


def test_get_weather_retries_on_failure():
    with patch("src.weather.requests.get") as mock_get:
        mock_get.side_effect = [Exception("Network error")] * 2 + [
            MagicMock(
                json=lambda: {
                    "current": {
                        "weathercode": 0,
                        "temperature_2m": 20.0,
                        "apparent_temperature": 19.0,
                        "relativehumidity_2m": 60,
                        "windspeed_10m": 2.0,
                        "precipitation": 0.0,
                    }
                },
                raise_for_status=MagicMock(),
            )
        ]
        result = get_weather(date="2026-05-14")
    assert result["weather_label"] == "快晴"
