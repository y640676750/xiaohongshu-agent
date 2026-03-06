from langchain_openai import ChatOpenAI
from app.config import MODEL_NAME, TEMPERATURE

def get_llm():
    # 先只做 openai，后面你要接 deepseek 我再给你加 base_url
    return ChatOpenAI(model=MODEL_NAME, temperature=TEMPERATURE)