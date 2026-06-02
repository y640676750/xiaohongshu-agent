"""Render analytics into Markdown / HTML / Telegram text.

This file is meant to be lightweight - no `pandas` / `matplotlib`. Pure
stdlib so the analytics report works on any environment (CI, MCP, CLI).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Optional

from app import analytics


def _bar(value: float, max_value: float, width: int = 20) -> str:
    if max_value <= 0:
        return ""
    n = max(0, min(width, int(round(value / max_value * width))))
    return "█" * n + "░" * (width - n)


def render_markdown(days: int = 14) -> str:
    report = analytics.full_report(days)
    s = report["summary"]

    lines: list[str] = []
    lines.append(f"# 小红书 AI Agent 数据分析报告")
    lines.append("")
    lines.append(f"- 报告生成时间: `{report['generated_at']}`")
    lines.append(f"- 统计窗口: 最近 **{days}** 天")
    lines.append("")
    lines.append("## 总览")
    lines.append("")
    lines.append(f"| 指标 | 数值 |")
    lines.append(f"| --- | --- |")
    lines.append(f"| 总文案数 | {s['total_posts']} |")
    lines.append(f"| 总曝光 | {s['total_impressions']} |")
    lines.append(f"| 总点赞 | {s['total_likes']} |")
    lines.append(f"| 总评论 | {s['total_comments']} |")
    lines.append(f"| 平均互动率 | {s['avg_engagement_rate']:.2%} |")
    lines.append("")

    lines.append("## 按状态分布")
    lines.append("")
    for status, n in s["by_status"].items():
        lines.append(f"- {status}: **{n}**")
    if not s["by_status"]:
        lines.append("- 暂无")
    lines.append("")

    lines.append("## 按主题分布与互动率")
    lines.append("")
    eng_map = s["avg_engagement_by_topic"]
    max_eng = max(eng_map.values()) if eng_map else 0.0
    lines.append("| 主题 | 篇数 | 平均互动率 | 可视化 |")
    lines.append("| --- | --- | --- | --- |")
    for topic, count in s["by_topic"].items():
        eng = eng_map.get(topic, 0.0)
        lines.append(f"| {topic} | {count} | {eng:.2%} | `{_bar(eng, max_eng)}` |")
    if not s["by_topic"]:
        lines.append("| - | - | - | - |")
    lines.append("")

    lines.append("## Top 10 文案")
    lines.append("")
    lines.append("| 排名 | 标题 | 主题 | 曝光 | 互动 | 互动率 | 病毒分 |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- |")
    for i, p in enumerate(report["top_posts"], 1):
        title = (p["title"] or "")[:30]
        lines.append(
            f"| {i} | {title} | {p['topic'] or '-'} | {p['impressions']} | "
            f"{p['interactions']} | {p['engagement_rate']:.2%} | {p['virality_score']:.1f} |"
        )
    if not report["top_posts"]:
        lines.append("| - | 暂无数据 | - | - | - | - | - |")
    lines.append("")

    lines.append("## 14 天发布趋势")
    lines.append("")
    lines.append("| 日期 | 篇数 | 平均互动率 |")
    lines.append("| --- | --- | --- |")
    for d in report["trend"]:
        lines.append(f"| {d['date']} | {d['posts']} | {d['avg_engagement_rate']:.2%} |")
    lines.append("")

    lines.append("## 下一轮建议主题（自动）")
    lines.append("")
    for t in report["suggested_topics"]:
        lines.append(
            f"- **{t['topic']}** - 综合分 `{t['score']}`（历史互动率 {t['engagement_rate']:.2%}）"
        )
    lines.append("")

    return "\n".join(lines)


def render_telegram(days: int = 7) -> str:
    """A short, mobile-friendly version for Telegram."""
    report = analytics.full_report(days)
    s = report["summary"]
    lines = [
        "📊 小红书 Agent 数据日报",
        f"窗口: 近 {days} 天 / 共 {s['total_posts']} 篇",
        f"曝光 {s['total_impressions']}  ·  点赞 {s['total_likes']}  ·  评论 {s['total_comments']}",
        f"平均互动率: {s['avg_engagement_rate']:.2%}",
        "",
        "🏆 Top 3 文案",
    ]
    for i, p in enumerate(report["top_posts"][:3], 1):
        lines.append(f"  {i}. {p['title'] or '-'[:32]}  ({p['virality_score']:.1f})")
    lines.append("")
    lines.append("🎯 下一轮建议主题")
    for t in report["suggested_topics"][:3]:
        lines.append(f"  • {t['topic']} (分数 {t['score']})")
    return "\n".join(lines)


HTML_TEMPLATE = """<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8" />
<title>小红书 AI Agent 数据分析</title>
<style>
  body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;background:#fafafa;color:#222;max-width:960px;margin:40px auto;padding:0 20px;}}
  h1{{border-bottom:3px solid #ff2442;padding-bottom:8px;}}
  h2{{margin-top:32px;color:#ff2442;}}
  table{{width:100%;border-collapse:collapse;margin:12px 0;background:#fff;box-shadow:0 1px 2px rgba(0,0,0,.06);}}
  th,td{{padding:8px 12px;border-bottom:1px solid #eee;text-align:left;font-size:14px;}}
  th{{background:#fff5f7;}}
  .bar{{background:#ffe4ea;display:inline-block;height:10px;border-radius:4px;vertical-align:middle;}}
  .badge{{display:inline-block;padding:2px 8px;background:#ff2442;color:#fff;border-radius:10px;font-size:12px;}}
  small{{color:#888;}}
</style>
</head>
<body>
{body}
<hr/>
<small>生成时间 {generated_at}</small>
</body>
</html>
"""


def render_html(days: int = 14) -> str:
    md = render_markdown(days)
    body_html = _markdown_to_html(md)
    return HTML_TEMPLATE.format(
        body=body_html,
        generated_at=analytics._now().isoformat(),
    )


def _markdown_to_html(md: str) -> str:
    """Tiny markdown → html converter, just enough for our report."""
    out: list[str] = []
    in_table = False
    table_header_done = False
    for line in md.split("\n"):
        if line.startswith("# "):
            out.append(f"<h1>{line[2:].strip()}</h1>")
            continue
        if line.startswith("## "):
            out.append(f"<h2>{line[3:].strip()}</h2>")
            continue
        if line.startswith("- "):
            out.append(f"<p>• {line[2:].strip()}</p>")
            continue
        if line.startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if not in_table:
                out.append("<table>")
                in_table = True
                table_header_done = False
            if set("".join(cells).replace(" ", "")) <= {"-"}:
                table_header_done = True
                continue
            tag = "th" if not table_header_done else "td"
            row = "".join(f"<{tag}>{c}</{tag}>" for c in cells)
            out.append(f"<tr>{row}</tr>")
            continue
        if in_table and not line.startswith("|"):
            out.append("</table>")
            in_table = False
        out.append(f"<p>{line}</p>" if line.strip() else "")
    if in_table:
        out.append("</table>")
    return "\n".join(out)


def write_report(
    out_dir: str = "outputs/reports",
    days: int = 14,
    formats: tuple[str, ...] = ("md", "html", "json"),
) -> dict[str, str]:
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    ts = analytics._now().strftime("%Y%m%d_%H%M%S")
    written: dict[str, str] = {}
    if "md" in formats:
        p = Path(out_dir) / f"report_{ts}.md"
        p.write_text(render_markdown(days), encoding="utf-8")
        written["md"] = str(p)
    if "html" in formats:
        p = Path(out_dir) / f"report_{ts}.html"
        p.write_text(render_html(days), encoding="utf-8")
        written["html"] = str(p)
    if "json" in formats:
        p = Path(out_dir) / f"report_{ts}.json"
        p.write_text(analytics.to_json(analytics.full_report(days)), encoding="utf-8")
        written["json"] = str(p)
    return written


def main():
    import sys

    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

    ap = argparse.ArgumentParser(description="生成数据分析报告")
    ap.add_argument("--days", type=int, default=14)
    ap.add_argument("--out", default="outputs/reports")
    ap.add_argument(
        "--format",
        nargs="+",
        default=["md", "html", "json"],
        choices=["md", "html", "json"],
    )
    ap.add_argument(
        "--telegram",
        action="store_true",
        help="同时把简版报告推送到 Telegram",
    )
    args = ap.parse_args()

    written = write_report(args.out, args.days, tuple(args.format))
    print("✅ 报告已生成:")
    for fmt, path in written.items():
        print(f"   {fmt}: {path}")

    if args.telegram:
        from app.notifier import send_telegram, send_telegram_file

        send_telegram(render_telegram(min(args.days, 7)))
        if "md" in written:
            send_telegram_file(written["md"], "📊 数据分析报告 (MD)")
        if "html" in written:
            send_telegram_file(written["html"], "📊 数据分析报告 (HTML)")


if __name__ == "__main__":
    main()
