from langchain_core.messages import SystemMessage, HumanMessage
from app.llm import get_llm


def rank_titles(post_text: str, titles_text: str, top_k: int = 3) -> str:
    llm = get_llm()

    system_prompt = f"""
你是小红书AI科技内容标题评审（更像编辑/增长负责人）。
任务：对候选标题打分并选出 Top{top_k}。

评分维度（每项0-10）：
- 点击欲望（好奇/信息差/实用感）
- 与正文匹配度（不标题党）
- 小红书语感（口语、轻、像人写的）
- 信息准确性（不夸大AI能力、不制造焦虑）

输出格式必须为：
【Top{top_k} 推荐】
1) 标题（总分x.x /10）- 1句理由
2) ...
3) ...

【其余备选评分】
- 标题A：x.x（一句短评）
- 标题B：x.x（一句短评）
...
"""

    user_prompt = f"""
正文：
{post_text}

候选标题：
{titles_text}

请按要求输出。
"""
    msgs = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]
    return llm.invoke(msgs).content
