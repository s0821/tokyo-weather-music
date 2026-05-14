import requests
from datetime import date as date_type

TOKYO_LAT = 35.6895
TOKYO_LON = 139.6917

WMO_LABELS = {
    0: "快晴", 1: "晴れ", 2: "一部曇り", 3: "曇り",
    45: "霧", 48: "着氷霧",
    51: "霧雨（弱）", 53: "霧雨", 55: "霧雨（強）",
    61: "小雨", 63: "雨", 65: "大雨",
    71: "小雪", 73: "雪", 75: "大雪",
    80: "にわか雨（弱）", 81: "にわか雨", 82: "にわか雨（強）",
    95: "雷雨", 96: "雷雨（ひょう）", 99: "雷雨（大ひょう）",
}


def detect_season(month: int) -> str:
    if month in (3, 4, 5):
        return "春"
    if month in (6, 7, 8):
        return "夏"
    if month in (9, 10, 11):
        return "秋"
    return "冬"


def get_weather(date: str = None, max_retries: int = 3) -> dict:
    today = date or str(date_type.today())
    month = int(today.split("-")[1])

    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": TOKYO_LAT,
        "longitude": TOKYO_LON,
        "current": [
            "weathercode",
            "temperature_2m",
            "apparent_temperature",
            "relativehumidity_2m",
            "windspeed_10m",
            "precipitation",
        ],
        "timezone": "Asia/Tokyo",
    }

    last_error = None
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, params=params, timeout=10)
            resp.raise_for_status()
            current = resp.json()["current"]
            code = current["weathercode"]
            return {
                "weather_label": WMO_LABELS.get(code, f"天気コード{code}"),
                "temperature": current["temperature_2m"],
                "feels_like": current["apparent_temperature"],
                "humidity": current["relativehumidity_2m"],
                "wind_speed": current["windspeed_10m"],
                "precipitation": current["precipitation"],
                "season": detect_season(month),
                "date": today,
            }
        except Exception as e:
            last_error = e

    raise RuntimeError(f"天気取得失敗（{max_retries}回試行）: {last_error}")
