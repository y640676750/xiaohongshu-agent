from app.notifier import send_telegram, send_telegram_file
from app.schema import Brief
from agents.writer import write_post
from agents.title_generator import generate_titles
from agents.title_ranker import rank_titles
from app.utils import save_output


def main():
    brief = Brief(
        link="{LINK}",
        selling_point="一分钟测出你的依恋风格 + 给到相处建议",
        audience="恋爱容易内耗、关系敏感、想更了解自己的人",
        keywords=["内耗", "依恋类型", "回避型", "焦虑型", "安全型"],
    )

    post_text = write_post(brief)
    print("\n【原始文案】\n")
    print(post_text)

    titles_text = generate_titles(post_text, n=10)
    print("\n【候选标题（生成）】\n")
    print(titles_text)

    ranked = rank_titles(post_text, titles_text, top_k=3)
    print("\n【标题评审（打分&Top3）】\n")
    print(ranked)

    saved_post = save_output(post_text, prefix="xhs")
    saved_titles = save_output(titles_text, prefix="titles_generated")
    saved_ranked = save_output(ranked, prefix="titles_ranked")

    # 推送 Telegram
    send_telegram("✅【小红书正文】\n\n" + post_text)
    send_telegram("✅【候选标题】\n\n" + titles_text)
    send_telegram("✅【标题Top3+评分】\n\n" + ranked)

    # 发送文件
    send_telegram_file(saved_post, "📎 正文文件")
    send_telegram_file(saved_titles, "📎 候选标题文件")
    send_telegram_file(saved_ranked, "📎 标题评分文件")


if __name__ == "__main__":
    main()