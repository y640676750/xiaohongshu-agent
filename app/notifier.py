import os
import requests
from pathlib import Path

TG_LIMIT = 3800  # 留余量

def _env(name: str) -> str:
    return (os.getenv(name) or "").strip()

def _post(method: str, payload: dict):
    token = _env("TELEGRAM_BOT_TOKEN")
    url = f"https://api.telegram.org/bot{token}/{method}"
    r = requests.post(url, json=payload, timeout=30)
    r.raise_for_status()
    return r

def send_telegram(text: str):
    token = _env("TELEGRAM_BOT_TOKEN")
    chat_id = _env("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return

    text = text.strip()
    if not text:
        return

    # 自动分段
    chunks = []
    while len(text) > TG_LIMIT:
        cut = text.rfind("\n", 0, TG_LIMIT)
        if cut == -1:
            cut = TG_LIMIT
        chunks.append(text[:cut])
        text = text[cut:].lstrip("\n")
    chunks.append(text)

    for i, ch in enumerate(chunks, 1):
        prefix = f"({i}/{len(chunks)})\n" if len(chunks) > 1 else ""
        _post("sendMessage", {
            "chat_id": chat_id,
            "text": prefix + ch,
            "disable_web_page_preview": True,
        })

def send_telegram_file(file_path: str, caption: str = ""):
    token = _env("TELEGRAM_BOT_TOKEN")
    chat_id = _env("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return

    p = Path(file_path)
    if not p.exists():
        return

    url = f"https://api.telegram.org/bot{token}/sendDocument"
    with p.open("rb") as f:
        files = {"document": (p.name, f)}
        data = {"chat_id": chat_id, "caption": caption[:900]}
        r = requests.post(url, data=data, files=files, timeout=60)
        r.raise_for_status()