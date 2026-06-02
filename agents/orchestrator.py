"""Multi-agent orchestrator (LangGraph).

The graph
---------

  ┌─────────────┐
  │  analyst    │  consult past data, pick topic, suggest hooks
  └─────┬───────┘
        ▼
  ┌─────────────┐   no fresh news?  use brief-only path
  │ news_agent  │───────────────────────────────┐
  └─────┬───────┘                               │
        ▼                                       ▼
  ┌─────────────┐                       ┌──────────────┐
  │ writer      │◀──────┐               │  writer (brief) │
  └─────┬───────┘       │               └──────┬───────┘
        ▼               │ revise                ▼
  ┌─────────────┐       │                ┌──────────────┐
  │ titler      │       │                │  titler      │
  └─────┬───────┘       │                └──────┬───────┘
        ▼               │                       ▼
  ┌─────────────┐       │                ┌──────────────┐
  │ critic      │───────┘ overall<7      │  critic      │
  └─────┬───────┘       (max 2 revisions) └──────┬───────┘
        ▼                                        ▼
  ┌─────────────────────── publisher ─────────────────────┐
  │ persist draft → schedule / publish → record metrics  │
  └───────────────────────────────────────────────────────┘

The orchestrator is also designed to be reused as a building block of
the MCP server (`tool: run_full_pipeline`).
"""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, TypedDict

from app import db
from app.notifier import send_telegram

from agents.analyst import build_analyst_brief, render_brief_text
from agents.critic import CriticResult, review_post


class GraphState(TypedDict, total=False):
    run_id: str
    topic: str
    style: str
    article: Optional[dict]
    brief: dict  # analyst brief
    post_text: str
    titles_text: str
    titles_ranked: str
    critic: dict
    revision_count: int
    post_id: int
    publish_result: dict
    auto_publish: bool
    auto_schedule_minutes: int
    skip_news: bool
    extra_user_brief: Optional[dict]


# ──────────────────────────── agent nodes ────────────────────────────


def _log(state: GraphState, agent: str, message: str, **meta) -> None:
    db.log_event(
        run_id=state.get("run_id") or "anonymous",
        agent=agent,
        message=message,
        meta=meta,
    )


def analyst_node(state: GraphState) -> GraphState:
    brief = build_analyst_brief()
    state["brief"] = brief
    if not state.get("topic"):
        state["topic"] = brief["next_topic_recommendation"]
    _log(state, "analyst", "brief built", next_topic=state["topic"])
    return state


def news_node(state: GraphState) -> GraphState:
    if state.get("skip_news"):
        _log(state, "news_agent", "skipped news fetching (brief-only mode)")
        return state

    try:
        from app.news_fetcher import fetch_all_news
        from app.news_summarizer import analyze_article, rank_articles
        from app.sources import RSS_SOURCES, WEB_SOURCES

        articles = fetch_all_news(RSS_SOURCES, WEB_SOURCES)
        _log(state, "news_agent", f"fetched {len(articles)} articles")
        if not articles:
            return state
        for a in articles[:5]:
            db.upsert_article(a)
            try:
                analyze_article(a)
                db.upsert_article(a)
            except Exception as e:
                _log(state, "news_agent", f"analyze failed: {e}", level="warn")
        best = rank_articles(articles[:5], max_items=1)
        if best:
            state["article"] = best[0]
            db.mark_article_used(best[0]["url"])
            _log(
                state,
                "news_agent",
                f"picked article: {best[0]['title']}",
                url=best[0]["url"],
                score=best[0].get("score"),
            )
    except Exception as e:
        _log(state, "news_agent", f"news pipeline failed: {e}", level="warn")
    return state


def writer_node(state: GraphState) -> GraphState:
    from agents.writer import write_post, write_post_from_article
    from app.schema import Brief

    article = state.get("article")
    topic = state.get("topic", "AI资讯")
    style = state.get("style", "科技前沿")
    analyst_hint = render_brief_text(state.get("brief") or {"summary": {}, "best_titles": [], "recommendations": []})

    if article:
        text = write_post_from_article({**article, "analyst_hint": analyst_hint})
    else:
        user_brief = state.get("extra_user_brief") or {
            "link": "{LINK}",
            "selling_point": f"围绕「{topic}」给读者一个看完就能用的干货分享",
            "audience": "想用AI提升效率的普通职场人和学生",
            "keywords": ["AI", topic, "效率", "实用"],
        }
        text = write_post(
            Brief(**user_brief),
            topic=f"{topic}|{style}",
        )

    state["post_text"] = text
    _log(state, "writer", f"draft length={len(text)}")
    return state


def titler_node(state: GraphState) -> GraphState:
    from agents.title_generator import generate_titles
    from agents.title_ranker import rank_titles

    post_text = state.get("post_text") or ""
    if not post_text:
        return state
    topic = state.get("topic", "AI资讯")

    try:
        titles_text = generate_titles(post_text, topic=topic, n=10)
    except Exception as e:
        titles_text = ""
        _log(state, "titler", f"generate failed: {e}", level="warn")

    ranked = ""
    if titles_text:
        try:
            ranked = rank_titles(post_text, titles_text, top_k=3)
        except Exception as e:
            _log(state, "titler", f"rank failed: {e}", level="warn")

    state["titles_text"] = titles_text
    state["titles_ranked"] = ranked
    _log(state, "titler", "titles generated")
    return state


def critic_node(state: GraphState) -> GraphState:
    text = state.get("post_text") or ""
    result: CriticResult = review_post(text)
    state["critic"] = result.to_dict()
    state["revision_count"] = (state.get("revision_count") or 0)
    _log(
        state,
        "critic",
        f"overall={result.overall} ship={result.ship}",
        suggestions=result.suggestions,
    )
    return state


def should_revise(state: GraphState) -> str:
    critic = state.get("critic") or {}
    overall = float(critic.get("overall") or 0)
    if overall >= 7 or (state.get("revision_count") or 0) >= 2:
        return "publish"
    state["revision_count"] = (state.get("revision_count") or 0) + 1
    return "revise"


def revise_node(state: GraphState) -> GraphState:
    """Ask the writer to revise based on critic feedback."""
    from langchain_core.messages import HumanMessage, SystemMessage

    from app.llm import get_llm

    if not os.getenv("OPENAI_API_KEY"):
        _log(state, "writer", "skipping revise (no API key)")
        return state

    critic = state.get("critic") or {}
    suggestions = "\n".join(f"- {s}" for s in critic.get("suggestions") or [])
    sys = "你是小红书内容写手，请根据审稿建议改写下面的文案。保留原文核心内容和结构，只针对建议做改进。"
    user = (
        f"审稿建议：\n{suggestions}\n\n"
        f"当前文案：\n{state.get('post_text', '')}\n\n"
        "请直接输出修改后的完整文案。"
    )
    try:
        llm = get_llm()
        rev = llm.invoke([SystemMessage(content=sys), HumanMessage(content=user)]).content
        state["post_text"] = rev
        _log(state, "writer", "post revised based on critic feedback")
    except Exception as e:
        _log(state, "writer", f"revise failed: {e}", level="warn")
    return state


def publisher_node(state: GraphState) -> GraphState:
    from app.publisher import publish_now, save_draft, schedule_in

    critic = state.get("critic") or {}
    post_id = save_draft(
        body=state.get("post_text", ""),
        topic=state.get("topic"),
        style=state.get("style"),
        article_url=(state.get("article") or {}).get("url"),
        titles_candidates=state.get("titles_text"),
        titles_ranked=state.get("titles_ranked"),
        quality_score=float(critic.get("overall") or 0),
        critic_feedback="\n".join(critic.get("suggestions") or []),
    )
    state["post_id"] = post_id
    _log(state, "publisher", f"draft saved id={post_id}")

    if state.get("auto_publish"):
        result = publish_now(post_id)
        state["publish_result"] = result
        _log(state, "publisher", "published immediately", **result)
    elif state.get("auto_schedule_minutes"):
        result = schedule_in(post_id, state["auto_schedule_minutes"])
        state["publish_result"] = result
        _log(state, "publisher", "scheduled", **result)
    return state


# ─────────────────────────── graph wiring ────────────────────────────


def build_graph():
    """Build and compile the LangGraph state machine. Returns the runnable graph."""
    from langgraph.graph import END, StateGraph

    g = StateGraph(GraphState)

    g.add_node("analyst", analyst_node)
    g.add_node("news", news_node)
    g.add_node("writer", writer_node)
    g.add_node("titler", titler_node)
    g.add_node("critic", critic_node)
    g.add_node("revise", revise_node)
    g.add_node("publisher", publisher_node)

    g.set_entry_point("analyst")
    g.add_edge("analyst", "news")
    g.add_edge("news", "writer")
    g.add_edge("writer", "titler")
    g.add_edge("titler", "critic")
    g.add_conditional_edges(
        "critic",
        should_revise,
        {"revise": "revise", "publish": "publisher"},
    )
    g.add_edge("revise", "titler")
    g.add_edge("publisher", END)
    return g.compile()


# ────────────────────────────── runners ──────────────────────────────


def run_pipeline(
    *,
    topic: Optional[str] = None,
    style: str = "科技前沿",
    auto_publish: bool = False,
    auto_schedule_minutes: int = 0,
    skip_news: bool = False,
    extra_user_brief: Optional[dict] = None,
    notify: bool = True,
) -> dict:
    """Run the full multi-agent pipeline once and return the final state."""
    state: GraphState = {
        "run_id": uuid.uuid4().hex[:12],
        "topic": topic or "",
        "style": style,
        "auto_publish": auto_publish,
        "auto_schedule_minutes": auto_schedule_minutes,
        "skip_news": skip_news,
        "extra_user_brief": extra_user_brief,
        "revision_count": 0,
    }
    if notify:
        send_telegram(f"🤖 Multi-Agent 流水线启动 run_id={state['run_id']}")

    graph = build_graph()
    final: GraphState = graph.invoke(state)  # type: ignore[assignment]

    if notify:
        send_telegram(
            "✅ Multi-Agent 流水线完成\n"
            f"run_id: {final.get('run_id')}\n"
            f"主题: {final.get('topic')}\n"
            f"草稿 ID: {final.get('post_id')}\n"
            f"质量分: {(final.get('critic') or {}).get('overall')}\n"
            f"修改轮数: {final.get('revision_count')}\n"
            f"发布结果: {final.get('publish_result') or '仅生成草稿'}"
        )
    return dict(final)


def main():
    import argparse
    import sys

    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

    ap = argparse.ArgumentParser(description="多 Agent 协同流水线")
    ap.add_argument("--topic", default=None)
    ap.add_argument("--style", default="科技前沿")
    ap.add_argument(
        "--auto-publish",
        action="store_true",
        help="生成完直接调用 publisher 发布（mock backend 时只是落地）",
    )
    ap.add_argument(
        "--schedule-minutes",
        type=int,
        default=0,
        help="生成完后把草稿安排到 N 分钟后发布",
    )
    ap.add_argument(
        "--skip-news",
        action="store_true",
        help="跳过资讯抓取，只用主题 brief 写文案",
    )
    ap.add_argument("--quiet", action="store_true", help="不推送 Telegram")
    args = ap.parse_args()

    out = run_pipeline(
        topic=args.topic,
        style=args.style,
        auto_publish=args.auto_publish,
        auto_schedule_minutes=args.schedule_minutes,
        skip_news=args.skip_news,
        notify=not args.quiet,
    )
    print("=" * 40)
    print("run_id:", out.get("run_id"))
    print("post_id:", out.get("post_id"))
    print("quality:", (out.get("critic") or {}).get("overall"))
    print("publish:", out.get("publish_result"))


if __name__ == "__main__":
    main()
