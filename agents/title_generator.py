from langchain_core.messages import SystemMessage, HumanMessage
from app.llm import get_llm


def generate_titles(post_text: str, n: int = 10) -> str:
    llm = get_llm()

    system_prompt = f"""
你是小红书爆款标题生成器（闺蜜口吻 + 理性测评风格）。
任务：基于正文内容生成 {n} 个标题备选。

硬规则：
- 每个标题 10-20 字为主，中文自然口语
- 不能夸大承诺：禁用“100%准确/包准/保证/必然/立刻解决”
- 标题要有钩子：反差/好奇/共鸣/清单/理性测评
- 避免泛泛而谈（不要“测测你是哪种人”这种空话）
输出格式：
1) 标题
2) 标题
...
"""

    user_prompt = f"正文如下，请据此生成标题：\n\n{post_text}\n"
    msgs = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]
    return llm.invoke(msgs).content