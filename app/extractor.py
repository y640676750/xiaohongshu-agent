import re
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


def resolve_xhs_link(url: str) -> str:
    """
    解析 xhslink 短链接跳转
    """
    try:
        r = requests.get(url, allow_redirects=True, timeout=15, headers=HEADERS)
        return r.url
    except Exception:
        return url


def get_meta_content(soup: BeautifulSoup, attrs: dict) -> str:
    tag = soup.find("meta", attrs=attrs)
    if tag and tag.get("content"):
        return tag["content"].strip()
    return ""


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
        "加载中",
        "编辑于",
        "关注",
        "赞",
        "收藏",
        "评论",
        "复制后打开",
        "查看笔记",
        "小红书号",
        "扫一扫",
        "下载小红书",
        "打开App",
    ]

    cleaned = []
    for line in lines:
        if any(k in line for k in noise_keywords):
            continue
        if len(line) <= 1:
            continue
        cleaned.append(line)

    seen = set()
    result = []
    for line in cleaned:
        if line not in seen:
            seen.add(line)
            result.append(line)

    return "\n".join(result[:120])


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
    过滤明显无关的短噪音行，并去重
    """
    drop_exact = {
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


def is_likely_author_name(line: str) -> bool:
    """
    判断一行是否更像作者名/账号名
    """
    if not line:
        return False

    # 太短，通常不像标题
    if len(line) <= 5:
        return True

    # 纯英文/数字/符号更像用户名
    if re.fullmatch(r"[A-Za-z0-9_.-]+", line):
        return True

    # 带明显账号感关键词，且长度较短
    author_keywords = [
        "测评",
        "日记",
        "日常",
        "记录",
        "分享",
        "同学",
        "学姐",
        "酱",
        "酱呀",
        "老师",
        "科技",
        "数码",
    ]
    if any(k in line for k in author_keywords) and len(line) <= 12:
        return True

    return False


def is_good_title_candidate(line: str) -> bool:
    if not line:
        return False

    if line.startswith("#"):
        return False

    if "http://" in line or "https://" in line:
        return False

    if "复制后打开" in line or "查看笔记" in line:
        return False

    if is_likely_author_name(line):
        return False

    # 标题长度控制
    if len(line) < 8 or len(line) > 40:
        return False

    # 太像标签堆
    if line.count("#") >= 2:
        return False

    return True


def extract_share_caption(raw_text: str) -> str:
    """
    从整段 Telegram 分享文案里，把链接和固定提示去掉，保留更像标题的文本
    """
    if not raw_text:
        return ""

    text = re.sub(r"https?://[^\s]+", "", raw_text)
    text = text.replace("复制后打开【小红书】查看笔记！", "")
    text = text.replace("复制后打开【小红书】", "")
    text = text.replace("查看笔记！", "")
    text = text.strip()

    return clean_text(text)


def pick_best_title(meta_title: str, body: str, share_caption: str = "") -> str:
    candidates = []

    # 1. 优先考虑分享文案里的句子
    if share_caption:
        caption_lines = [l.strip() for l in share_caption.splitlines() if l.strip()]
        candidates.extend(caption_lines[:5])

    # 2. meta/title
    if meta_title:
        meta_title = re.sub(r"\s*-\s*小红书\s*$", "", meta_title).strip()
        candidates.append(meta_title)

    # 3. 正文前几行
    body_lines = [line.strip() for line in body.splitlines() if line.strip()]
    candidates.extend(body_lines[:8])

    # 去重保序
    seen = set()
    uniq = []
    for c in candidates:
        if c and c not in seen:
            seen.add(c)
            uniq.append(c)

    def score(line: str) -> int:
        s = 0

        if is_good_title_candidate(line):
            s += 10

        # 更像小红书标题的词
        hook_words = ["原来", "难怪", "结果", "居然", "我一直以为", "第一次", "后来才发现"]
        if any(w in line for w in hook_words):
            s += 3

        # 有标点更像完整句
        if any(p in line for p in ["，", "。", "？", "！", "…"]):
            s += 2

        # 标题长度适中
        if 12 <= len(line) <= 28:
            s += 3

        if line.endswith("小红书"):
            s -= 5

        if is_likely_author_name(line):
            s -= 10

        return s

    if uniq:
        uniq.sort(key=score, reverse=True)
        best = uniq[0]
        if best:
            return best[:120]

    return "未提取到标题"


def extract_article(url: str, raw_text: str = ""):
    """
    url: 实际链接
    raw_text: Telegram 里整段分享文案（可选），用于辅助提取标题
    """
    share_caption = extract_share_caption(raw_text or "")

    url = resolve_xhs_link(url)

    r = requests.get(url, headers=HEADERS, timeout=20, allow_redirects=True)
    r.raise_for_status()

    final_url = r.url
    soup = BeautifulSoup(r.text, "html.parser")

    # 标题优先从 meta 获取
    meta_title = (
        get_meta_content(soup, {"property": "og:title"})
        or get_meta_content(soup, {"name": "twitter:title"})
        or (soup.title.get_text(strip=True) if soup.title else "")
    )

    # 描述优先从 meta 获取
    description = (
        get_meta_content(soup, {"property": "og:description"})
        or get_meta_content(soup, {"name": "description"})
        or get_meta_content(soup, {"name": "twitter:description"})
    )

    # 去掉脚本/样式
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    # 尝试抓正文容器
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

    # 用 description + 正文混合，优先拿到更干净的摘要
    if description and len(description) > 20:
        merged = f"{description}\n{raw_content[:1200]}"
    else:
        merged = raw_content[:1600]

    body, tags = split_content_and_tags(merged)
    body = normalize_body_lines(body)

    title = pick_best_title(meta_title, body, share_caption)

    return {
        "title": title,
        "body": body[:1600],
        "tags": tags[:20],
        "url": final_url,
    }