import pytest
from unittest.mock import patch, MagicMock
from src.main import run


MOCK_WEATHER = {
    "weather_label": "小雨", "temperature": 18.0, "feels_like": 16.0,
    "humidity": 75, "wind_speed": 3.0, "precipitation": 1.0,
    "season": "春", "date": "2026-05-14",
}
MOCK_PROMPT = {
    "suno_prompt": "soft piano rain",
    "title_ja": "春雨の東京",
    "title_en": "Spring Rain in Tokyo",
    "description": "説明文",
}


def test_run_happy_path():
    with patch("src.main.get_weather", return_value=MOCK_WEATHER) as mw, \
         patch("src.main.generate_prompt", return_value=MOCK_PROMPT) as mp, \
         patch("src.main.generate_music", return_value="/tmp/out.mp3") as ms, \
         patch("src.main.create_thumbnail", return_value="/tmp/thumb.png") as mt, \
         patch("src.main.upload_to_youtube", return_value="VIDEO123") as my:
        run()

    mw.assert_called_once()
    mp.assert_called_once_with(MOCK_WEATHER)
    ms.assert_called_once_with(MOCK_PROMPT["suno_prompt"])
    mt.assert_called_once()
    my.assert_called_once()


def test_run_skips_on_suno_failure():
    with patch("src.main.get_weather", return_value=MOCK_WEATHER), \
         patch("src.main.generate_prompt", return_value=MOCK_PROMPT), \
         patch("src.main.generate_music", side_effect=RuntimeError("suno fail")), \
         patch("src.main.create_thumbnail") as mt, \
         patch("src.main.upload_to_youtube") as my:
        run()  # should not raise

    mt.assert_not_called()
    my.assert_not_called()


def test_run_continues_with_default_thumbnail_on_thumbnail_failure():
    with patch("src.main.get_weather", return_value=MOCK_WEATHER), \
         patch("src.main.generate_prompt", return_value=MOCK_PROMPT), \
         patch("src.main.generate_music", return_value="/tmp/out.mp3"), \
         patch("src.main.create_thumbnail", return_value="assets/default_thumbnail.png"), \
         patch("src.main.upload_to_youtube", return_value="VIDEO123") as my:
        run()

    my.assert_called_once()
