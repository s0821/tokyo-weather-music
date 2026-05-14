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
