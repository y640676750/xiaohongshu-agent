"""
Full news pipeline:
  1. Fetch articles from all configured sources (RSS + web)
  2. Deduplicate against history
  3. Summarize each article with LLM
  4. Generate a daily digest
  5. Send digest + original URLs to Telegram
  6. Optionally feed the best articles into the XHS content generation pipeline
  7. Save raw articles to kb for future reference
"""

import argparse
import json
from datetime import datetime
from pathlib import Path

from app.sources import RSS_SOURCES, WEB_SOURCES
from app.news_fetcher import fetch_all_news
from app.news_summarizer import (
    summarize_article,
    generate_daily_digest,
    pick_best_for_content,
)
from app.notifier import send_telegram, send_telegram_file
from app.utils import save_output


RAW_ARCHIVE_DIR = "kb/news_archive"


def _save_raw_articles(articles: list[dict]):
    """Save fetched articles to archive for reference."""
    p = Path(RAW_ARCHIVE_DIR)
    p.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = p / f"articles_{ts}.json"
    filepath.write_text(
        json.dumps(articles, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return str(filepath)


def _build_source_links_message(articles: list[dict]) -> str:
    """Build a Telegram message listing all original article links."""
    if not articles:
        return ""

    lines = ["📎 原文链接汇总\n"]
    for i, a in enumerate(articles, 1):
        lines.append(f"{i}. [{a['source']}] {a['title']}")
        lines.append(f"   {a['url']}\n")

    return "\n".join(lines)


def _build_individual_summary_message(article: dict) -> str:
    """Build a Telegram message for a single summarized article."""
    lines = [
        f"📰 {article['title']}",
        f"📌 来源：{article['source']}",
        f"🔗 原文：{article['url']}",
    ]
    if article.get("summary"):
        lines.append(f"\n{article['summary']}")
    return "\n".join(lines)


def run_news_pipeline(
    summarize: bool = True,
    digest: bool = True,
    generate_content: bool = False,
    max_summarize: int = 10,
):
    """
    Main entry point for the news pipeline.

    Args:
        summarize: whether to run LLM summarization on each article
        digest: whether to generate a daily digest
        generate_content: whether to feed top articles into XHS content generation
        max_summarize: max number of articles to summarize (to control API costs)
    """
    print("=" * 50)
    print("🚀 Starting AI News Pipeline")
    print("=" * 50)

    # Step 1: Fetch
    print("\n📡 Step 1: Fetching articles from all sources...")
    articles = fetch_all_news(RSS_SOURCES, WEB_SOURCES)
    print(f"   Total new articles: {len(articles)}")

    if not articles:
        msg = "📡 本轮资讯抓取完成，暂无新的AI相关内容。"
        print(msg)
        send_telegram(msg)
        return

    # Save raw
    archive_path = _save_raw_articles(articles)
    print(f"   Archived to: {archive_path}")

    # Step 2: Summarize
    if summarize:
        print(f"\n🔍 Step 2: Summarizing top {min(len(articles), max_summarize)} articles...")
        to_summarize = articles[:max_summarize]
        for i, article in enumerate(to_summarize, 1):
            print(f"   [{i}/{len(to_summarize)}] {article['title'][:50]}...")
            summarize_article(article)

    # Step 3: Generate digest
    if digest:
        print("\n📝 Step 3: Generating daily digest...")
        digest_text = generate_daily_digest(articles)

        saved_digest = save_output(digest_text, prefix="ai_daily_digest")
        print(f"   Saved digest: {saved_digest}")

        send_telegram(digest_text)
        send_telegram_file(saved_digest, "📎 AI日报文件")

    # Step 4: Send original links
    print("\n🔗 Step 4: Sending original links to Telegram...")
    links_msg = _build_source_links_message(articles)
    if links_msg:
        send_telegram(links_msg)

    # Step 5: Send individual summaries for top articles
    if summarize:
        print("\n📬 Step 5: Sending individual summaries...")
        summarized = [a for a in articles if a.get("summarized")]
        top_articles = summarized[:5]
        for article in top_articles:
            msg = _build_individual_summary_message(article)
            send_telegram(msg)

    # Step 6: Generate XHS content from best articles
    if generate_content:
        print("\n✍️ Step 6: Generating XHS content from top articles...")
        _generate_xhs_from_articles(articles)

    print("\n✅ News pipeline complete!")
    print(f"   Articles fetched: {len(articles)}")
    if summarize:
        print(f"   Articles summarized: {len([a for a in articles if a.get('summarized')])}")


def _generate_xhs_from_articles(articles: list[dict]):
    """
    Take the best articles and generate XHS posts from them.
    Feeds real news data into the existing content generation pipeline.
    """
    from app.schema import Brief
    from agents.writer import write_post
    from agents.title_generator import generate_titles
    from agents.title_ranker import rank_titles

    best = pick_best_for_content(articles, max_items=2)

    for i, article in enumerate(best, 1):
        import re
        summary = article.get("summary", "")

        category_match = re.search(r"【分类】\s*(.+)", summary)
        category = category_match.group(1).strip() if category_match else "AI资讯"

        topic_map = {
            "AI资讯": "AI资讯",
            "AI使用技巧": "AI使用技巧",
            "AI工具推荐": "AI工具推荐",
        }
        topic = topic_map.get(category, "AI资讯")

        oneliner_match = re.search(r"【一句话总结】\s*(.+)", summary)
        selling_point = oneliner_match.group(1).strip() if oneliner_match else article["title"]

        brief = Brief(
            link=article["url"],
            selling_point=selling_point,
            audience="关注AI发展、想了解最新AI动态和技巧的人",
            keywords=_extract_keywords(article),
        )

        try:
            post_text = write_post(brief, topic=topic)
            titles_text = generate_titles(post_text, topic=topic, n=10)
            ranked = rank_titles(post_text, titles_text, top_k=3)

            saved_post = save_output(post_text, prefix=f"news_xhs_{i}")
            save_output(titles_text, prefix=f"news_titles_{i}")
            save_output(ranked, prefix=f"news_ranked_{i}")

            send_telegram(f"✍️【基于资讯生成 第{i}条】\n📰 原文：{article['title']}\n🔗 {article['url']}\n\n{post_text}")
            send_telegram(f"📋 候选标题：\n{titles_text}")
            send_telegram(f"🏆 标题Top3：\n{ranked}")
            send_telegram_file(saved_post, f"基于资讯生成 第{i}条 正文")
        except Exception as e:
            print(f"   [Content] Error generating XHS content for article {i}: {e}")
            send_telegram(f"⚠️ 第{i}条资讯内容生成失败：{article['title']}\n原文：{article['url']}")


def _extract_keywords(article: dict) -> list[str]:
    """Extract keywords from an article for Brief construction."""
    title = article.get("title", "")
    base_keywords = ["AI", "人工智能"]

    keyword_pool = [
        "ChatGPT", "GPT", "Claude", "Gemini", "大模型", "LLM",
        "OpenAI", "Anthropic", "Google", "Meta", "Midjourney",
        "Prompt", "AI工具", "效率", "AI绘画", "AI视频", "Sora",
        "开源", "Llama", "Mistral", "AI编程", "Copilot",
    ]

    text = title + " " + article.get("snippet", "")
    matched = [kw for kw in keyword_pool if kw.lower() in text.lower()]
    return list(set(base_keywords + matched))[:8]


def main():
    parser = argparse.ArgumentParser(description="AI News Pipeline")
    parser.add_argument(
        "--no-summarize",
        action="store_true",
        help="Skip LLM summarization (faster, cheaper)",
    )
    parser.add_argument(
        "--no-digest",
        action="store_true",
        help="Skip daily digest generation",
    )
    parser.add_argument(
        "--generate-content",
        action="store_true",
        help="Also generate XHS posts from top articles",
    )
    parser.add_argument(
        "--max-summarize",
        type=int,
        default=10,
        help="Max number of articles to summarize (default: 10)",
    )
    args = parser.parse_args()

    run_news_pipeline(
        summarize=not args.no_summarize,
        digest=not args.no_digest,
        generate_content=args.generate_content,
        max_summarize=args.max_summarize,
    )


if __name__ == "__main__":
    main()
