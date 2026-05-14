import pytest
from pathlib import Path
from src.thumbnail import create_thumbnail, _get_palette


def test_get_palette_spring_rain():
    bg, text = _get_palette("春", "小雨")
    assert isinstance(bg, tuple) and len(bg) == 3
    assert isinstance(text, tuple) and len(text) == 3


def test_get_palette_returns_tuple_for_all_combos():
    seasons = ["春", "夏", "秋", "冬"]
    weathers = ["快晴", "曇り", "小雨", "雪", "雷雨"]
    for s in seasons:
        for w in weathers:
            bg, text = _get_palette(s, w)
            assert len(bg) == 3
            assert len(text) == 3


def test_create_thumbnail_creates_file(tmp_path):
    output = str(tmp_path / "thumb.png")
    result = create_thumbnail(
        title_ja="春雨の東京",
        title_en="Spring Rain in Tokyo",
        date="2026-05-14",
        season="春",
        weather_label="小雨",
        output_path=output,
    )
    assert result == output
    assert Path(output).exists()
    assert Path(output).stat().st_size > 0


def test_create_thumbnail_falls_back_to_default(tmp_path):
    output = str(tmp_path / "thumb.png")
    default = str(tmp_path / "default.png")
    from PIL import Image
    Image.new("RGB", (1280, 720), (100, 100, 100)).save(default)

    with __import__("unittest.mock", fromlist=["patch"]).patch(
        "src.thumbnail.ImageDraw.Draw", side_effect=Exception("draw error")
    ):
        result = create_thumbnail(
            title_ja="test", title_en="test", date="2026-05-14",
            season="春", weather_label="晴れ",
            output_path=output, default_path=default,
        )
    assert result == default
