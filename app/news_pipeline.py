"""
AI资讯 → 小红书引流文案 → Telegram推送 完整流水线

核心流程：
  1. 从RSS/网页源抓取最新AI文章
  2. 去重
  3. LLM分析筛选最有价值的文章
  4. 基于真实文章内容生成小红书引流文案（标题+正文+标签）
  5. 文案 + 原文链接 一起推送到Telegram
"""

import argparse
import json
from datetime import datetime
from pathlib import Path

from app.sources import RSS_SOURCES, WEB_SOURCES
from app.news_fetcher import fetch_all_news
from app.news_summarizer import (
    analyze_article,
    rank_articles,
    build_source_links_message,
)
from agents.writer import write_post_from_article
from agents.title_generator import generate_titles
from agents.title_ranker import rank_titles
from app.notifier import send_telegram, send_telegram_file
from app.utils import save_output


RAW_ARCHIVE_DIR = "kb/news_archive"


def _save_raw_articles(articles: list[dict]):
    p = Path(RAW_ARCHIVE_DIR)
    p.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = p / f"articles_{ts}.json"

    save_data = []
    for a in articles:
        item = {k: v for k, v in a.items() if k != "page_content"}
        save_data.append(item)
    filepath.write_text(
        json.dumps(save_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return str(filepath)


def run_news_pipeline(max_articles: int = 5, max_posts: int = 3):
    """
    主入口：抓取 → 分析 → 生成小红书文案 → 推送Telegram

    Args:
        max_articles: 最多分析多少篇文章
        max_posts: 最多生成多少条小红书文案
    """
    print("=" * 50)
    print("🚀 AI资讯 → 小红书文案 流水线启动")
    print("=" * 50)

    # ── Step 1: 抓取 ──
    print("\n📡 Step 1: 抓取最新AI资讯...")
    articles = fetch_all_news(RSS_SOURCES, WEB_SOURCES)
    print(f"   新文章数量: {len(articles)}")

    if not articles:
        msg = "📡 本轮抓取完成，暂无新的AI相关内容。"
        print(msg)
        send_telegram(msg)
        return

    archive_path = _save_raw_articles(articles)
    print(f"   已归档: {archive_path}")

    # ── Step 2: LLM分析 + 筛选 ──
    print(f"\n🔍 Step 2: 分析文章价值（最多{max_articles}篇）...")
    to_analyze = articles[:max_articles]
    for i, article in enumerate(to_analyze, 1):
        print(f"   [{i}/{len(to_analyze)}] {article['title'][:50]}...")
        try:
            analyze_article(article)
        except Exception as e:
            print(f"   ⚠️ 分析失败: {e}")

    best = rank_articles(to_analyze, max_items=max_posts)
    print(f"   筛选出 {len(best)} 篇高价值文章")

    # ── Step 3: 为每篇生成小红书文案 ──
    print(f"\n✍️ Step 3: 生成小红书引流文案...")

    send_telegram(f"📌 本轮AI资讯推送（共{len(best)}条文案）\n抓取到 {len(articles)} 篇新文章，以下是最有价值的 {len(best)} 篇的小红书引流文案 👇")

    for i, article in enumerate(best, 1):
        print(f"\n   ── 第{i}条：{article['title'][:40]}... ──")

        # 生成文案
        try:
            post_text = write_post_from_article(article)
            print(f"   ✅ 文案已生成")
        except Exception as e:
            print(f"   ⚠️ 文案生成失败: {e}")
            send_telegram(f"⚠️ 第{i}条文案生成失败\n📰 {article['title']}\n🔗 {article['url']}")
            continue

        # 生成标题
        try:
            category = article.get("category_detected", "AI资讯")
            titles_text = generate_titles(post_text, topic=category, n=10)
            ranked = rank_titles(post_text, titles_text, top_k=3)
            print(f"   ✅ 标题已生成")
        except Exception as e:
            print(f"   ⚠️ 标题生成失败: {e}")
            titles_text = ""
            ranked = ""

        # 保存文件
        saved_post = save_output(post_text, prefix=f"news_xhs_{i}")
        if titles_text:
            save_output(titles_text, prefix=f"news_titles_{i}")
        if ranked:
            save_output(ranked, prefix=f"news_ranked_{i}")

        # ── 推送到Telegram：文案 + 原文链接打包一起 ──
        tg_msg = _build_post_message(i, article, post_text, ranked)
        send_telegram(tg_msg)
        send_telegram_file(saved_post, f"📎 第{i}条小红书文案")

    # ── Step 4: 推送所有原文链接汇总 ──
    print("\n🔗 Step 4: 推送原文链接汇总...")
    links_msg = build_source_links_message(articles)
    if links_msg:
        send_telegram(links_msg)

    print("\n" + "=" * 50)
    print(f"✅ 流水线完成！")
    print(f"   抓取文章: {len(articles)}")
    print(f"   生成文案: {len(best)}")
    print("=" * 50)


def _build_post_message(idx: int, article: dict, post_text: str, ranked: str) -> str:
    """把文案和原文信息打包成一条Telegram消息。"""
    lines = [
        f"━━━ 第{idx}条 ━━━",
        f"📰 资讯来源：{article['source']}",
        f"📌 原文标题：{article['title']}",
        f"🔗 原文链接：{article['url']}",
        "",
        "✍️ 小红书引流文案 👇",
        "─" * 20,
        post_text,
    ]

    if ranked:
        lines.extend([
            "",
            "🏆 推荐标题Top3 👇",
            "─" * 20,
            ranked,
        ])

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="AI资讯 → 小红书引流文案 流水线")
    parser.add_argument(
        "--max-articles",
        type=int,
        default=5,
        help="最多分析多少篇文章（默认5）",
    )
    parser.add_argument(
        "--max-posts",
        type=int,
        default=3,
        help="最多生成多少条小红书文案（默认3）",
    )
    args = parser.parse_args()

    run_news_pipeline(
        max_articles=args.max_articles,
        max_posts=args.max_posts,
    )


if __name__ == "__main__":
    main()
