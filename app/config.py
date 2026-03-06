import os

MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "openai")  # openai / deepseek 以后扩展
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4.1-mini")

TEMPERATURE = float(os.getenv("TEMPERATURE", "0.9"))