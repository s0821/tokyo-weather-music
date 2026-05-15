import json
import os
import anthropic

SYSTEM_PROMPT = """あなたはプロの音楽プロデューサーです。
東京の今日の天気と季節をもとに、SUNO AIで生成するインストゥルメンタル音楽のプロンプト、
曲タイトル（日本語・英語）、配信用説明文を作成してください。
ジャンルは ambient / lo-fi / Japanese instrumental の範囲で、
天候と季節の情感を豊かに反映させてください。
出力はJSON形式のみ。他のテキストは不要。
必ず以下のキーを含めること: suno_prompt, title_ja, title_en, description"""

FALLBACK_TEMPLATES = {
    ("春", "rain"): {
        "suno_prompt": "Gentle spring rain Tokyo, soft piano with ambient strings, melancholic hopeful, lo-fi instrumental, 85 BPM",
        "title_ja": "春雨の東京",
        "title_en": "Spring Rain in Tokyo",
        "description": "春の雨が静かに降る東京。柔らかなピアノの旋律をお届けします。\n\n#東京 #天気 #春 #ambient",
    },
    ("夏", "clear"): {
        "suno_prompt": "Bright summer morning Tokyo, upbeat acoustic guitar, warm sunshine feeling, lo-fi chill, 95 BPM",
        "title_ja": "夏の朝の東京",
        "title_en": "Summer Morning in Tokyo",
        "description": "眩しい夏の朝。爽やかなギターの音色と共に。\n\n#東京 #天気 #夏 #lofi",
    },
    ("秋", "cloud"): {
        "suno_prompt": "Quiet autumn afternoon Tokyo, contemplative piano, falling leaves feeling, ambient instrumental, 80 BPM",
        "title_ja": "秋の午後の東京",
        "title_en": "Autumn Afternoon in Tokyo",
        "description": "木の葉が揺れる秋の午後。しみじみとしたピアノ曲を。\n\n#東京 #天気 #秋 #ambient",
    },
    ("冬", "snow"): {
        "suno_prompt": "Silent winter snow Tokyo, delicate piano with bells, serene and cold, ambient instrumental, 70 BPM",
        "title_ja": "冬の雪の東京",
        "title_en": "Winter Snow in Tokyo",
        "description": "雪が降り積もる静かな冬の東京。繊細なピアノの響き。\n\n#東京 #天気 #冬 #ambient",
    },
}

DEFAULT_FALLBACK = {
    "suno_prompt": "Tokyo city ambience, peaceful instrumental, piano and strings, lo-fi chill, 85 BPM",
    "title_ja": "今日の東京",
    "title_en": "Tokyo Today",
    "description": "今日の東京の空気感を音楽で。\n\n#東京 #天気 #instrumental",
}


def _fallback_prompt(weather):
    season = weather.get("season", "")
    label = weather.get("weather_label", "")
    label_lower = label.lower()

    for (s, w_key), template in FALLBACK_TEMPLATES.items():
        if s == season and w_key in label_lower:
            t = dict(template)
            t["description"] = t["description"] + "\n気温: {}℃".format(weather.get("temperature", ""))
            return t

    for (s, _), template in FALLBACK_TEMPLATES.items():
        if s == season:
            t = dict(template)
            t["description"] = t["description"] + "\n気温: {}℃".format(weather.get("temperature", ""))
            return t

    return DEFAULT_FALLBACK


def generate_prompt(weather, max_retries=3):
    user_message = (
        "今日の東京の天気情報:\n"
        "- 天気: {}\n"
        "- 気温: {}℃（体感: {}℃）\n"
        "- 湿度: {}%\n"
        "- 風速: {}m/s\n"
        "- 降水量: {}mm\n"
        "- 季節: {}\n"
        "- 日付: {}\n"
    ).format(
        weather["weather_label"],
        weather["temperature"],
        weather["feels_like"],
        weather["humidity"],
        weather["wind_speed"],
        weather["precipitation"],
        weather["season"],
        weather["date"],
    )

    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
    last_error = None
    for _ in range(max_retries):
        try:
            message = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_message}],
            )
            text = message.content[0].text.strip()
            # マークダウンコードブロックを除去
            if text.startswith("```"):
                lines = text.splitlines()
                text = "\n".join(
                    l for l in lines
                    if not l.startswith("```")
                ).strip()
            return json.loads(text)
        except Exception as e:
            last_error = e

    print("[prompt] Claude API失敗、フォールバック使用: {}".format(last_error))
    return _fallback_prompt(weather)
