# xiaohongshu-ai-agent

小红书 AI 资讯 & AI 使用技巧自动化内容生成 Agent。

## 功能

### 内容生成
- **AI资讯**：自动生成最新 AI 行业动态、大模型更新、产品发布等资讯内容
- **AI使用技巧**：生成 Prompt 技巧、工作流搭建、效率提升等实操干货
- **AI工具推荐**：生成 AI 工具推荐、对比测评、场景推荐等内容

### 资讯自动抓取（新增）
- **RSS 订阅**：自动从 OpenAI Blog、Google AI、MIT Tech Review、The Verge、Hugging Face 等获取最新文章
- **网页抓取**：自动从 36氪、量子位、机器之心等中文科技媒体抓取 AI 相关资讯
- **智能摘要**：使用 LLM 对每篇文章生成中文摘要、核心要点、价值评分
- **每日日报**：自动生成 AI 日报，按重要性排序，发送到 Telegram
- **原文链接**：所有原文链接会一并发送到 Telegram，方便查阅
- **自动去重**：已推送过的文章不会重复推送
- **内容联动**：可将高价值资讯自动转化为小红书风格的内容

## 内容生成流程

1. **写作 Agent**：根据 Brief 和主题风格生成小红书正文
2. **标题生成 Agent**：根据正文生成多个候选标题
3. **标题评审 Agent**：对候选标题打分并选出 Top3
4. **Telegram 推送**：将生成内容推送到 Telegram

## 资讯抓取流程

1. **抓取**：从 RSS 和网页源获取最新文章
2. **去重**：与历史记录对比，过滤已推送内容
3. **AI筛选**：只保留 AI 相关的文章
4. **摘要**：使用 LLM 生成中文摘要和核心要点
5. **日报**：汇总生成每日 AI 日报
6. **推送**：日报 + 原文链接发送到 Telegram
7. **内容生成**（可选）：将高价值文章转化为小红书内容

## 主题分类

| 主题 | 文风 |
|------|------|
| AI资讯 | 科技前沿 / 行业解读 / 产品测评 |
| AI使用技巧 | 效率提升 / 创意玩法 / 职场实战 |
| AI工具推荐 | 新手入门 / 深度对比 / 场景推荐 |

## 使用方式

### 资讯抓取（推荐日常使用）

```bash
# 抓取最新资讯 + 摘要 + 日报 → 推送到 Telegram
python -m app.news_pipeline

# 抓取资讯并同时生成小红书内容
python -m app.news_pipeline --generate-content

# 快速模式（跳过 LLM 摘要，只推送标题和链接）
python -m app.news_pipeline --no-summarize

# 控制摘要数量（节省 API 费用）
python -m app.news_pipeline --max-summarize 5
```

### 内容生成

```bash
# 单次运行
python -m app.main

# 批量生成（指定主题）
python -m app.batch_main --topic "AI资讯"
python -m app.batch_main --topic "AI使用技巧"
python -m app.batch_main --topic "AI工具推荐"

# 先抓取资讯，再基于真实新闻生成内容
python -m app.batch_main --topic "AI资讯" --with-news
```

### 自动定时运行

通过 GitHub Actions 自动运行：

- **资讯抓取**：每天 3 次（北京时间 09:00 / 13:00 / 21:00）
- **内容生成**：每天 3 次（北京时间 10:00 / 16:00 / 20:00），按时段轮换主题

## 资讯源

### RSS 源
- OpenAI Blog
- Google AI Blog
- MIT Technology Review - AI
- The Verge - AI
- Ars Technica - AI
- Hugging Face Blog
- Towards Data Science
- AI工具集

### 网页抓取
- 36氪 AI频道
- 量子位
- 机器之心

> 可在 `app/sources.py` 中自行添加或修改数据源。

## 环境变量

- `OPENAI_API_KEY`：OpenAI API 密钥
- `MODEL_NAME`：模型名称（默认 `gpt-4.1-mini`）
- `TEMPERATURE`：温度参数
- `TELEGRAM_BOT_TOKEN`：Telegram 机器人 Token
- `TELEGRAM_CHAT_ID`：Telegram 聊天 ID
