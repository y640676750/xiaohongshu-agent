from pathlib import Path

from langchain_core.messages import SystemMessage, HumanMessage
from app.llm import get_llm
from app.tone_loader import load_tone_samples


def load_text(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def load_viral_structures(path: str = "kb/viral_structures.txt") -> str:
    p = Path(path)
    if not p.exists():
        return """
结构1：
开头一句强钩子（AI热点/痛点）
中间讲具体工具或技巧
结尾引导互动或收藏

结构2：
开头先抛一个"原来/没想到"式结论
中间演示实际效果
结尾加互动引导

结构3：
开头是一个效率痛点
中间对比手动 vs AI方案
结尾引导评论区讨论
"""
    return p.read_text(encoding="utf-8")


def parse_topic_and_style(topic: str) -> tuple[str, str]:
    if "|" in topic:
        base_topic, style = topic.split("|", 1)
        return base_topic.strip(), style.strip()
    return topic.strip(), "自然口语"


def build_topic_instruction(topic: str, style: str) -> str:
    if topic == "AI资讯":
        return f"""
当前文风：{style}

主题重点：
- 最新AI行业动态、大模型发布、产品更新
- 重点科普AI技术突破对普通人的影响
- 让读者快速了解"发生了什么""跟我有什么关系""我该怎么用"
- 用通俗易懂的语言解释技术概念

文风要求：
- 科技前沿：更强调"刚刚发布""重磅更新""行业地震"，制造信息差感
- 行业解读：更强调"这意味着什么""普通人怎么看懂""未来趋势"
- 产品测评：更强调"实测效果""对比体验""值不值得用"
"""
    elif topic == "AI使用技巧":
        return f"""
当前文风：{style}

主题重点：
- AI工具的实用技巧、Prompt技巧、工作流搭建
- 强调具体可操作的步骤和即时可用的方法
- 让读者看完就能上手实操

文风要求：
- 效率提升：更强调"省了X小时""以前要做一天，现在10分钟""效率翻倍"
- 创意玩法：更强调"没想到AI还能这样用""这个玩法太有意思了"
- 职场实战：更强调"汇报/PPT/数据分析/写方案，AI帮你搞定"
"""
    elif topic == "AI工具推荐":
        return f"""
当前文风：{style}

主题重点：
- 各类AI工具的推荐、对比、使用场景
- 帮助读者找到最适合自己的AI工具
- 突出工具的核心亮点和适用人群

文风要求：
- 新手入门：更强调"零基础也能用""手把手教你""小白友好"
- 深度对比：更强调"实测对比""各有优劣""选哪个看这篇就够了"
- 场景推荐：更强调"写论文用这个""做PPT用这个""不同场景最佳选择"
"""
    else:
        return f"当前文风：{style}"


def build_anti_duplicate_rules() -> str:
    return """
防重复要求：
- 不要总用同一种开头句式，例如不要每次都以"你还在手动..."开头
- 不要总用同一种结尾句式，例如不要每次都用"评论区告诉我"
- 不要每次都用同样的情绪词（如"震惊了""太强了""绝了"）
- 不要把语感样本里的原句直接改几个字后复用
- 标题和正文都尽量换一种表达角度
- 少一点模板腔，多一点真实分享感
"""


def write_post(brief, topic: str) -> str:
    llm = get_llm()
    system_prompt = load_text("prompts/writer_system.txt")
    tone_samples = load_tone_samples(max_samples=5)
    viral_structures = load_viral_structures()
    base_topic, style = parse_topic_and_style(topic)
    topic_instruction = build_topic_instruction(base_topic, style)
    anti_duplicate_rules = build_anti_duplicate_rules()

    user_prompt = f"""
当前主题：{base_topic}
当前文风：{style}

卖点：{brief.selling_point}
目标用户：{brief.audience}
关键词：{", ".join(brief.keywords)}
链接：{brief.link}

{topic_instruction}

下面是一些你要学习语感的小红书样本：
---
{tone_samples}
---

下面是可参考的爆款结构库：
---
{viral_structures}
---

请学习这些样本和结构的：
1. 开头钩子怎么写
2. 口语感和信息密度
3. 怎么自然引出工具/链接
4. 怎么加互动感和实用感
5. 怎么让内容更像真人分享的干货，而不是广告

{anti_duplicate_rules}

额外要求：
- 学风格，不要照抄
- 保持"专业干货70% + 亲切分享30%"
- 更适合AI工具推荐 / AI技巧分享 / AI资讯科普
- 避免夸大AI能力，例如"AI可以替代所有人""学了就能年薪百万"
- 少一点硬广，多一点"实测体验 / 效率对比 / 真实使用感受"
- 正文里要自然带出工具能力和使用方法，而不是生硬介绍
- 如果是AI资讯主题，要快速传达核心信息，让读者有信息增量
- 如果是AI使用技巧主题，要有具体步骤，让人看完就能用
- 如果是AI工具推荐主题，要有真实体验感和使用场景
- 不要输出解释，不要解释你为什么这么写

输出必须包含：
1）标题5个
2）正文1篇
3）话题标签10个
4）置顶评论引导1句
5）合规提醒若干条
"""

    msgs = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]
    return llm.invoke(msgs).content
