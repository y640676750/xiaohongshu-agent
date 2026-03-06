import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0.9)

system_prompt = """
你是小红书闺蜜型理性测评官，写心理/性格测试网站推广文案。
风格：闺蜜70% + 理性30%，避免夸大承诺。
输出：5个标题 + 1篇正文 + 10个话题 + 1句置顶评论引导
"""

user_prompt = """
卖点：一分钟测出你的依恋风格 + 给到相处建议
目标用户：恋爱容易内耗、关系敏感的人
链接：{LINK}
"""

messages = [
    SystemMessage(content=system_prompt),
    HumanMessage(content=user_prompt),
]

print(llm.invoke(messages).content)