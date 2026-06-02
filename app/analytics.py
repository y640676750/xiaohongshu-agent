"""Data analytics on top of the SQLite store.

Provides:
  * summary stats (total posts / posts per topic / engagement rates)
  * top performing titles and best topics
  * trend over time (posts-per-day, average engagement)
  * actionable insights for the next generation cycle

All functions are pure - they read from the DB and return primitives
that can be rendered in the Markdown/HTML dashboard, sent to Telegram,
or returned as an MCP tool result.
"""

from __future__ import annotations

import json
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

from app import db


def _safe_div(a: float, b: float) -> float:
    return (a / b) if b else 0.0


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_iso(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def compute_engagement(row: dict) -> dict[str, float]:
    """Derive CTR / engagement rate / virality score from a metrics row."""
    imp = max(0, int(row.get("impressions") or 0))
    likes = int(row.get("likes") or 0)
    comments = int(row.get("comments") or 0)
    shares = int(row.get("shares") or 0)
    collects = int(row.get("collects") or 0)
    follows = int(row.get("follows") or 0)

    interactions = likes + comments + shares + collects + follows
    engagement_rate = _safe_div(interactions, imp)
    quality_signal = likes + 2 * comments + 3 * shares + 2 * collects + 5 * follows
    virality_score = _safe_div(quality_signal, max(imp, 1)) * 100
    return {
        "impressions": imp,
        "interactions": interactions,
        "engagement_rate": engagement_rate,
        "virality_score": virality_score,
    }


def summary(days: int = 14) -> dict[str, Any]:
    """High-level numbers for the dashboard."""
    db.init_db()
    cutoff = (_now() - timedelta(days=days)).isoformat()

    posts = [p for p in db.list_posts(limit=10_000) if (p.get("created_at") or "") >= cutoff]
    metrics = db.latest_metrics_per_post()

    status_counter: Counter[str] = Counter(p["status"] for p in posts)
    topic_counter: Counter[str] = Counter((p.get("topic") or "未分类") for p in posts)

    eng_per_topic: dict[str, list[float]] = defaultdict(list)
    eng_per_post: dict[int, dict] = {}
    for m in metrics:
        e = compute_engagement(m)
        eng_per_post[m["post_id"]] = e
        eng_per_topic[m.get("topic") or "未分类"].append(e["engagement_rate"])

    avg_engagement_by_topic = {
        topic: round(statistics.mean(vals), 4) if vals else 0.0
        for topic, vals in eng_per_topic.items()
    }

    total_imp = sum(m.get("impressions") or 0 for m in metrics)
    total_likes = sum(m.get("likes") or 0 for m in metrics)
    total_comments = sum(m.get("comments") or 0 for m in metrics)

    return {
        "window_days": days,
        "total_posts": len(posts),
        "by_status": dict(status_counter),
        "by_topic": dict(topic_counter),
        "total_impressions": total_imp,
        "total_likes": total_likes,
        "total_comments": total_comments,
        "avg_engagement_rate": round(
            statistics.mean([e["engagement_rate"] for e in eng_per_post.values()])
            if eng_per_post
            else 0.0,
            4,
        ),
        "avg_engagement_by_topic": avg_engagement_by_topic,
    }


def top_posts(limit: int = 5) -> list[dict]:
    """Return the top posts by virality_score with a friendly preview."""
    metrics = db.latest_metrics_per_post()
    ranked = []
    for m in metrics:
        e = compute_engagement(m)
        post = db.get_post(m["post_id"]) or {}
        ranked.append({
            "post_id": m["post_id"],
            "title": post.get("title") or (post.get("body") or "")[:40],
            "topic": post.get("topic"),
            "status": post.get("status"),
            "impressions": e["impressions"],
            "interactions": e["interactions"],
            "engagement_rate": round(e["engagement_rate"], 4),
            "virality_score": round(e["virality_score"], 2),
            "scheduled_at": post.get("scheduled_at"),
            "published_at": post.get("published_at"),
        })
    ranked.sort(key=lambda r: r["virality_score"], reverse=True)
    return ranked[:limit]


def best_titles(limit: int = 10) -> list[dict]:
    """Titles of top performing posts - useful as the 'viral memory' feed."""
    return [
        {"title": r["title"], "virality_score": r["virality_score"], "topic": r["topic"]}
        for r in top_posts(limit)
        if r["title"]
    ]


def trend(days: int = 14) -> list[dict]:
    """Daily timeseries: posts published + avg engagement."""
    posts = db.list_posts(limit=10_000)
    metrics = db.latest_metrics_per_post()
    by_post_eng: dict[int, dict] = {m["post_id"]: compute_engagement(m) for m in metrics}

    days_iter = [(_now() - timedelta(days=i)).date() for i in range(days - 1, -1, -1)]
    out: list[dict] = []
    for day in days_iter:
        day_str = day.isoformat()
        posts_today = [
            p for p in posts
            if (_parse_iso(p.get("created_at")) or _now()).date() == day
        ]
        engs = [
            by_post_eng[p["id"]]["engagement_rate"]
            for p in posts_today
            if p["id"] in by_post_eng
        ]
        out.append({
            "date": day_str,
            "posts": len(posts_today),
            "avg_engagement_rate": round(statistics.mean(engs), 4) if engs else 0.0,
        })
    return out


def suggest_next_topics() -> list[dict]:
    """Heuristic: topics that historically outperform get a higher 'weight'."""
    s = summary(days=30)
    weights = []
    base_topics = ["AI资讯", "AI使用技巧", "AI工具推荐"]
    eng_map = s["avg_engagement_by_topic"]
    for t in base_topics:
        eng = eng_map.get(t, 0.0)
        published = s["by_topic"].get(t, 0)
        score = eng * 100 + max(0, 5 - published)  # explore less-used topics
        weights.append({"topic": t, "score": round(score, 2), "engagement_rate": eng})
    weights.sort(key=lambda r: r["score"], reverse=True)
    return weights


def full_report(days: int = 14) -> dict[str, Any]:
    return {
        "generated_at": _now().isoformat(),
        "summary": summary(days),
        "top_posts": top_posts(10),
        "best_titles": best_titles(10),
        "trend": trend(days),
        "suggested_topics": suggest_next_topics(),
    }


def to_json(report: dict[str, Any]) -> str:
    return json.dumps(report, ensure_ascii=False, indent=2)
