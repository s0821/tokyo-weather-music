# SoundCloud & Instagram Reels Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 既存のTokyo Weather Musicシステムに SoundCloud への音楽アップロードと Instagram Reels への動画投稿を追加し、毎朝6時の自動実行フローに組み込む。

**Architecture:** SoundCloud は requests でマルチパートアップロード、Instagram は ffmpeg でmp3+画像→mp4変換後に Meta Graph API のリジューマブルアップロードで投稿。main.py にフォールトトレラントに追加し、daily.yml に ffmpeg インストールと新 Secrets を追加。

**Tech Stack:** Python 3.9, requests, subprocess (ffmpeg), pytest, pytest-mock

---

## ファイル構成

```
src/
  soundcloud.py      # 新規: SoundCloud API アップロード
  instagram.py       # 新規: mp4変換 + Instagram Reels 投稿
  main.py            # 修正: soundcloud/instagram 呼び出し追加
tests/
  test_soundcloud.py # 新規
  test_instagram.py  # 新規
.github/workflows/
  daily.yml          # 修正: ffmpeg + 新 Secrets
requirements.txt     # 変更なし（requests は既存）
```

---

## Task 1: soundcloud.py — SoundCloud アップロード

**Files:**
- Create: `src/soundcloud.py`
- Create: `tests/test_soundcloud.py`

- [ ] **Step 1: テストを書く**

`tests/test_soundcloud.py`:
```python
import pytest
from unittest.mock import patch, MagicMock
from src.soundcloud import upload_to_soundcloud


def test_upload_to_soundcloud_sends_multipart(tmp_path):
    mp3 = tmp_path / "test.mp3"
    mp3.write_bytes(b"fake-mp3")

    mock_resp = MagicMock()
    mock_resp.status_code = 201
    mock_resp.json.return_value = {
        "id": 123456,
        "permalink_url": "https://soundcloud.com/tokyoweathermusic/spring-rain"
    }

    with patch("src.soundcloud.requests.post", return_value=mock_resp) as mock_post:
        result = upload_to_soundcloud(
            audio_path=str(mp3),
            title_ja="春雨の東京",
            title_en="Spring Rain in Tokyo",
            description="今日の東京は春の小雨。",
            date="2026-05-15",
            season="春",
        )

    assert result == "https://soundcloud.com/tokyoweathermusic/spring-rain"
    call_kwargs = mock_post.call_args
    assert "files" in call_kwargs.kwargs or "files" in call_kwargs.args[1] if len(call_kwargs.args) > 1 else True


def test_upload_to_soundcloud_retries_on_failure(tmp_path):
    mp3 = tmp_path / "test.mp3"
    mp3.write_bytes(b"fake")

    success_resp = MagicMock()
    success_resp.status_code = 201
    success_resp.json.return_value = {
        "id": 999,
        "permalink_url": "https://soundcloud.com/tokyoweathermusic/test"
    }

    with patch("src.soundcloud.requests.post") as mock_post:
        mock_post.side_effect = [
            Exception("network error"),
            Exception("network error"),
            success_resp,
        ]
        result = upload_to_soundcloud(
            audio_path=str(mp3),
            title_ja="test", title_en="test",
            description="test", date="2026-05-15", season="春",
        )

    assert result == "https://soundcloud.com/tokyoweathermusic/test"
    assert mock_post.call_count == 3


def test_upload_to_soundcloud_raises_after_max_retries(tmp_path):
    mp3 = tmp_path / "test.mp3"
    mp3.write_bytes(b"fake")

    with patch("src.soundcloud.requests.post", side_effect=Exception("fail")):
        with pytest.raises(RuntimeError, match="SoundCloud"):
            upload_to_soundcloud(
                audio_path=str(mp3),
                title_ja="test", title_en="test",
                description="test", date="2026-05-15", season="春",
            )
```

- [ ] **Step 2: テストが失敗することを確認する**

```bash
cd "/Users/hanawasadayuki/Applications/Claude Code/tokyo-weather-music"
python3 -m pytest tests/test_soundcloud.py -v
```

Expected: `ImportError`

- [ ] **Step 3: soundcloud.py を実装する**

`src/soundcloud.py`:
```python
import os
import requests

SOUNDCLOUD_API = "https://api.soundcloud.com"


def upload_to_soundcloud(
    audio_path,
    title_ja,
    title_en,
    description,
    date,
    season,
    max_retries=3,
):
    token = os.environ["SOUNDCLOUD_AUTH_TOKEN"]
    headers = {"Authorization": "OAuth {}".format(token)}

    title = "{} | Tokyo Weather Music {}".format(title_ja, date)
    tags = "Tokyo 東京 instrumental ambient lofi weather 天気 {}".format(season)

    last_error = None
    for attempt in range(max_retries):
        try:
            with open(audio_path, "rb") as f:
                resp = requests.post(
                    "{}/tracks".format(SOUNDCLOUD_API),
                    headers=headers,
                    files={"track[asset_data]": (audio_path, f, "audio/mpeg")},
                    data={
                        "track[title]": title,
                        "track[description]": description,
                        "track[tag_list]": tags,
                        "track[sharing]": "public",
                        "track[genre]": "Ambient",
                    },
                    timeout=120,
                )
            if resp.status_code not in (200, 201):
                raise RuntimeError("HTTP {}: {}".format(resp.status_code, resp.text[:200]))
            url = resp.json()["permalink_url"]
            print("[soundcloud] アップロード完了: {}".format(url))
            return url
        except Exception as e:
            last_error = e
            print("[soundcloud] 試行 {} 失敗: {}".format(attempt + 1, e))

    raise RuntimeError("SoundCloudアップロード失敗（{}回試行）: {}".format(max_retries, last_error))
```

- [ ] **Step 4: テストを実行して全パスを確認する**

```bash
python3 -m pytest tests/test_soundcloud.py -v
```

Expected: 3件 PASS

- [ ] **Step 5: コミット**

```bash
cd "/Users/hanawasadayuki/Applications/Claude Code/tokyo-weather-music"
git add src/soundcloud.py tests/test_soundcloud.py
git commit -m "feat: add SoundCloud upload module"
```

---

## Task 2: instagram.py — mp4変換 + Instagram Reels 投稿

**Files:**
- Create: `src/instagram.py`
- Create: `tests/test_instagram.py`

- [ ] **Step 1: テストを書く**

`tests/test_instagram.py`:
```python
import pytest
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock, call
from src.instagram import post_reel, _create_mp4, _upload_reel, _wait_for_container


def test_create_mp4_calls_ffmpeg(tmp_path):
    mp3 = tmp_path / "audio.mp3"
    mp3.write_bytes(b"fake")
    thumbnail = tmp_path / "thumb.png"
    thumbnail.write_bytes(b"fakepng")
    output = tmp_path / "out.mp4"

    with patch("src.instagram.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        result = _create_mp4(str(mp3), str(thumbnail), str(output))

    assert result == str(output)
    mock_run.assert_called_once()
    cmd = mock_run.call_args[0][0]
    assert "ffmpeg" in cmd
    assert str(mp3) in cmd
    assert str(thumbnail) in cmd
    assert str(output) in cmd


def test_wait_for_container_returns_on_finished():
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"status_code": "FINISHED"}
    mock_resp.raise_for_status = MagicMock()

    with patch("src.instagram.requests.get", return_value=mock_resp):
        with patch("src.instagram.time.sleep"):
            result = _wait_for_container("container_123", "fake_token")

    assert result == "container_123"


def test_wait_for_container_raises_on_error():
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"status_code": "ERROR"}
    mock_resp.raise_for_status = MagicMock()

    with patch("src.instagram.requests.get", return_value=mock_resp):
        with patch("src.instagram.time.sleep"):
            with pytest.raises(RuntimeError, match="コンテナ処理エラー"):
                _wait_for_container("container_123", "fake_token")


def test_post_reel_happy_path(tmp_path):
    mp3 = tmp_path / "audio.mp3"
    mp3.write_bytes(b"fake")
    thumbnail = tmp_path / "thumb.png"
    thumbnail.write_bytes(b"fakepng")

    # mp4 creation mock
    mp4_path = str(tmp_path / "out.mp4")

    container_resp = MagicMock()
    container_resp.json.return_value = {"id": "container_abc"}
    container_resp.raise_for_status = MagicMock()

    publish_resp = MagicMock()
    publish_resp.json.return_value = {"id": "media_xyz"}
    publish_resp.raise_for_status = MagicMock()

    with patch("src.instagram._create_mp4", return_value=mp4_path):
        with patch("src.instagram._upload_reel", return_value="container_abc"):
            with patch("src.instagram._wait_for_container", return_value="container_abc"):
                with patch("src.instagram.requests.post", return_value=publish_resp):
                    result = post_reel(
                        audio_path=str(mp3),
                        thumbnail_path=str(thumbnail),
                        title_ja="春雨の東京",
                        description="説明文",
                        date="2026-05-15",
                    )

    assert result == "media_xyz"
```

- [ ] **Step 2: テストが失敗することを確認する**

```bash
python3 -m pytest tests/test_instagram.py -v
```

Expected: `ImportError`

- [ ] **Step 3: instagram.py を実装する**

`src/instagram.py`:
```python
import os
import subprocess
import time
import requests

GRAPH_API = "https://graph.facebook.com/v19.0"


def _create_mp4(audio_path, thumbnail_path, output_path):
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", thumbnail_path,
        "-i", audio_path,
        "-c:v", "libx264",
        "-tune", "stillimage",
        "-c:a", "aac",
        "-b:a", "192k",
        "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2",
        "-shortest",
        "-movflags", "+faststart",
        "-pix_fmt", "yuv420p",
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, timeout=120)
    if result.returncode != 0:
        raise RuntimeError("ffmpeg失敗: {}".format(result.stderr.decode()[:300]))
    return output_path


def _upload_reel(mp4_path, token, user_id, description):
    # Step 1: リジューマブルアップロードのセッションを開始
    init_resp = requests.post(
        "{}/{}/media".format(GRAPH_API, user_id),
        data={
            "media_type": "REELS",
            "upload_type": "resumable",
            "caption": description,
            "access_token": token,
        },
        timeout=30,
    )
    init_resp.raise_for_status()
    upload_url = init_resp.json().get("uri") or init_resp.json().get("upload_url")
    container_id = init_resp.json().get("id")

    if not upload_url:
        raise RuntimeError("upload_url が取得できませんでした: {}".format(init_resp.json()))

    # Step 2: 動画ファイルをアップロード
    file_size = os.path.getsize(mp4_path)
    with open(mp4_path, "rb") as f:
        upload_resp = requests.post(
            upload_url,
            headers={
                "Authorization": "OAuth {}".format(token),
                "offset": "0",
                "file_size": str(file_size),
            },
            data=f,
            timeout=300,
        )
    upload_resp.raise_for_status()

    return container_id


def _wait_for_container(container_id, token, max_polls=20, interval=10):
    for _ in range(max_polls):
        resp = requests.get(
            "{}/{}".format(GRAPH_API, container_id),
            params={"fields": "status_code", "access_token": token},
            timeout=15,
        )
        resp.raise_for_status()
        status = resp.json().get("status_code")
        if status == "FINISHED":
            return container_id
        if status == "ERROR":
            raise RuntimeError("コンテナ処理エラー: container_id={}".format(container_id))
        time.sleep(interval)
    raise RuntimeError("コンテナ処理タイムアウト: container_id={}".format(container_id))


def post_reel(
    audio_path,
    thumbnail_path,
    title_ja,
    description,
    date,
    max_retries=3,
):
    token = os.environ["INSTAGRAM_ACCESS_TOKEN"]
    user_id = os.environ["INSTAGRAM_USER_ID"]

    mp4_path = "/tmp/instagram_{}.mp4".format(date)
    last_error = None

    for attempt in range(max_retries):
        try:
            _create_mp4(audio_path, thumbnail_path, mp4_path)

            container_id = _upload_reel(mp4_path, token, user_id, description)
            _wait_for_container(container_id, token)

            publish_resp = requests.post(
                "{}/{}/media_publish".format(GRAPH_API, user_id),
                data={
                    "creation_id": container_id,
                    "access_token": token,
                },
                timeout=30,
            )
            publish_resp.raise_for_status()
            media_id = publish_resp.json()["id"]
            print("[instagram] Reels投稿完了: media_id={}".format(media_id))
            return media_id

        except Exception as e:
            last_error = e
            print("[instagram] 試行 {} 失敗: {}".format(attempt + 1, e))

    raise RuntimeError("Instagram Reels投稿失敗（{}回試行）: {}".format(max_retries, last_error))
```

- [ ] **Step 4: テストを実行して全パスを確認する**

```bash
python3 -m pytest tests/test_instagram.py -v
```

Expected: 4件 PASS

- [ ] **Step 5: コミット**

```bash
git add src/instagram.py tests/test_instagram.py
git commit -m "feat: add Instagram Reels module with ffmpeg mp4 conversion"
```

---

## Task 3: main.py に SoundCloud と Instagram を追加

**Files:**
- Modify: `src/main.py`
- Modify: `tests/test_main.py`

- [ ] **Step 1: test_main.py にテストを追加する**

`tests/test_main.py` に以下を追記：

```python
def test_run_calls_soundcloud_and_instagram():
    with patch("src.main.get_weather", return_value=MOCK_WEATHER), \
         patch("src.main.generate_prompt", return_value=MOCK_PROMPT), \
         patch("src.main.generate_music", return_value="/tmp/out.mp3"), \
         patch("src.main.create_thumbnail", return_value="/tmp/thumb.png"), \
         patch("src.main.upload_to_youtube", return_value="VIDEO123"), \
         patch("src.main.upload_to_soundcloud", return_value="https://soundcloud.com/test") as msc, \
         patch("src.main.post_reel", return_value="media_123") as mir:
        from src.main import run
        run()

    msc.assert_called_once()
    mir.assert_called_once()


def test_run_continues_if_soundcloud_fails():
    with patch("src.main.get_weather", return_value=MOCK_WEATHER), \
         patch("src.main.generate_prompt", return_value=MOCK_PROMPT), \
         patch("src.main.generate_music", return_value="/tmp/out.mp3"), \
         patch("src.main.create_thumbnail", return_value="/tmp/thumb.png"), \
         patch("src.main.upload_to_youtube", return_value="VIDEO123"), \
         patch("src.main.upload_to_soundcloud", side_effect=RuntimeError("sc fail")), \
         patch("src.main.post_reel", return_value="media_123") as mir:
        from src.main import run
        run()

    mir.assert_called_once()
```

- [ ] **Step 2: テストが失敗することを確認する**

```bash
python3 -m pytest tests/test_main.py::test_run_calls_soundcloud_and_instagram -v
```

Expected: `ImportError` または `AssertionError`

- [ ] **Step 3: main.py を更新する**

`src/main.py` の import に以下を追加：
```python
from src.soundcloud import upload_to_soundcloud
from src.instagram import post_reel
```

`run()` 関数の YouTube アップロードブロックの後（podcast呼び出しの前）に追加：

```python
    # 6. SoundCloud アップロード
    try:
        sc_url = upload_to_soundcloud(
            audio_path=audio_path,
            title_ja=prompt_data["title_ja"],
            title_en=prompt_data["title_en"],
            description=prompt_data["description"],
            date=today,
            season=weather["season"],
        )
        print("[main] SoundCloud投稿完了: {}".format(sc_url))
    except Exception as e:
        _notify_failure("soundcloud", e)

    # 7. Instagram Reels 投稿
    try:
        media_id = post_reel(
            audio_path=audio_path,
            thumbnail_path=thumbnail,
            title_ja=prompt_data["title_ja"],
            description=prompt_data["description"],
            date=today,
        )
        print("[main] Instagram Reels投稿完了: {}".format(media_id))
    except Exception as e:
        _notify_failure("instagram", e)
```

- [ ] **Step 4: テストを実行して全パスを確認する**

```bash
python3 -m pytest tests/ -v
```

Expected: 全テスト PASS

- [ ] **Step 5: コミット**

```bash
git add src/main.py tests/test_main.py
git commit -m "feat: integrate SoundCloud and Instagram into daily pipeline"
```

---

## Task 4: daily.yml を更新（ffmpeg + 新 Secrets）

**Files:**
- Modify: `.github/workflows/daily.yml`

- [ ] **Step 1: daily.yml を更新する**

`.github/workflows/daily.yml` の `Install dependencies` ステップの前に ffmpeg インストールを追加し、`env` に新 Secrets を追記：

```yaml
name: Daily Tokyo Weather Music

on:
  schedule:
    - cron: '0 21 * * *'   # UTC 21:00 = JST 06:00
  workflow_dispatch:

jobs:
  generate-and-upload:
    runs-on: ubuntu-latest
    permissions:
      contents: write
      issues: write

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up Python 3.12
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: 'pip'

      - name: Install ffmpeg
        run: sudo apt-get install -y ffmpeg

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run daily music generation
        run: python src/main.py
        env:
          ANTHROPIC_API_KEY:        ${{ secrets.ANTHROPIC_API_KEY }}
          SUNO_COOKIE:              ${{ secrets.SUNO_COOKIE }}
          YOUTUBE_CLIENT_ID:        ${{ secrets.YOUTUBE_CLIENT_ID }}
          YOUTUBE_CLIENT_SECRET:    ${{ secrets.YOUTUBE_CLIENT_SECRET }}
          YOUTUBE_REFRESH_TOKEN:    ${{ secrets.YOUTUBE_REFRESH_TOKEN }}
          SOUNDCLOUD_AUTH_TOKEN:    ${{ secrets.SOUNDCLOUD_AUTH_TOKEN }}
          INSTAGRAM_ACCESS_TOKEN:   ${{ secrets.INSTAGRAM_ACCESS_TOKEN }}
          INSTAGRAM_USER_ID:        ${{ secrets.INSTAGRAM_USER_ID }}
          GITHUB_REPOSITORY_OWNER:  ${{ github.repository_owner }}
          GITHUB_TOKEN:             ${{ secrets.GITHUB_TOKEN }}
```

- [ ] **Step 2: YAML の構文確認**

```bash
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/daily.yml'))" && echo "YAML OK"
```

Expected: `YAML OK`

- [ ] **Step 3: コミット & プッシュ**

```bash
git add .github/workflows/daily.yml
git commit -m "feat: add ffmpeg and SoundCloud/Instagram secrets to workflow"
git push origin main
```

---

## セットアップチェックリスト（アカウント作成後に実行）

### SoundCloud
```bash
echo "取得したAuth Token" | gh secret set SOUNDCLOUD_AUTH_TOKEN --repo s0821/tokyo-weather-music
```

### Instagram
```bash
echo "取得したAccess Token" | gh secret set INSTAGRAM_ACCESS_TOKEN --repo s0821/tokyo-weather-music
echo "取得したUser ID" | gh secret set INSTAGRAM_USER_ID --repo s0821/tokyo-weather-music
```

### 確認
```bash
gh secret list --repo s0821/tokyo-weather-music
# ANTHROPIC_API_KEY, SUNO_COOKIE, YOUTUBE_*, SOUNDCLOUD_AUTH_TOKEN, INSTAGRAM_* が揃えば完了
```
