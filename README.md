# Codex Prompt：掘金 AI 技术周报生成器（请直接用本段作为输入）

你是资深 Python 工程师。请为我生成一个**可直接运行、可长期部署**的项目：  
**「掘金（Juejin）AI 领域内容的一周有用信息总结（周报）」**。

---

## 1. 目标

- 聚焦掘金上与 **人工智能相关的新技术、性能优化、系统架构、工具/框架**。
- 自动化：
  1) **每日采集**：抓取掘金内容（优先 RSSHub，其次 sitemap，最后标签列表页）。
  2) **入库去重**：写入 SQLite，按 URL hash 去重。
  3) **规则筛选**：过滤广告/水文/招聘/引流等。
  4) **每周周报**：聚合最近 7 天内容输出周报 Markdown。
  5) **可选 AI 总结**：如果环境变量提供 `OPENAI_API_KEY`，调用 OpenAI API 生成高质量周报；否则用本地规则生成「非 AI 版周报」。

---

## 2. 内容范围与筛选

### 2.1 AI 相关关键词（命中标题/标签/正文任一即可）
人工智能, AI, 大模型, LLM, AIGC, 机器学习, 深度学习,
Transformer, Diffusion, RAG, Agent,
推理, 训练, 微调, 部署, Serving,
vLLM, TensorRT, ONNX, Triton, CUDA,
量化, 蒸馏, LoRA,
性能, 延迟, 吞吐, QPS, 显存, 加速,
架构, 工程化, 可观测性, 多模型路由
### 2.2 排除关键词（命中即剔除）
招聘, 内推, 变现, 副业, 培训, 课程,
广告, 软文, 付费社群, 引流
### 2.3 质量门槛
- 正文提取后 **字数 < 600** 的默认认为低质量（可配置调整）
- 支持配置「作者白名单」（可选）

---

## 3. 数据源策略（按优先级实现，且可配置）

1) **RSSHub（优先）**
- 项目配置里允许填写多个 feed URL（RSSHub 掘金路由）。
- 采集器优先读取 RSS feeds：解析 title/link/published/summary。
- RSSHub 不可用时自动降级到下一策略。

2) **掘金 sitemap（次优）**
- 解析 sitemap XML 来发现文章 URL。
- 只抓取最近 7 天或最近 N 条（可配置）。
- 注意不要全量拉取所有 sitemap：支持配置最大 URL 数、最大 sitemap 数、超时与重试。

3) **标签列表页抓取（兜底）**
- 只在 RSSHub 与 sitemap 不可用时启用。
- 抓取掘金的 AI 相关标签页面（可配置多个标签页 URL），解析文章链接，再抓正文。
- 必须做频率控制（随机 sleep 0.5～1.5s）与重试。

---

## 4. 项目结构（请生成完整代码文件）

输出完整项目，结构如下：
.
├── README.md                  # 安装、配置、运行、部署（cron / systemd / Docker）说明
├── requirements.txt
├── config.example.yaml        # 或 .env.example（二选一即可，推荐 yaml）
├── data/                      # 运行时自动创建：db、输出、日志
└── src/
├── collector.py           # 采集（RSS / sitemap / HTML）
├── parser.py              # 正文提取（requests + BeautifulSoup），去脚本/样式/空白
├── store.py               # SQLite 表结构、去重（URL hash）、索引
├── filtering.py           # 关键词筛选、排除词、长度阈值、（可选）作者白名单
├── digest.py              # 周报生成（非 AI + AI）
├── notify.py              # 可选：输出到文件；如配置 SMTP 则邮件发送
├── cli.py                 # CLI 入口
└── init.py
---

## 5. CLI 需求（必须实现）

请实现命令行入口（任选其一：`python -m src.cli ...` 或 `python src/cli.py ...`），必须支持：

- `collect`：执行一次采集 + 解析正文 + 筛选 + 入库（用于每天跑）
- `digest --days 7`：生成最近 7 天周报到 `data/weekly.md`（非 AI）
- `digest --days 7 --ai`：
  - 如果存在 `OPENAI_API_KEY` → 使用 AI 总结
  - 如果不存在或调用失败 → 自动回退到非 AI 周报并提示
- `stats --days 7`：输出最近 N 天收录数、剔除数、Top 关键词命中统计等

---

## 6. AI 总结要求（可选功能，但请完整实现）

- 仅对**筛选后的条目**调用 AI（节省 token）。
- 固定输出格式（Markdown）：
  1) **本周概览**（3–5 条要点）
  2) **分组**：新技术/方法、性能优化/推理加速、架构与工程化、工具/框架（每组 3–8 条）
  3) 每条：标题 + 2–3 句摘要 + 原文链接
  4) **行动建议**：本周值得尝试的 3 件事
- 调用方式：使用官方 OpenAI Python SDK（新版本写法），从环境变量读取：
  - `OPENAI_API_KEY`
  - `OPENAI_MODEL`（默认 `gpt-4o-mini` 或同价位便宜模型）
- 设置超时与重试；失败不得崩溃，必须回退到非 AI 周报。

---

## 7. 抓取与稳定性要求（必须）

- requests 设置：
  - 合理 User-Agent
  - timeout（例如 10 秒）
  - 重试最多 3 次（指数退避）
- 同域请求简单限速：每次请求 sleep 0.5～1.5 秒随机
- 日志：`logging` 输出到控制台和 `data/app.log`

---

## 8. 输出要求

- 周报输出：
  - `data/weekly.md`
  - `data/weekly.json`（结构化字段：title, url, published, category, score, summary）
- README 中给出 cron 示例：
  - 每天执行一次 `collect`
  - 每周一上午生成周报（`digest --days 7 --ai` 或不带 `--ai`）

---

## 9. 交付标准

- 代码可直接运行
- 关键逻辑写清晰注释
- 提供最小配置示例（我只需要改 feed URL 或标签 URL 就能跑）
- 不要使用 Selenium/Playwright（除非完全没办法；优先 RSS/sitemap/HTTP 抓取）
- 请输出**整个项目的所有文件内容**，用清晰的文件分隔标记，例如：
FILE: README.md

…

FILE: requirements.txt

…

FILE: src/cli.py

…
确保我复制到本地后可以直接运行与部署。