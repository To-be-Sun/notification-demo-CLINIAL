# note Slack notifier

note の RSS を監視し、新着投稿を Slack の指定チャンネルに通知する GitHub Actions 用の小さな通知処理です。

対象 RSS:

```text
https://note.com/clinial/rss
```

## 仕組み

- GitHub Actions が定期実行されます。
- Actions 自体は 5分おきに起動し、実際の監視間隔は `RUN_INTERVAL_MINUTES` で制御します。
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
| Variable | `RUN_INTERVAL_MINUTES` | 監視間隔。単位は分 |
| Variable | `NOTIFY_LOOKBACK_HOURS` | 初回・未通知記事を何時間前まで通知するか |
| Variable | `MAX_NOTIFY_ITEMS` | 1回の実行で最大何件通知するか |

各 Variable は未設定でも動きます。

## デフォルト値

| 設定 | デフォルト |
|---|---|
| `NOTE_RSS_URL` | `https://note.com/clinial/rss` |
| `RUN_INTERVAL_MINUTES` | `30` |
| `NOTIFY_LOOKBACK_HOURS` | `24` |
| `MAX_NOTIFY_ITEMS` | `5` |

## 監視間隔

GitHub Actions の `schedule.cron` は repository variables を参照できません。
そのため workflow は 5分おきに起動し、スクリプト側で `RUN_INTERVAL_MINUTES` を見て実際にRSS確認するかを判断します。

例:

| `RUN_INTERVAL_MINUTES` | 動作 |
|---|---|
| `15` | 約15分おきにRSS確認 |
| `30` | 約30分おきにRSS確認 |
| `60` | 約1時間おきにRSS確認 |

## 手動実行

Actions タブから `Notify note posts to Slack` を選び、`Run workflow` で手動実行できます。

## 注意

Slack Webhook URL は Secret に保存し、コードや README に直接書かないでください。
一度チャットやドキュメントに貼った URL は漏えい扱いにして、Slack 側で再発行することを推奨します。
