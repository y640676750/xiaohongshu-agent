import argparse
import random
from app.viral_memory import save_viral_pattern

from app.schema import Brief
from agents.writer import write_post
from agents.title_generator import generate_titles
from agents.title_ranker import rank_titles
from app.utils import save_output
from app.notifier import send_telegram, send_telegram_file
from app.topic_styles import TOPIC_STYLES


def pick_styles_for_topic(topic: str, count: int = 3):
    styles = TOPIC_STYLES.get(topic, ["自然口语"])
    if len(styles) >= count:
        return random.sample(styles, count)
    result = []
    while len(result) < count:
        result.extend(styles)
    return result[:count]


def build_briefs(topic: str):
    if topic == "AI资讯":
        return [
            Brief(
                link="{LINK}",
                selling_point="第一时间带你了解AI行业最新动态，大模型更新、新产品发布、技术突破一网打尽",
                audience="关注AI发展、想掌握行业趋势的职场人和科技爱好者",
                keywords=["AI资讯", "大模型", "GPT", "Claude", "AI动态", "科技前沿"],
            ),
            Brief(
                link="{LINK}",
                selling_point="深度解读AI行业变化，帮你看懂技术趋势背后的机会",
                audience="想了解AI对自己行业影响的职场人士",
                keywords=["AI趋势", "行业变革", "技术解读", "人工智能", "未来趋势"],
            ),
            Brief(
                link="{LINK}",
                selling_point="最新AI产品实测体验，帮你判断值不值得用",
                audience="想尝试新AI产品但不知道从何下手的人",
                keywords=["AI产品", "实测", "体验", "新品发布", "AI评测"],
            ),
        ]
    elif topic == "AI使用技巧":
        return [
            Brief(
                link="{LINK}",
                selling_point="分享实用AI技巧，让你的工作效率翻倍，学完就能用",
                audience="想用AI提升工作效率的职场人士和学生",
                keywords=["AI技巧", "Prompt", "效率提升", "ChatGPT技巧", "AI实操"],
            ),
            Brief(
                link="{LINK}",
                selling_point="AI创意玩法大揭秘，你想不到的AI骚操作都在这里",
                audience="对AI感兴趣、喜欢探索新玩法的年轻人",
                keywords=["AI玩法", "创意", "AI绘画", "AI视频", "AI音乐"],
            ),
            Brief(
                link="{LINK}",
                selling_point="职场人必备的AI工作流，从写方案到做PPT全搞定",
                audience="每天被汇报、方案、PPT折磨的职场打工人",
                keywords=["职场AI", "写方案", "做PPT", "数据分析", "AI办公"],
            ),
        ]
    else:  # AI工具推荐
        return [
            Brief(
                link="{LINK}",
                selling_point="精选最好用的AI工具，零基础也能轻松上手",
                audience="AI小白、想入门但不知道用什么工具的人",
                keywords=["AI工具", "新手入门", "小白友好", "免费AI", "AI推荐"],
            ),
            Brief(
                link="{LINK}",
                selling_point="多款AI工具实测对比，帮你选出最适合的那个",
                audience="用过一些AI工具但想找到更好替代品的人",
                keywords=["AI对比", "工具测评", "ChatGPT", "Claude", "Gemini"],
            ),
            Brief(
                link="{LINK}",
                selling_point="不同场景下的最佳AI工具推荐，对号入座直接用",
                audience="有具体需求场景、想找到最佳AI解决方案的人",
                keywords=["AI写作", "AI绘画", "AI编程", "AI翻译", "场景推荐"],
            ),
        ]


def sanitize_name(text: str) -> str:
    return (
        text.replace("/", "_")
        .replace("\\", "_")
        .replace(" ", "_")
        .replace("：", "_")
        .replace(":", "_")
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", required=True, choices=["AI资讯", "AI使用技巧", "AI工具推荐"])
    parser.add_argument("--with-news", action="store_true", help="先抓取最新资讯，再基于真实新闻生成内容")
    args = parser.parse_args()

    if args.with_news:
        from app.news_pipeline import run_news_pipeline
        run_news_pipeline(max_articles=5, max_posts=3)
        return

    topic = args.topic
    briefs = build_briefs(topic)
    styles = pick_styles_for_topic(topic, count=3)

    send_telegram(f"📌 本轮自动生成主题：{topic}（共3条）")

    for idx, (brief, style) in enumerate(zip(briefs, styles), start=1):
        topic_with_style = f"{topic}|{style}"

        post_text = write_post(brief, topic=topic_with_style)
        titles_text = generate_titles(post_text, topic=topic, n=10)
        ranked = rank_titles(post_text, titles_text, top_k=3)

        safe_topic = sanitize_name(topic)
        safe_style = sanitize_name(style)

        saved_post = save_output(post_text, prefix=f"{safe_topic}_{safe_style}_xhs_{idx}")
        saved_titles = save_output(titles_text, prefix=f"{safe_topic}_{safe_style}_titles_generated_{idx}")
        saved_ranked = save_output(ranked, prefix=f"{safe_topic}_{safe_style}_titles_ranked_{idx}")

        send_telegram(f"✅【{topic}｜{style}｜第{idx}条 正文】\n\n" + post_text)
        send_telegram(f"✅【{topic}｜{style}｜第{idx}条 候选标题】\n\n" + titles_text)
        send_telegram(f"✅【{topic}｜{style}｜第{idx}条 标题Top3】\n\n" + ranked)

        send_telegram_file(saved_post, f"{topic}｜{style}｜第{idx}条 正文文件")
        send_telegram_file(saved_titles, f"{topic}｜{style}｜第{idx}条 候选标题文件")
        send_telegram_file(saved_ranked, f"{topic}｜{style}｜第{idx}条 标题评分文件")


if __name__ == "__main__":
    main()
