"""
Fetch AI news from RSS feeds and web sources.

Returns a list of ArticleItem dicts with:
  title, url, source, category, published, snippet
"""

import hashlib
import json
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import feedparser
import requests
from bs4 import BeautifulSoup

HISTORY_FILE = "kb/news_history.json"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}
MAX_AGE_HOURS = 48


def _url_hash(url: str) -> str:
    return hashlib.md5(url.strip().lower().encode()).hexdigest()


def _load_history() -> dict:
    p = Path(HISTORY_FILE)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_history(history: dict):
    p = Path(HISTORY_FILE)
    p.parent.mkdir(parents=True, exist_ok=True)

    cutoff = (datetime.now(timezone.utc) - timedelta(days=14)).isoformat()
    trimmed = {k: v for k, v in history.items() if v.get("seen_at", "") > cutoff}

    p.write_text(json.dumps(trimmed, ensure_ascii=False, indent=2), encoding="utf-8")


def _is_seen(history: dict, url: str) -> bool:
    return _url_hash(url) in history


def _mark_seen(history: dict, url: str):
    history[_url_hash(url)] = {"url": url, "seen_at": datetime.now(timezone.utc).isoformat()}


def _parse_published(entry) -> Optional[str]:
    for field in ("published_parsed", "updated_parsed"):
        tp = getattr(entry, field, None)
        if tp:
            try:
                dt = datetime(*tp[:6], tzinfo=timezone.utc)
                return dt.isoformat()
            except Exception:
                pass
    for field in ("published", "updated"):
        val = getattr(entry, field, None)
        if val:
            return str(val)
    return None


def _is_recent(published_str: Optional[str], max_hours: int = MAX_AGE_HOURS) -> bool:
    if not published_str:
        return True
    try:
        from email.utils import parsedate_to_datetime
        dt = parsedate_to_datetime(published_str) if "T" not in published_str else datetime.fromisoformat(published_str)
        cutoff = datetime.now(timezone.utc) - timedelta(hours=max_hours)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt > cutoff
    except Exception:
        return True


def _clean_html(html_text: str) -> str:
    if not html_text:
        return ""
    soup = BeautifulSoup(html_text, "html.parser")
    return soup.get_text(separator=" ", strip=True)[:500]


def _is_ai_related(title: str, snippet: str) -> bool:
    text = (title + " " + snippet).lower()
    ai_keywords = [
        "ai", "artificial intelligence", "机器学习", "深度学习",
        "大模型", "llm", "gpt", "claude", "gemini", "chatgpt",
        "copilot", "人工智能", "生成式", "generative",
        "transformer", "neural", "openai", "anthropic", "google ai",
        "midjourney", "stable diffusion", "sora", "大语言模型",
        "prompt", "agent", "rag", "langchain", "hugging face",
        "meta ai", "llama", "mistral", "ai工具", "ai应用",
    ]
    return any(kw in text for kw in ai_keywords)


def fetch_rss(source: dict, history: dict) -> list[dict]:
    """Fetch articles from a single RSS source."""
    articles = []
    try:
        feed = feedparser.parse(source["url"])
        for entry in feed.entries[:20]:
            url = getattr(entry, "link", "")
            if not url or _is_seen(history, url):
                continue

            title = getattr(entry, "title", "").strip()
            if not title:
                continue

            snippet = _clean_html(
                getattr(entry, "summary", "") or getattr(entry, "description", "")
            )

            published = _parse_published(entry)
            if not _is_recent(published):
                continue

            if not _is_ai_related(title, snippet):
                continue

            articles.append({
                "title": title,
                "url": url,
                "source": source["name"],
                "category": source["category"],
                "published": published or datetime.now(timezone.utc).isoformat(),
                "snippet": snippet,
            })
    except Exception as e:
        print(f"[RSS] Error fetching {source['name']}: {e}")

    return articles


def fetch_web(source: dict, history: dict) -> list[dict]:
    """Scrape article links from a web page."""
    articles = []
    try:
        r = requests.get(source["url"], headers=HEADERS, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        links = soup.select(source.get("selector", "a"))[:15]
        base = source.get("base_url", "")

        for a_tag in links:
            href = a_tag.get("href", "")
            if not href:
                continue
            if href.startswith("/"):
                href = base.rstrip("/") + href

            if not href.startswith("http"):
                continue

            if _is_seen(history, href):
                continue

            title = a_tag.get_text(strip=True)
            if not title or len(title) < 6:
                continue

            if not _is_ai_related(title, ""):
                continue

            articles.append({
                "title": title,
                "url": href,
                "source": source["name"],
                "category": source["category"],
                "published": datetime.now(timezone.utc).isoformat(),
                "snippet": "",
            })
    except Exception as e:
        print(f"[WEB] Error fetching {source['name']}: {e}")

    return articles


def fetch_page_content(url: str, max_chars: int = 3000) -> str:
    """Fetch the main text content of a web page for summarization."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=20, allow_redirects=True)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        for tag in soup(["script", "style", "noscript", "nav", "footer", "header"]):
            tag.decompose()

        content_selectors = [
            "article",
            '[class*="article-content"]',
            '[class*="post-content"]',
            '[class*="entry-content"]',
            '[class*="content"]',
            "main",
        ]

        for sel in content_selectors:
            nodes = soup.select(sel)
            for node in nodes:
                text = node.get_text("\n", strip=True)
                if len(text) > 200:
                    return text[:max_chars]

        return soup.get_text("\n", strip=True)[:max_chars]
    except Exception as e:
        print(f"[PAGE] Error fetching {url}: {e}")
        return ""


def fetch_all_news(rss_sources: list, web_sources: list) -> list[dict]:
    """
    Fetch from all configured sources, dedup against history, return new articles.
    """
    history = _load_history()
    all_articles = []

    for src in rss_sources:
        items = fetch_rss(src, history)
        all_articles.extend(items)
        if items:
            print(f"  [RSS] {src['name']}: {len(items)} new articles")
        time.sleep(1)

    for src in web_sources:
        items = fetch_web(src, history)
        all_articles.extend(items)
        if items:
            print(f"  [WEB] {src['name']}: {len(items)} new articles")
        time.sleep(1)

    for article in all_articles:
        _mark_seen(history, article["url"])

    _save_history(history)

    return all_articles
