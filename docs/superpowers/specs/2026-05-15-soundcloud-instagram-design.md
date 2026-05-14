# SoundCloud & Instagram Reels 追加配信 — 設計ドキュメント

**作成日:** 2026-05-15
**ステータス:** 承認済み

---

## 概要

既存のTokyo Weather Musicシステム（YouTube・Spotify配信済み）に、SoundCloudとInstagram Reelsへの全自動配信を追加する。毎朝6:00 JSTのGitHub Actions実行時に、既存フローと並行して両プラットフォームへ投稿する。

---

## 追加するモジュール

### src/soundcloud.py

**役割:** SoundCloud APIで生成したmp3をアップロードする。

**処理フロー:**
1. SoundCloud OAuth2トークンで認証
2. `POST https://api.soundcloud.com/tracks` でmp3アップロード
3. タイトル・説明文・タグを設定（prompt.pyの出力を流用）
4. 公開設定: public

**出力:** SoundCloudのtrack URL

**認証情報:**
- `SOUNDCLOUD_CLIENT_ID` — OAuth2 Client ID
- `SOUNDCLOUD_CLIENT_SECRET` — OAuth2 Client Secret
- `SOUNDCLOUD_AUTH_TOKEN` — OAuth2 Access Token（長期トークン）

---

### src/instagram.py

**役割:** mp3+サムネイル画像をmp4動画に変換し、Instagram Reelsとして投稿する。

**処理フロー:**
1. ffmpegでmp3 + サムネイルPNG → mp4（縦型 1080×1920px、30秒ループ）
2. Meta Graph APIで動画をアップロード（Container作成）
3. Containerが処理完了するまでポーリング
4. 公開リクエストで投稿確定

**出力:** InstagramのメディアID

**認証情報:**
- `INSTAGRAM_ACCESS_TOKEN` — Meta Graph API Long-lived Token
- `INSTAGRAM_USER_ID` — Instagram Business Account の User ID
- `FACEBOOK_PAGE_ID` — リンクするFacebookページのID

**前提条件:**
- Instagram Business/Creator アカウント
- Facebookページにリンク済み
- Meta Developer App で Instagram Graph API 有効化済み

---

## 動画変換仕様（Instagram Reels）

```
入力: mp3ファイル + サムネイルPNG（1280×720）
出力: mp4（縦型 1080×1920px）
設定:
  - 画像をpillow でリサイズ（上下黒帯または縦型構図）
  - 音声: aac 192kbps
  - 映像: h264 静止画ループ
  - 時間: 60秒（mp3が60秒未満の場合はそのまま）
ツール: ffmpeg（GitHub Actions ubuntu-latestで apt-get install ffmpeg）
```

---

## 更新するファイル

| ファイル | 変更内容 |
|---|---|
| `src/soundcloud.py` | 新規作成 |
| `src/instagram.py` | 新規作成 |
| `src/main.py` | soundcloud / instagram 呼び出しを追加 |
| `.github/workflows/daily.yml` | ffmpegインストール・新Secrets追加 |
| `requirements.txt` | 追加依存なし（requestsのみ使用） |

---

## GitHub Secrets 追加一覧

| Secret名 | 内容 |
|---|---|
| `SOUNDCLOUD_CLIENT_ID` | SoundCloud OAuth2 Client ID |
| `SOUNDCLOUD_CLIENT_SECRET` | SoundCloud OAuth2 Client Secret |
| `SOUNDCLOUD_AUTH_TOKEN` | SoundCloud OAuth2 Access Token |
| `INSTAGRAM_ACCESS_TOKEN` | Meta Graph API Long-lived Token |
| `INSTAGRAM_USER_ID` | Instagram Business User ID |
| `FACEBOOK_PAGE_ID` | Facebook Page ID |

---

## エラーハンドリング

| モジュール | 失敗時の挙動 |
|---|---|
| soundcloud.py | 3回リトライ → GitHub Issue通知、他プラットフォームは続行 |
| instagram.py | 3回リトライ → GitHub Issue通知、他プラットフォームは続行 |

---

## 実装フェーズ

1. SoundCloudアカウント作成・API認証情報取得 → GitHub Secrets登録
2. soundcloud.py実装・テスト
3. Instagramアカウント作成・Business化・Meta App作成 → GitHub Secrets登録
4. instagram.py実装・テスト
5. main.py・daily.yml更新
6. 全体テスト
