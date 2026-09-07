#!/usr/bin/env python3
"""
note記事 投稿前リマインド通知スクリプト
------------------------------------------------
Notionの「🎯プロジェクト管理DB」から、指定日数後に公開予定のnote記事タスクを取得し、
Slackの#mediaチャンネルへ日付順にリマインド通知する。

想定運用: GitHub Actions で1日1回実行 (notify_note_to_slack.py と同じ構成)。
"""

import datetime as dt
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path


DEFAULT_DATA_SOURCE_ID = "b7bb50d8-eca7-4293-ae56-0dc85be0e9a7"
DEFAULT_STATE_FILE = "state/reminded.json"
DEFAULT_LOOKAHEAD_DAYS = 3
DEFAULT_TAG = "認知施策"
NOTION_VERSION = "2025-09-03"
JST = dt.timezone(dt.timedelta(hours=9))


def env_int(name, default):
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    try:
        return int(value)
    except ValueError:
        raise ValueError(f"{name} must be an integer")


def load_state(path):
    if not path.exists():
        return {"reminded": []}
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_state(path, state):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(state, file, ensure_ascii=False, indent=2)
        file.write("\n")


def notion_query(data_source_id, api_key, target_date, tag):
    url = f"https://api.notion.com/v1/data_sources/{data_source_id}/query"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }
    payload = {
        "filter": {
            "and": [
                {"property": "タグ", "multi_select": {"contains": tag}},
                {"property": "タイプ", "select": {"equals": "task"}},
                {"property": "日付", "date": {"equals": target_date}},
                {"property": "ステータス", "status": {"does_not_equal": "Done"}},
                {"property": "ステータス", "status": {"does_not_equal": "Archive"}},
            ]
        },
        "sorts": [{"property": "日付", "direction": "ascending"}],
    }

    results = []
    start_cursor = None
    while True:
        body = dict(payload)
        if start_cursor:
            body["start_cursor"] = start_cursor
        request = urllib.request.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
        results.extend(data.get("results", []))
        if not data.get("has_more"):
            break
        start_cursor = data.get("next_cursor")
    return results


def extract_title(page):
    props = page.get("properties", {})
    parts = props.get("名前", {}).get("title", [])
    text = "".join(part.get("plain_text", "") for part in parts)
    return text or "(無題)"


def extract_assignee(page):
    people = page.get("properties", {}).get("担当者", {}).get("people", [])
    if people:
        return people[0].get("name") or "未設定"
    return "未設定"


def build_slack_message(pages, target_date, lookahead_days):
    lines = [
        f"*:bell: {target_date} 公開予定のnote記事があります（{lookahead_days}日前リマインド）*"
    ]
    for page in pages:
        title = extract_title(page)
        assignee = extract_assignee(page)
        link = page.get("url", "")
        lines.append(f"• <{link}|{title}>　(担当: {assignee})")

    return {
        "text": f"{target_date} 公開予定のnote記事リマインド",
        "blocks": [
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "\n".join(lines)},
            }
        ],
    }


def post_to_slack(webhook_url, message):
    request = urllib.request.Request(
        webhook_url,
        data=json.dumps(message).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        body = response.read().decode("utf-8", errors="replace")
        if response.status >= 400:
            raise RuntimeError(f"Slack returned {response.status}: {body}")


def main():
    notion_api_key = os.environ.get("NOTION_API_KEY")
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
    data_source_id = os.environ.get("NOTION_DATA_SOURCE_ID", DEFAULT_DATA_SOURCE_ID)
    lookahead_days = env_int("REMINDER_LOOKAHEAD_DAYS", DEFAULT_LOOKAHEAD_DAYS)
    tag = os.environ.get("REMINDER_TAG", DEFAULT_TAG)
    state_file = Path(os.environ.get("REMINDER_STATE_FILE", DEFAULT_STATE_FILE))
    dry_run = os.environ.get("DRY_RUN", "").lower() in {"1", "true", "yes"}

    if not notion_api_key:
        print("NOTION_API_KEY is required", file=sys.stderr)
        return 2
    if not webhook_url and not dry_run:
        print("SLACK_WEBHOOK_URL is required", file=sys.stderr)
        return 2

    target_date = (dt.datetime.now(JST).date() + dt.timedelta(days=lookahead_days)).isoformat()

    pages = notion_query(data_source_id, notion_api_key, target_date, tag)

    state = load_state(state_file)
    reminded = state.setdefault("reminded", [])
    reminded_keys = {(entry["page_id"], entry["date"]) for entry in reminded}

    candidates = [page for page in pages if (page["id"], target_date) not in reminded_keys]

    if not candidates:
        print(f"[INFO] {target_date} 公開予定の未リマインド記事はありません。")
        return 0

    message = build_slack_message(candidates, target_date, lookahead_days)

    if dry_run:
        print("DRY_RUN:")
        print(json.dumps(message, ensure_ascii=False, indent=2))
        return 0

    post_to_slack(webhook_url, message)

    now = dt.datetime.now(dt.timezone.utc).isoformat()
    for page in candidates:
        reminded.append({"page_id": page["id"], "date": target_date, "reminded_at": now})
    state["reminded"] = reminded[-500:]
    save_state(state_file, state)

    print(f"[INFO] {len(candidates)}件のリマインドを送信しました。")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (urllib.error.URLError, RuntimeError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        raise SystemExit(1)
