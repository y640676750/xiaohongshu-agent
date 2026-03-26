"""
Use LLM to summarize, categorize, and extract key insights from fetched articles.
Produces structured summaries ready for Telegram delivery and content generation.
"""

from langchain_core.messages import SystemMessage, HumanMessage
from app.llm import get_llm
from app.news_fetcher import fetch_page_content


SUMMARIZER_SYSTEM = """你是一位资深AI行业分析师和科技博主助理。

你的任务是：
1. 阅读给定的文章内容
2. 用中文写一段200-300字的精炼摘要
3. 提取3-5个核心要点
4. 判断这篇文章属于哪个类别：
   - "AI资讯"：新产品发布、公司动态、行业新闻、政策变化、融资消息
   - "AI使用技巧"：工具教程、Prompt技巧、工作流方法、实操指南
   - "AI工具推荐"：工具介绍、功能评测、工具对比
5. 评估这篇文章的价值（1-10分）：是否值得分享给关注AI的小红书读者
6. 提取可用于小红书内容创作的灵感要点

输出格式（严格按照此格式）：

【分类】{类别}
【价值评分】{1-10}
【一句话总结】{一句话概括}
【摘要】
{200-300字摘要}
【核心要点】
1. {要点1}
2. {要点2}
3. {要点3}
【小红书创作灵感】
{可以怎么把这个内容变成小红书爆款的思路，1-2句话}
"""


BATCH_DIGEST_SYSTEM = """你是一位资深AI行业分析师，负责每日AI资讯汇总。

你的任务是把多条AI新闻/文章汇总成一份结构清晰的中文日报，适合通过Telegram发送给关注AI的读者。

要求：
1. 按重要性排序
2. 每条新闻用1-2句话概括核心信息
3. 标注来源和原文链接
4. 在最后给出"今日看点"总结（2-3句话概括今天AI领域最值得关注的趋势）
5. 语言简洁专业，但要通俗易懂

输出格式：

📡 AI日报 | {日期}

🔥 重要资讯

{按重要性排列的新闻条目，每条格式：}
{序号}. 【{来源}】{一句话标题摘要}
   {补充1-2句关键信息}
   🔗 {原文链接}

💡 技巧 & 工具

{AI使用技巧/工具类内容条目}
{序号}. 【{来源}】{一句话标题摘要}
   {补充信息}
   🔗 {原文链接}

📌 今日看点
{2-3句话总结今天最值得关注的AI趋势}
"""


def summarize_article(article: dict) -> dict:
    """
    Fetch full content and produce a structured summary for a single article.
    Returns the article dict enriched with summary fields.
    """
    llm = get_llm()

    page_content = fetch_page_content(article["url"])

    content_for_llm = f"""
标题：{article['title']}
来源：{article['source']}
链接：{article['url']}

原文摘要：
{article.get('snippet', '')}

原文内容：
{page_content if page_content else '（未能获取原文内容，请基于标题和摘要进行分析）'}
"""

    msgs = [
        SystemMessage(content=SUMMARIZER_SYSTEM),
        HumanMessage(content=content_for_llm),
    ]

    try:
        result = llm.invoke(msgs).content
        article["summary"] = result
        article["summarized"] = True
    except Exception as e:
        print(f"[Summarizer] Error summarizing {article['title']}: {e}")
        article["summary"] = ""
        article["summarized"] = False

    return article


def generate_daily_digest(articles: list[dict]) -> str:
    """
    Generate a daily digest from a batch of articles.
    This is the main output sent to Telegram.
    """
    if not articles:
        return "📡 暂无新的AI资讯"

    llm = get_llm()

    articles_text = ""
    for i, a in enumerate(articles, 1):
        articles_text += f"""
---
文章 {i}:
标题：{a['title']}
来源：{a['source']}
分类：{a['category']}
链接：{a['url']}
摘要：{a.get('snippet', '')}
AI摘要：{a.get('summary', '')[:300]}
---
"""

    from datetime import datetime
    today = datetime.now().strftime("%Y年%m月%d日")

    msgs = [
        SystemMessage(content=BATCH_DIGEST_SYSTEM),
        HumanMessage(content=f"今天是{today}，以下是今天收集到的{len(articles)}条AI相关文章，请生成日报：\n\n{articles_text}"),
    ]

    try:
        return llm.invoke(msgs).content
    except Exception as e:
        print(f"[Digest] Error generating digest: {e}")
        return _fallback_digest(articles, today)


def _fallback_digest(articles: list[dict], date_str: str) -> str:
    """Simple fallback digest without LLM."""
    lines = [f"📡 AI日报 | {date_str}\n"]

    news = [a for a in articles if a["category"] == "资讯"]
    tips = [a for a in articles if a["category"] != "资讯"]

    if news:
        lines.append("🔥 重要资讯\n")
        for i, a in enumerate(news, 1):
            lines.append(f"{i}. 【{a['source']}】{a['title']}")
            if a.get("snippet"):
                lines.append(f"   {a['snippet'][:100]}")
            lines.append(f"   🔗 {a['url']}\n")

    if tips:
        lines.append("💡 技巧 & 工具\n")
        for i, a in enumerate(tips, 1):
            lines.append(f"{i}. 【{a['source']}】{a['title']}")
            if a.get("snippet"):
                lines.append(f"   {a['snippet'][:100]}")
            lines.append(f"   🔗 {a['url']}\n")

    return "\n".join(lines)


def pick_best_for_content(articles: list[dict], max_items: int = 3) -> list[dict]:
    """
    From summarized articles, pick the best ones for turning into
    XHS content. Prioritizes high-value, recent articles.
    """
    summarized = [a for a in articles if a.get("summarized")]
    if not summarized:
        return articles[:max_items]

    def _extract_score(article: dict) -> int:
        summary = article.get("summary", "")
        try:
            import re
            match = re.search(r"【价值评分】\s*(\d+)", summary)
            if match:
                return int(match.group(1))
        except Exception:
            pass
        return 5

    summarized.sort(key=_extract_score, reverse=True)
    return summarized[:max_items]
