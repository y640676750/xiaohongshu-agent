"""Critic agent.

Reviews a generated Xiaohongshu post and returns a structured JSON-ish
score plus actionable suggestions. The orchestrator uses the score to
decide whether to ship the post or send it back to the writer.

The critic only needs the post text - no API key or external service.
If an LLM is available it will be used for richer feedback, otherwise a
deterministic heuristic kicks in (so tests / dry runs still work).
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, asdict
from typing import Optional

from langchain_core.messages import HumanMessage, SystemMessage

from app.llm import get_llm


CRITIC_SYSTEM = """你是一位专业的小红书内容审稿编辑。

请对下面的小红书文案打分（每项 0-10 分）并给出 1-2 句改进建议：
1. 标题点击欲望 click_appeal
2. 正文信息密度 info_density
3. 小红书口语感 tone_fit
4. 合规与真实性 compliance（不夸大、不焦虑营销）
5. 标签恰当度 tag_fit

最后给出一个 0-10 的综合分 overall。

严格输出 JSON：
{
  "click_appeal": 0-10,
  "info_density": 0-10,
  "tone_fit": 0-10,
  "compliance": 0-10,
  "tag_fit": 0-10,
  "overall": 0-10,
  "suggestions": ["...", "..."],
  "ship": true/false   // overall >= 7 才能 ship
}
"""


@dataclass
class CriticResult:
    overall: float
    click_appeal: float = 0
    info_density: float = 0
    tone_fit: float = 0
    compliance: float = 0
    tag_fit: float = 0
    suggestions: list[str] = None  # type: ignore[assignment]
    ship: bool = False
    raw: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        d["suggestions"] = list(self.suggestions or [])
        return d


_RISKY_PATTERNS = [
    r"年薪百万",
    r"月入十万",
    r"暴富",
    r"取代所有人",
    r"100%\s*确定",
    r"绝对",
    r"永远\s*不会",
]
_GOOD_SIGNALS = ["#", "技巧", "实测", "对比", "步骤", "教程", "推荐"]


def _heuristic_score(text: str) -> CriticResult:
    """Deterministic fallback so the critic always works without an API key."""
    score = 7.0
    notes: list[str] = []

    if len(text) < 250:
        score -= 1.5
        notes.append("正文过短，信息密度可能不足，建议加 1-2 个具体例子或步骤。")

    if len(text) > 1600:
        score -= 1.0
        notes.append("正文偏长，小红书读者更习惯 400-800 字范围。")

    hashtags = re.findall(r"#[\w\u4e00-\u9fff]+", text)
    if len(hashtags) < 5:
        score -= 1.0
        notes.append("话题标签不足 5 个，建议补足到 8-10 个。")
    elif len(hashtags) > 15:
        score -= 0.5
        notes.append("话题标签过多，控制在 10 个左右更利于推荐。")

    if not any(g in text for g in _GOOD_SIGNALS):
        score -= 0.5
        notes.append("缺少具体抓手词（实测/对比/步骤等），可加强干货感。")

    for pat in _RISKY_PATTERNS:
        if re.search(pat, text):
            score -= 1.5
            notes.append(f"包含夸大或焦虑词「{pat}」，需要替换为更克制的表达。")

    score = max(0.0, min(10.0, score))

    return CriticResult(
        overall=round(score, 1),
        click_appeal=round(min(10.0, score + 0.5), 1),
        info_density=round(score, 1),
        tone_fit=round(score, 1),
        compliance=10.0 if not notes or all("夸大" not in n for n in notes) else 6.0,
        tag_fit=round(min(10.0, 6 + len(hashtags) / 2), 1),
        suggestions=notes or ["内容质量良好，可直接发布。"],
        ship=score >= 7,
        raw="heuristic",
    )


def _safe_json_loads(text: str) -> Optional[dict]:
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except Exception:
        return None


def review_post(post_text: str) -> CriticResult:
    """Score a post. Uses LLM if `OPENAI_API_KEY` is set, falls back otherwise."""
    if not os.getenv("OPENAI_API_KEY"):
        return _heuristic_score(post_text)

    try:
        llm = get_llm()
        msgs = [
            SystemMessage(content=CRITIC_SYSTEM),
            HumanMessage(content=f"待评审小红书文案：\n\n{post_text}"),
        ]
        raw = llm.invoke(msgs).content
        data = _safe_json_loads(raw)
        if not data:
            heur = _heuristic_score(post_text)
            heur.raw = raw
            return heur
        overall = float(data.get("overall") or 0)
        return CriticResult(
            overall=overall,
            click_appeal=float(data.get("click_appeal") or 0),
            info_density=float(data.get("info_density") or 0),
            tone_fit=float(data.get("tone_fit") or 0),
            compliance=float(data.get("compliance") or 0),
            tag_fit=float(data.get("tag_fit") or 0),
            suggestions=list(data.get("suggestions") or []),
            ship=bool(data.get("ship", overall >= 7)),
            raw=raw,
        )
    except Exception as e:
        result = _heuristic_score(post_text)
        result.suggestions.insert(0, f"LLM 审稿失败，降级到启发式评估: {e}")
        return result
