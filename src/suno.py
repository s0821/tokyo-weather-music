import os
import time
import requests

# 新しいSUNO APIは auth.suno.com ベースの JWT を直接使用
SUNO_BASE = "https://studio-api.suno.ai"
DEFAULT_OUTPUT = "/tmp/suno_output.mp3"


def _extract_jwt(cookie_str):
    """SUNO_COOKIE から JWT 値を取り出す。
    形式: "__session=eyJ..." → "eyJ..." を返す
    """
    for part in cookie_str.split(";"):
        part = part.strip()
        if part.startswith("__session="):
            return part[len("__session="):]
    # フォールバック: 値全体を返す（旧形式のトークン文字列の場合）
    return cookie_str.strip()


def _poll_until_complete(clip_id, jwt, max_polls=40, interval=30):
    headers = {"Authorization": "Bearer {}".format(jwt)}
    for _ in range(max_polls):
        resp = requests.get(
            "{}/api/feed/?ids={}".format(SUNO_BASE, clip_id),
            headers=headers,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        # 新APIは clips リストまたは直接オブジェクトを返す場合がある
        clips = data.get("clips") or data.get("data") or [data]
        if clips:
            clip = clips[0]
            if clip.get("status") == "complete" and clip.get("audio_url"):
                return clip["audio_url"]
        time.sleep(interval)
    raise RuntimeError("タイムアウト: clip_id={} が{}回のポーリングで完了しなかった".format(clip_id, max_polls))


def generate_music(suno_prompt, output_path=DEFAULT_OUTPUT, max_retries=3):
    cookie_str = os.environ.get("SUNO_COOKIE", "")
    jwt = _extract_jwt(cookie_str)
    last_error = None

    for attempt in range(max_retries):
        try:
            headers = {
                "Authorization": "Bearer {}".format(jwt),
                "Content-Type": "application/json",
            }
            payload = {
                "prompt": suno_prompt,
                "mv": "chirp-v4-5",  # 最新モデル
                "title": "",
                "tags": "instrumental ambient lofi",
                "make_instrumental": True,
                "generation_type": "TEXT",
            }
            gen_resp = requests.post(
                "{}/api/generate/v2/".format(SUNO_BASE),
                json=payload,
                headers=headers,
                timeout=30,
            )
            gen_resp.raise_for_status()
            resp_data = gen_resp.json()
            clips = resp_data.get("clips") or resp_data.get("data") or [resp_data]
            clip_id = clips[0]["id"]

            audio_url = _poll_until_complete(clip_id, jwt)

            dl_resp = requests.get(audio_url, timeout=60)
            dl_resp.raise_for_status()
            with open(output_path, "wb") as f:
                f.write(dl_resp.content)
            print("[suno] 音楽生成完了: {}".format(output_path))
            return output_path

        except Exception as e:
            last_error = e
            print("[suno] 試行 {} 失敗: {}".format(attempt + 1, e))

    raise RuntimeError("SUNO音楽生成失敗（{}回試行）: {}".format(max_retries, last_error))
