import json
import re
import requests
from pathlib import Path

from app.extractor import extract_article
from app.utils import save_output

BOT_TOKEN = None
STATE_FILE = "kb/processed_updates.json"


def load_token():
    import os
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("没有找到 TELEGRAM_BOT_TOKEN")
    return token


def load_state():
    path = Path(STATE_FILE)

    if not path.exists():
        return {"last_update_id": 0}

    return json.loads(path.read_text())


def save_state(state):
    Path(STATE_FILE).write_text(json.dumps(state))


def extract_links(text):

    pattern = r"https?://[^\s]+"

    return re.findall(pattern, text)


def fetch_updates(token, offset):

    url = f"https://api.telegram.org/bot{token}/getUpdates"

    params = {"offset": offset}

    r = requests.get(url, params=params)

    return r.json()


def process_message(text):

    links = extract_links(text)

    for link in links:

        if "xhslink.com" in link or "xiaohongshu.com" in link:

            print("发现小红书链接:", link)

            data = extract_article(link)

            content = f"""
标题：
{data['title']}

正文：
{data['body']}

标签：
{' '.join(data['tags'])}

来源：
{data['url']}
"""

            save_output(content, prefix="tone_sample")

            print("已保存语感样本")


def main():

    token = load_token()

    state = load_state()

    offset = state["last_update_id"] + 1

    data = fetch_updates(token, offset)

    for item in data["result"]:

        update_id = item["update_id"]

        if "message" in item:

            text = item["message"].get("text", "")

            process_message(text)

        state["last_update_id"] = update_id

    save_state(state)


if __name__ == "__main__":
    main()