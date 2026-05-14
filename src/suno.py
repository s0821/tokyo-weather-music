import os
import time
import requests

SUNO_BASE = "https://studio-api.suno.ai"
DEFAULT_OUTPUT = "/tmp/suno_output.mp3"


def _get_jwt(cookie):
    resp = requests.get(
        "{}/api/auth/session".format(SUNO_BASE),
        headers={"Cookie": cookie},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()["session"]["sunoToken"]


def _poll_until_complete(clip_id, jwt, max_polls=40, interval=30):
    headers = {"Authorization": "Bearer {}".format(jwt)}
    for _ in range(max_polls):
        resp = requests.get(
            "{}/api/feed/?ids={}".format(SUNO_BASE, clip_id),
            headers=headers,
            timeout=15,
        )
        resp.raise_for_status()
        clip = resp.json()["clips"][0]
        if clip["status"] == "complete" and clip.get("audio_url"):
            return clip["audio_url"]
        time.sleep(interval)
    raise RuntimeError("タイムアウト: clip_id={} が{}回のポーリングで完了しなかった".format(clip_id, max_polls))


def generate_music(suno_prompt, output_path=DEFAULT_OUTPUT, max_retries=3):
    cookie = os.environ.get("SUNO_COOKIE", "")
    last_error = None

    for attempt in range(max_retries):
        try:
            jwt = _get_jwt(cookie)
            headers = {
                "Authorization": "Bearer {}".format(jwt),
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
                "{}/api/generate/v2/".format(SUNO_BASE),
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
            print("[suno] 試行 {} 失敗: {}".format(attempt + 1, e))

    raise RuntimeError("SUNO音楽生成失敗（{}回試行）: {}".format(max_retries, last_error))
