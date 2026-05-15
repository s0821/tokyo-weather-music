import os
import time
import requests

REPLICATE_API = "https://api.replicate.com/v1"
# Meta MusicGen latest version (2024)
MUSICGEN_VERSION = "671ac645ce5e552cc63a54a2bbff63fcf798043055d2dac5fc9e36a837eedcfb"
DEFAULT_OUTPUT = "/tmp/suno_output.mp3"


def _start_prediction(prompt, duration=60):
    token = os.environ["REPLICATE_API_TOKEN"]
    resp = requests.post(
        "{}/predictions".format(REPLICATE_API),
        headers={
            "Authorization": "Token {}".format(token),
            "Content-Type": "application/json",
        },
        json={
            "version": MUSICGEN_VERSION,
            "input": {
                "prompt": prompt,
                "model_version": "large",
                "output_format": "mp3",
                "normalization_strategy": "peak",
                "duration": duration,
            },
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["id"]


def _poll_prediction(prediction_id, max_polls=40, interval=15):
    token = os.environ["REPLICATE_API_TOKEN"]
    headers = {"Authorization": "Token {}".format(token)}
    for _ in range(max_polls):
        resp = requests.get(
            "{}/predictions/{}".format(REPLICATE_API, prediction_id),
            headers=headers,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        status = data.get("status")
        if status == "succeeded":
            output = data.get("output")
            if isinstance(output, list):
                return output[0]
            return output
        if status in ("failed", "canceled"):
            raise RuntimeError("MusicGen失敗: {}".format(data.get("error", status)))
        time.sleep(interval)
    raise RuntimeError("タイムアウト: prediction_id={}".format(prediction_id))


def generate_music(suno_prompt, output_path=DEFAULT_OUTPUT, max_retries=3):
    last_error = None
    for attempt in range(max_retries):
        try:
            prediction_id = _start_prediction(suno_prompt)
            print("[suno] MusicGen生成開始: id={}".format(prediction_id))

            audio_url = _poll_prediction(prediction_id)

            dl_resp = requests.get(audio_url, timeout=120)
            dl_resp.raise_for_status()
            with open(output_path, "wb") as f:
                f.write(dl_resp.content)
            print("[suno] 音楽生成完了: {}".format(output_path))
            return output_path

        except Exception as e:
            last_error = e
            print("[suno] 試行 {} 失敗: {}".format(attempt + 1, e))
            if attempt < max_retries - 1:
                time.sleep(10)

    raise RuntimeError("SUNO音楽生成失敗（{}回試行）: {}".format(max_retries, last_error))
