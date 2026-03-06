import re
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


def clean_text(text: str) -> str:
    text = text.replace("\xa0", " ").replace("\u200b", "")
    lines = [line.strip() for line in text.splitlines()]
    lines = [line for line in lines if line]

    noise_keywords = [
        "ICP备",
        "营业执照",
        "互联网药品信息服务资格证",
        "违法不良信息举报",
        "网络文化经营许可证",
        "增值电信业务经营许可证",
        "算法备案",
        "地址：",
        "电话：",
        "更多",
        "发现",
        "发布",
        "通知",
        "创作中心",
        "业务合作",
        "小红书",
        "加载中",
        "编辑于",
        "关注",
        "赞",
        "收藏",
        "评论",
    ]

    cleaned = []
    for line in lines:
        if any(k in line for k in noise_keywords):
            continue
        if len(line) <= 1:
            continue
        cleaned.append(line)

    # 去重但保序
    seen = set()
    result = []
    for line in cleaned:
        if line not in seen:
            seen.add(line)
            result.append(line)

    return "\n".join(result[:120])


def get_meta_content(soup: BeautifulSoup, attrs: dict) -> str:
    tag = soup.find("meta", attrs=attrs)
    if tag and tag.get("content"):
        return tag["content"].strip()
    return ""


def split_content_and_tags(text: str):
    """
    把正文和 #话题标签 拆开
    """
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    body_lines = []
    tags = []

    for line in lines:
        # 单独一行是标签
        if line.startswith("#"):
            tags.extend(re.findall(r"#\S+", line))
            continue

        # 行内也可能混有标签
        inline_tags = re.findall(r"#\S+", line)
        if inline_tags:
            tags.extend(inline_tags)
            line = re.sub(r"#\S+", "", line).strip()

        if line:
            body_lines.append(line)

    # 标签去重保序
    seen = set()
    final_tags = []
    for tag in tags:
        if tag not in seen:
            seen.add(tag)
            final_tags.append(tag)

    return "\n".join(body_lines).strip(), final_tags


def normalize_body_lines(body: str) -> str:
    """
    进一步过滤明显无关的短噪音行，并去重
    """
    drop_exact = {
        "sunny心理测试",
        "关注",
        "加载中",
    }

    lines = [line.strip() for line in body.splitlines() if line.strip()]
    filtered = []
    seen = set()

    for line in lines:
        if line in drop_exact:
            continue
        if re.fullmatch(r"编辑于\s*\d{2}-\d{2}", line):
            continue
        if line in seen:
            continue

        seen.add(line)
        filtered.append(line)

    return "\n".join(filtered[:50]).strip()


def extract_article(url: str):
    r = requests.get(url, headers=HEADERS, timeout=20, allow_redirects=True)
    r.raise_for_status()

    final_url = r.url
    soup = BeautifulSoup(r.text, "html.parser")

    # 1. 标题优先从 meta 里拿
    title = (
        get_meta_content(soup, {"property": "og:title"})
        or get_meta_content(soup, {"name": "twitter:title"})
        or (soup.title.get_text(strip=True) if soup.title else "")
    )

    # 2. 描述优先从 meta 里拿
    description = (
        get_meta_content(soup, {"property": "og:description"})
        or get_meta_content(soup, {"name": "description"})
        or get_meta_content(soup, {"name": "twitter:description"})
    )

    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    content_candidates = []

    selectors = [
        "article",
        '[class*="content"]',
        '[class*="desc"]',
        '[class*="detail"]',
        '[class*="note"]',
        '[id*="content"]',
    ]

    for sel in selectors:
        for node in soup.select(sel):
            txt = node.get_text("\n", strip=True)
            if txt and len(txt) > 80:
                content_candidates.append(txt)

    if content_candidates:
        raw_content = max(content_candidates, key=len)
    else:
        raw_content = soup.get_text("\n", strip=True)

    raw_content = clean_text(raw_content)

    if description and len(description) > 20:
        merged = f"{description}\n{raw_content[:1200]}"
    else:
        merged = raw_content[:1600]

    body, tags = split_content_and_tags(merged)
    body = normalize_body_lines(body)

    clean_title = clean_text(title)[:120]

    # 如果标题为空，就从正文前几行里兜底提取
    if not clean_title:
        body_lines = [line.strip() for line in body.splitlines() if line.strip()]
        for line in body_lines[:5]:
            if (
                6 <= len(line) <= 40
                and not line.startswith("#")
                and "点击" not in line
                and "话题标签" not in line
            ):
                clean_title = line
                break

    if not clean_title:
        clean_title = "未提取到标题"

    return {
        "title": clean_title,
        "body": body[:1600],
        "tags": tags[:20],
        "url": final_url,
    }