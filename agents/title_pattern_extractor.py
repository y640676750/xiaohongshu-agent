import re
from pathlib import Path

INPUT_FILE = "kb/performance_pool/processed/top_titles.txt"
OUTPUT_FILE = "kb/title_patterns_learned.txt"


def normalize_title(title: str):

    patterns = [
        r"我.*?以为",
        r"难怪我",
        r"原来",
        r"为什么我",
        r"第一次",
    ]

    for p in patterns:
        title = re.sub(p + r".*", p + "X", title)

    title = re.sub(r"[0-9]+", "X", title)

    return title


def extract_patterns():

    path = Path(INPUT_FILE)

    if not path.exists():
        print("没有找到爆款标题")
        return

    titles = [
        l.strip()
        for l in path.read_text(encoding="utf-8").splitlines()
        if l.strip()
    ]

    patterns = set()

    for t in titles:
        p = normalize_title(t)
        patterns.add(p)

    Path(OUTPUT_FILE).write_text("\n".join(patterns), encoding="utf-8")

    print("标题结构已生成")