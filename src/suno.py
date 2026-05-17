import os
import time
import subprocess
import tempfile
import requests

HF_API_URL = "https://api-inference.huggingface.co/models/facebook/musicgen-small"
DEFAULT_OUTPUT = "/tmp/suno_output.mp3"
SEGMENT_SECONDS = 30
NUM_SEGMENTS = 6  # 30s x 6 = 3 minutes


def _hf_headers():
    token = os.environ.get("HF_API_TOKEN", "")
    return {"Authorization": "Bearer {}".format(token)}


def _generate_segment(prompt, max_retries=5):
    for attempt in range(max_retries):
        resp = requests.post(
            HF_API_URL,
            headers=_hf_headers(),
            json={
                "inputs": prompt,
                "parameters": {"max_new_tokens": 1500},  # ~30秒
            },
            timeout=120,
        )

        if resp.status_code == 200:
            return resp.content

        if resp.status_code == 503:
            wait = min(30 * (attempt + 1), 120)
            print("[suno] モデル読み込み中、{}秒待機...".format(wait))
            time.sleep(wait)
            continue

        resp.raise_for_status()

    raise RuntimeError("HFセグメント生成失敗（{}回試行）".format(max_retries))


def generate_music(suno_prompt, output_path=DEFAULT_OUTPUT, max_retries=3):
    last_error = None
    for attempt in range(max_retries):
        try:
            segment_files = []
            for i in range(NUM_SEGMENTS):
                print("[suno] セグメント {}/{} 生成中...".format(i + 1, NUM_SEGMENTS))
                audio_bytes = _generate_segment(suno_prompt)
                tmp = tempfile.mktemp(suffix=".flac")
                with open(tmp, "wb") as f:
                    f.write(audio_bytes)
                segment_files.append(tmp)

            # ffmpegで結合してmp3に変換
            concat_list = tempfile.mktemp(suffix=".txt")
            with open(concat_list, "w") as f:
                for seg in segment_files:
                    f.write("file '{}'\n".format(seg))

            subprocess.run(
                [
                    "ffmpeg", "-y",
                    "-f", "concat", "-safe", "0",
                    "-i", concat_list,
                    "-c:a", "libmp3lame", "-q:a", "2",
                    output_path,
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            print("[suno] 音楽生成完了: {}".format(output_path))
            return output_path

        except Exception as e:
            last_error = e
            print("[suno] 試行 {} 失敗: {}".format(attempt + 1, e))
            if attempt < max_retries - 1:
                time.sleep(10)

    raise RuntimeError("音楽生成失敗（{}回試行）: {}".format(max_retries, last_error))
