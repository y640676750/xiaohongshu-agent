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
开头一句强钩子
中间讲自己的经历或情绪
结尾自然引导测试

结构2：
开头先抛一个“原来/难怪”式结论
中间解释原因
结尾加互动引导

结构3：
开头是很强的共鸣问题
中间列出几种典型表现
结尾引导用户去测
"""
    return p.read_text(encoding="utf-8")


def parse_topic_and_style(topic: str) -> tuple[str, str]:
    if "|" in topic:
        base_topic, style = topic.split("|", 1)
        return base_topic.strip(), style.strip()
    return topic.strip(), "自然口语"


def build_topic_instruction(topic: str, style: str) -> str:
    if topic == "八字":
        return f"""
当前文风：{style}

主题重点：
- 突出“生日 -> 生辰八字 -> AI命理解读”
- 重点强调：性格、五行、婚恋、事业、财富
- 写出“原来很多解释不清的东西，终于能看懂一点”的感觉
- 产品不是传统算命口吻，而是“更适合年轻人的 AI 命理分析”

文风要求：
- 神秘感：更强调“原来生日背后真有一套逻辑”“很多解释不清的感觉突然被说中了”
- 自我探索：更强调“把自己看懂一点”“原来我很多反应不是没来由的”
- 恋爱命理：更强调“为什么总在感情里反复”“婚恋倾向/关系模式”
"""
    elif topic == "MBTI":
        return f"""
当前文风：{style}

主题重点：
- 突出免费、轻量、适合分享
- 强调人格类型、社交模式、职场相处、自我认知
- 更偏年轻人口语和测试感

文风要求：
- 轻测试感：像“顺手测一下，结果挺有意思”
- 社交吐槽：更强调“为什么我和别人总聊不来/相处别扭”
- 职场共鸣：更强调“开会、同事沟通、情绪消耗、适合什么工作方式”
"""
    elif topic == "恋爱测试":
        return f"""
当前文风：{style}

主题重点：
- 强调恋爱模式、依恋风格、关系内耗、情绪拉扯
- 更适合闺蜜聊天式表达
- 更强调共鸣和情绪代入

文风要求：
- 闺蜜聊天：像闺蜜半夜聊天，口语更强、更亲近
- 内耗共鸣：更强调“为什么我总是想太多/患得患失/忍不住反复想”
- 关系反差：更强调“表面看起来很独立，结果一谈恋爱就不是这样”
"""
    else:
        return f"当前文风：{style}"


def build_anti_duplicate_rules() -> str:
    return """
防重复要求：
- 不要总用同一种开头句式，例如不要每次都以“我一直以为...”开头
- 不要总用同一种结尾句式，例如不要每次都用“测完回来告诉我”
- 不要每次都用同样的情绪词（如“沉默了”“震惊了”“太准了”）
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
2. 口语感和情绪表达
3. 怎么自然引出测试/链接
4. 怎么加互动感和代入感
5. 怎么让内容更像真人发的小红书，而不是广告

{anti_duplicate_rules}

额外要求：
- 学风格，不要照抄
- 保持“闺蜜70% + 理性30%”
- 更适合心理测试 / 性格测试 / 命理预测网站推广
- 避免夸张承诺，例如“100%准确”“包准”“保证有效”
- 少一点硬广，多一点“体验感 / 共鸣感 / 自我探索感”
- 正文里要自然带出产品能力，而不是生硬介绍
- 如果是八字主题，要自然写出“输入生日 -> 生成八字 -> AI解读”
- 如果是 MBTI 主题，要更轻、更适合分享
- 如果是恋爱测试主题，要更有关系感和情绪代入
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