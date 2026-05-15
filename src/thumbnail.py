import os
import io
import requests
import time
from PIL import Image, ImageDraw, ImageFont, ImageFilter

WIDTH, HEIGHT = 1280, 720
DEFAULT_THUMBNAIL = os.path.join(os.path.dirname(__file__), "../assets/default_thumbnail.png")

REPLICATE_API = "https://api.replicate.com/v1"
FLUX_VERSION = "black-forest-labs/flux-schnell"

SCENE_TEMPLATES = {
    ("春", "rain"): "rainy spring day in Tokyo, wet streets reflecting cherry blossom petals, soft rain, Shinjuku",
    ("春", "clear"): "sunny spring morning in Tokyo, cherry blossoms in full bloom, Meguro River, warm golden light",
    ("春", "cloud"): "overcast spring afternoon in Tokyo, cherry blossom trees along Chidorigafuchi, misty atmosphere",
    ("夏", "clear"): "bright summer morning in Tokyo, blue sky, Shibuya crossing, vibrant city life, intense sunlight",
    ("夏", "rain"): "summer rain in Tokyo, people with umbrellas, neon reflections on wet pavement, Shinjuku at dusk",
    ("夏", "cloud"): "cloudy summer afternoon in Tokyo, humid air, Sumida River, overcast sky, lush green trees",
    ("秋", "clear"): "crisp autumn day in Tokyo, golden and red maple leaves, Shinjuku Gyoen, clear blue sky",
    ("秋", "cloud"): "grey autumn afternoon in Tokyo, fallen leaves on the ground, quiet residential street, moody light",
    ("秋", "rain"): "autumn rain in Tokyo, wet maple leaves, ginkgo trees turning yellow, misty Hamarikyu Gardens",
    ("冬", "snow"): "snowy winter morning in Tokyo, Mount Fuji visible in the distance, snow-covered rooftops, silence",
    ("冬", "clear"): "clear winter morning in Tokyo, crisp cold air, frost, Senso-ji temple, Mount Fuji on the horizon",
    ("冬", "cloud"): "grey winter afternoon in Tokyo, bare trees, Ueno Park, cold and quiet atmosphere",
}
DEFAULT_SCENE = "peaceful Tokyo cityscape, golden hour light, urban landscape, cinematic"


def _build_image_prompt(season, weather_label, title_ja):
    label = weather_label.lower()
    scene = None
    for (s, w_key), template in SCENE_TEMPLATES.items():
        if s == season and w_key in label:
            scene = template
            break
    if not scene:
        for (s, _), template in SCENE_TEMPLATES.items():
            if s == season:
                scene = template
                break
    if not scene:
        scene = DEFAULT_SCENE

    return (
        "photorealistic, professional photography, {}, "
        "high resolution, 4k, cinematic composition, beautiful lighting, "
        "no text, no watermark, no people focus"
    ).format(scene)


def _generate_image_replicate(prompt, output_path):
    token = os.environ.get("REPLICATE_API_TOKEN", "")
    if not token:
        return None

    resp = requests.post(
        "{}/models/{}/predictions".format(REPLICATE_API, FLUX_VERSION),
        headers={
            "Authorization": "Token {}".format(token),
            "Content-Type": "application/json",
        },
        json={
            "input": {
                "prompt": prompt,
                "width": 1280,
                "height": 720,
                "num_outputs": 1,
                "output_format": "png",
                "output_quality": 90,
            }
        },
        timeout=30,
    )
    resp.raise_for_status()
    prediction_id = resp.json()["id"]

    for _ in range(40):
        time.sleep(5)
        poll = requests.get(
            "{}/predictions/{}".format(REPLICATE_API, prediction_id),
            headers={"Authorization": "Token {}".format(token)},
            timeout=15,
        )
        poll.raise_for_status()
        data = poll.json()
        status = data.get("status")
        if status == "succeeded":
            output = data.get("output", [])
            url = output[0] if isinstance(output, list) else output
            img_data = requests.get(url, timeout=60).content
            img = Image.open(io.BytesIO(img_data)).convert("RGB")
            img = img.resize((WIDTH, HEIGHT), Image.LANCZOS)
            img.save(output_path, "PNG")
            return output_path
        if status in ("failed", "canceled"):
            return None

    return None


def _overlay_text(image_path, title_ja, title_en, date):
    img = Image.open(image_path).convert("RGBA")

    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.rectangle([(0, HEIGHT - 220), (WIDTH, HEIGHT)], fill=(0, 0, 0, 160))
    img = Image.alpha_composite(img, overlay).convert("RGB")
    draw = ImageDraw.Draw(img)

    try:
        font_paths = [
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
            "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc",
        ]
        font_large = None
        for fp in font_paths:
            if os.path.exists(fp):
                font_large = ImageFont.truetype(fp, 56)
                font_medium = ImageFont.truetype(fp, 32)
                font_small = ImageFont.truetype(fp, 24)
                break
        if font_large is None:
            font_large = ImageFont.load_default()
            font_medium = font_large
            font_small = font_large
    except Exception:
        font_large = ImageFont.load_default()
        font_medium = font_large
        font_small = font_large

    draw.text((WIDTH // 2, HEIGHT - 165), title_ja, fill=(255, 255, 255), font=font_large, anchor="mm")
    draw.text((WIDTH // 2, HEIGHT - 100), title_en, fill=(220, 220, 220), font=font_medium, anchor="mm")
    draw.text((WIDTH // 2, HEIGHT - 55), "Tokyo Weather Music  {}".format(date), fill=(180, 180, 180), font=font_small, anchor="mm")

    img.save(image_path, "PNG")
    return image_path


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
        prompt = _build_image_prompt(season, weather_label, title_ja)
        print("[thumbnail] 画像生成プロンプト: {}".format(prompt[:80]))

        result = _generate_image_replicate(prompt, output_path)
        if result:
            _overlay_text(output_path, title_ja, title_en, date)
            print("[thumbnail] リアルサムネイル生成完了: {}".format(output_path))
            return output_path

    except Exception as e:
        print("[thumbnail] FLUX生成失敗、フォールバック: {}".format(e))

    try:
        from PIL import Image, ImageDraw, ImageFont
        PALETTES = {
            "春": (255, 220, 230),
            "夏": (220, 240, 255),
            "秋": (255, 230, 200),
            "冬": (220, 230, 250),
        }
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
