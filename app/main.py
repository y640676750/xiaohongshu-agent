from app.notifier import send_telegram, send_telegram_file
from app.schema import Brief
from agents.writer import write_post
from agents.title_generator import generate_titles
from agents.title_ranker import rank_titles
from app.utils import save_output


def main():
    brief = Brief(
        link="{LINK}",
        selling_point="分享3个最实用的ChatGPT使用技巧，学完效率直接翻倍",
        audience="想用AI提升工作效率的职场人和学生",
        keywords=["ChatGPT", "AI技巧", "效率提升", "Prompt", "AI工具"],
    )

    post_text = write_post(brief, topic="AI使用技巧")
    print("\n【原始文案】\n")
    print(post_text)

    titles_text = generate_titles(post_text, topic="AI使用技巧", n=10)
    print("\n【候选标题（生成）】\n")
    print(titles_text)

    ranked = rank_titles(post_text, titles_text, top_k=3)
    print("\n【标题评审（打分&Top3）】\n")
    print(ranked)

    saved_post = save_output(post_text, prefix="xhs")
    saved_titles = save_output(titles_text, prefix="titles_generated")
    saved_ranked = save_output(ranked, prefix="titles_ranked")

    send_telegram("✅【小红书正文】\n\n" + post_text)
    send_telegram("✅【候选标题】\n\n" + titles_text)
    send_telegram("✅【标题Top3+评分】\n\n" + ranked)

    send_telegram_file(saved_post, "📎 正文文件")
    send_telegram_file(saved_titles, "📎 候选标题文件")
    send_telegram_file(saved_ranked, "📎 标题评分文件")


if __name__ == "__main__":
    main()
