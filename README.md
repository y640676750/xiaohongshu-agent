# xiaohongshu-ai-agent

小红书 AI 资讯 & AI 使用技巧自动化内容生成 Agent。

## 功能

- **AI资讯**：自动生成最新 AI 行业动态、大模型更新、产品发布等资讯内容
- **AI使用技巧**：生成 Prompt 技巧、工作流搭建、效率提升等实操干货
- **AI工具推荐**：生成 AI 工具推荐、对比测评、场景推荐等内容

## 内容生成流程

1. **写作 Agent**：根据 Brief 和主题风格生成小红书正文
2. **标题生成 Agent**：根据正文生成多个候选标题
3. **标题评审 Agent**：对候选标题打分并选出 Top3
4. **Telegram 推送**：将生成内容推送到 Telegram

## 主题分类

| 主题 | 文风 |
|------|------|
| AI资讯 | 科技前沿 / 行业解读 / 产品测评 |
| AI使用技巧 | 效率提升 / 创意玩法 / 职场实战 |
| AI工具推荐 | 新手入门 / 深度对比 / 场景推荐 |

## 使用方式

### 单次运行

```bash
python -m app.main
```

### 批量生成（指定主题）

```bash
python -m app.batch_main --topic "AI资讯"
python -m app.batch_main --topic "AI使用技巧"
python -m app.batch_main --topic "AI工具推荐"
```

### 自动定时运行

通过 GitHub Actions 每天自动运行 3 次（北京时间 10:00 / 16:00 / 20:00），按时段轮换主题。

## 环境变量

- `OPENAI_API_KEY`：OpenAI API 密钥
- `MODEL_NAME`：模型名称（默认 `gpt-4.1-mini`）
- `TEMPERATURE`：温度参数
- `TELEGRAM_BOT_TOKEN`：Telegram 机器人 Token
- `TELEGRAM_CHAT_ID`：Telegram 聊天 ID
