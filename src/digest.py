import json
import logging
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from openai import OpenAI

LOGGER = logging.getLogger(__name__)


CATEGORY_RULES = {
    "新技术/方法": ["llm", "aigc", "transformer", "diffusion", "agent", "rag"],
    "性能优化/推理加速": [
        "性能",
        "延迟",
        "吞吐",
        "qps",
        "加速",
        "tensorrt",
        "triton",
        "cuda",
        "vllm",
        "onnx",
    ],
    "架构与工程化": ["架构", "工程", "可观测", "部署", "serving"],
    "工具/框架": ["工具", "框架", "sdk", "库"],
}


def categorize_record(record: dict) -> str:
    content = " ".join(
        [
            record.get("title", ""),
            record.get("summary", ""),
            record.get("content", ""),
            " ".join(record.get("tags", [])),
        ]
    ).lower()
    for category, keywords in CATEGORY_RULES.items():
        if any(keyword.lower() in content for keyword in keywords):
            return category
    return "其他"


def render_non_ai_digest(records: list[dict]) -> tuple[str, list[dict]]:
    grouped = defaultdict(list)
    json_rows: list[dict] = []

    for record in records:
        category = categorize_record(record)
        grouped[category].append(record)
        json_rows.append(
            {
                "title": record.get("title"),
                "url": record.get("url"),
                "published": record.get("published"),
                "category": category,
                "score": len(record.get("matched_keywords", [])),
                "summary": record.get("summary") or "",
            }
        )

    lines = ["# 掘金 AI 周报", "", "## 本周概览", ""]
    lines.append(f"- 本周收录 {len(records)} 篇 AI 相关内容")
    lines.append("- 聚焦新技术、性能优化、架构工程与工具框架")
    lines.append("")

    for category, items in grouped.items():
        lines.append(f"## {category}")
        for record in items:
            summary = record.get("summary") or ""
            if not summary:
                summary = (record.get("content") or "")[:120] + "..."
            lines.append(f"- **{record.get('title') or '未命名'}**")
            lines.append(f"  - {summary}")
            lines.append(f"  - {record.get('url')}")
        lines.append("")

    lines.append("## 行动建议")
    lines.append("- 挑选 1~2 篇性能优化文章，尝试在当前项目中验证")
    lines.append("- 关注本周新出现的工具/框架，评估试用成本")
    lines.append("- 梳理一条可落地的架构优化思路")
    lines.append("")
    return "\n".join(lines), json_rows


def render_ai_digest(records: list[dict], model: str) -> str:
    client = OpenAI()
    content_lines = []
    for record in records:
        content_lines.append(
            f"标题：{record.get('title')}
链接：{record.get('url')}
摘要：{record.get('summary')}
正文：{record.get('content')[:600]}"
        )
    prompt = """你是资深 AI 技术编辑，请基于以下文章生成周报，输出 Markdown：

1) 本周概览（3-5 条要点）
2) 分组：新技术/方法、性能优化/推理加速、架构与工程化、工具/框架（每组 3-8 条）
3) 每条：标题 + 2-3 句摘要 + 原文链接
4) 行动建议：本周值得尝试的 3 件事

请直接输出 Markdown，不要附加其它解释。
"""
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "你是专业技术周报编辑"},
            {"role": "user", "content": prompt + "\n\n" + "\n\n".join(content_lines)},
        ],
        timeout=30,
    )
    return response.choices[0].message.content


def write_digest(data_dir: Path, markdown: str, json_rows: list[dict]) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "weekly.md").write_text(markdown, encoding="utf-8")
    (data_dir / "weekly.json").write_text(
        json.dumps(json_rows, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def generate_digest(records: list[dict], data_dir: Path, use_ai: bool, model: str) -> None:
    if not records:
        markdown = "# 掘金 AI 周报\n\n本周暂无符合条件的内容。\n"
        write_digest(data_dir, markdown, [])
        return

    if use_ai:
        try:
            markdown = render_ai_digest(records, model)
            json_rows = []
            write_digest(data_dir, markdown, json_rows)
            return
        except Exception as exc:
            LOGGER.warning("AI digest failed, fallback to non-AI: %s", exc)

    markdown, json_rows = render_non_ai_digest(records)
    write_digest(data_dir, markdown, json_rows)
    LOGGER.info("Digest generated at %s", datetime.utcnow().isoformat())
