# xiaohongshu-ai-agent

小红书 AI 资讯 & AI 使用技巧自动化内容生成 Agent。

## 核心功能

自动抓取最新AI资讯 → 筛选最有价值的文章 → 基于真实内容生成小红书引流文案 → 文案+原文链接推送到Telegram。

### 完整流程

```
RSS源(8个) + 网页源(3个)
       ↓
  抓取最新AI文章 + 去重
       ↓
  LLM分析：分类 + 打分 + 提取核心信息
       ↓
  筛选最有价值的文章
       ↓
  基于真实文章内容生成小红书引流文案
  （标题5个 + 正文 + 话题标签 + 评论引导）
       ↓
  推送到Telegram：文案 + 原文链接打包发送
```

### Telegram推送内容

每条推送包含：
- 📰 原文标题、来源、链接
- ✍️ 小红书引流文案（正文 + 标签）
- 🏆 推荐标题 Top3
- 📎 所有原文链接汇总

## 使用方式

### 资讯抓取 → 生成文案 → 推送（主要用法）

```bash
# 默认：分析5篇文章，生成3条文案
python -m app.news_pipeline

# 自定义数量
python -m app.news_pipeline --max-articles 10 --max-posts 5
```

### 纯内容生成（不抓取资讯）

```bash
python -m app.batch_main --topic "AI资讯"
python -m app.batch_main --topic "AI使用技巧"
python -m app.batch_main --topic "AI工具推荐"

# 先抓取资讯，再基于真实新闻生成
python -m app.batch_main --topic "AI资讯" --with-news
```

### 自动定时运行

| Workflow | 时间（北京时间） | 功能 |
|----------|-----------------|------|
| `auto_news.yml` | 09:00 / 13:00 / 21:00 | 抓取资讯 → 生成文案 → 推送Telegram |
| `auto_post.yml` | 10:00 / 16:00 / 20:00 | 按主题轮换生成小红书内容 |

## 数据源

### RSS (8个)
OpenAI Blog, Google AI Blog, MIT Technology Review, The Verge, Ars Technica, Hugging Face Blog, Towards Data Science, AI工具集

### 网页 (3个)
36氪 AI频道, 量子位, 机器之心

> 可在 `app/sources.py` 中自行添加或修改数据源。

## 主题分类

| 主题 | 文风 |
|------|------|
| AI资讯 | 科技前沿 / 行业解读 / 产品测评 |
| AI使用技巧 | 效率提升 / 创意玩法 / 职场实战 |
| AI工具推荐 | 新手入门 / 深度对比 / 场景推荐 |

## 环境变量

- `OPENAI_API_KEY`：OpenAI API 密钥
- `MODEL_NAME`：模型名称（默认 `gpt-4.1-mini`）
- `TEMPERATURE`：温度参数
- `TELEGRAM_BOT_TOKEN`：Telegram 机器人 Token
- `TELEGRAM_CHAT_ID`：Telegram 聊天 ID
