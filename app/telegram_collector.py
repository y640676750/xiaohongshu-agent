import re
from app.extractor import extract_article
from pathlib import Path
from datetime import datetime


def handle_message(text: str):

    url_pattern = r"https?://[^\s]+"

    match = re.search(url_pattern, text)
    if not match:
        return "没有检测到链接"

    url = match.group()

    article = extract_article(url)

    save_article(article)

    return "已保存爆款样本"
def save_article(article):

    Path("kb/xhs_examples").mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    file = Path("kb/xhs_examples") / f"sample_{ts}.md"

    content = f"""
标题：
{article['title']}

正文：
{article['content']}

来源：
{article['url']}
"""

    file.write_text(content, encoding="utf-8")
