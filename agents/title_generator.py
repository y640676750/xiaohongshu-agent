from pathlib import Path

from langchain_core.messages import SystemMessage, HumanMessage
from app.llm import get_llm
from app.tone_loader import load_tone_samples
from app.viral_memory import load_viral_memory


def load_viral_title_patterns() -> str:
    path = Path("kb/title_patterns.txt")

    if path.exists():
        return path.read_text(encoding="utf-8")

    return """
常见爆款标题结构：

1
用了这个AI工具，效率直接翻倍

2
原来AI还能这样用，后悔没早知道

3
这个AI技巧，帮我省了X小时

4
刚发布的AI工具，我先替你们试了

5
别再手动做XX了，AI一键搞定

6
AI圈又炸了，这次是真的强

7
实测X款AI工具，最好用的是这个

8
普通人用AI赚钱/提效的正确姿势

9
ChatGPT/Claude都不知道的隐藏技巧

10
这个AI玩法，90%的人还不知道
"""


def build_topic_instruction(topic: str) -> str:

    if topic == "AI资讯":
        return """
主题重点：
- 最新AI动态
- 大模型更新
- 行业趋势
- 技术突破
- 产品发布
- 政策变化

标题风格：
信息差 + 紧迫感 + 好奇心

例如感觉：
AI圈又出大事了
这个更新太重要了，赶紧看
"""
    elif topic == "AI使用技巧":
        return """
主题重点：
- Prompt技巧
- 工作流搭建
- 效率提升
- 具体操作方法
- 实用模板

标题风格：
干货感 + 效率对比 + 获得感

例如感觉：
学会这个技巧，效率翻10倍
用了这个方法，再也不加班了
"""
    elif topic == "AI工具推荐":
        return """
主题重点：
- 工具对比
- 使用场景
- 核心功能
- 适合人群
- 免费/付费

标题风格：
测评感 + 场景感 + 实用推荐

例如感觉：
实测5款AI写作工具，最好用的是这个
做PPT再也不求人了
"""
    else:
        return ""


def build_anti_repeat_rules() -> str:
    return """
防重复要求：

不要每次都用：
别再...了
原来...
这个AI工具...

要多变化表达：

例如：
- 我后来发现一个更好的方法
- 试了很多工具，最后留下的是这几个
- 朋友推荐的，用了真香
- 突然发现效率提升了好多

不要让所有标题结构完全一样。
"""


def generate_titles(post_text: str, topic: str, n: int = 10) -> str:
    llm = get_llm()
    patterns_path = Path("kb/title_patterns_learned.txt")

    learned_patterns = ""

    if patterns_path.exists():
        learned_patterns = patterns_path.read_text(encoding="utf-8")
    viral_memory = load_viral_memory()

    tone_samples = load_tone_samples(max_samples=5)

    title_patterns = load_viral_title_patterns()

    topic_instruction = build_topic_instruction(topic)

    anti_repeat_rules = build_anti_repeat_rules()

    system_prompt = f"""
你是一个非常懂小红书生态的AI科技内容标题创作者。

目标：
根据正文内容生成更容易点击的小红书标题。
以下是系统记录的一些高点击标题结构：

{viral_memory}

可以参考这些结构，但不要照抄。
以下是系统从真实爆款学习到的标题结构：

{learned_patterns}

请参考这些结构生成标题。

标题特点：

- 有信息增量
- 有好奇心
- 有实用感
- 不像广告

不要：

❌ 夸大AI能力
❌ "学了就能年薪百万"
❌ "AI替代所有人"
❌ 制造AI焦虑

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
