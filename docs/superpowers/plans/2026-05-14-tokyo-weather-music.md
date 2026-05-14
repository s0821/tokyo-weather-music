# Tokyo Weather Music Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 東京の毎日の天候データをもとにSUNOでインストゥルメンタル音楽を自動生成し、YouTubeとSpotify（ポッドキャスト）へ毎日自動配信するシステムを構築する。

**Architecture:** モジュール分割Pythonパッケージ（weather→prompt→suno→thumbnail→youtube/podcast）をGitHub Actionsが毎朝6:00 JSTに順次実行する。各モジュールは独立してテスト可能な単一責任設計。

**Tech Stack:** Python 3.12, requests, anthropic SDK, Pillow, google-api-python-client, pytest, pytest-mock, GitHub Actions

---

## ファイル構成

```
tokyo-weather-music/
├── .github/workflows/daily.yml
├── src/
│   ├── weather.py          # Open-Meteo APIから東京天気取得
│   ├── prompt.py           # Claude APIでSUNOプロンプト生成
│   ├── suno.py             # SUNO非公式API経由で音楽生成
│   ├── thumbnail.py        # Pillowでサムネイル生成
│   ├── youtube.py          # YouTube Data API v3でアップロード
│   ├── podcast.py          # RSS feed更新・GitHub Pages配信（Phase 2）
│   └── main.py             # オーケストレーター
├── docs/
│   ├── episodes/           # mp3ホスティング用（GitHub Pages）
│   └── feed.xml            # Spotify用RSSフィード
├── assets/
│   └── default_thumbnail.png
├── tests/
│   ├── test_weather.py
│   ├── test_prompt.py
│   ├── test_suno.py
│   ├── test_thumbnail.py
│   ├── test_youtube.py
│   ├── test_podcast.py
│   └── test_main.py
├── .env.example
├── .gitignore
└── requirements.txt
```

---

## Task 1: プロジェクトスキャフォールディング

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `.gitignore`
- Create: `src/__init__.py`
- Create: `tests/__init__.py`
- Create: `docs/episodes/.gitkeep`

- [ ] **Step 1: requirements.txtを作成する**

```
anthropic>=0.40.0
requests>=2.32.0
Pillow>=10.4.0
google-api-python-client>=2.140.0
google-auth-oauthlib>=1.2.0
google-auth-httplib2>=0.2.0
python-dotenv>=1.0.1
pytest>=8.3.0
pytest-mock>=3.14.0
```

- [ ] **Step 2: .env.exampleを作成する**

```
ANTHROPIC_API_KEY=your_anthropic_api_key_here
SUNO_COOKIE=your_suno_session_cookie_here
YOUTUBE_CLIENT_ID=your_youtube_client_id_here
YOUTUBE_CLIENT_SECRET=your_youtube_client_secret_here
YOUTUBE_REFRESH_TOKEN=your_youtube_refresh_token_here
GITHUB_REPOSITORY_OWNER=your_github_username_here
```

- [ ] **Step 3: .gitignoreを作成する**

```
__pycache__/
*.py[cod]
.env
*.mp3
*.png
!assets/default_thumbnail.png
.pytest_cache/
dist/
*.egg-info/
```

- [ ] **Step 4: ディレクトリと空ファイルを作成する**

```bash
mkdir -p src tests docs/episodes assets
touch src/__init__.py tests/__init__.py docs/episodes/.gitkeep
```

- [ ] **Step 5: 依存パッケージをインストールする**

```bash
pip install -r requirements.txt
```

Expected: エラーなくインストール完了

- [ ] **Step 6: コミット**

```bash
git init
git add requirements.txt .env.example .gitignore src/__init__.py tests/__init__.py docs/episodes/.gitkeep
git commit -m "chore: initial project scaffolding"
```

---

## Task 2: weather.py — 東京天気取得

**Files:**
- Create: `src/weather.py`
- Create: `tests/test_weather.py`

- [ ] **Step 1: テストを書く**

`tests/test_weather.py`:
```python
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
```

- [ ] **Step 2: テストが失敗することを確認する**

```bash
pytest tests/test_weather.py -v
```

Expected: `ImportError` または `ModuleNotFoundError`

- [ ] **Step 3: weather.pyを実装する**

`src/weather.py`:
```python
import requests
from datetime import date as date_type

TOKYO_LAT = 35.6895
TOKYO_LON = 139.6917

WMO_LABELS = {
    0: "快晴", 1: "晴れ", 2: "一部曇り", 3: "曇り",
    45: "霧", 48: "着氷霧",
    51: "霧雨（弱）", 53: "霧雨", 55: "霧雨（強）",
    61: "小雨", 63: "雨", 65: "大雨",
    71: "小雪", 73: "雪", 75: "大雪",
    80: "にわか雨（弱）", 81: "にわか雨", 82: "にわか雨（強）",
    95: "雷雨", 96: "雷雨（ひょう）", 99: "雷雨（大ひょう）",
}


def detect_season(month: int) -> str:
    if month in (3, 4, 5):
        return "春"
    if month in (6, 7, 8):
        return "夏"
    if month in (9, 10, 11):
        return "秋"
    return "冬"


def get_weather(date: str | None = None, max_retries: int = 3) -> dict:
    today = date or str(date_type.today())
    month = int(today.split("-")[1])

    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": TOKYO_LAT,
        "longitude": TOKYO_LON,
        "current": [
            "weathercode",
            "temperature_2m",
            "apparent_temperature",
            "relativehumidity_2m",
            "windspeed_10m",
            "precipitation",
        ],
        "timezone": "Asia/Tokyo",
    }

    last_error = None
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, params=params, timeout=10)
            resp.raise_for_status()
            current = resp.json()["current"]
            code = current["weathercode"]
            return {
                "weather_label": WMO_LABELS.get(code, f"天気コード{code}"),
                "temperature": current["temperature_2m"],
                "feels_like": current["apparent_temperature"],
                "humidity": current["relativehumidity_2m"],
                "wind_speed": current["windspeed_10m"],
                "precipitation": current["precipitation"],
                "season": detect_season(month),
                "date": today,
            }
        except Exception as e:
            last_error = e

    raise RuntimeError(f"天気取得失敗（{max_retries}回試行）: {last_error}")
```

- [ ] **Step 4: テストを実行して全パスを確認する**

```bash
pytest tests/test_weather.py -v
```

Expected: 全テストPASS

- [ ] **Step 5: コミット**

```bash
git add src/weather.py tests/test_weather.py
git commit -m "feat: add weather module with Open-Meteo API and season detection"
```

---

## Task 3: prompt.py — Claude APIプロンプト生成

**Files:**
- Create: `src/prompt.py`
- Create: `tests/test_prompt.py`

- [ ] **Step 1: テストを書く**

`tests/test_prompt.py`:
```python
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
```

- [ ] **Step 2: テストが失敗することを確認する**

```bash
pytest tests/test_prompt.py -v
```

Expected: `ImportError`

- [ ] **Step 3: prompt.pyを実装する**

`src/prompt.py`:
```python
import json
import os
import anthropic

SYSTEM_PROMPT = """あなたはプロの音楽プロデューサーです。
東京の今日の天気と季節をもとに、SUNO AIで生成するインストゥルメンタル音楽のプロンプト、
曲タイトル（日本語・英語）、配信用説明文を作成してください。
ジャンルは ambient / lo-fi / Japanese instrumental の範囲で、
天候と季節の情感を豊かに反映させてください。
出力はJSON形式のみ。他のテキストは不要。
必ず以下のキーを含めること: suno_prompt, title_ja, title_en, description"""

FALLBACK_TEMPLATES = {
    ("春", "rain"): {
        "suno_prompt": "Gentle spring rain Tokyo, soft piano with ambient strings, melancholic hopeful, lo-fi instrumental, 85 BPM",
        "title_ja": "春雨の東京",
        "title_en": "Spring Rain in Tokyo",
        "description": "春の雨が静かに降る東京。柔らかなピアノの旋律をお届けします。\n\n#東京 #天気 #春 #ambient",
    },
    ("夏", "clear"): {
        "suno_prompt": "Bright summer morning Tokyo, upbeat acoustic guitar, warm sunshine feeling, lo-fi chill, 95 BPM",
        "title_ja": "夏の朝の東京",
        "title_en": "Summer Morning in Tokyo",
        "description": "眩しい夏の朝。爽やかなギターの音色と共に。\n\n#東京 #天気 #夏 #lofi",
    },
    ("秋", "cloud"): {
        "suno_prompt": "Quiet autumn afternoon Tokyo, contemplative piano, falling leaves feeling, ambient instrumental, 80 BPM",
        "title_ja": "秋の午後の東京",
        "title_en": "Autumn Afternoon in Tokyo",
        "description": "木の葉が揺れる秋の午後。しみじみとしたピアノ曲を。\n\n#東京 #天気 #秋 #ambient",
    },
    ("冬", "snow"): {
        "suno_prompt": "Silent winter snow Tokyo, delicate piano with bells, serene and cold, ambient instrumental, 70 BPM",
        "title_ja": "冬の雪の東京",
        "title_en": "Winter Snow in Tokyo",
        "description": "雪が降り積もる静かな冬の東京。繊細なピアノの響き。\n\n#東京 #天気 #冬 #ambient",
    },
}

DEFAULT_FALLBACK = {
    "suno_prompt": "Tokyo city ambience, peaceful instrumental, piano and strings, lo-fi chill, 85 BPM",
    "title_ja": "今日の東京",
    "title_en": "Tokyo Today",
    "description": "今日の東京の空気感を音楽で。\n\n#東京 #天気 #instrumental",
}


def _fallback_prompt(weather: dict) -> dict:
    season = weather.get("season", "")
    label = weather.get("weather_label", "")
    label_lower = label.lower()

    for (s, w_key), template in FALLBACK_TEMPLATES.items():
        if s == season and w_key in label_lower:
            t = dict(template)
            t["description"] = t["description"] + f"\n気温: {weather.get('temperature', '')}℃"
            return t

    # season only match
    for (s, _), template in FALLBACK_TEMPLATES.items():
        if s == season:
            t = dict(template)
            t["description"] = t["description"] + f"\n気温: {weather.get('temperature', '')}℃"
            return t

    return DEFAULT_FALLBACK


def generate_prompt(weather: dict, max_retries: int = 3) -> dict:
    user_message = (
        f"今日の東京の天気情報:\n"
        f"- 天気: {weather['weather_label']}\n"
        f"- 気温: {weather['temperature']}℃（体感: {weather['feels_like']}℃）\n"
        f"- 湿度: {weather['humidity']}%\n"
        f"- 風速: {weather['wind_speed']}m/s\n"
        f"- 降水量: {weather['precipitation']}mm\n"
        f"- 季節: {weather['season']}\n"
        f"- 日付: {weather['date']}\n"
    )

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    last_error = None
    for _ in range(max_retries):
        try:
            message = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=512,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_message}],
            )
            return json.loads(message.content[0].text)
        except Exception as e:
            last_error = e

    print(f"[prompt] Claude API失敗、フォールバック使用: {last_error}")
    return _fallback_prompt(weather)
```

- [ ] **Step 4: テストを実行して全パスを確認する**

```bash
pytest tests/test_prompt.py -v
```

Expected: 全テストPASS

- [ ] **Step 5: コミット**

```bash
git add src/prompt.py tests/test_prompt.py
git commit -m "feat: add prompt module with Claude API and season/weather fallback templates"
```

---

## Task 4: suno.py — SUNO音楽生成

**Files:**
- Create: `src/suno.py`
- Create: `tests/test_suno.py`

- [ ] **Step 1: テストを書く**

`tests/test_suno.py`:
```python
import pytest
from unittest.mock import patch, MagicMock, call
from src.suno import generate_music, _get_jwt, _poll_until_complete


def test_get_jwt_extracts_token():
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"session": {"sunoToken": "test-jwt-token"}}
    mock_resp.raise_for_status = MagicMock()
    with patch("src.suno.requests.get", return_value=mock_resp):
        token = _get_jwt("test-cookie")
    assert token == "test-jwt-token"


def test_poll_until_complete_returns_on_complete():
    complete_clip = {"status": "complete", "audio_url": "https://cdn.suno.ai/test.mp3"}
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"clips": [complete_clip]}
    mock_resp.raise_for_status = MagicMock()
    with patch("src.suno.requests.get", return_value=mock_resp):
        with patch("src.suno.time.sleep"):
            result = _poll_until_complete("clip-id-123", "jwt-token")
    assert result == "https://cdn.suno.ai/test.mp3"


def test_poll_until_complete_raises_on_timeout():
    pending_clip = {"status": "processing", "audio_url": None}
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"clips": [pending_clip]}
    mock_resp.raise_for_status = MagicMock()
    with patch("src.suno.requests.get", return_value=mock_resp):
        with patch("src.suno.time.sleep"):
            with pytest.raises(RuntimeError, match="タイムアウト"):
                _poll_until_complete("clip-id", "jwt", max_polls=2)


def test_generate_music_downloads_file(tmp_path):
    jwt_mock = "test-jwt"
    gen_resp = MagicMock()
    gen_resp.json.return_value = {"clips": [{"id": "clip-123"}]}
    gen_resp.raise_for_status = MagicMock()

    poll_resp = MagicMock()
    poll_resp.json.return_value = {"clips": [{"status": "complete", "audio_url": "https://cdn.suno.ai/test.mp3"}]}
    poll_resp.raise_for_status = MagicMock()

    audio_bytes = b"fake-mp3-data"
    dl_resp = MagicMock()
    dl_resp.content = audio_bytes
    dl_resp.raise_for_status = MagicMock()

    with patch("src.suno._get_jwt", return_value=jwt_mock):
        with patch("src.suno.requests.post", return_value=gen_resp):
            with patch("src.suno.requests.get") as mock_get:
                mock_get.side_effect = [poll_resp, dl_resp]
                with patch("src.suno.time.sleep"):
                    output = generate_music("soft piano", output_path=str(tmp_path / "out.mp3"))

    assert output == str(tmp_path / "out.mp3")
    assert (tmp_path / "out.mp3").read_bytes() == audio_bytes
```

- [ ] **Step 2: テストが失敗することを確認する**

```bash
pytest tests/test_suno.py -v
```

Expected: `ImportError`

- [ ] **Step 3: suno.pyを実装する**

`src/suno.py`:
```python
import os
import time
import requests

SUNO_BASE = "https://studio-api.suno.ai"
DEFAULT_OUTPUT = "/tmp/suno_output.mp3"


def _get_jwt(cookie: str) -> str:
    resp = requests.get(
        f"{SUNO_BASE}/api/auth/session",
        headers={"Cookie": cookie},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()["session"]["sunoToken"]


def _poll_until_complete(clip_id: str, jwt: str, max_polls: int = 40, interval: int = 30) -> str:
    headers = {"Authorization": f"Bearer {jwt}"}
    for _ in range(max_polls):
        resp = requests.get(
            f"{SUNO_BASE}/api/feed/?ids={clip_id}",
            headers=headers,
            timeout=15,
        )
        resp.raise_for_status()
        clip = resp.json()["clips"][0]
        if clip["status"] == "complete" and clip.get("audio_url"):
            return clip["audio_url"]
        time.sleep(interval)
    raise RuntimeError(f"タイムアウト: clip_id={clip_id} が{max_polls}回のポーリングで完了しなかった")


def generate_music(
    suno_prompt: str,
    output_path: str = DEFAULT_OUTPUT,
    max_retries: int = 3,
) -> str:
    cookie = os.environ["SUNO_COOKIE"]
    last_error = None

    for attempt in range(max_retries):
        try:
            jwt = _get_jwt(cookie)
            headers = {
                "Authorization": f"Bearer {jwt}",
                "Content-Type": "application/json",
            }
            payload = {
                "prompt": suno_prompt,
                "mv": "chirp-v3-5",
                "title": "",
                "tags": "instrumental ambient",
                "make_instrumental": True,
            }
            gen_resp = requests.post(
                f"{SUNO_BASE}/api/generate/v2/",
                json=payload,
                headers=headers,
                timeout=30,
            )
            gen_resp.raise_for_status()
            clip_id = gen_resp.json()["clips"][0]["id"]

            audio_url = _poll_until_complete(clip_id, jwt)

            dl_resp = requests.get(audio_url, timeout=60)
            dl_resp.raise_for_status()
            with open(output_path, "wb") as f:
                f.write(dl_resp.content)
            return output_path

        except Exception as e:
            last_error = e
            print(f"[suno] 試行 {attempt + 1} 失敗: {e}")

    raise RuntimeError(f"SUNO音楽生成失敗（{max_retries}回試行）: {last_error}")
```

- [ ] **Step 4: テストを実行して全パスを確認する**

```bash
pytest tests/test_suno.py -v
```

Expected: 全テストPASS

- [ ] **Step 5: コミット**

```bash
git add src/suno.py tests/test_suno.py
git commit -m "feat: add suno module for music generation via unofficial API"
```

---

## Task 5: thumbnail.py — サムネイル生成

**Files:**
- Create: `src/thumbnail.py`
- Create: `assets/default_thumbnail.png`（プレースホルダー）
- Create: `tests/test_thumbnail.py`

- [ ] **Step 1: テストを書く**

`tests/test_thumbnail.py`:
```python
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
    # デフォルト画像を作成
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
```

- [ ] **Step 2: テストが失敗することを確認する**

```bash
pytest tests/test_thumbnail.py -v
```

Expected: `ImportError`

- [ ] **Step 3: デフォルトサムネイルを生成する**

```python
# 一度だけ実行してassets/default_thumbnail.pngを生成する
from PIL import Image, ImageDraw, ImageFont
img = Image.new("RGB", (1280, 720), (80, 80, 80))
draw = ImageDraw.Draw(img)
draw.text((640, 360), "Tokyo Weather Music", fill=(200, 200, 200), anchor="mm")
img.save("assets/default_thumbnail.png")
```

```bash
python -c "
from PIL import Image, ImageDraw
img = Image.new('RGB', (1280, 720), (80, 80, 80))
draw = ImageDraw.Draw(img)
draw.text((640, 360), 'Tokyo Weather Music', fill=(200, 200, 200))
img.save('assets/default_thumbnail.png')
"
```

- [ ] **Step 4: thumbnail.pyを実装する**

`src/thumbnail.py`:
```python
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


def _get_palette(season: str, weather_label: str) -> tuple:
    label = weather_label.lower()
    for (s, w_key), colors in PALETTES.items():
        if s == season and w_key in label:
            return colors
    for (s, _), colors in PALETTES.items():
        if s == season:
            return colors
    return DEFAULT_PALETTE


def create_thumbnail(
    title_ja: str,
    title_en: str,
    date: str,
    season: str,
    weather_label: str,
    output_path: str = "/tmp/thumbnail.png",
    default_path: str = DEFAULT_THUMBNAIL,
) -> str:
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
        draw.text((WIDTH // 2, HEIGHT // 2 + 80), f"Tokyo Weather Music  {date}", fill=text_color, font=font_small, anchor="mm")

        img.save(output_path)
        return output_path
    except Exception as e:
        print(f"[thumbnail] サムネイル生成失敗、デフォルト使用: {e}")
        return default_path
```

- [ ] **Step 5: テストを実行して全パスを確認する**

```bash
pytest tests/test_thumbnail.py -v
```

Expected: 全テストPASS

- [ ] **Step 6: コミット**

```bash
git add src/thumbnail.py assets/default_thumbnail.png tests/test_thumbnail.py
git commit -m "feat: add thumbnail module with season/weather color palette"
```

---

## Task 6: youtube.py — YouTube動画アップロード

**Files:**
- Create: `src/youtube.py`
- Create: `tests/test_youtube.py`

- [ ] **Step 1: テストを書く**

`tests/test_youtube.py`:
```python
import pytest
from unittest.mock import patch, MagicMock
from src.youtube import upload_to_youtube, _build_service


def test_build_service_uses_env_credentials():
    with patch("src.youtube.os.environ", {
        "YOUTUBE_CLIENT_ID": "cid",
        "YOUTUBE_CLIENT_SECRET": "csec",
        "YOUTUBE_REFRESH_TOKEN": "rtoken",
    }):
        with patch("src.youtube.build") as mock_build:
            with patch("src.youtube.Credentials") as mock_cred:
                _build_service()
                mock_cred.assert_called_once()
                mock_build.assert_called_once_with("youtube", "v3", credentials=mock_cred.return_value)


def test_upload_to_youtube_calls_insert(tmp_path):
    mp3 = tmp_path / "test.mp3"
    mp3.write_bytes(b"fake")
    thumb = tmp_path / "thumb.png"
    thumb.write_bytes(b"fakepng")

    mock_service = MagicMock()
    mock_service.videos().insert().execute.return_value = {"id": "VIDEO_ID_123"}
    mock_service.thumbnails().set().execute.return_value = {}

    with patch("src.youtube._build_service", return_value=mock_service):
        with patch("src.youtube.MediaFileUpload"):
            result = upload_to_youtube(
                audio_path=str(mp3),
                thumbnail_path=str(thumb),
                title_ja="春雨の東京",
                title_en="Spring Rain in Tokyo",
                description="テスト説明文",
                date="2026-05-14",
                season="春",
            )

    assert result == "VIDEO_ID_123"
    mock_service.videos().insert.assert_called_once()


def test_upload_to_youtube_retries_on_failure(tmp_path):
    mp3 = tmp_path / "test.mp3"
    mp3.write_bytes(b"fake")
    thumb = tmp_path / "thumb.png"
    thumb.write_bytes(b"fakepng")

    mock_service = MagicMock()
    mock_service.videos().insert().execute.side_effect = [
        Exception("API error"),
        Exception("API error"),
        {"id": "VIDEO_SUCCESS"},
    ]
    mock_service.thumbnails().set().execute.return_value = {}

    with patch("src.youtube._build_service", return_value=mock_service):
        with patch("src.youtube.MediaFileUpload"):
            result = upload_to_youtube(
                audio_path=str(mp3),
                thumbnail_path=str(thumb),
                title_ja="test", title_en="test",
                description="test", date="2026-05-14", season="春",
            )
    assert result == "VIDEO_SUCCESS"
```

- [ ] **Step 2: テストが失敗することを確認する**

```bash
pytest tests/test_youtube.py -v
```

Expected: `ImportError`

- [ ] **Step 3: youtube.pyを実装する**

`src/youtube.py`:
```python
import os
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials

YOUTUBE_SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def _build_service():
    creds = Credentials(
        token=None,
        refresh_token=os.environ["YOUTUBE_REFRESH_TOKEN"],
        client_id=os.environ["YOUTUBE_CLIENT_ID"],
        client_secret=os.environ["YOUTUBE_CLIENT_SECRET"],
        token_uri="https://oauth2.googleapis.com/token",
        scopes=YOUTUBE_SCOPES,
    )
    return build("youtube", "v3", credentials=creds)


def upload_to_youtube(
    audio_path: str,
    thumbnail_path: str,
    title_ja: str,
    title_en: str,
    description: str,
    date: str,
    season: str,
    max_retries: int = 3,
) -> str:
    service = _build_service()
    title = f"{title_ja} | Tokyo Weather Music {date}"
    tags = ["Tokyo", "東京", "instrumental", "ambient", "lofi", "weather", "天気", season]

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": "10",
        },
        "status": {"privacyStatus": "public"},
    }

    last_error = None
    for attempt in range(max_retries):
        try:
            media = MediaFileUpload(audio_path, mimetype="audio/mpeg", resumable=True)
            response = service.videos().insert(
                part="snippet,status",
                body=body,
                media_body=media,
            ).execute()
            video_id = response["id"]

            service.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(thumbnail_path, mimetype="image/png"),
            ).execute()

            print(f"[youtube] アップロード完了: https://youtu.be/{video_id}")
            return video_id

        except Exception as e:
            last_error = e
            print(f"[youtube] 試行 {attempt + 1} 失敗: {e}")

    raise RuntimeError(f"YouTubeアップロード失敗（{max_retries}回試行）: {last_error}")
```

- [ ] **Step 4: テストを実行して全パスを確認する**

```bash
pytest tests/test_youtube.py -v
```

Expected: 全テストPASS

- [ ] **Step 5: コミット**

```bash
git add src/youtube.py tests/test_youtube.py
git commit -m "feat: add youtube module for video upload with OAuth2"
```

---

## Task 7: main.py — オーケストレーター

**Files:**
- Create: `src/main.py`
- Create: `tests/test_main.py`

- [ ] **Step 1: テストを書く**

`tests/test_main.py`:
```python
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
```

- [ ] **Step 2: テストが失敗することを確認する**

```bash
pytest tests/test_main.py -v
```

Expected: `ImportError`

- [ ] **Step 3: main.pyを実装する**

`src/main.py`:
```python
import os
import subprocess
from datetime import date

from src.weather import get_weather
from src.prompt import generate_prompt
from src.suno import generate_music
from src.thumbnail import create_thumbnail
from src.youtube import upload_to_youtube


def _notify_failure(module: str, error: Exception) -> None:
    print(f"[main] 致命的エラー: {module} — {error}")
    if os.environ.get("GITHUB_ACTIONS"):
        title = f"Tokyo Weather Music 失敗: {module}"
        body = f"モジュール: {module}\\nエラー: {error}"
        subprocess.run(
            ["gh", "issue", "create", "--title", title, "--body", body],
            check=False,
        )


def run() -> None:
    today = str(date.today())

    # 1. 天気取得
    try:
        weather = get_weather(date=today)
        print(f"[main] 天気取得完了: {weather['weather_label']} {weather['temperature']}℃")
    except RuntimeError as e:
        _notify_failure("weather", e)
        return

    # 2. プロンプト生成（失敗時はフォールバック済みなので例外なし）
    prompt_data = generate_prompt(weather)
    print(f"[main] プロンプト生成完了: {prompt_data['title_ja']}")

    # 3. SUNO音楽生成
    audio_path = f"/tmp/tokyo_music_{today}.mp3"
    try:
        generate_music(prompt_data["suno_prompt"], output_path=audio_path)
        print(f"[main] 音楽生成完了: {audio_path}")
    except RuntimeError as e:
        print(f"[main] 音楽生成失敗、本日はスキップ: {e}")
        return

    # 4. サムネイル生成（失敗してもデフォルト画像で続行）
    thumb_path = f"/tmp/thumbnail_{today}.png"
    thumbnail = create_thumbnail(
        title_ja=prompt_data["title_ja"],
        title_en=prompt_data["title_en"],
        date=today,
        season=weather["season"],
        weather_label=weather["weather_label"],
        output_path=thumb_path,
    )
    print(f"[main] サムネイル生成完了: {thumbnail}")

    # 5. YouTube アップロード
    try:
        video_id = upload_to_youtube(
            audio_path=audio_path,
            thumbnail_path=thumbnail,
            title_ja=prompt_data["title_ja"],
            title_en=prompt_data["title_en"],
            description=prompt_data["description"],
            date=today,
            season=weather["season"],
        )
        print(f"[main] YouTube投稿完了: https://youtu.be/{video_id}")
    except RuntimeError as e:
        _notify_failure("youtube", e)


if __name__ == "__main__":
    run()
```

- [ ] **Step 4: テストを実行して全パスを確認する**

```bash
pytest tests/test_main.py -v
```

Expected: 全テストPASS

- [ ] **Step 5: 全テストをまとめて実行する**

```bash
pytest tests/ -v
```

Expected: 全テストPASS

- [ ] **Step 6: コミット**

```bash
git add src/main.py tests/test_main.py
git commit -m "feat: add main orchestrator with per-module error handling"
```

---

## Task 8: GitHub Actions ワークフロー設定

**Files:**
- Create: `.github/workflows/daily.yml`

- [ ] **Step 1: .github/workflowsディレクトリを作成する**

```bash
mkdir -p .github/workflows
```

- [ ] **Step 2: daily.ymlを作成する**

`.github/workflows/daily.yml`:
```yaml
name: Daily Tokyo Weather Music

on:
  schedule:
    - cron: '0 21 * * *'   # UTC 21:00 = JST 06:00
  workflow_dispatch:         # 手動トリガー（テスト用）

jobs:
  generate-and-upload:
    runs-on: ubuntu-latest
    permissions:
      contents: write        # podcast.pyのgit push用（Phase 2）
      issues: write          # 失敗通知用

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up Python 3.12
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: 'pip'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run daily music generation
        run: python src/main.py
        env:
          ANTHROPIC_API_KEY:      ${{ secrets.ANTHROPIC_API_KEY }}
          SUNO_COOKIE:            ${{ secrets.SUNO_COOKIE }}
          YOUTUBE_CLIENT_ID:      ${{ secrets.YOUTUBE_CLIENT_ID }}
          YOUTUBE_CLIENT_SECRET:  ${{ secrets.YOUTUBE_CLIENT_SECRET }}
          YOUTUBE_REFRESH_TOKEN:  ${{ secrets.YOUTUBE_REFRESH_TOKEN }}
          GITHUB_REPOSITORY_OWNER: ${{ github.repository_owner }}
          GITHUB_TOKEN:           ${{ secrets.GITHUB_TOKEN }}
```

- [ ] **Step 3: GitHub Secretsの設定手順を確認する**

GitHubリポジトリ → Settings → Secrets and variables → Actions → New repository secret で以下を登録：

| Secret名 | 取得方法 |
|---|---|
| `ANTHROPIC_API_KEY` | console.anthropic.com → API Keys |
| `SUNO_COOKIE` | ブラウザでsuno.comにログイン → DevTools → Application → Cookies → `__Secure-next-auth.session-token` の値 |
| `YOUTUBE_CLIENT_ID` | Google Cloud Console → APIとサービス → 認証情報 → OAuth 2.0クライアントID |
| `YOUTUBE_CLIENT_SECRET` | 同上 |
| `YOUTUBE_REFRESH_TOKEN` | 後述のOAuth2セットアップ手順で取得 |

- [ ] **Step 4: YouTube OAuth2リフレッシュトークンを取得する**

```bash
# google-auth-oauthlib をインストール済みであることを確認
pip show google-auth-oauthlib

# トークン取得スクリプトを実行（ローカルで1回だけ）
python - <<'EOF'
from google_auth_oauthlib.flow import InstalledAppFlow

flow = InstalledAppFlow.from_client_config(
    {
        "installed": {
            "client_id": "YOUR_CLIENT_ID",
            "client_secret": "YOUR_CLIENT_SECRET",
            "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    },
    scopes=["https://www.googleapis.com/auth/youtube.upload"],
)
creds = flow.run_local_server(port=0)
print("REFRESH_TOKEN:", creds.refresh_token)
EOF
```

表示された `REFRESH_TOKEN` を `YOUTUBE_REFRESH_TOKEN` Secretに登録する。

- [ ] **Step 5: workflow_dispatchで手動実行テストを行う**

GitHubリポジトリ → Actions → Daily Tokyo Weather Music → Run workflow

Expected: ワークフローが正常完了し、YouTubeに動画が投稿される

- [ ] **Step 6: コミット**

```bash
git add .github/workflows/daily.yml
git commit -m "feat: add GitHub Actions daily workflow"
```

---

## Task 9: podcast.py — Spotify配信（Phase 2）

**Files:**
- Create: `src/podcast.py`
- Create: `docs/feed.xml`（初期テンプレート）
- Create: `tests/test_podcast.py`

- [ ] **Step 1: テストを書く**

`tests/test_podcast.py`:
```python
import pytest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch, MagicMock
from src.podcast import update_feed, _add_episode_to_feed


SAMPLE_FEED = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Tokyo Weather Music</title>
    <link>https://example.github.io/tokyo-weather-music</link>
    <description>東京の天候をテーマにした毎日のインストゥルメンタル音楽</description>
  </channel>
</rss>"""


def test_add_episode_to_feed_inserts_item(tmp_path):
    feed_path = tmp_path / "feed.xml"
    feed_path.write_text(SAMPLE_FEED, encoding="utf-8")

    _add_episode_to_feed(
        feed_path=str(feed_path),
        title="春雨の東京",
        description="説明文",
        mp3_url="https://example.github.io/tokyo-weather-music/episodes/2026-05-14.mp3",
        file_size=1024000,
        pub_date="Thu, 14 May 2026 06:00:00 +0900",
        guid="2026-05-14",
    )

    tree = ET.parse(feed_path)
    items = tree.findall(".//item")
    assert len(items) == 1
    assert items[0].find("title").text == "春雨の東京"
    assert items[0].find("guid").text == "2026-05-14"


def test_add_episode_prepends_newest_first(tmp_path):
    feed_path = tmp_path / "feed.xml"
    feed_path.write_text(SAMPLE_FEED, encoding="utf-8")

    for guid in ["2026-05-13", "2026-05-14"]:
        _add_episode_to_feed(
            feed_path=str(feed_path), title=f"Test {guid}", description="",
            mp3_url=f"https://example.github.io/episodes/{guid}.mp3",
            file_size=1000, pub_date="Thu, 14 May 2026 06:00:00 +0900", guid=guid,
        )

    tree = ET.parse(feed_path)
    items = tree.findall(".//item")
    assert items[0].find("guid").text == "2026-05-14"


def test_update_feed_copies_mp3_and_updates_xml(tmp_path):
    feed_path = tmp_path / "feed.xml"
    feed_path.write_text(SAMPLE_FEED, encoding="utf-8")
    episodes_dir = tmp_path / "episodes"
    episodes_dir.mkdir()
    mp3 = tmp_path / "out.mp3"
    mp3.write_bytes(b"x" * 1024)

    with patch("src.podcast._git_commit_push") as mock_git:
        update_feed(
            audio_path=str(mp3),
            title_ja="春雨の東京",
            description="説明文",
            date="2026-05-14",
            feed_path=str(feed_path),
            episodes_dir=str(episodes_dir),
            base_url="https://example.github.io/tokyo-weather-music",
        )
    assert (episodes_dir / "2026-05-14.mp3").exists()
    mock_git.assert_called_once()
```

- [ ] **Step 2: テストが失敗することを確認する**

```bash
pytest tests/test_podcast.py -v
```

Expected: `ImportError`

- [ ] **Step 3: 初期feed.xmlを作成する**

`docs/feed.xml`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">
  <channel>
    <title>Tokyo Weather Music</title>
    <link>https://GITHUB_REPOSITORY_OWNER.github.io/tokyo-weather-music</link>
    <description>東京の毎日の天候をテーマにした自動生成インストゥルメンタル音楽</description>
    <language>ja</language>
    <itunes:category text="Music"/>
    <itunes:explicit>false</itunes:explicit>
  </channel>
</rss>
```

- [ ] **Step 4: podcast.pyを実装する**

`src/podcast.py`:
```python
import os
import shutil
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from pathlib import Path

DOCS_DIR = os.path.join(os.path.dirname(__file__), "../docs")
DEFAULT_FEED = os.path.join(DOCS_DIR, "feed.xml")
DEFAULT_EPISODES_DIR = os.path.join(DOCS_DIR, "episodes")
JST = timezone(timedelta(hours=9))


def _git_commit_push(date: str) -> None:
    subprocess.run(["git", "config", "user.email", "action@github.com"], check=True)
    subprocess.run(["git", "config", "user.name", "GitHub Actions"], check=True)
    subprocess.run(["git", "add", "docs/"], check=True)
    subprocess.run(["git", "commit", "-m", f"podcast: add episode {date}"], check=True)
    subprocess.run(["git", "push"], check=True)


def _add_episode_to_feed(
    feed_path: str,
    title: str,
    description: str,
    mp3_url: str,
    file_size: int,
    pub_date: str,
    guid: str,
) -> None:
    ET.register_namespace("itunes", "http://www.itunes.com/dtds/podcast-1.0.dtd")
    tree = ET.parse(feed_path)
    channel = tree.find("channel")

    item = ET.Element("item")
    ET.SubElement(item, "title").text = title
    ET.SubElement(item, "description").text = description
    enclosure = ET.SubElement(item, "enclosure")
    enclosure.set("url", mp3_url)
    enclosure.set("type", "audio/mpeg")
    enclosure.set("length", str(file_size))
    ET.SubElement(item, "pubDate").text = pub_date
    ET.SubElement(item, "guid").text = guid

    # 最新エピソードを先頭に挿入
    first_item_idx = None
    for i, child in enumerate(channel):
        if child.tag == "item":
            first_item_idx = i
            break
    if first_item_idx is not None:
        channel.insert(first_item_idx, item)
    else:
        channel.append(item)

    tree.write(feed_path, encoding="utf-8", xml_declaration=True)


def update_feed(
    audio_path: str,
    title_ja: str,
    description: str,
    date: str,
    feed_path: str = DEFAULT_FEED,
    episodes_dir: str = DEFAULT_EPISODES_DIR,
    base_url: str | None = None,
    max_retries: int = 3,
) -> None:
    owner = os.environ.get("GITHUB_REPOSITORY_OWNER", "owner")
    if base_url is None:
        base_url = f"https://{owner}.github.io/tokyo-weather-music"

    dest = os.path.join(episodes_dir, f"{date}.mp3")
    shutil.copy2(audio_path, dest)

    mp3_url = f"{base_url}/episodes/{date}.mp3"
    file_size = Path(dest).stat().st_size
    now_jst = datetime.now(JST)
    pub_date = now_jst.strftime("%a, %d %b %Y 06:00:00 +0900")

    _add_episode_to_feed(
        feed_path=feed_path,
        title=title_ja,
        description=description,
        mp3_url=mp3_url,
        file_size=file_size,
        pub_date=pub_date,
        guid=date,
    )

    last_error = None
    for attempt in range(max_retries):
        try:
            _git_commit_push(date)
            print(f"[podcast] RSS更新・push完了: {mp3_url}")
            return
        except subprocess.CalledProcessError as e:
            last_error = e
            print(f"[podcast] git push 試行 {attempt + 1} 失敗: {e}")

    raise RuntimeError(f"podcast git push失敗（{max_retries}回試行）: {last_error}")
```

- [ ] **Step 5: main.pyにpodcast呼び出しを追加する**

`src/main.py` の `upload_to_youtube` 成功後のブロックに追記：

```python
    # 6. Podcast RSS更新（Phase 2）
    try:
        from src.podcast import update_feed
        update_feed(
            audio_path=audio_path,
            title_ja=prompt_data["title_ja"],
            description=prompt_data["description"],
            date=today,
        )
    except Exception as e:
        _notify_failure("podcast", e)
```

- [ ] **Step 6: テストを実行して全パスを確認する**

```bash
pytest tests/test_podcast.py tests/test_main.py -v
```

Expected: 全テストPASS

- [ ] **Step 7: GitHub PagesをdocsフォルダでONにする**

GitHubリポジトリ → Settings → Pages → Source: Deploy from a branch → Branch: `main` / `docs` → Save

- [ ] **Step 8: Spotify for Podcastersにフィードを登録する（1回のみ手動）**

1. https://podcasters.spotify.com にアクセス
2. 「ポッドキャストを追加」→「既存のRSSフィードを持っている」
3. RSS URL: `https://{あなたのGitHubユーザー名}.github.io/tokyo-weather-music/feed.xml` を入力
4. 登録完了後は以降すべて自動

- [ ] **Step 9: コミット**

```bash
git add src/podcast.py src/main.py docs/feed.xml tests/test_podcast.py
git commit -m "feat: add podcast module for Spotify RSS auto-distribution (Phase 2)"
```

---

## Task 10: 全体統合テスト・最終確認

- [ ] **Step 1: 全テストを実行する**

```bash
pytest tests/ -v --tb=short
```

Expected: 全テストPASS（警告は無視可）

- [ ] **Step 2: workflow_dispatchで本番動作を確認する**

GitHub Actions → Daily Tokyo Weather Music → Run workflow → 実行完了後：
- YouTube チャンネルに動画が投稿されていること
- `docs/episodes/` にmp3が追加されていること
- `docs/feed.xml` に新エピソードが追記されていること

- [ ] **Step 3: 最終コミット・タグ付け**

```bash
git tag v1.0.0
git push origin main --tags
```

---

## セットアップチェックリスト（初回のみ）

- [ ] GitHub リポジトリを作成し push
- [ ] GitHub Secrets に5つの認証情報を登録
- [ ] YouTube OAuth2 Refresh Token を取得してSecretに登録
- [ ] GitHub Pages を `docs/` フォルダで有効化
- [ ] Spotify for Podcasters にRSSフィードを1回登録
- [ ] workflow_dispatch で動作確認

---

## 補足: SUNO Cookieの定期更新

SUNO のセッションCookieは数週間〜数ヶ月で失効します。失効するとワークフローがエラーになり、GitHub Issueで通知されます。その際は：

1. ブラウザで suno.com にログイン
2. DevTools → Application → Cookies → `__Secure-next-auth.session-token` の値をコピー
3. GitHub Secrets の `SUNO_COOKIE` を更新
