#!/usr/bin/env python3
import datetime as dt
import email.utils
import html
import json
import os
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path


DEFAULT_RSS_URL = "https://note.com/clinial/rss"
DEFAULT_STATE_FILE = "state/notified.json"


def text_of(parent, name):
    for child in parent:
        if child.tag.split("}", 1)[-1] == name:
            return (child.text or "").strip()
    return ""


def parse_datetime(value):
    if not value:
        return None
    try:
        parsed = email.utils.parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)


def fetch_rss(url):
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "note-slack-notifier/1.0",
            "Accept": "application/rss+xml, application/xml, text/xml",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def parse_items(xml_bytes):
    root = ET.fromstring(xml_bytes)
    items = []
    for element in root.iter():
        if element.tag.split("}", 1)[-1] != "item":
            continue

        title = html.unescape(text_of(element, "title"))
        link = text_of(element, "link")
        guid = text_of(element, "guid") or link
        pub_date_raw = text_of(element, "pubDate")
        published_at = parse_datetime(pub_date_raw)

        if not link:
            continue

        items.append(
            {
                "id": guid,
                "title": title or link,
                "link": link,
                "published_at": published_at,
                "published_at_raw": pub_date_raw,
            }
        )
    return items


def load_state(path):
    if not path.exists():
        return {"notified": []}
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_state(path, state):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(state, file, ensure_ascii=False, indent=2)
        file.write("\n")


def post_to_slack(webhook_url, item):
    published = item["published_at"]
    if published:
        published_text = published.astimezone(dt.timezone(dt.timedelta(hours=9))).strftime(
            "%Y-%m-%d %H:%M JST"
        )
    else:
        published_text = item["published_at_raw"] or "不明"

    message = {
        "text": f"Clinial公式noteが更新されました: {item['title']}",
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        "*Clinial公式noteが更新されました*\n\n"
                        f"*<{item['link']}|{item['title']}>*\n"
                        f"公開日: {published_text}"
                    ),
                },
            }
        ],
    }

    body = json.dumps(message).encode("utf-8")
    request = urllib.request.Request(
        webhook_url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        response_body = response.read().decode("utf-8", errors="replace")
        if response.status >= 400:
            raise RuntimeError(f"Slack returned {response.status}: {response_body}")


def env_int(name, default):
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    try:
        return int(value)
    except ValueError:
        raise ValueError(f"{name} must be an integer")


def main():
    rss_url = os.environ.get("NOTE_RSS_URL", DEFAULT_RSS_URL)
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
    state_file = Path(os.environ.get("STATE_FILE", DEFAULT_STATE_FILE))
    lookback_hours = env_int("NOTIFY_LOOKBACK_HOURS", 24)
    max_items = env_int("MAX_NOTIFY_ITEMS", 5)
    dry_run = os.environ.get("DRY_RUN", "").lower() in {"1", "true", "yes"}

    if not webhook_url and not dry_run:
        print("SLACK_WEBHOOK_URL is required", file=sys.stderr)
        return 2

    xml_bytes = fetch_rss(rss_url)
    items = parse_items(xml_bytes)
    items.sort(key=lambda item: item["published_at"] or dt.datetime.min.replace(tzinfo=dt.timezone.utc))

    state = load_state(state_file)
    notified = state.setdefault("notified", [])
    notified_ids = {entry["id"] for entry in notified}

    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=lookback_hours)
    candidates = []
    for item in items:
        if item["id"] in notified_ids:
            continue
        if lookback_hours > 0 and item["published_at"] and item["published_at"] < cutoff:
            continue
        candidates.append(item)

    candidates = candidates[-max_items:]

    if not candidates:
        print("No new posts to notify.")
        return 0

    for item in candidates:
        if dry_run:
            print(f"DRY_RUN: would notify {item['title']} {item['link']}")
            continue
        else:
            post_to_slack(webhook_url, item)
            print(f"Notified: {item['title']} {item['link']}")

        notified.append(
            {
                "id": item["id"],
                "title": item["title"],
                "link": item["link"],
                "notified_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            }
        )

    state["notified"] = notified[-200:]
    if not dry_run:
        save_state(state_file, state)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (urllib.error.URLError, ET.ParseError, RuntimeError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        raise SystemExit(1)
