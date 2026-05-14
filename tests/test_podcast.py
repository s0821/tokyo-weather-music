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
            feed_path=str(feed_path), title="Test {}".format(guid), description="",
            mp3_url="https://example.github.io/episodes/{}.mp3".format(guid),
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
