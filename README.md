# 掘金 AI 技术周报生成器

本项目用于自动化收集掘金（Juejin）AI 领域的文章，并生成每周有价值信息的周报。支持 RSSHub / sitemap / 标签页多种采集策略，内置去重、关键词过滤、正文长度阈值与 AI 总结（可选）。

## 功能特性

- **每日采集**：优先 RSSHub，其次 sitemap，再到标签页抓取
- **去重入库**：SQLite 存储，基于 URL hash 去重
- **规则筛选**：关键词过滤、排除广告/招聘等低质量内容
- **周报输出**：生成 `data/weekly.md` 和 `data/weekly.json`
- **AI 总结**（可选）：配置 `OPENAI_API_KEY` 后输出高质量总结

## 目录结构

```
.
├── README.md
├── requirements.txt
├── config.example.yaml
├── data/
└── src/
    ├── collector.py
    ├── parser.py
    ├── store.py
    ├── filtering.py
    ├── digest.py
    ├── notify.py
    ├── cli.py
    └── __init__.py
```

## 安装

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 配置

复制并修改配置：

```bash
cp config.example.yaml config.yaml
```

主要配置项：

- `sources.rss_feeds`: RSSHub feed URL
- `sources.sitemap_urls`: 掘金 sitemap
- `sources.tag_urls`: 标签列表页
- `filtering.*`: 关键词、排除词、作者白名单
- `ai.model`: OpenAI 模型

如果需要 AI 总结，设置环境变量：

```bash
export OPENAI_API_KEY=YOUR_KEY
export OPENAI_MODEL=gpt-4o-mini
```

## 运行

### 采集（每日）

```bash
python -m src.cli collect
```

### 生成周报（非 AI）

```bash
python -m src.cli digest --days 7
```

### 生成周报（AI 优先）

```bash
python -m src.cli digest --days 7 --ai
```

### 统计信息

```bash
python -m src.cli stats --days 7
```

## 周报输出

- `data/weekly.md`
- `data/weekly.json`

## 部署建议

### Cron

每天采集一次：

```
0 9 * * * /path/to/python -m src.cli collect >> /path/to/data/cron.log 2>&1
```

每周一生成周报：

```
0 10 * * 1 /path/to/python -m src.cli digest --days 7 --ai >> /path/to/data/cron.log 2>&1
```

### Systemd

将命令写入 systemd service + timer，定时执行 `collect` 和 `digest`。

### Docker

可将本项目作为定时任务容器部署，使用 host 上的 cron 或定时触发器调用 CLI。

## 说明

- 若 RSSHub / sitemap 不可用，将自动降级到标签页抓取。
- 请求带有随机延迟并配置重试，避免频繁访问。
- AI 总结失败将自动回退到非 AI 周报。
