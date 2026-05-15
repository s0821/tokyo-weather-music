import os
import subprocess
from datetime import datetime, timezone, timedelta

from src.weather import get_weather
from src.prompt import generate_prompt
from src.suno import generate_music
from src.thumbnail import create_thumbnail
from src.youtube import upload_to_youtube

JST = timezone(timedelta(hours=9))


def _notify_failure(module, error):
    print("[main] 致命的エラー: {} — {}".format(module, error))
    if os.environ.get("GITHUB_ACTIONS"):
        title = "Tokyo Weather Music 失敗: {}".format(module)
        body = "モジュール: {}\nエラー: {}".format(module, error)
        subprocess.run(
            ["gh", "issue", "create", "--title", title, "--body", body],
            check=False,
        )


def run():
    now_jst = datetime.now(JST)
    today = now_jst.strftime("%Y-%m-%d")
    timestamp = now_jst.strftime("%Y-%m-%d_%H%M")

    # 1. 天気取得
    try:
        weather = get_weather(date=today)
        print("[main] 天気取得完了: {} {}℃".format(weather["weather_label"], weather["temperature"]))
    except RuntimeError as e:
        _notify_failure("weather", e)
        return

    # 2. プロンプト生成（フォールバックありなので例外なし）
    prompt_data = generate_prompt(weather)
    print("[main] プロンプト生成完了: {}".format(prompt_data["title_ja"]))

    # 3. SUNO音楽生成
    audio_path = "/tmp/tokyo_music_{}.mp3".format(timestamp)
    try:
        generate_music(prompt_data["suno_prompt"], output_path=audio_path)
        print("[main] 音楽生成完了: {}".format(audio_path))
    except RuntimeError as e:
        print("[main] 音楽生成失敗、本日はスキップ: {}".format(e))
        return

    # 4. サムネイル生成（失敗してもデフォルト画像で続行）
    thumb_path = "/tmp/thumbnail_{}.png".format(timestamp)
    thumbnail = create_thumbnail(
        title_ja=prompt_data["title_ja"],
        title_en=prompt_data["title_en"],
        date=today,
        season=weather["season"],
        weather_label=weather["weather_label"],
        output_path=thumb_path,
    )
    print("[main] サムネイル生成完了: {}".format(thumbnail))

    # 5. YouTubeアップロード
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
        print("[main] YouTube投稿完了: https://youtu.be/{}".format(video_id))
    except RuntimeError as e:
        _notify_failure("youtube", e)

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


if __name__ == "__main__":
    run()
