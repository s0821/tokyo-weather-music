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
    mock_service.videos.return_value.insert.return_value.execute.return_value = {"id": "VIDEO_ID_123"}
    mock_service.thumbnails.return_value.set.return_value.execute.return_value = {}

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
    mock_service.videos.return_value.insert.assert_called_once()


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
