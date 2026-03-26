"""
Analyze fetched articles: classify, score value, extract content for XHS generation.
"""

import re

from langchain_core.messages import SystemMessage, HumanMessage
from app.llm import get_llm
from app.news_fetcher import fetch_page_content


ANALYZER_SYSTEM = """你是一位资深AI行业分析师。

任务：阅读下面的文章，做以下分析：

1. 用中文一句话概括文章核心内容
2. 判断分类：
   - "AI资讯"：新产品发布、公司动态、行业新闻、技术突破
   - "AI使用技巧"：工具教程、Prompt技巧、工作流方法
   - "AI工具推荐"：工具介绍、功能评测、工具对比
3. 评估价值（1-10分）：这篇文章对普通人了解AI有多大帮助？
4. 提取核心信息（3-5个要点，中文）

输出格式（严格按照此格式，不要加其他内容）：

【分类】{类别}
【评分】{1-10}
【一句话】{一句话概括}
【要点】
1. {要点1}
2. {要点2}
3. {要点3}
"""


def analyze_article(article: dict) -> dict:
    """
    Fetch full content and analyze a single article.
    Enriches article dict with: category_detected, score, oneliner, keypoints, page_content.
    """
    page_content = fetch_page_content(article["url"])
    article["page_content"] = page_content

    llm = get_llm()

    prompt = f"""标题：{article['title']}
来源：{article['source']}

摘要：{article.get('snippet', '')}

正文：{page_content if page_content else '（未能获取原文，请基于标题和摘要分析）'}"""

    msgs = [
        SystemMessage(content=ANALYZER_SYSTEM),
        HumanMessage(content=prompt),
    ]

    try:
        result = llm.invoke(msgs).content
        article["analysis"] = result

        cat = re.search(r"【分类】\s*(.+)", result)
        score = re.search(r"【评分】\s*(\d+)", result)
        oneliner = re.search(r"【一句话】\s*(.+)", result)

        article["category_detected"] = cat.group(1).strip() if cat else article["category"]
        article["score"] = int(score.group(1)) if score else 5
        article["oneliner"] = oneliner.group(1).strip() if oneliner else article["title"]
        article["analyzed"] = True
    except Exception as e:
        print(f"   ⚠️ 分析失败: {e}")
        article["analysis"] = ""
        article["category_detected"] = article["category"]
        article["score"] = 5
        article["oneliner"] = article["title"]
        article["analyzed"] = False

    return article


def rank_articles(articles: list[dict], max_items: int = 5) -> list[dict]:
    """Pick the most valuable articles for XHS content generation."""
    scored = sorted(articles, key=lambda a: a.get("score", 0), reverse=True)
    return scored[:max_items]


def build_source_links_message(articles: list[dict]) -> str:
    """Build Telegram message listing original article links."""
    if not articles:
        return ""

    lines = ["📎 本轮资讯原文链接\n"]
    for i, a in enumerate(articles, 1):
        lines.append(f"{i}. 【{a['source']}】{a['title']}")
        lines.append(f"   🔗 {a['url']}\n")

    return "\n".join(lines)
