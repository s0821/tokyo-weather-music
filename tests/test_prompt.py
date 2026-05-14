import json
import pytest
from unittest.mock import patch, MagicMock
from src.prompt import generate_prompt, _fallback_prompt


def _make_weather():
    return {
        "weather_label": "小雨",
        "temperature": 18.2,
        "feels_like": 16.5,
        "humidity": 78,
        "wind_speed": 3.2,
        "precipitation": 1.4,
        "season": "春",
        "date": "2026-05-14",
    }


def test_generate_prompt_returns_required_keys():
    payload = {
        "suno_prompt": "Gentle spring rain piano",
        "title_ja": "春雨の東京",
        "title_en": "Spring Rain in Tokyo",
        "description": "今日の東京は春の小雨。",
    }
    mock_message = MagicMock()
    mock_message.content[0].text = json.dumps(payload)

    with patch("src.prompt.anthropic.Anthropic") as MockClient:
        MockClient.return_value.messages.create.return_value = mock_message
        result = generate_prompt(_make_weather())

    assert "suno_prompt" in result
    assert "title_ja" in result
    assert "title_en" in result
    assert "description" in result


def test_generate_prompt_falls_back_on_api_failure():
    with patch("src.prompt.anthropic.Anthropic") as MockClient:
        MockClient.return_value.messages.create.side_effect = Exception("API error")
        result = generate_prompt(_make_weather())

    assert "suno_prompt" in result
    assert "title_ja" in result


def test_fallback_prompt_covers_all_seasons_and_weathers():
    weathers = [
        {"season": "春", "weather_label": "晴れ"},
        {"season": "夏", "weather_label": "大雨"},
        {"season": "秋", "weather_label": "曇り"},
        {"season": "冬", "weather_label": "雪"},
    ]
    for w in weathers:
        result = _fallback_prompt(w)
        assert result["suno_prompt"]
        assert result["title_ja"]
