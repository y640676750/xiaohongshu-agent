from langchain_core.messages import SystemMessage, HumanMessage
from app.llm import get_llm
from app.tone_loader import load_tone_samples


def generate_titles(post_text: str, topic: str, n: int = 10) -> str:
    llm = get_llm()
    tone_samples = load_tone_samples(max_samples=5)

    system_prompt = f"""
你是小红书爆款标题生成器。

目标：
根据正文生成更像小红书原生风格、点击率更高的标题。

当前主题：
{topic}

你要优先学习这些高点击标题结构：
1. 我一直以为X，结果Y
2. 原来X真的会影响Y
3. 难怪我总是X
4. 测完我沉默了
5. 第一次知道X还能这样
6. 生日居然真的能看出X
7. 原来我不是X，是Y
8. 难怪我恋爱总是这样
9. MBTI之外，我更震惊的是这个
10. 一直解释不清的感觉，终于被说中了

标题要求：
- 每个标题尽量 10-20 字
- 更像小红书女生口语
- 有好奇心、共鸣、反差、代入感
- 不要太营销，不要像广告
- 不要“100%准确”“包准”“绝对”
- 不要过度玄学恐吓
- 可以适当使用：
  “原来 / 难怪 / 我一直以为 / 结果 / 居然 / 测完 / 第一次知道”

不同主题侧重点：
1. 八字命理：
   强调生日、八字、五行、性格、婚恋、事业、财富、自我了解
2. MBTI：
   强调人格、社交、情绪模式、职场关系、自我探索
3. 恋爱测试：
   强调恋爱脑、依恋、回避型、焦虑型、关系内耗、心动模式

输出格式必须严格如下：
1. 标题
2. 标题
3. 标题
...
"""

    user_prompt = f"""
这是正文内容：
---
{post_text}
---

这是你要学习语感的样本：
---
{tone_samples}
---

请根据正文和语感样本，生成 {n} 个标题。
"""

    msgs = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]
    return llm.invoke(msgs).content