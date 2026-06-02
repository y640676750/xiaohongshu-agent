# Xiaohongshu AI Agent

> 一个用 **LangGraph 多 Agent 协同 + MCP Server + 自动发帖 + 数据分析回路** 串起来的小红书 AI 资讯/技巧自动化创作系统。

[![Tests](https://github.com/y640676750/xiaohongshu-agent/actions/workflows/tests.yml/badge.svg)](https://github.com/y640676750/xiaohongshu-agent/actions/workflows/tests.yml)
[![Orchestrator](https://github.com/y640676750/xiaohongshu-agent/actions/workflows/orchestrate.yml/badge.svg)](https://github.com/y640676750/xiaohongshu-agent/actions/workflows/orchestrate.yml)
[![Analytics](https://github.com/y640676750/xiaohongshu-agent/actions/workflows/analytics.yml/badge.svg)](https://github.com/y640676750/xiaohongshu-agent/actions/workflows/analytics.yml)

---

## 一图看懂

```
                              ┌──────────────────────────────┐
                              │   MCP Server (FastMCP)       │   ← Claude / Cursor / 任意 MCP 客户端
                              │   tools/resources 全量暴露    │
                              └──────────────┬───────────────┘
                                             │
                                             ▼
   ┌───────────────────  LangGraph 多 Agent 协同  ──────────────────┐
   │                                                                │
   │  analyst → news_agent → writer → titler → critic               │
   │     ▲                                  │                       │
   │     │ 数据回路                          │ overall<7 → revise   │
   │     │                                  ▼                       │
   │     │                              publisher                   │
   └─────┴──────────────────────────────────┬────────────────────────┘
                                            ▼
                       ┌──────────────────────────────────────┐
                       │  自动发帖 (Mock / Webhook 后端可换)   │
                       │  草稿池 → 调度 → 发布 → 指标采集      │
                       └──────────────────┬───────────────────┘
                                          ▼
                       ┌──────────────────────────────────────┐
                       │  数据分析 (SQLite + 报告 md/html/json)│
                       │  topic 互动率 / Top 文案 / 趋势 / 建议│
                       └──────────────────────────────────────┘
```

## 核心能力

| 模块 | 文件 | 说明 |
| --- | --- | --- |
| 🤖 多 Agent 协同 | `agents/orchestrator.py` | LangGraph 编排 6 个 Agent：分析师/资讯/写手/标题/审稿/发布 |
| 🧠 Critic Agent | `agents/critic.py` | 5 维评分 + 综合分，无 API Key 时降级为启发式审稿 |
| 📊 数据分析 | `app/analytics.py`, `app/dashboard.py` | SQLite + 互动率/病毒分/趋势/推荐主题 + md/html/json 报告 |
| 🚀 自动发帖 | `app/publisher.py` | 草稿池 / 定时调度 / Mock 与 Webhook 双后端 |
| 🔌 MCP Server | `mcp_server/server.py` | 全功能以 MCP 工具/资源暴露，可被 Cursor、Claude Desktop 调用 |
| 📡 资讯抓取 | `app/news_fetcher.py`, `app/news_summarizer.py` | 8 RSS + 3 网页源，自动去重、LLM 打分 |
| ✍️ 内容生成 | `agents/writer.py`, `agents/title_generator.py` | 基于真实资讯生成小红书文案 + 标题 Top3 |
| 🔔 通知 | `app/notifier.py` | 文案/报告/事件分段推送 Telegram |
| 🗓️ 定时任务 | `.github/workflows/*.yml` | 资讯/编排/分析三套定时 + tests CI |

## 一键安装

```bash
git clone https://github.com/y640676750/xiaohongshu-agent.git
cd xiaohongshu-agent
pip install -r requirements.txt
cp .env.example .env       # 填入 OPENAI_API_KEY 等
```

## 五种用法

### 1. 一句话跑完整流水线（推荐）

```bash
python -m agents.orchestrator --topic "AI使用技巧" --skip-news
```

会自动：① 分析过往数据 → ② 抓资讯 / 跳过 → ③ 写正文 → ④ 生成标题 → ⑤ 审稿打分 → ⑥ 不达标自动改写 → ⑦ 落库为草稿（可选直接发布）。
所有事件都会被记录到 `events` 表，方便排查。

```bash
python -m agents.orchestrator --auto-publish                  # 写完直接走发布
python -m agents.orchestrator --schedule-minutes 30           # 30 分钟后再发
```

### 2. 资讯 → 小红书文案 → Telegram

```bash
python -m app.news_pipeline --max-articles 10 --max-posts 5
```

### 3. 按主题批量生成

```bash
python -m app.batch_main --topic "AI资讯"
python -m app.batch_main --topic "AI使用技巧"
python -m app.batch_main --topic "AI工具推荐"
```

### 4. 自动发帖（独立 CLI）

```bash
# 列出本地草稿
python -m app.publisher list

# 把草稿 12 安排到 20 分钟后发布
python -m app.publisher schedule 12 --in-minutes 20

# 立即发布草稿 12
python -m app.publisher publish 12

# 发布所有到期定时任务（适合放 CI 周期跑）
python -m app.publisher publish-due

# 写入真实互动数据（也可由 webhook backend 自动写入）
python -m app.publisher metrics 12 --impressions 5000 --likes 320 --comments 28 --collects 95
```

### 5. 数据分析报告

```bash
python -m app.dashboard --days 14                              # 生成 md + html + json
python -m app.dashboard --days 7  --telegram                   # 同时推送 Telegram 日报
```

报告输出到 `outputs/reports/`，HTML 直接浏览器打开。

## MCP Server

把整套能力变成 MCP 工具，让 Claude Desktop / Cursor / 任何 MCP 客户端直接驱动：

```bash
python -m mcp_server.server                 # stdio (默认，桌面客户端用)
python -m mcp_server.server --transport streamable-http --port 8765    # HTTP 模式
```

详细工具列表与接入方式见 [`mcp_server/README.md`](./mcp_server/README.md)。

### 暴露的 MCP 工具一览

| 类别 | 工具 |
| --- | --- |
| 资讯 | `fetch_ai_news`, `rank_news` |
| 写作 | `generate_xhs_post`, `generate_titles`, `rank_titles`, `review_post` |
| 编排 | `run_full_pipeline` |
| 发布 | `list_drafts`, `get_post`, `schedule_post`, `publish_post`, `publish_due`, `record_metrics` |
| 分析 | `analytics_report`, `analytics_summary`, `export_report` |

外加只读 resources：

- `xhs://posts/recent`
- `xhs://articles/recent`
- `xhs://analytics/summary`

## 数据模型

SQLite，无需额外服务：

| 表 | 字段（要点） |
| --- | --- |
| `articles` | url(unique), title, source, category, score, oneliner, fetched_at |
| `posts`    | topic, body, title, hashtags(json), status(draft/scheduled/published/failed), quality_score, scheduled_at, published_at |
| `metrics`  | post_id, impressions, likes, comments, shares, collects, follows |
| `events`   | run_id, agent, level, message, meta(json) - 多 Agent 全链路日志 |

默认路径：`kb/xhs_agent.db`，用 `XHS_DB_PATH` 覆盖。

## 自动发帖后端

| 后端 | env | 行为 |
| --- | --- | --- |
| `mock`（默认） | `XHS_PUBLISHER_BACKEND=mock` | 写入 `outputs/published/*.md` + Telegram 通知 + 生成模拟指标 |
| `webhook` | `XHS_PUBLISHER_BACKEND=webhook` + `XHS_PUBLISH_WEBHOOK=https://...` | POST 文案到自托管发布器（Playwright cookie 方案、xhs-cli、SDK 二开等）；返回 `{"id","url"}` |

> 小红书没有官方写入 API，因此真发布层通过 webhook 解耦。把账号 Cookie 留在你自己的 worker 里，主服务只负责生成与调度。

## 数据分析回路

`analyst_node` 每次启动时会读 `metrics` 表，得出：

- 各主题的互动率
- 历史 Top 标题（喂回 `title_generator` 作为爆款记忆）
- 下一轮建议主题（兼顾互动率与多样性）

再把摘要塞进 writer 的 system prompt，实现"**数据 → 内容 → 数据**"自循环。

## 定时任务（GitHub Actions）

| Workflow | 时间（北京时间） | 作用 |
| --- | --- | --- |
| `auto_news.yml` | 09:00 / 13:00 / 21:00 | 资讯 → 文案 → Telegram |
| `auto_post.yml` | 10:00 / 16:00 / 20:00 | 按主题轮换生成 |
| `orchestrate.yml` | 09:30 / 17:30 | 全链路多 Agent 协同（含审稿/改写/草稿/调度） |
| `analytics.yml` | 每周一 08:00 | 生成周报并推 Telegram |
| `tests.yml` | push / PR | 跑 pytest |

也支持手动触发，可在 workflow 输入页指定主题、文风、是否直接发布等。

## 环境变量速查

```dotenv
OPENAI_API_KEY=sk-...
MODEL_NAME=gpt-4.1-mini
TEMPERATURE=0.9

TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

XHS_PUBLISHER_BACKEND=mock              # 或 webhook
XHS_PUBLISH_WEBHOOK=                    # webhook 后端必填
XHS_PUBLISH_TOKEN=                      # 可选

XHS_DB_PATH=kb/xhs_agent.db

MCP_TRANSPORT=stdio                     # stdio / sse / streamable-http
MCP_HOST=127.0.0.1
MCP_PORT=8765
```

完整模板见 [`.env.example`](./.env.example)。

## 测试

```bash
pip install pytest
pytest -q
```

`tests/` 下覆盖：DB 层、analytics 聚合、publisher 流水线、Critic 启发式、所有模块的可导入性。**全部不依赖任何 API Key**。

## Docker

```bash
docker build -t xhs-agent .
docker run --rm -e OPENAI_API_KEY=... -v $PWD/data:/data xhs-agent
# 暴露 MCP HTTP:
docker run --rm -p 8765:8765 -e OPENAI_API_KEY=... xhs-agent \
  python -m mcp_server.server --transport streamable-http --host 0.0.0.0 --port 8765
```

## 项目结构

```
xiaohongshu-agent/
├── agents/                  # 各 Agent
│   ├── analyst.py           # 数据分析师
│   ├── critic.py            # 审稿
│   ├── orchestrator.py      # LangGraph 编排 ⭐
│   ├── title_generator.py
│   ├── title_ranker.py
│   ├── title_pattern_extractor.py
│   ├── performance_analyzer.py
│   └── writer.py
├── app/                     # 业务能力
│   ├── analytics.py         # 数据分析 ⭐
│   ├── dashboard.py         # 报告 md/html/json ⭐
│   ├── db.py                # SQLite 数据层 ⭐
│   ├── publisher.py         # 自动发帖 ⭐
│   ├── cli.py               # 统一 CLI
│   ├── news_fetcher.py
│   ├── news_pipeline.py
│   ├── news_summarizer.py
│   ├── notifier.py
│   ├── sources.py
│   └── ...
├── mcp_server/              # MCP Server ⭐
│   ├── server.py
│   └── README.md
├── kb/                      # 知识库 & 数据库
├── outputs/                 # 生成的文案 / 报告 / 已发布文件
├── prompts/
├── tests/                   # pytest
├── .github/workflows/       # 4 个 workflow
├── Dockerfile
└── README.md
```

## License

MIT.

## 致谢

- [Model Context Protocol](https://modelcontextprotocol.io)
- [LangGraph](https://github.com/langchain-ai/langgraph)
- 项目持续受小红书内容社区与开源 AI 工具链启发。
