"""MCP server entry point.

Run with:

    python -m mcp_server.server          # stdio transport (default)
    python -m mcp_server.server --http   # HTTP transport on 0.0.0.0:8765

Configure in Claude Desktop / Cursor by pointing the MCP host at this
module - see `mcp_server/README.md` for the JSON snippet.

The server depends on the official `mcp` Python SDK (>= 1.2). If the
SDK is missing we emit an actionable error instead of a stacktrace.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from typing import Any, Optional

try:
    from mcp.server.fastmcp import FastMCP
except Exception as e:  # pragma: no cover - exercised only when sdk missing
    sys.stderr.write(
        "[mcp_server] 缺少 `mcp` Python SDK，请先安装：\n"
        "    pip install 'mcp[cli]>=1.2'\n"
        f"原始异常: {e}\n"
    )
    raise SystemExit(1)

from app import analytics, db, publisher
from app.news_fetcher import fetch_all_news
from app.news_summarizer import analyze_article, rank_articles
from app.sources import RSS_SOURCES, WEB_SOURCES


mcp = FastMCP(
    name="xiaohongshu-ai-agent",
    instructions=(
        "Xiaohongshu (小红书) content automation toolkit. Provides tools to "
        "fetch AI news, run a multi-agent writing pipeline, queue / publish "
        "drafts and inspect analytics. All write operations target the local "
        "SQLite store at $XHS_DB_PATH (default kb/xhs_agent.db)."
    ),
)


# ───────────────────────────── news / research ─────────────────────────────


@mcp.tool()
def fetch_ai_news(max_items: int = 10, analyze: bool = False) -> dict:
    """Fetch and dedupe the latest AI articles from the configured RSS + web sources.

    Args:
        max_items: cap on number of articles returned (most-recent first).
        analyze:   if True, run the LLM analyzer to add category / score / oneliner.
    """
    articles = fetch_all_news(RSS_SOURCES, WEB_SOURCES)
    articles = articles[:max_items]
    for a in articles:
        db.upsert_article(a)
    if analyze:
        for a in articles:
            try:
                analyze_article(a)
                db.upsert_article(a)
            except Exception as e:
                a["error"] = str(e)
    return {"count": len(articles), "articles": articles}


@mcp.tool()
def rank_news(limit: int = 5) -> list[dict]:
    """Return the top-N most valuable recent articles (must have been analyzed)."""
    rows = db.list_recent_articles(limit=200)
    ranked = rank_articles(rows, max_items=limit)
    return ranked


# ───────────────────────────── writing pipeline ─────────────────────────────


@mcp.tool()
def generate_xhs_post(
    topic: str = "AI资讯",
    style: str = "科技前沿",
    selling_point: Optional[str] = None,
    audience: Optional[str] = None,
    keywords: Optional[list[str]] = None,
    link: str = "{LINK}",
) -> dict:
    """Generate a Xiaohongshu post for a topic/brief (no news fetching)."""
    from agents.writer import write_post
    from app.schema import Brief

    brief = Brief(
        link=link,
        selling_point=selling_point or f"围绕「{topic}」给读者一篇看完就能用的小红书干货",
        audience=audience or "想了解AI并用上的普通职场人和学生",
        keywords=keywords or ["AI", topic, "效率"],
    )
    text = write_post(brief, topic=f"{topic}|{style}")
    return {"topic": topic, "style": style, "post": text}


@mcp.tool()
def generate_titles(post_text: str, topic: str = "AI资讯", n: int = 10) -> dict:
    """Generate N candidate titles for a draft post."""
    from agents.title_generator import generate_titles as _gen

    return {"titles": _gen(post_text, topic=topic, n=n)}


@mcp.tool()
def rank_titles(post_text: str, titles_text: str, top_k: int = 3) -> dict:
    """Rank candidate titles and return the top K with explanations."""
    from agents.title_ranker import rank_titles as _rank

    return {"ranked": _rank(post_text, titles_text, top_k=top_k)}


@mcp.tool()
def review_post(post_text: str) -> dict:
    """Run the critic agent on a post and return structured scores."""
    from agents.critic import review_post as _review

    return _review(post_text).to_dict()


@mcp.tool()
def run_full_pipeline(
    topic: Optional[str] = None,
    style: str = "科技前沿",
    skip_news: bool = False,
    auto_publish: bool = False,
    auto_schedule_minutes: int = 0,
) -> dict:
    """Run the full multi-agent pipeline: analyst → news → writer → titler → critic → publisher."""
    from agents.orchestrator import run_pipeline

    result = run_pipeline(
        topic=topic,
        style=style,
        skip_news=skip_news,
        auto_publish=auto_publish,
        auto_schedule_minutes=auto_schedule_minutes,
        notify=False,
    )
    return {
        "run_id": result.get("run_id"),
        "post_id": result.get("post_id"),
        "quality_score": (result.get("critic") or {}).get("overall"),
        "revision_count": result.get("revision_count"),
        "topic": result.get("topic"),
        "publish_result": result.get("publish_result"),
        "post_preview": (result.get("post_text") or "")[:600],
    }


# ───────────────────────────── publisher / queue ─────────────────────────────


@mcp.tool()
def list_drafts(status: Optional[str] = None, limit: int = 20) -> list[dict]:
    """List posts in the local DB. Optionally filter by status."""
    return db.list_posts(status=status, limit=limit)


@mcp.tool()
def get_post(post_id: int) -> Optional[dict]:
    """Fetch a single post by id."""
    return db.get_post(post_id)


@mcp.tool()
def schedule_post(post_id: int, scheduled_at: str) -> dict:
    """Schedule a draft for publication. `scheduled_at` is ISO8601 UTC."""
    return publisher.schedule_post(post_id, scheduled_at)


@mcp.tool()
def publish_post(post_id: int) -> dict:
    """Publish a draft immediately (backend chosen by XHS_PUBLISHER_BACKEND)."""
    return publisher.publish_now(post_id)


@mcp.tool()
def publish_due(limit: int = 10) -> list[dict]:
    """Publish every scheduled draft whose time has come."""
    return publisher.publish_due(limit=limit)


@mcp.tool()
def record_metrics(
    post_id: int,
    impressions: int = 0,
    likes: int = 0,
    comments: int = 0,
    shares: int = 0,
    collects: int = 0,
    follows: int = 0,
) -> dict:
    """Record real-world engagement numbers for a published post."""
    mid = publisher.record_metrics(
        post_id,
        impressions=impressions,
        likes=likes,
        comments=comments,
        shares=shares,
        collects=collects,
        follows=follows,
    )
    return {"metrics_id": mid, "post_id": post_id}


# ───────────────────────────── analytics ─────────────────────────────


@mcp.tool()
def analytics_report(days: int = 14) -> dict:
    """Return the full analytics JSON (summary, top posts, trend, suggestions)."""
    return analytics.full_report(days)


@mcp.tool()
def analytics_summary(days: int = 14) -> dict:
    """Lightweight summary stats over the given window."""
    return analytics.summary(days)


@mcp.tool()
def export_report(days: int = 14, format: str = "md") -> dict:
    """Render a report to disk and return its path. format: md | html | json."""
    from app.dashboard import write_report

    return write_report(days=days, formats=(format,))


# ───────────────────────────── resources ─────────────────────────────


@mcp.resource("xhs://posts/recent")
def recent_posts_resource() -> str:
    rows = db.list_posts(limit=30)
    return json.dumps(rows, ensure_ascii=False, indent=2)


@mcp.resource("xhs://analytics/summary")
def analytics_summary_resource() -> str:
    return json.dumps(analytics.summary(14), ensure_ascii=False, indent=2)


@mcp.resource("xhs://articles/recent")
def recent_articles_resource() -> str:
    return json.dumps(db.list_recent_articles(50), ensure_ascii=False, indent=2)


# ───────────────────────────── entry point ─────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(description="Xiaohongshu Agent MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "streamable-http"],
        default=os.getenv("MCP_TRANSPORT", "stdio"),
    )
    parser.add_argument("--host", default=os.getenv("MCP_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("MCP_PORT", "8765")))
    args = parser.parse_args()

    db.init_db()
    if args.transport in ("sse", "streamable-http"):
        mcp.settings.host = args.host
        mcp.settings.port = args.port
        mcp.run(transport=args.transport)
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
