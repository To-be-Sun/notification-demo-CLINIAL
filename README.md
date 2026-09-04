# note Slack notifier

note の RSS を監視し、新着投稿を Slack の指定チャンネルに通知する GitHub Actions 用の小さな通知処理です。

対象 RSS:

```text
https://note.com/clinial/rss
```

## 仕組み

- GitHub Actions が定期実行されます。
- `scripts/notify_note_to_slack.py` が note RSS を取得します。
- `state/notified.json` に記録済みの記事は再通知しません。
- 新着があれば Slack Incoming Webhook に投稿します。
- 通知後、`state/notified.json` を自動更新してリポジトリへ commit します。

## GitHub 側の設定

リポジトリの Settings > Secrets and variables > Actions で、以下を登録してください。

| 種別 | 名前 | 内容 |
|---|---|---|
| Secret | `SLACK_WEBHOOK_URL` | Slack Incoming Webhook URL |
| Variable | `NOTE_RSS_URL` | `https://note.com/clinial/rss` |
| Variable | `NOTIFY_LOOKBACK_HOURS` | 初回・未通知記事を何時間前まで通知するか |
| Variable | `MAX_NOTIFY_ITEMS` | 1回の実行で最大何件通知するか |

`NOTE_RSS_URL`、`NOTIFY_LOOKBACK_HOURS`、`MAX_NOTIFY_ITEMS` は未設定でも動きます。

## デフォルト値

| 設定 | デフォルト |
|---|---|
| `NOTE_RSS_URL` | `https://note.com/clinial/rss` |
| `NOTIFY_LOOKBACK_HOURS` | `24` |
| `MAX_NOTIFY_ITEMS` | `5` |

## 手動実行

Actions タブから `Notify note posts to Slack` を選び、`Run workflow` で手動実行できます。

## 注意

Slack Webhook URL は Secret に保存し、コードや README に直接書かないでください。
一度チャットやドキュメントに貼った URL は漏えい扱いにして、Slack 側で再発行することを推奨します。
