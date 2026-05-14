from PIL import Image, ImageDraw, ImageFont
import os

WIDTH, HEIGHT = 1280, 720
DEFAULT_THUMBNAIL = os.path.join(os.path.dirname(__file__), "../assets/default_thumbnail.png")

PALETTES = {
    ("春", "rain"): ((200, 220, 240), (50, 50, 80)),
    ("春", "clear"): ((255, 230, 240), (80, 50, 70)),
    ("春", "cloud"): ((220, 220, 230), (60, 60, 80)),
    ("夏", "clear"): ((255, 240, 180), (180, 100, 20)),
    ("夏", "rain"): ((180, 210, 230), (30, 60, 100)),
    ("夏", "cloud"): ((200, 210, 220), (50, 70, 90)),
    ("秋", "clear"): ((255, 220, 180), (140, 80, 30)),
    ("秋", "cloud"): ((210, 190, 170), (90, 60, 40)),
    ("秋", "rain"): ((180, 170, 160), (70, 60, 50)),
    ("冬", "snow"): ((230, 240, 255), (80, 100, 140)),
    ("冬", "clear"): ((210, 230, 255), (60, 80, 120)),
    ("冬", "cloud"): ((200, 210, 220), (70, 80, 100)),
}
DEFAULT_PALETTE = ((200, 200, 210), (60, 60, 80))


def _get_palette(season, weather_label):
    label = weather_label.lower()
    for (s, w_key), colors in PALETTES.items():
        if s == season and w_key in label:
            return colors
    for (s, _), colors in PALETTES.items():
        if s == season:
            return colors
    return DEFAULT_PALETTE


def create_thumbnail(
    title_ja,
    title_en,
    date,
    season,
    weather_label,
    output_path="/tmp/thumbnail.png",
    default_path=DEFAULT_THUMBNAIL,
):
    try:
        bg_color, text_color = _get_palette(season, weather_label)
        img = Image.new("RGB", (WIDTH, HEIGHT), bg_color)
        draw = ImageDraw.Draw(img)

        try:
            font_large = ImageFont.truetype("/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc", 64)
            font_medium = ImageFont.truetype("/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc", 36)
            font_small = ImageFont.truetype("/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc", 28)
        except (IOError, OSError):
            font_large = ImageFont.load_default()
            font_medium = font_large
            font_small = font_large

        draw.text((WIDTH // 2, HEIGHT // 2 - 80), title_ja, fill=text_color, font=font_large, anchor="mm")
        draw.text((WIDTH // 2, HEIGHT // 2), title_en, fill=text_color, font=font_medium, anchor="mm")
        draw.text((WIDTH // 2, HEIGHT // 2 + 80), "Tokyo Weather Music  {}".format(date), fill=text_color, font=font_small, anchor="mm")

        img.save(output_path)
        return output_path
    except Exception as e:
        print("[thumbnail] サムネイル生成失敗、デフォルト使用: {}".format(e))
        return default_path
