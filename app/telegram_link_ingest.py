import json
import re
import requests
from pathlib import Path
from datetime import datetime

from app.extractor import extract_article

BOT_TOKEN = None
STATE_FILE = "kb/processed_updates.json"
TONE_SAMPLE_DIR = "kb/tone_pool/samples"


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

    return json.loads(path.read_text(encoding="utf-8"))


def save_state(state):
    path = Path(STATE_FILE)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")


def extract_links(text):
    pattern = r"https?://[^\s]+"
    return re.findall(pattern, text)


def fetch_updates(token, offset):
    url = f"https://api.telegram.org/bot{token}/getUpdates"
    params = {"offset": offset}

    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    return r.json()


def save_tone_sample(data):
    folder = Path(TONE_SAMPLE_DIR)
    folder.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    file = folder / f"sample_{ts}.md"

    tags_text = " ".join(data["tags"]) if data.get("tags") else "无"

    content = f"""标题：
{data['title']}

正文：
{data['body']}

话题标签：
{tags_text}

来源：
{data['url']}
"""

    file.write_text(content, encoding="utf-8")
    print("已保存语感样本：", file)


def process_message(text):
    links = extract_links(text)

    for link in links:
        if "xhslink.com" in link or "xiaohongshu.com" in link:
            print("发现小红书链接:", link)

            data = extract_article(link)

            save_tone_sample(data)


def main():
    token = load_token()
    state = load_state()
    offset = state["last_update_id"] + 1

    data = fetch_updates(token, offset)

    for item in data.get("result", []):
        update_id = item["update_id"]

        if "message" in item:
            text = item["message"].get("text", "")
            process_message(text)

        state["last_update_id"] = update_id

    save_state(state)


if __name__ == "__main__":
    main()