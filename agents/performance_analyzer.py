import csv
from pathlib import Path

RAW_FILE = "kb/performance_pool/raw/posts.csv"
OUTPUT_FILE = "kb/performance_pool/processed/top_titles.txt"
VIRAL_MEMORY = "kb/viral_memory.txt"


def calculate_score(impressions, clicks, conversions):
    if impressions == 0:
        return 0

    ctr = clicks / impressions
    cvr = conversions / clicks if clicks else 0

    score = ctr * 0.6 + cvr * 0.4
    return score


def analyze_performance(top_k=20):

    path = Path(RAW_FILE)

    if not path.exists():
        print("没有找到 performance 数据")
        return

    results = []

    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            title = row["title"]
            impressions = int(row["impressions"])
            clicks = int(row["clicks"])
            conversions = int(row["conversions"])

            score = calculate_score(impressions, clicks, conversions)

            results.append((title, score))

    results.sort(key=lambda x: x[1], reverse=True)

    top_titles = [r[0] for r in results[:top_k]]

    Path(OUTPUT_FILE).write_text("\n".join(top_titles), encoding="utf-8")

    with open(VIRAL_MEMORY, "a", encoding="utf-8") as f:
        for t in top_titles:
            f.write(t + "\n")

    print("爆款标题已更新")