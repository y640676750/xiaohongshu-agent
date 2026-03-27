import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0.9)

system_prompt = """
你是小红书AI科技博主，专注分享最新AI资讯和实用AI技巧。
风格：专业干货70% + 亲切分享30%，避免夸大AI能力。
输出：5个标题 + 1篇正文 + 10个话题 + 1句置顶评论引导
"""

user_prompt = """
卖点：分享3个ChatGPT隐藏技巧，让你的使用效率翻倍
目标用户：想用AI提升工作效率但还不太会用的职场人
链接：{LINK}
"""

messages = [
    SystemMessage(content=system_prompt),
    HumanMessage(content=user_prompt),
]

print(llm.invoke(messages).content)
