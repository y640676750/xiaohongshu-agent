import sys
import re
from pathlib import Path
from datetime import datetime
from app.extractor import extract_article


def extract_url(text: str) -> str | None:
    match = re.search(r"https?://[^\s]+", text)
    return match.group(0) if match else None


def save_sample(article):
    Path("kb/tone_pool/samples").mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    file = Path("kb/tone_pool/samples") / f"sample_{ts}.md"

    tags_text = "\n".join(article["tags"]) if article["tags"] else "无"

    content = f"""标题：
{article['title']}

正文：
{article['body']}

话题标签：
{tags_text}

来源：
{article['url']}
"""
    file.write_text(content, encoding="utf-8")
    print("样本已保存：", file)


def main():
    if len(sys.argv) < 2:
        print("请提供链接或整段分享文案")
        return

    raw_text = " ".join(sys.argv[1:])
    url = extract_url(raw_text)

    if not url:
        print("没有检测到有效链接")
        return

    print("检测到链接：", url)

    article = extract_article(url)
    save_sample(article)


if __name__ == "__main__":
    main()