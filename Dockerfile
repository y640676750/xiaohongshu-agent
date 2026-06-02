FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    XHS_DB_PATH=/data/xhs_agent.db

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

RUN mkdir -p /data outputs/reports outputs/published kb/news_archive

VOLUME ["/data"]
EXPOSE 8765

# Default: run the multi-agent pipeline once, generate a draft, and exit.
# Override with `docker run ... python -m mcp_server.server` to expose as MCP.
CMD ["python", "-m", "agents.orchestrator", "--skip-news", "--topic", "AI使用技巧"]
