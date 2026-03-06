from langchain_core.messages import SystemMessage, HumanMessage
from app.llm import get_llm
from app.tone_loader import load_tone_samples


def load_text(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def build_topic_instruction(topic: str) -> str:
    if topic == "八字":
        return """
重点写法：
- 突出“生日 -> 生辰八字 -> AI命理解读”
- 重点强调：性格、五行、婚恋、事业、财富
- 要写出“原来很多解释不清的东西，终于能看懂一点”的感觉
- 语气更偏“好奇 + 自我探索”
"""
    elif topic == "MBTI":
        return """
重点写法：
- 突出免费、轻量、适合分享
- 强调人格类型、社交模式、职场相处、自我认知
- 更偏年轻人口语和测试感
"""
    elif topic == "恋爱测试":
        return """
重点写法：
- 强调恋爱模式、依恋风格、关系内耗、情绪拉扯
- 更适合闺蜜聊天式表达
- 更强调共鸣和情绪代入
"""
    else:
        return ""


def write_post(brief, topic: str) -> str:
    llm = get_llm()
    system_prompt = load_text("prompts/writer_system.txt")
    tone_samples = load_tone_samples(max_samples=5)
    topic_instruction = build_topic_instruction(topic)

    user_prompt = f"""
当前主题：{topic}

卖点：{brief.selling_point}
目标用户：{brief.audience}
关键词：{", ".join(brief.keywords)}
链接：{brief.link}

{topic_instruction}

下面是一些你要学习语感的小红书样本：
---
{tone_samples}
---

请学习这些样本的：
1. 开头钩子怎么写
2. 口语感和情绪表达
3. 怎么自然引出测试/链接
4. 怎么加互动感和代入感

要求：
- 学风格，不要照抄
- 保持“闺蜜70% + 理性30%”
- 更适合心理测试/性格测试/命理预测网站推广
- 避免夸张承诺，例如“100%准确”“包准”“保证有效”
- 输出必须包含：
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