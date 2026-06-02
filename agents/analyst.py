"""Analyst agent.

Aggregates the analytics DB into a short, actionable brief that the
orchestrator feeds back into the writer / titler. This is the
"data-driven feedback loop" of the multi-agent system.
"""

from __future__ import annotations

from typing import Any

from app import analytics


def build_analyst_brief() -> dict[str, Any]:
    """Produce a structured snapshot of recent performance + recommendations."""
    summary = analytics.summary(days=14)
    suggested = analytics.suggest_next_topics()
    best = analytics.best_titles(5)

    next_topic = suggested[0]["topic"] if suggested else "AI资讯"

    recommendations = []
    if summary["avg_engagement_rate"] < 0.02:
        recommendations.append(
            "整体互动率偏低，建议在开头钩子里加入更具体的数字 / 对比 / 痛点。"
        )
    if summary["total_posts"] < 3:
        recommendations.append("近 14 天产量较少，可以加大每日生成量来积累数据。")

    eng_map = summary.get("avg_engagement_by_topic") or {}
    if eng_map:
        worst = min(eng_map.items(), key=lambda kv: kv[1])
        if worst[1] < summary["avg_engagement_rate"]:
            recommendations.append(
                f"主题「{worst[0]}」表现弱于平均，建议下一轮尝试不同文风。"
            )

    if not recommendations:
        recommendations.append("数据健康，可继续按计划生成。")

    return {
        "next_topic_recommendation": next_topic,
        "topic_scores": suggested,
        "summary": summary,
        "best_titles": best,
        "recommendations": recommendations,
    }


def render_brief_text(brief: dict[str, Any]) -> str:
    """Compact prompt-friendly markdown for inclusion in a writer system msg."""
    lines = ["📊 数据分析师建议（基于历史互动数据）"]
    s = brief["summary"]
    lines.append(
        f"近 14 天: {s['total_posts']} 篇 / 总曝光 {s['total_impressions']} / "
        f"平均互动率 {s['avg_engagement_rate']:.2%}"
    )
    lines.append(f"下一轮推荐主题: {brief['next_topic_recommendation']}")

    if brief["best_titles"]:
        lines.append("历史 Top 标题:")
        for t in brief["best_titles"]:
            lines.append(f"  - {t['title']} (病毒分 {t['virality_score']})")

    lines.append("行动建议:")
    for r in brief["recommendations"]:
        lines.append(f"  • {r}")
    return "\n".join(lines)
