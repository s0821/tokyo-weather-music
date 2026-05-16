import os
import shutil
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from pathlib import Path

DOCS_DIR = os.path.join(os.path.dirname(__file__), "../docs")
DEFAULT_FEED = os.path.join(DOCS_DIR, "feed.xml")
DEFAULT_EPISODES_DIR = os.path.join(DOCS_DIR, "episodes")
JST = timezone(timedelta(hours=9))


def _git_commit_push(timestamp):
    subprocess.run(["git", "config", "user.email", "action@github.com"], check=True)
    subprocess.run(["git", "config", "user.name", "GitHub Actions"], check=True)
    subprocess.run(["git", "pull", "--rebase", "origin", "main"], check=True)
    subprocess.run(["git", "add", "docs/"], check=True)
    result = subprocess.run(
        ["git", "commit", "-m", "podcast: add episode {}".format(timestamp)],
        capture_output=True,
    )
    if result.returncode != 0 and b"nothing to commit" in result.stdout + result.stderr:
        return
    result.check_returncode()
    subprocess.run(["git", "push"], check=True)


def _add_episode_to_feed(
    feed_path,
    title,
    description,
    mp3_url,
    file_size,
    pub_date,
    guid,
):
    ET.register_namespace("itunes", "http://www.itunes.com/dtds/podcast-1.0.dtd")
    tree = ET.parse(feed_path)
    channel = tree.find("channel")

    item = ET.Element("item")
    ET.SubElement(item, "title").text = title
    ET.SubElement(item, "description").text = description
    enclosure = ET.SubElement(item, "enclosure")
    enclosure.set("url", mp3_url)
    enclosure.set("type", "audio/mpeg")
    enclosure.set("length", str(file_size))
    ET.SubElement(item, "pubDate").text = pub_date
    ET.SubElement(item, "guid").text = guid

    # 最新エピソードを先頭に挿入
    first_item_idx = None
    for i, child in enumerate(channel):
        if child.tag == "item":
            first_item_idx = i
            break
    if first_item_idx is not None:
        channel.insert(first_item_idx, item)
    else:
        channel.append(item)

    tree.write(feed_path, encoding="utf-8", xml_declaration=True)


def update_feed(
    audio_path,
    title_ja,
    description,
    date,
    feed_path=DEFAULT_FEED,
    episodes_dir=DEFAULT_EPISODES_DIR,
    base_url=None,
    max_retries=3,
):
    owner = os.environ.get("GITHUB_REPOSITORY_OWNER", "owner")
    if base_url is None:
        base_url = "https://{}.github.io/tokyo-weather-music".format(owner)

    now_jst = datetime.now(JST)
    timestamp = now_jst.strftime("%Y-%m-%d_%H%M")
    dest = os.path.join(episodes_dir, "{}.mp3".format(timestamp))
    shutil.copy2(audio_path, dest)

    mp3_url = "{}/episodes/{}.mp3".format(base_url, timestamp)
    file_size = Path(dest).stat().st_size
    pub_date = now_jst.strftime("%a, %d %b %Y %H:%M:%S +0900")

    _add_episode_to_feed(
        feed_path=feed_path,
        title=title_ja,
        description=description,
        mp3_url=mp3_url,
        file_size=file_size,
        pub_date=pub_date,
        guid=timestamp,
    )

    last_error = None
    for attempt in range(max_retries):
        try:
            _git_commit_push(timestamp)
            print("[podcast] RSS更新・push完了: {}".format(mp3_url))
            return
        except subprocess.CalledProcessError as e:
            last_error = e
            print("[podcast] git push 試行 {} 失敗: {}".format(attempt + 1, e))

    raise RuntimeError("podcast git push失敗（{}回試行）: {}".format(max_retries, last_error))
