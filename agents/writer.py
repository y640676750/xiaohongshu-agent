from langchain_core.messages import SystemMessage, HumanMessage
from app.llm import get_llm

def load_text(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def write_post(brief) -> str:
    llm = get_llm()
    system_prompt = load_text("prompts/writer_system.txt")

    user_prompt = f"""
卖点：{brief.selling_point}
目标用户：{brief.audience}
关键词：{", ".join(brief.keywords)}
链接：{brief.link}
请严格按格式输出。
"""
    msgs = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]
    return llm.invoke(msgs).content