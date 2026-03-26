"""
AI news and tips sources configuration.

Each source has:
  - name: human-readable name
  - type: "rss" or "web"
  - url: feed URL or page URL
  - category: "资讯" or "技巧" (used for routing to the right content pipeline)
"""

RSS_SOURCES = [
    {
        "name": "OpenAI Blog",
        "url": "https://openai.com/blog/rss.xml",
        "category": "资讯",
    },
    {
        "name": "Google AI Blog",
        "url": "https://blog.google/technology/ai/rss/",
        "category": "资讯",
    },
    {
        "name": "MIT Technology Review - AI",
        "url": "https://www.technologyreview.com/topic/artificial-intelligence/feed",
        "category": "资讯",
    },
    {
        "name": "The Verge - AI",
        "url": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
        "category": "资讯",
    },
    {
        "name": "Ars Technica - AI",
        "url": "https://feeds.arstechnica.com/arstechnica/technology-lab",
        "category": "资讯",
    },
    {
        "name": "Hugging Face Blog",
        "url": "https://huggingface.co/blog/feed.xml",
        "category": "技巧",
    },
    {
        "name": "Towards Data Science (Medium)",
        "url": "https://towardsdatascience.com/feed",
        "category": "技巧",
    },
    {
        "name": "AI工具集",
        "url": "https://ai-bot.cn/feed/",
        "category": "技巧",
    },
]

WEB_SOURCES = [
    {
        "name": "36氪 AI频道",
        "url": "https://36kr.com/information/AI/",
        "category": "资讯",
        "selector": "a.article-item-title",
        "base_url": "https://36kr.com",
    },
    {
        "name": "量子位",
        "url": "https://www.qbitai.com/",
        "category": "资讯",
        "selector": "h4.post-title a, h2.post-title a",
        "base_url": "https://www.qbitai.com",
    },
    {
        "name": "机器之心",
        "url": "https://www.jiqizhixin.com/",
        "category": "资讯",
        "selector": "a.article-item__title",
        "base_url": "https://www.jiqizhixin.com",
    },
]
