import argparse
import random

from app.schema import Brief
from agents.writer import write_post
from agents.title_generator import generate_titles
from agents.title_ranker import rank_titles
from app.utils import save_output
from app.notifier import send_telegram, send_telegram_file
from app.topic_styles import TOPIC_STYLES


def pick_styles_for_topic(topic: str, count: int = 3) -> list[str]:
    styles = TOPIC_STYLES.get(topic, ["自然口语"])
    if len(styles) >= count:
        return random.sample(styles, count)
    # 如果样式不够，就补齐
    result = []
    while len(result) < count:
        result.extend(styles)
    return result[:count]


def build_briefs(topic: str):
    if topic == "八字":
        return [
            Brief(
                link="{LINK}",
                selling_point="输入生日即可生成生辰八字，AI解析性格、五行、婚恋、事业、财富",
                audience="对命理、自我探索、恋爱和事业方向感兴趣的人",
                keywords=["生日", "生辰八字", "五行", "婚恋", "事业", "财富"],
            ),
            Brief(
                link="{LINK}",
                selling_point="通过生日快速生成八字分析，帮你从命理角度看懂自己",
                audience="喜欢测试、命理、性格分析的年轻女生",
                keywords=["八字", "性格", "五行", "命理", "自我了解"],
            ),
            Brief(
                link="{LINK}",
                selling_point="AI八字解析，一分钟了解你的命理性格和感情趋势",
                audience="想了解自己感情模式和事业方向的人",
                keywords=["感情", "命理", "八字", "事业", "性格"],
            ),
        ]
    elif topic == "MBTI":
        return [
            Brief(
                link="{LINK}",
                selling_point="免费 MBTI 性格测试，快速看懂自己的人格类型",
                audience="喜欢人格测试、社交分析、自我探索的人",
                keywords=["MBTI", "人格类型", "性格测试", "自我探索"],
            ),
            Brief(
                link="{LINK}",
                selling_point="AI 帮你解读 MBTI，看看你到底适合什么相处方式",
                audience="想更了解自己社交风格和职场模式的人",
                keywords=["MBTI", "社交", "职场", "性格"],
            ),
            Brief(
                link="{LINK}",
                selling_point="用 MBTI 看懂自己的情绪和关系模式",
                audience="想搞懂自己和别人相处方式的人",
                keywords=["MBTI", "关系模式", "情绪", "人格"],
            ),
        ]
    else:  # 恋爱测试
        return [
            Brief(
                link="{LINK}",
                selling_point="免费恋爱测试，看看你在感情里到底是什么类型",
                audience="恋爱容易内耗、敏感、想了解自己关系模式的人",
                keywords=["恋爱测试", "依恋类型", "内耗", "关系模式"],
            ),
            Brief(
                link="{LINK}",
                selling_point="测测你的恋爱脑指数和依恋风格",
                audience="总在感情里反复纠结的人",
                keywords=["恋爱脑", "依恋", "焦虑型", "回避型"],
            ),
            Brief(
                link="{LINK}",
                selling_point="看看你为什么总在恋爱里患得患失",
                audience="想更了解自己感情模式的女生",
                keywords=["恋爱", "患得患失", "关系", "测试"],
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
    parser.add_argument("--topic", required=True, choices=["八字", "MBTI", "恋爱测试"])
    args = parser.parse_args()

    topic = args.topic
    briefs = build_briefs(topic)
    styles = pick_styles_for_topic(topic, count=3)

    send_telegram(f"📌 本轮自动生成主题：{topic}（共3条）")

    for idx, (brief, style) in enumerate(zip(briefs, styles), start=1):
        # 把文风拼到 topic 里传给 writer，方便 writer 里做风格控制
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