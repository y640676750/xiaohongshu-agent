# MCP Server - Xiaohongshu AI Agent

把本项目的能力暴露成 [Model Context Protocol](https://modelcontextprotocol.io) 工具，任何 MCP 客户端 (Claude Desktop / Cursor / Continue / 自研客户端) 都可以远程驱动。

## 启动

```bash
pip install -r requirements.txt        # 含 mcp[cli]
python -m mcp_server.server            # stdio 模式（默认，用于桌面客户端）
python -m mcp_server.server --transport streamable-http --port 8765   # HTTP 模式
```

## 可调用工具

| 类别 | 工具 | 作用 |
| --- | --- | --- |
| 资讯 | `fetch_ai_news(max_items, analyze)` | 抓取去重最新 AI 资讯 |
| 资讯 | `rank_news(limit)` | 按 LLM 评分排序文章 |
| 写作 | `generate_xhs_post(topic, style, ...)` | 单步生成小红书文案 |
| 写作 | `generate_titles(post_text, topic, n)` | 生成 N 个候选标题 |
| 写作 | `rank_titles(post_text, titles_text, top_k)` | 标题打分排序 |
| 审稿 | `review_post(post_text)` | Critic Agent 打分（5 维 + 综合分） |
| 编排 | `run_full_pipeline(topic, style, ...)` | 跑完整多 Agent 流水线 |
| 发布 | `list_drafts(status, limit)` | 列出本地草稿 / 待发 / 已发 |
| 发布 | `schedule_post(post_id, scheduled_at)` | 安排定时发布 |
| 发布 | `publish_post(post_id)` | 立即发布 |
| 发布 | `publish_due(limit)` | 发布所有到期定时内容 |
| 发布 | `record_metrics(post_id, ...)` | 写入真实互动数据 |
| 分析 | `analytics_report(days)` | 完整 JSON 报告 |
| 分析 | `analytics_summary(days)` | 简版统计 |
| 分析 | `export_report(days, format)` | 导出 md/html/json 报告到 outputs/reports |

并暴露三个 MCP resources（只读）：

- `xhs://posts/recent` - 最近 30 条文案
- `xhs://analytics/summary` - 14 天数据汇总
- `xhs://articles/recent` - 近期抓取的资讯

## 在 Claude Desktop 中接入

把下面这段加入 `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) 或 `%APPDATA%\Claude\claude_desktop_config.json` (Windows)：

```json
{
  "mcpServers": {
    "xiaohongshu-agent": {
      "command": "python",
      "args": ["-m", "mcp_server.server"],
      "cwd": "/absolute/path/to/xiaohongshu-agent",
      "env": {
        "OPENAI_API_KEY": "sk-...",
        "MODEL_NAME": "gpt-4.1-mini",
        "XHS_DB_PATH": "/absolute/path/to/xiaohongshu-agent/kb/xhs_agent.db"
      }
    }
  }
}
```

## 在 Cursor 中接入

`Settings → MCP → Add` 后填：

```json
{
  "xiaohongshu-agent": {
    "command": "python",
    "args": ["-m", "mcp_server.server"],
    "cwd": "/absolute/path/to/xiaohongshu-agent"
  }
}
```

## HTTP 模式（自托管 / 远程调用）

```bash
python -m mcp_server.server --transport streamable-http --host 0.0.0.0 --port 8765
```

然后用任何支持 streamable-http 的客户端连接 `http://YOUR_HOST:8765/mcp`。

## 安全提示

- 所有写操作（保存草稿、发布、记录指标）都写在本地 SQLite，不会自动外泄
- `publish_post` 默认走 `mock` 后端（写 Markdown + 发 Telegram 通知）
- 想接真发布渠道，把 `XHS_PUBLISHER_BACKEND=webhook` 并配合 `XHS_PUBLISH_WEBHOOK`
