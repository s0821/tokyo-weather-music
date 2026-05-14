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
    audio_path,
    thumbnail_path,
    title_ja,
    title_en,
    description,
    date,
    season,
    max_retries=3,
):
    service = _build_service()
    title = "{} | Tokyo Weather Music {}".format(title_ja, date)
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

            print("[youtube] アップロード完了: https://youtu.be/{}".format(video_id))
            return video_id

        except Exception as e:
            last_error = e
            print("[youtube] 試行 {} 失敗: {}".format(attempt + 1, e))

    raise RuntimeError("YouTubeアップロード失敗（{}回試行）: {}".format(max_retries, last_error))
