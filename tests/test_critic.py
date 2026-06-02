"""Critic agent: heuristic mode (works without API key)."""

import os

import pytest


@pytest.fixture(autouse=True)
def no_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)


def test_critic_short_post_is_flagged():
    from agents.critic import review_post

    r = review_post("太短")
    assert r.overall < 7
    assert any("过短" in s for s in r.suggestions)


def test_critic_balanced_post_passes():
    from agents.critic import review_post

    body = (
        "这次实测了 3 个 AI 写作工具，结论先放在开头：A 工具最适合写汇报，B 最适合改简历。"
        "下面我会一个一个对比，包括具体步骤、效果对比、价格情况，看完你就能直接抄作业。"
        "用了之后我每天能省 1 小时，工作流也跟着稳定了。"
        "想用对 AI 工具的，看完再选不亏。具体玩法和模板我都整理好了，按步骤来就行。"
        "更详细的对比、实战案例、避坑指南都在这里，省去你自己摸索的时间。"
        "我还录了一段 30 秒的演示视频，看完应该就能上手用了。"
        "感兴趣的可以点个收藏，下一篇我会展开讲怎么把这些工具串成自己的工作流。"
        "#AI #ChatGPT #工具推荐 #效率 #职场 #小红书 #实测 #教程"
    )
    r = review_post(body)
    assert r.overall >= 6.5


def test_critic_flags_unrealistic_claims():
    from agents.critic import review_post

    body = "学会这个 AI，年薪百万不是梦！#AI #暴富"
    r = review_post(body)
    assert any("夸大" in s for s in r.suggestions)
