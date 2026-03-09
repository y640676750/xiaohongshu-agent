import json
import re
import requests
from pathlib import Path
from datetime import datetime

from app.extractor import extract_article

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
    # 保留你原来的提取格式，不改
    pattern = r"https?://[^\s]+"
    return re.findall(pattern, text)


def fetch_updates(token, offset):
    url = f"https://api.telegram.org/bot{token}/getUpdates"
    params = {"offset": offset}

    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    return r.json()


def send_reply(token, chat_id, text, reply_to_message_id=None):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": True,
    }
    if reply_to_message_id:
        payload["reply_to_message_id"] = reply_to_message_id

    try:
        requests.post(url, json=payload, timeout=20)
    except Exception:
        pass


def save_tone_sample(data):
    folder = Path(TONE_SAMPLE_DIR)
    folder.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    file = folder / f"sample_{ts}.md"

    tags_text = "\n".join(data["tags"]) if data.get("tags") else "无"

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
    return file


def process_message(token, chat_id, message_id, text):
    links = extract_links(text)

    found_xhs = False

    for link in links:
        if "xhslink.com" in link or "xiaohongshu.com" in link:
            found_xhs = True
            print("发现小红书链接:", link)

            try:
                data = extract_article(link, raw_text=text)
                saved_file = save_tone_sample(data)

                reply_text = (
                    f"✅ 已采集成功\n\n"
                    f"标题：{data['title']}\n"
                    f"标签数：{len(data['tags'])}\n"
                    f"文件：{saved_file.name}"
                )
                send_reply(token, chat_id, reply_text, reply_to_message_id=message_id)
                print("已保存语感样本：", saved_file)

            except Exception as e:
                error_text = f"⚠️ 采集失败：{str(e)[:200]}"
                send_reply(token, chat_id, error_text, reply_to_message_id=message_id)
                print("采集失败：", e)

    if not found_xhs:
        print("未发现小红书链接")


def main():
    token = load_token()
    state = load_state()
    offset = state["last_update_id"] + 1

    data = fetch_updates(token, offset)

    for item in data.get("result", []):
        update_id = item["update_id"]

        if "message" in item:
            message = item["message"]
            text = message.get("text", "")
            chat_id = message.get("chat", {}).get("id")
            message_id = message.get("message_id")

            if text and chat_id:
                process_message(token, chat_id, message_id, text)

        state["last_update_id"] = update_id

    save_state(state)


if __name__ == "__main__":
    main()