from pathlib import Path

from langchain_core.messages import SystemMessage, HumanMessage
from app.llm import get_llm
from app.tone_loader import load_tone_samples


def load_viral_title_patterns() -> str:
    path = Path("kb/title_patterns.txt")

    if path.exists():
        return path.read_text(encoding="utf-8")

    return """
常见爆款标题结构：

1
我一直以为X，结果Y

2
原来X真的会影响Y

3
难怪我总是X

4
第一次知道X还能这样

5
测完我沉默了

6
原来我不是X，是Y

7
难怪我恋爱总是这样

8
原来生日真的能看出性格

9
MBTI之外，我更震惊的是这个

10
一直解释不清的感觉，终于被说中了
"""


def build_topic_instruction(topic: str) -> str:

    if topic == "八字":
        return """
主题重点：
- 生日
- 生辰八字
- 五行
- 命理
- 性格
- 婚恋
- 事业
- 财富

标题风格：
神秘感 + 好奇心 + 自我探索

例如感觉：
原来生日真的会影响性格
难怪我总是这样想事情
"""
    elif topic == "MBTI":
        return """
主题重点：
- MBTI
- 人格类型
- 社交模式
- 情绪模式
- 职场关系

标题风格：
轻测试感 + 社交吐槽 + 共鸣

例如感觉：
MBTI之外我更震惊的是这个
难怪我总和别人聊不到一起
"""
    elif topic == "恋爱测试":
        return """
主题重点：
- 恋爱模式
- 依恋类型
- 情绪拉扯
- 关系内耗

标题风格：
闺蜜聊天 + 共鸣 + 情绪反差

例如感觉：
难怪我恋爱总是这样
原来我不是恋爱脑，是这个
"""
    else:
        return ""


def build_anti_repeat_rules() -> str:
    return """
防重复要求：

不要每次都用：
我一直以为...
原来...
难怪...

要多变化表达：

例如：
- 我后来才发现
- 一直解释不清的感觉
- 后来我去测了一个东西
- 突然有点理解自己了

不要让所有标题结构完全一样。
"""


def generate_titles(post_text: str, topic: str, n: int = 10) -> str:
    llm = get_llm()

    tone_samples = load_tone_samples(max_samples=5)

    title_patterns = load_viral_title_patterns()

    topic_instruction = build_topic_instruction(topic)

    anti_repeat_rules = build_anti_repeat_rules()

    system_prompt = f"""
你是一个非常懂小红书生态的标题创作者。

目标：
根据正文内容生成更容易点击的小红书标题。

标题特点：

- 有共鸣
- 有好奇心
- 有代入感
- 不像广告

不要：

❌ 标题党
❌ 夸张承诺
❌ “100%准确”
❌ “包准”

{topic_instruction}

可参考爆款标题结构：

{title_patterns}

{anti_repeat_rules}

标题长度：

10-20字最佳
"""

    user_prompt = f"""
这是正文内容：

---
{post_text}
---

这是语感样本：

---
{tone_samples}
---

请生成 {n} 个不同风格的标题。

输出格式：

1. 标题
2. 标题
3. 标题
...
"""

    msgs = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]

    return llm.invoke(msgs).content