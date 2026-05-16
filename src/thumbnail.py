import os
import io
import requests
import random
from PIL import Image, ImageDraw, ImageFont

WIDTH, HEIGHT = 1280, 720
DEFAULT_THUMBNAIL = os.path.join(os.path.dirname(__file__), "../assets/default_thumbnail.png")

UNSPLASH_API = "https://api.unsplash.com"

SEARCH_QUERIES = {
    ("春", "rain"): ["Tokyo rain spring cherry blossom", "Japan rainy street spring"],
    ("春", "clear"): ["Tokyo cherry blossom spring", "Meguro River sakura", "Japan spring morning"],
    ("春", "cloud"): ["Tokyo spring cloudy", "Japan cherry blossom overcast"],
    ("夏", "clear"): ["Tokyo summer sunshine", "Shibuya summer blue sky", "Japan summer city"],
    ("夏", "rain"): ["Tokyo summer rain neon", "Japan rainy season street", "Tokyo wet street night"],
    ("夏", "cloud"): ["Tokyo summer cloudy", "Japan humid summer"],
    ("秋", "clear"): ["Tokyo autumn leaves", "Japan fall foliage", "Shinjuku Gyoen autumn"],
    ("秋", "cloud"): ["Tokyo autumn grey", "Japan fall moody"],
    ("秋", "rain"): ["Tokyo autumn rain", "Japan fall rainy street"],
    ("冬", "snow"): ["Tokyo snow", "Japan winter snow temple", "Tokyo snowy street"],
    ("冬", "clear"): ["Tokyo winter clear Mount Fuji", "Japan winter morning frost"],
    ("冬", "cloud"): ["Tokyo winter grey", "Japan winter cold city"],
}
DEFAULT_QUERIES = ["Tokyo cityscape", "Tokyo street", "Japan urban landscape"]


def _get_queries(season, weather_label):
    label = weather_label.lower()
    for (s, w_key), queries in SEARCH_QUERIES.items():
        if s == season and w_key in label:
            return queries
    for (s, _), queries in SEARCH_QUERIES.items():
        if s == season:
            return queries
    return DEFAULT_QUERIES


def _fetch_unsplash_photo(season, weather_label):
    token = os.environ.get("UNSPLASH_ACCESS_KEY", "")
    if not token:
        return None

    queries = _get_queries(season, weather_label)
    random.shuffle(queries)

    for query in queries:
        try:
            resp = requests.get(
                "{}/search/photos".format(UNSPLASH_API),
                headers={"Authorization": "Client-ID {}".format(token)},
                params={
                    "query": query,
                    "orientation": "landscape",
                    "per_page": 20,
                    "content_filter": "high",
                },
                timeout=15,
            )
            resp.raise_for_status()
            results = resp.json().get("results", [])
            if results:
                photo = random.choice(results)
                img_url = photo["urls"]["regular"]
                img_data = requests.get(img_url, timeout=30).content
                img = Image.open(io.BytesIO(img_data)).convert("RGB")
                img = img.resize((WIDTH, HEIGHT), Image.LANCZOS)
                return img
        except Exception as e:
            print("[thumbnail] Unsplash クエリ失敗 '{}': {}".format(query, e))
            continue

    return None


def _overlay_text(img, title_ja, title_en, date):
    img = img.convert("RGBA")
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.rectangle([(0, HEIGHT - 220), (WIDTH, HEIGHT)], fill=(0, 0, 0, 170))
    img = Image.alpha_composite(img, overlay).convert("RGB")
    draw = ImageDraw.Draw(img)

    font_large = font_medium = font_small = None
    font_paths = [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/noto-cjk/NotoSansCJK-Bold.ttc",
    ]
    for fp in font_paths:
        if os.path.exists(fp):
            font_large = ImageFont.truetype(fp, 56)
            font_medium = ImageFont.truetype(fp, 32)
            font_small = ImageFont.truetype(fp, 24)
            break
    if font_large is None:
        font_large = font_medium = font_small = ImageFont.load_default()

    draw.text((WIDTH // 2, HEIGHT - 165), title_ja, fill=(255, 255, 255), font=font_large, anchor="mm")
    draw.text((WIDTH // 2, HEIGHT - 100), title_en, fill=(220, 220, 220), font=font_medium, anchor="mm")
    draw.text((WIDTH // 2, HEIGHT - 55), "Tokyo Weather Music  {}".format(date), fill=(180, 180, 180), font=font_small, anchor="mm")

    return img


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
        img = _fetch_unsplash_photo(season, weather_label)
        if img:
            img = _overlay_text(img, title_ja, title_en, date)
            img.save(output_path, "PNG")
            print("[thumbnail] Unsplashサムネイル生成完了: {}".format(output_path))
            return output_path
    except Exception as e:
        print("[thumbnail] Unsplash失敗、フォールバック: {}".format(e))

    try:
        PALETTES = {"春": (255, 220, 230), "夏": (220, 240, 255), "秋": (255, 230, 200), "冬": (220, 230, 250)}
        bg = PALETTES.get(season, (200, 210, 220))
        img = Image.new("RGB", (WIDTH, HEIGHT), bg)
        draw = ImageDraw.Draw(img)
        font = ImageFont.load_default()
        draw.text((WIDTH // 2, HEIGHT // 2 - 40), title_ja, fill=(50, 50, 80), font=font, anchor="mm")
        draw.text((WIDTH // 2, HEIGHT // 2 + 10), title_en, fill=(50, 50, 80), font=font, anchor="mm")
        draw.text((WIDTH // 2, HEIGHT // 2 + 50), "Tokyo Weather Music  {}".format(date), fill=(80, 80, 100), font=font, anchor="mm")
        img.save(output_path)
        return output_path
    except Exception:
        return default_path
