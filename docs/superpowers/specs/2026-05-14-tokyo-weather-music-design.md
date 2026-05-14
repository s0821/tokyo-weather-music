# Tokyo Weather Music — 設計ドキュメント

**作成日:** 2026-05-14  
**ステータス:** 承認済み

---

## 概要

東京の毎日の天候データをもとにSUNOでインストゥルメンタル音楽を自動生成し、YouTubeへ動画アップロード・Spotifyへポッドキャストとして配信するシステム。GitHub Actionsで毎朝6時（JST）に完全自動実行する。

---

## 外部サービスと費用

| サービス | 用途 | 費用 |
|---|---|---|
| Open-Meteo API | 東京天気取得 | 無料 |
| Anthropic Claude API (claude-sonnet-4-6) | プロンプト生成 | 従量課金（1日数円） |
| SUNO Pro | 音楽生成 | $8/月 |
| YouTube Data API v3 | 動画アップロード | 無料（クォータ制） |
| GitHub Actions | スケジューラー | 無料枠内 |
| GitHub Pages | mp3ホスティング（Spotify用RSS） | 無料 |
| Spotify for Podcasters | RSSフィード登録（初回1回のみ手動） | 無料 |

---

## アーキテクチャ

### 全体フロー

```
[GitHub Actions / 毎朝6:00 JST (UTC 21:00)]
        │
        ▼
  1. weather.py      東京の気象データ取得（Open-Meteo）
        │
        ▼
  2. prompt.py       Claude APIで気象×季節を解釈しプロンプト生成
        │
        ▼
  3. suno.py         非公式suno-apiで音楽生成・mp3ダウンロード
        │
        ▼
  4. thumbnail.py    天候×季節に合ったサムネイル画像生成（Pillow）
        │
        ├─────────────────────────────────┐
        ▼                                 ▼
  5. youtube.py                     6. podcast.py
     YouTube動画アップロード           mp3をGitHub Pagesに保存
                                       feed.xmlを自動更新
                                             │
                                             ▼
                                   Spotifyが自動取得（数時間以内）
```

### ディレクトリ構成

```
tokyo-weather-music/
├── .github/
│   └── workflows/
│       └── daily.yml             # スケジューラー（毎朝6:00 JST）
├── src/
│   ├── main.py                   # 全モジュールを順番に呼ぶオーケストレーター
│   ├── weather.py                # 気象データ取得
│   ├── prompt.py                 # Claude APIプロンプト生成
│   ├── suno.py                   # SUNO音楽生成・ダウンロード
│   ├── thumbnail.py              # サムネイル画像生成
│   ├── youtube.py                # YouTube動画アップロード
│   └── podcast.py                # RSS feed更新・GitHub Pages配信
├── docs/
│   ├── episodes/                 # 生成されたmp3ファイル（GitHub Pages経由で公開）
│   └── feed.xml                  # Spotify用RSSフィード（自動更新）
├── assets/
│   └── fonts/                    # サムネイル用日本語フォント
├── tests/
│   ├── test_weather.py
│   ├── test_prompt.py
│   └── test_thumbnail.py
└── requirements.txt
```

---

## モジュール詳細

### 1. weather.py

**役割:** Open-Meteo API（無料）から東京の気象データを取得し、季節情報を付加する。

**取得データ:**
- 天気コード（WMO Weather Code） → 晴れ/曇り/雨/雪等に変換
- 気温（℃）・体感温度（℃）
- 湿度（%）
- 風速（m/s）
- 降水量（mm）

**季節判定:** 月日から自動判定
- 春: 3〜5月
- 夏: 6〜8月
- 秋: 9〜11月
- 冬: 12〜2月

**出力（dict）:**
```json
{
  "weather_label": "小雨",
  "temperature": 18.2,
  "feels_like": 16.5,
  "humidity": 78,
  "wind_speed": 3.2,
  "precipitation": 1.4,
  "season": "春",
  "date": "2026-05-14"
}
```

---

### 2. prompt.py

**役割:** Claude API（claude-sonnet-4-6）で気象データ＋季節を解釈し、SUNOプロンプト・曲タイトル・YouTube/Spotify説明文をJSON形式で生成する。

**Claude APIへのシステムプロンプト:**
```
あなたは音楽プロデューサーです。東京の今日の天気と季節をもとに、
SUNO AIで生成するインストゥルメンタル音楽のプロンプト、
曲タイトル（日本語・英語）、配信用説明文を作成してください。

ジャンルは ambient / lo-fi / Japanese instrumental の範囲で、
天候と季節の情感を豊かに反映させてください。

出力はJSON形式のみ。他のテキストは不要。
```

**出力（JSON）:**
```json
{
  "suno_prompt": "Gentle spring rain in Tokyo, soft piano with ambient strings, melancholic yet hopeful, lo-fi instrumental, 90 BPM",
  "title_ja": "春雨の東京 — 静かな朝",
  "title_en": "Spring Rain in Tokyo — A Quiet Morning",
  "description": "今日の東京は春の小雨。18℃の穏やかな朝に、しっとりとした旋律をお届けします。\n\n#東京 #天気 #インストゥルメンタル #ambient #lofi"
}
```

**フォールバック:** Claude API失敗時は天候ラベルと季節から定義済みテンプレートを使用。

---

### 3. suno.py

**役割:** 非公式ライブラリ（[gcui-art/suno-api](https://github.com/gcui-art/suno-api)）経由でSUNO Proアカウントから音楽を生成し、mp3をダウンロードする。

**処理フロー:**
1. SUNOセッションCookieで認証（GitHub Secretsから取得）
2. `suno_prompt` を送信して生成リクエスト
3. ポーリング（30秒間隔 × 最大20回）で完了確認
4. 完了後mp3をダウンロードし `/tmp/output.mp3` に保存

**注意事項:**
- SUNOのCookieは定期的に（数週間〜数ヶ月）失効するため、更新が必要
- 将来的にSUNO Enterprise API（正式版）が利用可能になれば、このモジュールのみ差し替えで対応可能な設計

---

### 4. thumbnail.py

**役割:** Pillowで1280×720pxのサムネイル画像を生成する。

**デザイン仕様:**
- 背景色：天候×季節のパレットから自動選択
  - 春×晴れ: パステルピンク〜薄緑
  - 夏×晴れ: 鮮やかな青〜黄橙
  - 秋×曇り: 深いオレンジ〜茶
  - 冬×雪: 青白〜白
  - 雨（季節問わず）: グレー〜深青
- テキスト（中央配置）: 曲タイトル日本語・英語・日付・「Tokyo Weather Music」

**フォールバック:** Pillow失敗時はデフォルト画像（assets/default_thumbnail.png）を使用し、処理を続行。

---

### 5. youtube.py

**役割:** YouTube Data API v3でmp3＋サムネイルを動画としてアップロードする。

**アップロード設定:**
- カテゴリ: Music (10)
- 公開設定: public
- タグ: `["Tokyo", "東京", "instrumental", "ambient", "lofi", "weather", "天気", 季節名]`
- タイトル: `{title_ja} | Tokyo Weather Music {YYYY-MM-DD}`
- 説明文: Claude生成テキスト＋気象データサマリ

**認証:** OAuth2（Client ID / Client Secret / Refresh Token をGitHub Secretsで管理）。Refresh Tokenは失効しないlong-lived tokenを使用。

---

### 6. podcast.py

**役割:** SpotifyポッドキャストとしてRSSフィード経由で自動配信する。

**処理フロー:**
1. mp3を `docs/episodes/YYYY-MM-DD.mp3` にコピー
2. `docs/feed.xml`（RSS 2.0）に新エピソードを追記
3. 変更をgit commit＆push → GitHub Pagesが自動でホスティング
4. Spotifyが定期巡回でRSSを検出 → 数時間以内にSpotifyで聴ける

**RSS feed.xmlのエピソード要素:**
```xml
<item>
  <title>春雨の東京 — 静かな朝</title>
  <enclosure url="https://{GITHUB_REPOSITORY_OWNER}.github.io/tokyo-weather-music/episodes/2026-05-14.mp3"
             type="audio/mpeg" length="{mp3ファイルサイズ（バイト）}"/>
  <pubDate>Wed, 14 May 2026 06:00:00 +0900</pubDate>
  <description>今日の東京は春の小雨...</description>
  <guid>2026-05-14</guid>
</item>
```

**初回セットアップ（1回のみ手動）:**
1. GitHubリポジトリでGitHub Pages（`docs/`フォルダ）を有効化
2. Spotify for Podcasters でRSSフィードURL（`https://{GITHUB_REPOSITORY_OWNER}.github.io/tokyo-weather-music/feed.xml`）を登録（`GITHUB_REPOSITORY_OWNER` は実際のGitHubユーザー名）

---

## GitHub Actions設定

```yaml
# .github/workflows/daily.yml
name: Daily Tokyo Weather Music
on:
  schedule:
    - cron: '0 21 * * *'   # UTC 21:00 = JST 06:00
  workflow_dispatch:         # 手動トリガーも可能

jobs:
  generate-and-upload:
    runs-on: ubuntu-latest
    permissions:
      contents: write        # podcast.pyのgit push用
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install -r requirements.txt
      - run: python src/main.py
        env:
          ANTHROPIC_API_KEY:      ${{ secrets.ANTHROPIC_API_KEY }}
          SUNO_COOKIE:            ${{ secrets.SUNO_COOKIE }}
          YOUTUBE_CLIENT_ID:      ${{ secrets.YOUTUBE_CLIENT_ID }}
          YOUTUBE_CLIENT_SECRET:  ${{ secrets.YOUTUBE_CLIENT_SECRET }}
          YOUTUBE_REFRESH_TOKEN:  ${{ secrets.YOUTUBE_REFRESH_TOKEN }}
```

**GitHub Secrets一覧:**

| Secret名 | 内容 | 更新頻度 |
|---|---|---|
| `ANTHROPIC_API_KEY` | Claude API キー | 不要（失効なし） |
| `SUNO_COOKIE` | SUNOセッションCookie | 数週間〜数ヶ月ごと |
| `YOUTUBE_CLIENT_ID` | YouTube OAuth2 クライアントID | 不要 |
| `YOUTUBE_CLIENT_SECRET` | YouTube OAuth2 クライアントシークレット | 不要 |
| `YOUTUBE_REFRESH_TOKEN` | YouTube OAuth2 リフレッシュトークン | 不要（long-lived） |

---

## エラーハンドリング

### 失敗時の挙動マトリクス

| モジュール | 失敗時の挙動 |
|---|---|
| weather.py | 3回リトライ → 失敗なら当日処理を中止 |
| prompt.py | 3回リトライ → 失敗ならテンプレートフォールバックで続行 |
| suno.py | 3回リトライ → 失敗なら当日スキップ（翌日に続く） |
| thumbnail.py | デフォルト画像で続行（致命的エラーにしない） |
| youtube.py | 3回リトライ → 失敗ならGitHub Issue通知 |
| podcast.py | 3回リトライ → 失敗ならGitHub Issue通知 |

### 通知
致命的失敗時はGitHub Actions経由でGitHub Issueを自動作成し、失敗モジュール名とエラー内容を記録する。

---

## 実装フェーズ

### Phase 1（初期リリース）
- weather.py, prompt.py, suno.py, thumbnail.py, youtube.py, main.py
- GitHub Actions daily.yml
- YouTube自動投稿の完全自動化

### Phase 2（Spotify対応）
- podcast.py
- GitHub Pages設定
- feed.xml初期生成
- Spotify for Podcastersへのフィード登録（手順書作成）

---

## 制約・注意事項

- **SUNO非公式API:** SUNOの利用規約上グレーゾーン。Enterprise API（正式版）が公開された際にはsuno.pyのみ差し替えで対応可能な設計としている。
- **SUNO Cookie失効:** 定期的な手動更新が必要。失効検知時はGitHub Issue通知で対応。
- **YouTubeクォータ:** YouTube Data API v3の無料クォータ（1日10,000ユニット）内で動作。動画アップロードは1,600ユニット消費のため、1日1本は問題なし。
- **Spotifyポッドキャスト:** 「音楽」ではなく「ポッドキャスト」セクションに表示される。Spotify Musicのライブラリには入らない。
