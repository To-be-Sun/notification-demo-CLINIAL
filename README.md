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

---

# note投稿スケジュール リマインダー

Notionの「🎯プロジェクト管理DB」を監視し、公開予定日の指定日数前になったら
note記事の投稿予定をSlackの指定チャンネルにリマインド通知します。

## 仕組み

- GitHub Actions が1日1回（デフォルト 09:00 JST）起動します。
- `scripts/remind_note_schedule.py` が Notion Data Source API に対して、
  「タグ=認知施策」「タイプ=task」「日付=今日+`REMINDER_LOOKAHEAD_DAYS`日後」
  「ステータスがDone/Archive以外」の条件でクエリします。
- 該当する記事タスクを公開予定日順にまとめてSlackへ通知します。
- 通知済みの記事は `state/reminded.json` に記録し、二重通知を防ぎます。

## GitHub 側の設定

リポジトリの Settings > Secrets and variables > Actions で、以下を登録してください。

| 種別 | 名前 | 内容 |
|---|---|---|
| Secret | `NOTION_API_KEY` | Notion Internal Integration Token（🎯プロジェクト管理DBに共有が必要） |
| Secret | `SLACK_WEBHOOK_URL` | Slack Incoming Webhook URL（上記の投稿通知と共用可） |
| Variable | `NOTION_DATA_SOURCE_ID` | 対象データソースID（デフォルト: `b7bb50d8-eca7-4293-ae56-0dc85be0e9a7`） |
| Variable | `REMINDER_LOOKAHEAD_DAYS` | 何日前にリマインドするか（デフォルト: `3`） |
| Variable | `REMINDER_TAG` | 対象とするタグ（デフォルト: `認知施策`） |

### Notion Integration の準備

1. https://www.notion.so/my-integrations で Internal Integration を作成し、トークンを取得
2. 対象の「🎯プロジェクト管理DB」を開き、右上の「…」→「コネクト」から作成したIntegrationを共有

## 手動実行

Actions タブから `Remind upcoming note posts on Slack` を選び、`Run workflow` で手動実行できます。
