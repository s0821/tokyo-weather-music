# Tokyo Weather Music

東京の毎日の天候データをもとにSUNO AIでインストゥルメンタル音楽を自動生成し、YouTubeとSpotify（ポッドキャスト）へ毎日自動配信するシステム。

## セットアップ

### 必要なGitHub Secrets

| Secret名 | 取得方法 |
|---|---|
| `ANTHROPIC_API_KEY` | [console.anthropic.com](https://console.anthropic.com) → API Keys |
| `SUNO_COOKIE` | suno.comにログイン → DevTools → Application → Cookies → `__Secure-next-auth.session-token` の値 |
| `YOUTUBE_CLIENT_ID` | Google Cloud Console → APIとサービス → 認証情報 → OAuth 2.0クライアントID |
| `YOUTUBE_CLIENT_SECRET` | 同上 |
| `YOUTUBE_REFRESH_TOKEN` | 下記スクリプトで取得 |

### YouTube OAuth2 Refresh Token の取得（1回のみ）

```python
from google_auth_oauthlib.flow import InstalledAppFlow

flow = InstalledAppFlow.from_client_config(
    {
        "installed": {
            "client_id": "YOUR_CLIENT_ID",
            "client_secret": "YOUR_CLIENT_SECRET",
            "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    },
    scopes=["https://www.googleapis.com/auth/youtube.upload"],
)
creds = flow.run_local_server(port=0)
print("REFRESH_TOKEN:", creds.refresh_token)
```

### SUNO Cookie の定期更新

SUNO のセッションCookieは数週間〜数ヶ月で失効します。失効すると GitHub Issue で通知されます。

1. suno.com にログイン
2. DevTools → Application → Cookies → `__Secure-next-auth.session-token` の値をコピー
3. GitHub Secrets の `SUNO_COOKIE` を更新

## Spotify配信（Phase 2）

Phase 2ではpodcast.pyが自動的にRSSフィードを更新し、Spotifyへ配信します。
初回のみ [Spotify for Podcasters](https://podcasters.spotify.com) でRSSフィードを登録してください。

## アーキテクチャ

```
天気取得（Open-Meteo）→ プロンプト生成（Claude API）→ 音楽生成（SUNO）
→ サムネイル生成（Pillow）→ YouTube投稿 / Spotify RSS更新
```
